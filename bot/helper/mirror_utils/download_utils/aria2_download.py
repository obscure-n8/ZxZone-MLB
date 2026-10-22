from __future__ import annotations

from bot import (
    aria2,
    aria2_options,
    aria2c_global,
    task_dict,
    task_dict_lock,
    config_dict,
    non_queued_dl,
    queue_dict_lock,
    LOGGER,
)
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.task_manager import check_running_tasks
from bot.helper.listeners import tasks_listener as task
from bot.helper.mirror_utils.status_utils.aria_status import Aria2Status
from bot.helper.telegram_helper.message_utils import sendStatusMessage, sendingMessage


async def add_aria2c_download(
    listener: task.TaskListener, dpath: str, header: str, ratio: int, seed_time: int
):
    a2c_opt = {**aria2_options}
    [a2c_opt.pop(k) for k in aria2c_global if k in aria2_options]
    a2c_opt["dir"] = dpath
    a2c_opt["user-agent"] = (
        "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Mobile Safari/537.36"
    )
    if listener.name:
        a2c_opt["out"] = listener.name
    if header:
        a2c_opt["header"] = header
    if ratio:
        a2c_opt["seed-ratio"] = ratio
    if seed_time:
        a2c_opt["seed-time"] = seed_time
    if TORRENT_TIMEOUT := config_dict["TORRENT_TIMEOUT"]:
        a2c_opt["bt-stop-timeout"] = f"{TORRENT_TIMEOUT}"
    add_to_queue, event = await check_running_tasks(listener.mid)
    if add_to_queue:
        if listener.link.startswith("magnet:"):
            a2c_opt["pause-metadata"] = "true"
        else:
            a2c_opt["pause"] = "true"
    try:
        download = (await sync_to_async(aria2.add, listener.link, a2c_opt))[0]
    except Exception as e:
        LOGGER.info("Aria2c Download Error: %s", e)
        await listener.onDownloadError(e)
        return
    await clean_target(listener.link)
    if download.error_message:
        error = str(download.error_message).replace("<", " ").replace(">", " ")
        LOGGER.info("Aria2c Download Error: %s", error)
        await listener.onDownloadError(error)
        return
    name, gid = download.name, download.gid
    async with task_dict_lock:
        task_dict[listener.mid] = Aria2Status(listener, gid, queued=add_to_queue)
    if add_to_queue:
        LOGGER.info("Added to Queue/Download: %s. Gid: %s", name, gid)
        if (not listener.select or not download.is_torrent) and listener.multi <= 1:
            await sendStatusMessage(listener.message)
    else:
        async with queue_dict_lock:
            non_queued_dl.add(listener.mid)
        LOGGER.info("Aria2Download started: %s. Gid: %s", name, gid)
    await listener.onDownloadStart()
    if (
        not add_to_queue
        and (not listener.select or not config_dict["BASE_URL"])
        and listener.multi <= 1
    ):
        await sendStatusMessage(listener.message)
    elif listener.select and download.is_torrent and not download.is_metadata:
        if not add_to_queue:
            await sync_to_async(aria2.client.force_pause, gid)
        SBUTTONS = bt_selection_buttons(gid)
        msg = f"<code>{name}</code>\n\n{listener.tag}, your download paused. Choose files then press <b>Done Selecting</b> button to start downloading."
        await sendingMessage(
            msg, listener.message, config_dict["IMAGE_PAUSE"], SBUTTONS
        )
    if add_to_queue:
        await event.wait()
        async with task_dict_lock:
            if listener.mid not in task_dict:
                return
            task = task_dict[listener.mid]
            task.queued = False
            new_gid = task.gid()
        await sync_to_async(aria2.client.unpause, new_gid)
        LOGGER.info("Start Queued Download from Aria2c: %s. Gid: %s", name, gid)
        async with queue_dict_lock:
            non_queued_dl.add(listener.mid)
