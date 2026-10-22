from __future__ import annotations
from asyncio import wait_for, Event, wrap_future, sleep, gather
from functools import partial
from os import path as ospath
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler
from time import time

from bot import (
    task_dict,
    task_dict_lock,
    non_queued_dl,
    queue_dict_lock,
    jd_lock,
    jd_downloads,
    LOGGER,
)
from bot.helper.ext_utils.bot_utils import new_thread, retry_function, sync_to_async
from bot.helper.ext_utils.jdownloader_booter import jdownloader
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.task_manager import (
    check_limits_size,
    check_running_tasks,
    stop_duplicate_check,
)
from bot.helper.listeners import tasks_listener as task
from bot.helper.listeners.jdownloader_listener import onDownloadStart
from bot.helper.mirror_utils.status_utils.jdownloader_status import JDownloaderStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    sendStatusMessage,
    editMessage,
    deleteMessage,
)


async def configureDownload(_, query, obj):
    data = query.data.split()
    await query.answer()
    match data[1]:
        case "sdone":
            obj.event.set()
        case "cancel":
            await editMessage("Task has been cancelled.", query.message)
            obj.is_cancelled = True
            obj.event.set()


class JDownloaderHelper:
    def __init__(self, listener: task.TaskListener):
        self._listener = listener
        self._timeout = 300
        self._reply_to = ""
        self.event = Event()
        self.is_cancelled = False

    @new_thread
    async def _event_handler(self):
        pfunc = partial(configureDownload, obj=self)
        handler = self._listener.client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^jdq") & user(self._listener.user_id)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=self._timeout)
        except:
            await editMessage(
                "Timed Out. Task has been cancelled!", self._listener.editable
            )
            self.is_cancelled = True
            self.event.set()
        finally:
            self._listener.client.remove_handler(*handler)

    async def waitForConfigurations(self):
        future = self._event_handler()
        buttons = ButtonMaker()
        buttons.button_link("Select", "https://my.jdownloader.org")
        buttons.button_data("Done Selecting", "jdq sdone")
        buttons.button_data("Cancel", "jdq cancel")
        msg = f"<code>{self._listener.name}</code>\n\n{self._listener.tag}, disable/remove the unwanted files or change variants or edit files names from myJdownloader site, but don't start it manually. After finish press <b>Done Selecting</b>!.\n\n<i>Timeout: {self._timeout}s</i>"
        await editMessage(msg, self._listener.editable, buttons.build_menu(2))
        await wrap_future(future)
        return self.is_cancelled


async def add_jd_download(listener: task.TaskListener, path: str):
    async with jd_lock:
        if jdownloader.device is None:
            await editMessage(jdownloader.error, listener.editable)
            return

        try:
            await wait_for(retry_function(0, jdownloader.device.jd.version), timeout=5)
        except:
            is_connected = await sync_to_async(jdownloader.jdconnect)
            if not is_connected:
                await listener.onDownloadError(jdownloader.error)
                return
            await sync_to_async(jdownloader.connectToDevice)

        if not jd_downloads:
            await retry_function(0, jdownloader.device.linkgrabber.clear_list)
            if odl := await retry_function(
                0, jdownloader.device.downloads.query_packages, [{}]
            ):
                await retry_function(
                    0,
                    jdownloader.device.downloads.remove_links,
                    package_ids=[od["uuid"] for od in odl],
                )

        jdata = [
            {
                "autoExtract": False,
                "links": listener.link,
                "packageName": listener.name or None,
            }
        ]
        await retry_function(0, jdownloader.device.linkgrabber.add_links, jdata)

        await sleep(0.5)

        while await retry_function(0, jdownloader.device.linkgrabber.is_collecting):
            pass

        start_time = time()
        online_packages, corrupted_packages = [], []
        size = gid = 0
        remove_unknown = False
        name, error = "", ""
        path = path.replace("//", "/")
        while (time() - start_time) < 20:
            jdata = [
                {
                    "bytesTotal": True,
                    "saveTo": True,
                    "availableOnlineCount": True,
                    "availableTempUnknownCount": True,
                    "availableUnknownCount": True,
                }
            ]
            queued_downloads = await retry_function(
                0, jdownloader.device.linkgrabber.query_packages, jdata
            )

            if not online_packages and corrupted_packages and error:
                await gather(
                    listener.onDownloadError(error),
                    retry_function(
                        0,
                        jdownloader.device.linkgrabber.remove_links,
                        package_ids=corrupted_packages,
                    ),
                )
                return
            for pack in queued_downloads:
                online = pack.get("onlineCount", 1)
                if online == 0:
                    error = f"{pack.get('name', '')}"
                    LOGGER.error(error)
                    corrupted_packages.append(pack["uuid"])
                    continue
                save_to, org_dir = pack["saveTo"], "/root/Downloads/"
                if gid == 0:
                    gid = pack["uuid"]
                    jd_downloads[gid] = {"status": "collect"}
                    if save_to.startswith(org_dir):
                        name = save_to.replace(org_dir, "", 1).split("/", 1)[0]
                    else:
                        name = save_to.replace(path, "", 1).split("/", 1)[0]

                if (
                    pack.get("tempUnknownCount", 0) > 0
                    or pack.get("unknownCount", 0) > 0
                ):
                    remove_unknown = True

                size += pack.get("bytesTotal", 0)
                online_packages.append(pack["uuid"])
                if save_to.startswith(org_dir):
                    await retry_function(
                        0,
                        jdownloader.device.linkgrabber.set_download_directory,
                        save_to.replace(org_dir, path, 1),
                        [pack["uuid"]],
                    )

            if online_packages:
                if listener.join and len(online_packages) > 1:
                    listener.name = listener.sameDir["name"]
                    await retry_function(
                        0,
                        jdownloader.device.linkgrabber.move_to_new_package,
                        listener.name,
                        ospath.join(path, listener.name),
                        package_ids=online_packages,
                    )
                    continue
                break
        else:
            error = (
                name or "Download not added! Maybe some issues in jdownloader or site!"
            )
            await gather(
                deleteMessage(listener.editable), listener.onDownloadError(error)
            )
            if corrupted_packages or online_packages:
                packages_to_remove = corrupted_packages + online_packages
                await retry_function(
                    0,
                    jdownloader.device.linkgrabber.remove_links,
                    package_ids=packages_to_remove,
                )
            return

        jd_downloads[gid]["ids"] = online_packages
        corrupted_links = []
        if remove_unknown:
            links = await retry_function(
                0,
                jdownloader.device.linkgrabber.query_links,
                [{"packageUUIDs": online_packages, "availability": True}],
            )
            corrupted_links = [
                link["uuid"]
                for link in links
                if link["availability"].lower() != "online"
            ]

        if corrupted_packages or corrupted_links:
            await retry_function(
                0,
                jdownloader.device.linkgrabber.remove_links,
                corrupted_links,
                corrupted_packages,
            )

    listener.name = listener.name or name

    msg, button = await stop_duplicate_check(listener)
    if msg:
        await gather(
            deleteMessage(listener.editable), listener.onDownloadError(msg, button)
        )
        return

    if msg := await check_limits_size(listener, size):
        LOGGER.info("File/folder size over the limit size!")
        await gather(
            retry_function(
                0,
                jdownloader.device.linkgrabber.remove_links,
                package_ids=online_packages,
            ),
            deleteMessage(listener.editable),
            listener.onDownloadError(
                f"{msg}. File/folder size is {get_readable_file_size(size)}."
            ),
        )
        listener.removeFromSameDir()
        return

    if listener.select and await JDownloaderHelper(listener).waitForConfigurations():
        await retry_function(
            0, jdownloader.device.linkgrabber.remove_links, package_ids=online_packages
        )
        listener.removeFromSameDir()
        return

    await deleteMessage(listener.editable)

    add_to_queue, event = await check_running_tasks(listener.mid)
    if add_to_queue:
        LOGGER.info("Added to Queue/Download: %s", listener.name)
        async with task_dict_lock:
            task_dict[listener.mid] = QueueStatus(listener, size, f"{gid}", "dl")
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

    await retry_function(
        0,
        jdownloader.device.linkgrabber.move_to_downloadlist,
        package_ids=online_packages,
    )

    await sleep(0.5)

    download_packages = await retry_function(
        0, jdownloader.device.downloads.query_packages, [{"saveTo": True}]
    )
    async with jd_lock:
        packages = []
        for pack in download_packages:
            if pack["saveTo"].startswith(path):
                if not packages:
                    del jd_downloads[gid]
                    gid = pack["uuid"]
                    jd_downloads[gid] = {"status": "down"}
                packages.append(pack["uuid"])
        if packages:
            jd_downloads[gid]["ids"] = packages

    if not packages:
        await listener.onDownloadError("This download have been removed manually!")
        return

    await retry_function(
        0, jdownloader.device.downloads.force_download, package_ids=packages
    )

    async with task_dict_lock:
        task_dict[listener.mid] = JDownloaderStatus(listener, f"{gid}")

    async with queue_dict_lock:
        non_queued_dl.add(listener.mid)

    await onDownloadStart()

    if from_queue:
        LOGGER.info("Start Queued Download from JDownloader: %s", listener.name)
    else:
        LOGGER.info("Download with JDownloader: %s", listener.name)
        await listener.onDownloadStart()
        if listener.multi <= 1:
            await sendStatusMessage(listener.message)
