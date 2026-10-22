from __future__ import annotations
from secrets import token_urlsafe

from bot import task_dict, task_dict_lock, non_queued_dl, queue_dict_lock, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    check_limits_size,
)
from bot.helper.listeners import tasks_listener as task
from bot.helper.mirror_utils.gdrive_utlis.count import gdCount
from bot.helper.mirror_utils.gdrive_utlis.delete import gdDelete
from bot.helper.mirror_utils.gdrive_utlis.download import gdDownload
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage


async def add_gd_download(listener: task.TaskListener, path: str):
    drive = gdCount()
    name, mime_type, size, _, _ = await sync_to_async(
        drive.count, listener.link, listener.user_id
    )
    if not mime_type:
        await listener.onDownloadError(name)
        return
    listener.name = listener.name or name

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

    gid = token_urlsafe(12)
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
    drive = gdDownload(listener, path)
    async with task_dict_lock:
        task_dict[listener.mid] = GdriveStatus(listener, drive, size, gid, "dl")
    async with queue_dict_lock:
        non_queued_dl.add(listener.mid)
    if from_queue:
        LOGGER.info("Start Queued Download from GDrive: %s", listener.name)
    else:
        LOGGER.info("Download from GDrive: %s", listener.name)
        await listener.onDownloadStart()
        if listener.multi <= 1:
            await sendStatusMessage(listener.message)
    await sync_to_async(drive.download)
    if listener.isSharer:
        msg = await sync_to_async(
            gdDelete().deletefile, listener.link, listener.user_id
        )
        LOGGER.info("%s (Sharer Link): %s", msg, listener.link)
