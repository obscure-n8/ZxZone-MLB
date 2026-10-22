from asyncio import gather, sleep
from time import time

from bot import aria2, task_dict, task_dict_lock, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import (
    bt_selection_buttons,
    new_thread,
    sync_to_async,
)
from bot.helper.ext_utils.files_utils import clean_unwanted, clean_target
from bot.helper.ext_utils.status_utils import get_readable_file_size, getTaskByGid
from bot.helper.ext_utils.task_manager import stop_duplicate_check, check_limits_size
from bot.helper.mirror_utils.status_utils.aria_status import Aria2Status
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    deleteMessage,
    sendingMessage,
    update_status_message,
)


@new_thread
async def _onDownloadStarted(api, gid):
    download = await sync_to_async(api.get_download, gid)
    if download.options.follow_torrent == "false":
        return
    if download.is_metadata:
        LOGGER.info("onDownloadStarted: %s METADATA", gid)
        await sleep(1)
        if task := await getTaskByGid(gid):
            if task.listener.select:
                meta = await sendMessage(
                    "<i>Downloading <b>Metadata</b>, please wait...</i>",
                    task.listener.message,
                )
                while True:
                    await sleep(0.5)
                    if download.is_removed or download.followed_by_ids:
                        await deleteMessage(meta)
                        break
                    download = download.live
        return
    LOGGER.info("onDownloadStarted: %s - Gid: %s", download.name, gid)
    task = None
    await sleep(1)
    if task := await getTaskByGid(gid):
        download = await sync_to_async(api.get_download, gid)
        await sleep(2)
        download = download.live
        task.listener.name = download.name
        file, name = await stop_duplicate_check(task.listener)
        if file:
            LOGGER.info("File/folder already in Drive!")
            task.listener.name = name
            await task.listener.onDownloadError("File/folder already in Drive!", file)
            await sync_to_async(api.remove, [download], force=True, files=True)
            return

        size = download.total_length
        if msg := await check_limits_size(task.listener, size):
            LOGGER.info("File/folder size over the limit size!")
            await gather(
                task.listener.onDownloadError(
                    f"{msg}. File/folder size is {get_readable_file_size(size)}."
                ),
                sync_to_async(api.remove, [download], force=True, files=True),
            )


@new_thread
async def _onDownloadComplete(api, gid):
    try:
        download = await sync_to_async(api.get_download, gid)
    except:
        return
    if download.options.follow_torrent == "false":
        return
    if download.followed_by_ids:
        new_gid = download.followed_by_ids[0]
        LOGGER.info("Gid changed from %s to %s", gid, new_gid)
        await sleep(1.5)
        task = await getTaskByGid(new_gid)
        if task := await getTaskByGid(new_gid):
            if config_dict["BASE_URL"] and task.listener.select:
                if not task.queued:
                    await sync_to_async(api.client.force_pause, new_gid)
                SBUTTONS = bt_selection_buttons(new_gid)
                msg = f"<code>{task.name()}</code>\n\n{task.listener.tag}, your download paused. Choose files then press <b>Done Selecting</b> button to start downloading."
                await sendingMessage(
                    msg, task.listener.message, config_dict["IMAGE_PAUSE"], SBUTTONS
                )
    elif download.is_torrent:
        if task := await getTaskByGid(gid):
            if hasattr(task, "listener") and task.seeding:
                LOGGER.info("Cancelling Seed: %s onDownloadComplete")
                await gather(
                    task.listener.onUploadError(
                        f"Seeding stopped with Ratio {task.ratio()} ({task.seeding_time()})"
                    ),
                    sync_to_async(api.remove, [download], force=True, files=True),
                )
    else:
        LOGGER.info("onDownloadComplete: %s - Gid: %s", download.name, gid)
        if task := await getTaskByGid(gid):
            await task.listener.onDownloadComplete()
            await sync_to_async(api.remove, [download], force=True, files=True)


@new_thread
async def _onBtDownloadComplete(api, gid):
    seed_start_time = time()
    await sleep(1)
    download = await sync_to_async(api.get_download, gid)
    if download.options.follow_torrent == "false":
        return
    LOGGER.info("onBtDownloadComplete: %s - Gid: %s", download.name, gid)
    task = await getTaskByGid(gid)
    if not task:
        return

    if task.listener.select:
        res = download.files
        await gather(
            *[clean_target(file_o.path) for file_o in res if not file_o.selected]
        )
        await clean_unwanted(download.dir)

    if task.listener.seed:
        try:
            await sync_to_async(api.set_options, {"max-upload-limit": "0"}, [download])
        except Exception as e:
            LOGGER.error(
                "%s You are not able to seed because you added global option seed-time=0 without adding specific seed_time for this torrent GID: %s",
                e,
                gid,
            )
    else:
        try:
            await sync_to_async(api.client.force_pause, gid)
        except Exception as e:
            LOGGER.error("%s GID: %s", e, gid)

    await task.listener.onDownloadComplete()
    download = download.live
    if task.listener.seed:
        if download.is_complete:
            if task := await getTaskByGid(gid):
                LOGGER.info("Cancelling Seed: %s", download.name)
                await gather(
                    task.listener.onUploadError(
                        f"Seeding stopped with Ratio {task.ratio()} ({task.seeding_time()})"
                    ),
                    sync_to_async(api.remove, [download], force=True, files=True),
                )
        else:
            async with task_dict_lock:
                if task.listener.mid not in task_dict:
                    await sync_to_async(api.remove, [download], force=True, files=True)
                    return
                task_dict[task.listener.mid] = Aria2Status(task.listener, gid, True)
                task_dict[task.listener.mid].start_time = seed_start_time
            LOGGER.info("Seeding started: %s - Gid: %s", download.name, gid)
            await update_status_message(task.listener.message.chat.id)
    else:
        await sync_to_async(api.remove, [download], force=True, files=True)


@new_thread
async def _onDownloadStopped(api, gid):
    await sleep(4)
    if task := await getTaskByGid(gid):
        task.listener.name = task.name().replace("[METADATA]", "")
        await task.listener.onDownloadError("Dead torrent!")


@new_thread
async def _onDownloadError(api, gid):
    LOGGER.error("onDownloadError: %s", gid)
    error = "None"
    try:
        download = await sync_to_async(api.get_download, gid)
        if download.options.follow_torrent == "false":
            return
        error = download.error_message
        raise ValueError(error)
    except Exception as e:
        LOGGER.error("Failed to get download: %s", e)

    if task := await getTaskByGid(gid):
        task.listener.name = task.name().replace("[METADATA]", "")
        await task.listener.onDownloadError(error)


def start_aria2_listener():
    aria2.listen_to_notifications(
        threaded=False,
        on_download_start=_onDownloadStarted,
        on_download_error=_onDownloadError,
        on_download_stop=_onDownloadStopped,
        on_download_complete=_onDownloadComplete,
        on_bt_download_complete=_onBtDownloadComplete,
        timeout=60,
    )
