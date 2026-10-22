from asyncio import sleep
from time import time

from bot import QbTorrents, qb_listener_lock, get_client, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.status_utils import (
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
)


def get_download(client, tag, old_info=None):
    try:
        return client.torrents_info(tag=tag)[0]
    except Exception as e:
        LOGGER.error("%s: Qbittorrent, while getting torrent info. Tag: %s", e, tag)
        return old_info


class QbittorrentStatus:
    def __init__(self, listener, seeding=False, queued=False):
        self.listener = listener
        self.queued = queued
        self.seeding = seeding
        self.client = get_client()
        self._info = None
        self._elapsed = time()

    @staticmethod
    def engine():
        return "qBittorrent"

    def _update(self, attempt=0):
        if new_info := get_download(self.client, f"{self.listener.mid}"):
            self._info = new_info
        elif attempt < 3:
            return self._update(attempt + 1)

    def elapsed(self):
        return get_readable_time(time() - self._elapsed)

    def progress(self):
        return f"{round(self._info.progress * 100, 2)}%"

    def processed_bytes(self):
        return get_readable_file_size(self._info.downloaded)

    def speed(self):
        return f"{get_readable_file_size(self._info.dlspeed)}/s"

    def name(self):
        return (
            f"[METADATA]{self._info.name}"
            if self._info.state in ("metaDL", "checkingResumeData")
            else self._info.name
        )

    def size(self):
        return get_readable_file_size(self._info.size)

    def eta(self):
        return get_readable_time(self._info.eta)

    def status(self):
        self._update()
        state = self._info.state
        if state == "queuedDL" or self.queued:
            return MirrorStatus.STATUS_QUEUEDL
        if state == "queuedUP":
            return MirrorStatus.STATUS_QUEUEUP
        if state in ("pausedDL", "pausedUP"):
            return MirrorStatus.STATUS_PAUSED
        if state in ("checkingUP", "checkingDL"):
            return MirrorStatus.STATUS_CHECKING
        if state in ("stalledUP", "uploading") and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self):
        return self._info.num_seeds

    def leechers_num(self):
        return self._info.num_leechs

    def uploaded_bytes(self):
        return get_readable_file_size(self._info.uploaded)

    def upload_speed(self):
        return f"{get_readable_file_size(self._info.upspeed)}/s"

    def ratio(self):
        return f"{round(self._info.ratio, 3)}"

    def seeding_time(self):
        return get_readable_time(self._info.seeding_time)

    def task(self):
        return self

    def gid(self):
        return self.hash()[:12]

    def hash(self):
        self._update()
        return self._info.hash

    async def cancel_task(self):
        await sync_to_async(self._update)
        await sync_to_async(self.client.torrents_pause, torrent_hashes=self._info.hash)
        if not self.seeding:
            if self.queued:
                LOGGER.info("Cancelling QueueDL: %s", self.name())
                msg = "Task have been removed from queue/download"
            else:
                LOGGER.info("Cancelling Download: %s", self._info.name)
                msg = "Download stopped by user!"
            await sleep(0.3)
            await self.listener.onDownloadError(msg)
            await sync_to_async(
                self.client.torrents_delete,
                torrent_hashes=self._info.hash,
                delete_files=True,
            )
            await sync_to_async(self.client.torrents_delete_tags, tags=self._info.tags)
            async with qb_listener_lock:
                QbTorrents.pop(self._info.tags, None)
