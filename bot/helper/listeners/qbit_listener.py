from asyncio import sleep, gather
from os import path as ospath
from time import time

from bot import (
    bot_loop,
    task_dict,
    task_dict_lock,
    Intervals,
    config_dict,
    QbTorrents,
    qb_listener_lock,
    get_client,
    LOGGER,
)
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task
from bot.helper.ext_utils.files_utils import clean_unwanted, clean_target
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time,
    getTaskByGid,
)
from bot.helper.ext_utils.task_manager import stop_duplicate_check, check_limits_size
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import update_status_message


async def _remove_torrent(client, hash_, tag):
    await sync_to_async(client.torrents_delete, torrent_hashes=hash_, delete_files=True)
    async with qb_listener_lock:
        QbTorrents.pop(tag, None)
    await sync_to_async(client.torrents_delete_tags, tags=tag)


@new_task
async def _onDownloadError(err, tor, listfile=None):
    LOGGER.info("Cancelling Download: %s", tor.name)
    ext_hash = tor.hash
    task = await getTaskByGid(ext_hash[:12])
    if hasattr(task, "client"):
        await gather(
            task.listener.onDownloadError(err, listfile),
            sync_to_async(task.client.torrents_pause, torrent_hashes=ext_hash),
        )
        await sleep(0.3)
        await _remove_torrent(task.client, ext_hash, tor.tags)


@new_task
async def _onSeedFinish(tor):
    ext_hash = tor.hash
    LOGGER.info("Cancelling Seed: %s", tor.name)
    task = await getTaskByGid(ext_hash[:12])
    if hasattr(task, "client"):
        await gather(
            task.listener.onUploadError(
                f"Seeding stopped with Ratio {round(tor.ratio, 3)} ({get_readable_time(tor.seeding_time)})"
            ),
            _remove_torrent(task.client, ext_hash, tor.tags),
        )


@new_task
async def _stop_duplicate(tor):
    task = await getTaskByGid(tor.hash[:12])
    if hasattr(task, "listener"):
        task.listener.name = tor.content_path.rsplit("/", 1)[-1].rsplit(".!qB", 1)[0]
        file, name = await stop_duplicate_check(task.listener)
        if file:
            task.listener.name = name
            LOGGER.info("File/folder already in Drive!")
            _onDownloadError("File/folder already available in Drive.", tor, file)


@new_task
async def _download_limits(tor):
    task = await getTaskByGid(tor.hash[:12])
    if hasattr(task, "listener") and (
        msg := await check_limits_size(task.listener, tor.size)
    ):
        LOGGER.info("File/folder size over the limit size!")
        _onDownloadError(
            f"{msg}. File/folder size is {get_readable_file_size(tor.size)}.", tor
        )


@new_task
async def _onDownloadComplete(tor):
    ext_hash = tor.hash
    tag = tor.tags
    await sleep(2)
    task = await getTaskByGid(ext_hash[:12])
    if hasattr(task, "client"):
        if not task.listener.seed:
            await sync_to_async(task.client.torrents_pause, torrent_hashes=ext_hash)
        if task.listener.select:
            await clean_unwanted(task.listener.dir)
            path = tor.content_path.rsplit("/", 1)[0]
            res = await sync_to_async(task.client.torrents_files, torrent_hash=ext_hash)
            for f in res:
                if f.priority == 0:
                    await clean_target(ospath.join(path, f.name))
        await task.listener.onDownloadComplete()
        client = await sync_to_async(get_client)
        if task.listener.seed:
            async with task_dict_lock:
                if task.listener.mid in task_dict:
                    removed = False
                    task_dict[task.listener.mid] = QbittorrentStatus(
                        task.listener, True
                    )
                else:
                    removed = True
            if removed:
                await _remove_torrent(client, ext_hash, tag)
                return
            async with qb_listener_lock:
                if tag in QbTorrents:
                    QbTorrents[tag]["seeding"] = True
                else:
                    return
            LOGGER.info("Seeding started: %s - Hash: %s", tor.name, ext_hash)
            await gather(
                update_status_message(task.listener.message.chat.id),
                sync_to_async(client.auth_log_out),
            )
        else:
            await _remove_torrent(client, ext_hash, tag)


async def _qb_listener():
    client = await sync_to_async(get_client)
    TORRENT_TIMEOUT = config_dict["TORRENT_TIMEOUT"]
    STOP_DUPLICATE = config_dict["STOP_DUPLICATE"]
    while True:
        async with qb_listener_lock:
            try:
                if len(await sync_to_async(client.torrents_info)) == 0:
                    Intervals["qb"] = ""
                    await sync_to_async(client.auth_log_out)
                    return
                for tor_info in await sync_to_async(client.torrents_info):
                    tag = tor_info.tags
                    if tag not in QbTorrents:
                        continue
                    state = tor_info.state
                    if state == "metaDL":
                        QbTorrents[tag]["stalled_time"] = time()
                        if (
                            TORRENT_TIMEOUT
                            and time() - tor_info.added_on >= TORRENT_TIMEOUT
                        ):
                            _onDownloadError("Dead torrent!", tor_info)
                        else:
                            await sync_to_async(
                                client.torrents_reannounce, torrent_hashes=tor_info.hash
                            )
                    elif state == "downloading":
                        QbTorrents[tag]["stalled_time"] = time()
                        if STOP_DUPLICATE and not QbTorrents[tag]["stop_dup_check"]:
                            QbTorrents[tag]["stop_dup_check"] = True
                            _stop_duplicate(tor_info)
                        if not QbTorrents[tag]["limit_check"]:
                            QbTorrents[tag]["limit_check"] = True
                            _download_limits(tor_info)
                    elif state == "stalledDL":
                        if (
                            not QbTorrents[tag]["rechecked"]
                            and 0.99989999999999999 < tor_info.progress < 1
                        ):
                            msg = f"Force recheck - Name: {tor_info.name} Hash: {tor_info.hash} Downloaded Bytes: {tor_info.downloaded} Size: {tor_info.size} Total Size: {tor_info.total_size}"
                            LOGGER.warning(msg)
                            await sync_to_async(
                                client.torrents_recheck, torrent_hashes=tor_info.hash
                            )
                            QbTorrents[tag]["rechecked"] = True
                        elif (
                            TORRENT_TIMEOUT
                            and time() - QbTorrents[tag]["stalled_time"]
                            >= TORRENT_TIMEOUT
                        ):
                            _onDownloadError("Dead torrent!", tor_info)
                        else:
                            await sync_to_async(
                                client.torrents_reannounce, torrent_hashes=tor_info.hash
                            )
                    elif state == "missingFiles":
                        await sync_to_async(
                            client.torrents_recheck, torrent_hashes=tor_info.hash
                        )
                    elif state == "error":
                        _onDownloadError(
                            "No enough space for this torrent on device", tor_info
                        )
                    elif (
                        tor_info.completion_on != 0
                        and not QbTorrents[tag]["uploaded"]
                        and state
                        not in ["checkingUP", "checkingDL", "checkingResumeData"]
                    ):
                        QbTorrents[tag]["uploaded"] = True
                        _onDownloadComplete(tor_info)
                    elif (
                        state in ["pausedUP", "pausedDL"] and QbTorrents[tag]["seeding"]
                    ):
                        QbTorrents[tag]["seeding"] = False
                        _onSeedFinish(tor_info)
            except Exception as e:
                LOGGER.error(e)
                client = await sync_to_async(get_client)
        await sleep(3)


async def onDownloadStart(tag):
    async with qb_listener_lock:
        QbTorrents[tag] = {
            "stalled_time": time(),
            "stop_dup_check": False,
            "limit_check": False,
            "rechecked": False,
            "uploaded": False,
            "seeding": False,
        }
        if not Intervals["qb"]:
            Intervals["qb"] = bot_loop.create_task(_qb_listener())
