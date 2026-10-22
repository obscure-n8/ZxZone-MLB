from __future__ import annotations
from os import path as ospath
from secrets import token_urlsafe

from bot import (
    LOGGER,
    aria2_options,
    aria2c_global,
    task_dict,
    task_dict_lock,
    non_queued_dl,
    queue_dict_lock,
)
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.links_utils import get_link
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    check_limits_size,
)
from bot.helper.listeners import tasks_listener as task
from bot.helper.listeners.direct_listener import DirectListener
from bot.helper.mirror_utils.status_utils.direct_status import DirectStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage


async def add_direct_download(listener: task.TaskListener, path: str):
    details = listener.link
    listener.link = get_link(listener.message)
    if not (contents := details.get("contents")):
        await listener.onDownloadError("Link not contain any content to download!")
        return
    size = details["total_size"]

    if not listener.name:
        listener.name = details["title"]
    path = ospath.join(path, listener.name)

    file, name = await stop_duplicate_check(listener)
    if file:
        listener.name = name
        LOGGER.info("File/folder already in Drive!")
        await listener.onDownloadError("File/folder already in Drive!", file)
        return

    if msg := await check_limits_size(listener, size):
        LOGGER.info("File/folder size over the limit size!")
        await listener.onDownloadError(
            f"{msg}. File/folder size is {get_readable_file_size(size)}."
        )
        return

    gid = token_urlsafe(10)
    add_to_queue, event = await check_running_tasks(listener.mid)
    if add_to_queue:
        LOGGER.info("Added to Queue/Download: %s", listener.name)
        async with task_dict_lock:
            task_dict[listener.mid] = QueueStatus(listener, size, gid, "dl")
        await listener.onDownloadStart()
        if listener.multi <= 1:
            await sendStatusMessage(listener.message)
        await event.wait()
        async with task_dict_lock:
            if listener.mid not in task_dict:
                return
        from_queue = True
    else:
        from_queue = False

    a2c_opt = {**aria2_options}
    [a2c_opt.pop(k) for k in aria2c_global if k in aria2_options]
    if header := details.get("header"):
        a2c_opt["header"] = header
    a2c_opt["follow-torrent"] = "false"
    a2c_opt["follow-metalink"] = "false"
    directListener = DirectListener(listener, size, path, a2c_opt)
    async with task_dict_lock:
        task_dict[listener.mid] = DirectStatus(listener, directListener, gid)

    async with queue_dict_lock:
        non_queued_dl.add(listener.mid)

    if from_queue:
        LOGGER.info("Start Queued Download from Direct Download: %s", listener.name)
    else:
        LOGGER.info("Download from Direct Download: %s", listener.name)
        await listener.onDownloadStart()
        if listener.multi <= 1:
            await sendStatusMessage(listener.message)

    await sync_to_async(directListener.download, contents)
