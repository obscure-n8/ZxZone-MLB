from __future__ import annotations
from asyncio import gather
from json import loads
from secrets import token_urlsafe

from bot import task_dict, task_dict_lock, queue_dict_lock, non_queued_dl, LOGGER
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    check_limits_size,
)
from bot.helper.listeners import tasks_listener as task
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage


async def add_rclone_download(listener: task.TaskListener, path: str):
    if listener.link.startswith("mrcc:"):
        listener.link = listener.link.split("mrcc:", 1)[1]
        config_path = f"rclone/{listener.user_id}.conf"
    else:
        config_path = "rclone.conf"
    try:
        remote, listener.link = listener.link.split(":", 1)
    except:
        await listener.onDownloadError("Invalid link/path to download!")
        return
    listener.link = listener.link.strip("/")

    cmd1 = [
        "wzone",
        "lsjson",
        "--fast-list",
        "--stat",
        "--no-mimetype",
        "--no-modtime",
        "--config",
        config_path,
        f"{remote}:{listener.link}",
    ]
    cmd2 = [
        "wzone",
        "size",
        "--fast-list",
        "--json",
        "--config",
        config_path,
        f"{remote}:{listener.link}",
    ]
    res1, res2 = await gather(cmd_exec(cmd1), cmd_exec(cmd2))
    if res1[2] or res2[2]:
        if res1[2] != -9:
            msg = f"Error: While getting rclone stat/size. Path: {remote}:{listener.link}. Stderr: {res1[1] or res2[1]}"
            await listener.onDownloadError(msg)
        return
    try:
        rstat, rsize = loads(res1[0]), loads(res2[0])
    except Exception as err:
        await listener.onDownloadError(f"RcloneDownload JsonLoad: {err}")
        return
    if rstat["IsDir"]:
        if not listener.name:
            listener.name = (
                listener.link.rsplit("/", 1)[-1] if listener.link else remote
            )
        path += listener.name
    else:
        listener.name = listener.link.rsplit("/", 1)[-1]
    size = rsize["bytes"]
    gid = token_urlsafe(12)
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

    RCTransfer = RcloneTransferHelper(listener)
    async with task_dict_lock:
        task_dict[listener.mid] = RcloneStatus(listener, RCTransfer, gid, "dl")
    async with queue_dict_lock:
        non_queued_dl.add(listener.mid)

    if from_queue:
        LOGGER.info("Start Queued Download with rclone: %s", listener.link)
    else:
        await listener.onDownloadStart()
        if listener.multi <= 1:
            await sendStatusMessage(listener.message)
        LOGGER.info("Download with rclone: %s", listener.link)

    await RCTransfer.download(remote, config_path, path)
