from time import time

from bot import LOGGER, VID_MODE
from bot.helper.ext_utils.bot_utils import async_to_sync
from bot.helper.ext_utils.files_utils import get_path_size
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    MirrorStatus,
    get_readable_time,
)


class FFMpegStatus:
    def __init__(self, listener, obj, gid, status):
        self._gid = gid
        self._obj = obj
        self._status = status
        self._time = time()
        self.listener = listener

    @staticmethod
    def engine():
        return "FFmpeg"

    def elapsed(self):
        return get_readable_time(time() - self._time)

    def processed_bytes(self):
        return get_readable_file_size(self._obj.processed_bytes)

    def gid(self):
        return self._gid

    def progress(self):
        if self._status != "direct":
            return self._obj.percentage
        try:
            progress_raw = self._obj.processed_bytes / self._obj.size * 100
        except:
            progress_raw = 0
        return f"{round(progress_raw, 2)}%"

    def speed(self):
        return f"{get_readable_file_size(self._obj.speed)}/s"

    def name(self):
        return self._obj.name if self._obj else self.listener.name

    def size(self):
        size = (
            self._obj.size
            if self._obj
            else async_to_sync(get_path_size, self.listener.dir)
        )
        return get_readable_file_size(size)

    def timeout(self):
        return get_readable_time(180 - (time() - self._time))

    def eta(self):
        if self._status != "direct":
            return get_readable_time(self._obj.eta)
        try:
            return get_readable_time(
                (self._obj.size - self._obj.processed_bytes) / self._obj.speed
            )
        except:
            return "~"

    def status(self):
        match self._status:
            case "meta":
                return MirrorStatus.STATUS_METADATA
            case "sv":
                return MirrorStatus.STATUS_SAMVID
            case "wait":
                return MirrorStatus.STATUS_WAIT

        match self._obj.mode:
            case "vid_vid" | "vid_aud" | "vid_sub":
                return MirrorStatus.STATUS_MERGING
            case "convert":
                return MirrorStatus.STATUS_CONVERT
            case "subsync":
                return MirrorStatus.STATUS_SUBSYNC
            case "compress":
                return MirrorStatus.STATUS_COMPRESS
            case "trim":
                return MirrorStatus.STATUS_TRIM
            case "watermark":
                return MirrorStatus.STATUS_WATERMARK
            case "rmstream":
                return MirrorStatus.STATUS_RMSTREAM
            case _:
                return MirrorStatus.STATUS_EXTRACTING

    def task(self):
        return self

    async def cancel_task(self):
        match self._status:
            case "sv":
                info = "Creating sample video"
            case "meta":
                info = "Edit metadata"
            case _:
                info = VID_MODE[self._obj.mode]

        LOGGER.info("Cancelling %s: %s", info, self.name())
        if self.listener.suproc and self.listener.suproc.returncode is None:
            self.listener.suproc.kill()
        else:
            self.listener.suproc = "cancelled"
        await self.listener.onUploadError(f"{info} stopped by user!")
