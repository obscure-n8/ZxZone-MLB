from __future__ import annotations
from aiofiles.os import path as aiopath
from time import time
from asyncio import gather

from bot import (
    task_dict,
    task_dict_lock,
    config_dict,
    non_queued_dl,
    queue_dict_lock,
    get_client,
    LOGGER,
)
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.task_manager import check_running_tasks
from bot.helper.listeners import tasks_listener as task
from bot.helper.listeners.qbit_listener import onDownloadStart
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    deleteMessage,
    sendStatusMessage,
    sendingMessage,
)


async def add_qb_torrent(
    listener: task.TaskListener, path: str, ratio: int, seed_time: int
):
    client = await sync_to_async(get_client)
    ADD_TIME = time()
    try:
        url = listener.link
        tpath = None
        if await aiopath.exists(listener.link):
            url = None
            tpath = listener.link
        add_to_queue, event = await check_running_tasks(listener.mid)
        op = await sync_to_async(
            client.torrents_add,
            url,
            tpath,
            path,
            is_paused=add_to_queue,
            tags=f"{listener.mid}",
            ratio_limit=ratio,
            seeding_time_limit=seed_time,
            headers={"user-agent": "Wget/1.12"},
        )
        if op.lower() == "ok.":
            tor_info = await sync_to_async(client.torrents_info, tag=f"{listener.mid}")
            if len(tor_info) == 0:
                while True:
                    tor_info = await sync_to_async(
                        client.torrents_info, tag=f"{listener.mid}"
                    )
                    if len(tor_info) > 0:
                        break
                    if time() - ADD_TIME >= 120:
                        msg = "Not added! Check if the link is valid or not. If it's torrent file then report, this happens if torrent file size above 10mb."
                        await listener.onDownloadError(msg)
                        return
            tor_info = tor_info[0]
            listener.name = tor_info.name
            ext_hash = tor_info.hash
        else:
            await listener.onDownloadError(
                "This Torrent already added or unsupported/invalid link/file.",
                listener.message,
            )
            return
        async with task_dict_lock:
            task_dict[listener.mid] = QbittorrentStatus(listener, queued=add_to_queue)
        await onDownloadStart(f"{listener.mid}")
        if add_to_queue:
            LOGGER.info(
                "Added to Queue/Download: %s - Hash: %s", tor_info.name, ext_hash
            )
        else:
            async with queue_dict_lock:
                non_queued_dl.add(listener.mid)
            LOGGER.info("QbitDownload started: %s - Hash: %s", tor_info.name, ext_hash)
        await listener.onDownloadStart()
        if config_dict["BASE_URL"] and listener.select:
            if listener.link.startswith("magnet:"):
                metamsg = "<i>Downloading <b>Metadata</b>, please wait...</i>"
                meta = await sendMessage(metamsg, listener.message)
                while True:
                    tor_info = await sync_to_async(
                        client.torrents_info, tag=f"{listener.mid}"
                    )
                    if len(tor_info) == 0:
                        await deleteMessage(meta)
                        return
                    try:
                        tor_info = tor_info[0]
                        if tor_info.state not in [
                            "metaDL",
                            "checkingResumeData",
                            "pausedDL",
                        ]:
                            await deleteMessage(meta)
                            break
                    except:
                        await deleteMessage(meta)
                        return
            ext_hash = tor_info.hash
            if not add_to_queue:
                await sync_to_async(client.torrents_pause, torrent_hashes=ext_hash)
            SBUTTONS = bt_selection_buttons(ext_hash)
            msg = f"<code>{tor_info.name}</code>\n\n{listener.tag}, your download paused. Choose files then press <b>Done Selecting</b> button to start downloading."
            await sendingMessage(
                msg, listener.message, config_dict["IMAGE_PAUSE"], SBUTTONS
            )
        elif listener.multi <= 1:
            await sendStatusMessage(listener.message)
        if add_to_queue:
            await event.wait()
            async with task_dict_lock:
                if listener.mid not in task_dict:
                    return
                task_dict[listener.mid].queued = False
            await sync_to_async(client.torrents_resume, torrent_hashes=ext_hash)
            LOGGER.info(
                "Start Queued Download from Qbittorrent: %s - Hash: %s",
                tor_info.name,
                ext_hash,
            )
            async with queue_dict_lock:
                non_queued_dl.add(listener.mid)
    except Exception as e:
        await listener.onDownloadError(e)
    finally:
        await gather(clean_target(listener.link), sync_to_async(client.auth_log_out))
