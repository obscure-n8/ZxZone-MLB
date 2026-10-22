from aiofiles.os import listdir, path as aiopath, makedirs
from aioshutil import move
from asyncio import sleep, gather
from html import escape
from os import path as ospath
from random import choice
from requests import utils as rutils
from time import time


from bot import (
    bot_loop,
    bot_name,
    task_dict,
    task_dict_lock,
    Intervals,
    aria2,
    config_dict,
    non_queued_up,
    non_queued_dl,
    queued_up,
    queued_dl,
    queue_dict_lock,
    LOGGER,
    DATABASE_URL,
)
from bot.helper.common import TaskConfig
from bot.helper.ext_utils.bot_utils import (
    is_premium_user,
    is_pm_enabled,
    UserDaily,
    default_button,
    sync_to_async,
)
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.files_utils import (
    get_path_size,
    clean_download,
    clean_target,
    join_files,
)
from bot.helper.ext_utils.links_utils import (
    is_magnet,
    is_url,
    get_link,
    is_media,
    is_gdrive_link,
    get_stream_link,
    is_gdrive_id,
)
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.status_utils import (
    action,
    get_date_time,
    get_readable_file_size,
    get_readable_time,
)
from bot.helper.ext_utils.task_manager import start_from_queued, check_running_tasks
from bot.helper.ext_utils.telegraph_helper import TelePost
from bot.helper.mirror_utils.gdrive_utlis.upload import gdUpload
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.gofile_upload_status import GofileUploadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_utils.upload_utils.gofile_uploader import GoFileUploader
from bot.helper.mirror_utils.upload_utils.telegram_uploader import TgUploader
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    limit,
    sendCustom,
    sendMedia,
    sendMessage,
    auto_delete_message,
    sendSticker,
    sendFile,
    copyMessage,
    sendingMessage,
    update_status_message,
    delete_status,
)
from bot.helper.video_utils.executor import VidEcxecutor


class TaskListener(TaskConfig):
    def __init__(self):
        super().__init__()

    @staticmethod
    async def clean():
        try:
            if st := Intervals["status"]:
                for intvl in list(st.values()):
                    intvl.cancel()
            Intervals["status"].clear()
            await gather(sync_to_async(aria2.purge), delete_status())
        except:
            pass

    def removeFromSameDir(self):
        if self.sameDir and self.mid in self.sameDir["tasks"]:
            self.sameDir["tasks"].remove(self.mid)
            self.sameDir["total"] -= 1

    async def onDownloadStart(self):
        if (
            self.isSuperChat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and DATABASE_URL
        ):
            await DbManager().add_incomplete_task(
                self.message.chat.id, self.message.link, self.tag
            )

    async def onDownloadComplete(self):
        multi_links = False
        if self.sameDir and self.mid in self.sameDir["tasks"]:
            while not (
                self.sameDir["total"] in [1, 0]
                or self.sameDir["total"] > 1
                and len(self.sameDir["tasks"]) > 1
            ):
                await sleep(0.5)

        async with task_dict_lock:
            if (
                self.sameDir
                and self.sameDir["total"] > 1
                and self.mid in self.sameDir["tasks"]
            ):
                self.sameDir["tasks"].remove(self.mid)
                self.sameDir["total"] -= 1
                folder_name = self.sameDir["name"]
                spath = ospath.join(self.dir, folder_name)
                des_path = ospath.join(
                    f"{config_dict['DOWNLOAD_DIR']}{list(self.sameDir['tasks'])[0]}",
                    folder_name,
                )
                await makedirs(des_path, exist_ok=True)
                for item in await listdir(spath):
                    if item.endswith((".aria2", ".!qB")):
                        continue
                    item_path = ospath.join(spath, item)
                    if item in await listdir(des_path):
                        await move(
                            item_path, ospath.join(des_path, f"{self.mid}-{item}")
                        )
                    else:
                        await move(item_path, ospath.join(des_path, item))
                multi_links = True
            task = task_dict[self.mid]
            self.name = task.name()
            gid = task.gid()
        LOGGER.info("Download completed: %s", self.name)
        if multi_links:
            await self.onUploadError("Downloaded! Waiting for other tasks.")
            return

        up_path = ospath.join(self.dir, self.name)
        if not await aiopath.exists(up_path):
            try:
                files = await listdir(self.dir)
                self.name = files[-1]
                if self.name == "yt-dlp-thumb":
                    self.name = files[0]
            except Exception as e:
                await self.onUploadError(e)
                return

        await self.isOneFile(up_path)
        await self.reName()

        up_path = ospath.join(self.dir, self.name)
        size = await get_path_size(up_path)

        if not config_dict["QUEUE_ALL"]:
            if not config_dict["QUEUE_COMPLETE"]:
                async with queue_dict_lock:
                    if self.mid in non_queued_dl:
                        non_queued_dl.remove(self.mid)
            await start_from_queued()

        if self.join and await aiopath.isdir(up_path):
            await join_files(up_path)

        if self.extract:
            up_path = await self.proceedExtract(up_path, size, gid)
            if not up_path:
                return
            up_dir, self.name = ospath.split(up_path)
            size = await get_path_size(up_dir)

        if self.sampleVideo:
            up_path = await self.generateSampleVideo(up_path, gid)
            if not up_path:
                return
            up_dir, self.name = ospath.split(up_path)
            size = await get_path_size(up_dir)

        if self.compress:
            if self.vidMode:
                up_path = await VidEcxecutor(self, up_path, gid).execute()
                if not up_path:
                    return
                self.seed = False

            up_path = await self.proceedCompress(up_path, size, gid)
            if not up_path:
                return

        if not self.compress and self.vidMode:
            up_path = await VidEcxecutor(self, up_path, gid).execute()
            if not up_path:
                return
            self.seed = False

        if not self.compress and not self.extract:
            up_path = await self.preName(up_path)
            await self.editMetadata(up_path, gid)

        if one_path := await self.isOneFile(up_path):
            up_path = one_path

        up_dir, self.name = ospath.split(up_path)
        size = await get_path_size(up_dir)
        if self.isLeech:
            o_files, m_size = [], []
            if not self.compress:
                result = await self.proceedSplit(up_dir, m_size, o_files, size, gid)
                if not result:
                    return

        add_to_queue, event = await check_running_tasks(self.mid, "up")
        await start_from_queued()
        if add_to_queue:
            LOGGER.info("Added to Queue/Upload: %s", self.name)
            async with task_dict_lock:
                task_dict[self.mid] = QueueStatus(self, size, gid, "Up")
            await event.wait()
            async with task_dict_lock:
                if self.mid not in task_dict:
                    return
            LOGGER.info("Start from Queued/Upload: %s", self.name)
        async with queue_dict_lock:
            non_queued_up.add(self.mid)

        size = await get_path_size(up_dir)

        if not self.isLeech and self.isGofile:
            go = GoFileUploader(self)
            async with task_dict_lock:
                task_dict[self.mid] = GofileUploadStatus(self, go, size, gid)
            await gather(update_status_message(self.message.chat.id), go.goUpload())
            if go.is_cancelled:
                return

        if self.isLeech:
            for s in m_size:
                size -= s
            LOGGER.info("Leech Name: %s", self.name)
            tg = TgUploader(self, up_dir, size)
            async with task_dict_lock:
                task_dict[self.mid] = TelegramStatus(self, tg, size, gid, "up")
            await gather(
                update_status_message(self.message.chat.id), tg.upload(o_files, m_size)
            )
        elif is_gdrive_id(self.upDest):
            LOGGER.info("GDrive Uploading: %s", self.name)
            drive = gdUpload(self, up_path)
            async with task_dict_lock:
                task_dict[self.mid] = GdriveStatus(self, drive, size, gid, "up")
            await gather(
                update_status_message(self.message.chat.id),
                sync_to_async(drive.upload, size),
            )
        else:
            LOGGER.info("RClone Uploading: %s", self.name)
            RCTransfer = RcloneTransferHelper(self)
            async with task_dict_lock:
                task_dict[self.mid] = RcloneStatus(self, RCTransfer, gid, "up")
            await gather(
                update_status_message(self.message.chat.id),
                RCTransfer.upload(up_path, size),
            )

    async def onUploadComplete(
        self, link, size, files, folders, mime_type, rclonePath="", dir_id=""
    ):
        if (
            self.isSuperChat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and DATABASE_URL
        ):
            await DbManager().rm_complete_task(self.message.link)

        LOGGER.info("Task Done: %s", self.name)
        dt_date, dt_time = get_date_time(self.message)
        buttons = ButtonMaker()
        buttons_scr = ButtonMaker()
        daily_size = size
        size = get_readable_file_size(size)
        reply_to = self.message.reply_to_message
        images = (
            choice(config_dict["IMAGE_COMPLETE"].split())
            if config_dict["IMAGE_COMPLETE"]
            else ""
        )
        TIME_ZONE_TITLE = config_dict["TIME_ZONE_TITLE"]
        if (chat_id := config_dict["LINK_LOG"]) and self.isSuperChat:
            msg = (
                "<b>LINK LOGS</b>\n"
                f"<code>{escape(self.name)}</code>\n"
                f"<b>Cc: </b>{self.tag}\n"
                f"<b>ID: </b><code>{self.user_id}</code>\n"
                f"<b>Size: </b>{size}\n"
                f"<b>Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
                f"<b>Action: </b>{action(self.message)}\n"
                "<b>Status: </b>#done\n"
            )
            if self.isLeech:
                msg += f"<b>Total Files: </b>{folders}\n"
                if mime_type != 0:
                    msg += f"<b>Corrupted Files: </b>{mime_type}\n"
            else:
                msg += f"<b>Type: </b>{mime_type}\n"
                if mime_type == "Folder":
                    if folders:
                        msg += f"<b>SubFolders: </b>{folders}\n"
                    msg += f"<b>Files: </b>{files}\n"
            msg += f"<b>Source Link:</b>\n<code>{get_link(self.message, get_source=True)}</code>"
            if reply_to and is_media(reply_to):
                await sendMedia(msg, chat_id, reply_to)
            else:
                await sendCustom(msg, chat_id)
        msg = f'<a href="https://t.me/zonexusmlgroup4gb"><b><i>Bot Of ZxZone</b></i></a>\n'
        msg += f"<code>{escape(self.name)}</code>\n"
        msg += f"<b>Size: </b>{size}\n"
        if self.isLeech:
            if config_dict["SOURCE_LINK"]:
                scr_link = get_link(self.message)
                if is_magnet(scr_link):
                    tele = TelePost(config_dict["SOURCE_LINK_TITLE"])
                    mag_link = await sync_to_async(
                        tele.create_post,
                        f"<code>{escape(self.name)}<br>({size})</code><br>{scr_link}",
                    )
                    buttons.button_link("Source Link", mag_link)
                    buttons_scr.button_link("Source Link", mag_link)
                elif is_url(scr_link):
                    buttons.button_link("Source Link", scr_link)
                    buttons_scr.button_link("Source Link", scr_link)
            if is_pm_enabled(self.user_id, self.user_dict) and self.isSuperChat:
                buttons.button_link("View File(s)", f"http://t.me/{bot_name}")
            msg += f"<b>Total Files: </b>{folders}\n"
            if mime_type != 0:
                msg += f"<b>Corrupted Files: </b>{mime_type}\n"
            msg += (
                f"<b>Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
                f"<b>Cc: </b>{self.tag}\n"
                f"<b>Action: </b>{action(self.message)}\n\n"
            )
            ONCOMPLETE_LEECH_LOG = config_dict["ONCOMPLETE_LEECH_LOG"]
            if not files:
                uploadmsg = await sendingMessage(
                    msg, self.message, images, buttons.build_menu(2)
                )
                if is_pm_enabled(self.user_id, self.user_dict) and self.isSuperChat:
                    if reply_to and is_media(reply_to):
                        await sendMedia(
                            msg, self.user_id, reply_to, buttons_scr.build_menu(2)
                        )
                    else:
                        await copyMessage(
                            self.user_id, uploadmsg, buttons_scr.build_menu(2)
                        )
                if (chat_id := config_dict["LEECH_LOG"]) and ONCOMPLETE_LEECH_LOG:
                    await copyMessage(chat_id, uploadmsg, buttons_scr.build_menu(2))
            else:
                result_msg = 0
                fmsg = "<b></b>\n"
                for index, (tlink, name) in enumerate(files.items(), start=1):
                    fmsg += f' <a href=""></a>\n'
                    limit.text(fmsg + msg)
                    if len(msg + fmsg) - limit.total > 4090:
                        uploadmsg = await sendMessage(
                            msg + fmsg, self.message, buttons.build_menu(2)
                        )
                        await sleep(1)
                        if (
                            is_pm_enabled(self.user_id, self.user_dict)
                            and self.isSuperChat
                        ):
                            if reply_to and is_media(reply_to) and result_msg == 0:
                                await sendMedia(
                                    msg + fmsg,
                                    self.user_id,
                                    reply_to,
                                    buttons_scr.build_menu(2),
                                )
                                result_msg += 1
                            else:
                                await copyMessage(
                                    self.user_id, uploadmsg, buttons_scr.build_menu(2)
                                )
                        if (
                            chat_id := config_dict["LEECH_LOG"]
                        ) and ONCOMPLETE_LEECH_LOG:
                            await copyMessage(
                                chat_id, uploadmsg, buttons_scr.build_menu(2)
                            )
                        if self.isSuperChat and (
                            stime := config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
                        ):
                            bot_loop.create_task(
                                auto_delete_message(uploadmsg, stime=stime)
                            )
                        fmsg = ""
                if fmsg != "":
                    limit.text(msg + fmsg)
                    if len(msg + fmsg) - limit.total > 1024:
                        uploadmsg = await sendMessage(
                            msg + fmsg, self.message, buttons.build_menu(2)
                        )
                    else:
                        uploadmsg = await sendingMessage(
                            msg + fmsg, self.message, images, buttons.build_menu(2)
                        )
                    if is_pm_enabled(self.user_id, self.user_dict) and self.isSuperChat:
                        if reply_to and is_media(reply_to):
                            await sendMedia(
                                msg + fmsg,
                                self.user_id,
                                reply_to,
                                buttons_scr.build_menu(2),
                            )
                        else:
                            await copyMessage(
                                self.user_id, uploadmsg, buttons_scr.build_menu(2)
                            )
                    if (chat_id := config_dict["LEECH_LOG"]) and ONCOMPLETE_LEECH_LOG:
                        await copyMessage(chat_id, uploadmsg, buttons_scr.build_menu(2))
                if STICKERID_LEECH := config_dict["STICKERID_LEECH"]:
                    await sendSticker(STICKERID_LEECH, self.message)
            if self.seed:
                if self.newDir:
                    await clean_target(self.newDir, True)
                async with queue_dict_lock:
                    if self.mid in non_queued_up:
                        non_queued_up.remove(self.mid)
                await start_from_queued()
                return
        else:
            msg += f"<b>Type: </b>{mime_type}\n"
            if mime_type == "Folder":
                if folders:
                    msg += f"<b>SubFolders: </b>{folders}\n"
                msg += f"<b>Files: </b>{files}\n"
            msg += (
                f"<b>Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
                f"<b>Cc: </b>{self.tag}\n"
                f"<b>Action: </b>{action(self.message)}\n"
            )
            if link or rclonePath:
                if self.isGofile:
                    golink = await sync_to_async(short_url, self.isGofile, self.user_id)
                    buttons.button_link("GoFile Link", golink)
                if link:
                    if (
                        all(
                            x not in link
                            for x in config_dict["CLOUD_LINK_FILTERS"].split()
                        )
                        or (self.privateLink and is_gdrive_link(link))
                        or self.upDest.startswith("mrcc")
                    ):
                        link = await sync_to_async(short_url, link, self.user_id)
                        buttons.button_link("Cloud Link", link)
                else:
                    msg += f"\n\n<b>Path:</b> <code>{rclonePath}</code>"
                if (
                    rclonePath
                    and (RCLONE_SERVE_URL := config_dict["RCLONE_SERVE_URL"])
                    and not self.upDest.startswith("mrcc")
                    and not self.privateLink
                ):
                    remote, path = rclonePath.split(":", 1)
                    url_path = rutils.quote(path)
                    share_url = f"{RCLONE_SERVE_URL}/{remote}/{url_path}"
                    if mime_type == "Folder":
                        share_url += "/"
                    buttons.button_link(
                        "RClone Link",
                        await sync_to_async(short_url, share_url, self.user_id),
                    )
                    if stream_link := get_stream_link(
                        mime_type, f"{remote}/{url_path}"
                    ):
                        buttons.button_link(
                            "Stream Link",
                            await sync_to_async(short_url, stream_link, self.user_id),
                        )
                if not rclonePath:
                    INDEX_URL = ""
                    if self.privateLink:
                        INDEX_URL = self.user_dict.get("index_url", "")
                    elif config_dict["INDEX_URL"]:
                        INDEX_URL = config_dict["INDEX_URL"]

                    if INDEX_URL:
                        url_path = rutils.quote(self.name)
                        share_url = f"{INDEX_URL}/{url_path}"
                        if mime_type == "Folder":
                            share_url = await sync_to_async(
                                short_url, f"{share_url}/", self.user_id
                            )
                            buttons.button_link("Index Link", share_url)
                        else:
                            share_url = await sync_to_async(
                                short_url, share_url, self.user_id
                            )
                            buttons.button_link("Index Link", share_url)
                            if config_dict["VIEW_LINK"]:
                                share_urls = await sync_to_async(
                                    short_url,
                                    f"{INDEX_URL}/{url_path}?a=view",
                                    self.user_id,
                                )
                                buttons.button_link("View Link", share_urls)
            else:
                msg += f"\n\n<b>Path:</b> <code>{rclonePath}</code>"
            if (but_key := config_dict["BUTTON_FOUR_NAME"]) and (
                but_url := config_dict["BUTTON_FOUR_URL"]
            ):
                buttons.button_link(but_key, but_url)
            if (but_key := config_dict["BUTTON_FIVE_NAME"]) and (
                but_url := config_dict["BUTTON_FIVE_URL"]
            ):
                buttons.button_link(but_key, but_url)
            if (but_key := config_dict["BUTTON_SIX_NAME"]) and (
                but_url := config_dict["BUTTON_SIX_URL"]
            ):
                buttons.button_link(but_key, but_url)
            if config_dict["SOURCE_LINK"]:
                scr_link = get_link(self.message)
                if is_magnet(scr_link):
                    tele = TelePost(config_dict["SOURCE_LINK_TITLE"])
                    mag_link = await sync_to_async(
                        tele.create_post,
                        f"<code>{escape(self.name)}<br>({size})</code><br>{scr_link}",
                    )
                    buttons.button_link("Source Link", mag_link)
                elif is_url(scr_link):
                    buttons.button_link("Source Link", scr_link)
            if config_dict["SAVE_MESSAGE"] and self.isSuperChat:
                buttons.button_data("Save Message", "save", "footer")
            uploadmsg = await sendingMessage(
                msg, self.message, images, buttons.build_menu(2)
            )
            if STICKERID_MIRROR := config_dict["STICKERID_MIRROR"]:
                await sendSticker(STICKERID_MIRROR, self.message)
            if chat_id := config_dict["MIRROR_LOG"]:
                await copyMessage(chat_id, uploadmsg)
            if is_pm_enabled(self.user_id, self.user_dict) and self.isSuperChat:
                button = (
                    await default_button(uploadmsg)
                    if config_dict["SAVE_MESSAGE"]
                    else uploadmsg.reply_markup
                )
                if reply_to and is_media(reply_to):
                    await sendMedia(msg, self.user_id, reply_to, button)
                else:
                    await copyMessage(self.user_id, uploadmsg, button)
            if self.seed:
                if self.newDir:
                    await clean_target(self.newDir, True)
                elif self.compress:
                    await clean_target(ospath.join(self.dir, self.name), True)
                async with queue_dict_lock:
                    if self.mid in non_queued_up:
                        non_queued_up.remove(self.mid)
                await start_from_queued()
                return
        if (
            config_dict["DAILY_MODE"]
            and not self.isClone
            and not is_premium_user(self.user_id)
        ):
            await UserDaily(self.user_id).set_daily_limit(daily_size)
        await clean_download(self.dir)
        async with task_dict_lock:
            task_dict.pop(self.mid, None)
            count = len(task_dict)
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id)

        async with queue_dict_lock:
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()

        if self.isSuperChat and (
            stime := config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
        ):
            bot_loop.create_task(
                auto_delete_message(self.message, uploadmsg, reply_to, stime=stime)
            )

    async def onDownloadError(self, error, listfile=None):
        async with task_dict_lock:
            task_dict.pop(self.mid, None)
            count = len(task_dict)
            self.removeFromSameDir()
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id)
        if (
            self.isSuperChat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and DATABASE_URL
        ):
            await DbManager().rm_complete_task(self.message.link)

        if not isinstance(error, str):
            error = str(error)
        reply_to = self.message.reply_to_message
        dt_date, dt_time = get_date_time(self.message)
        TIME_ZONE_TITLE = config_dict["TIME_ZONE_TITLE"]
        if (chat_id := config_dict["LINK_LOG"]) and self.isSuperChat:
            msg = "<b>LINK LOGS</b>\n"
            if self.name:
                msg += f"<code>{self.name}</code>\n"
            msg += (
                f"<b>Cc: </b>{self.tag}\n"
                f"<b>ID: </b><code>{self.user_id}</code>\n"
                f"<b>Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
                f"<b>Action: </b>{action(self.message)}\n"
                f"<b>Status: </b>#undone\n"
                f"<b>On: </b>{'#clone' if self.isClone else '#download'}\n"
                f"<b>Source Link:</b>\n<code>{get_link(self.message, get_source=True)}</code>"
            )
            if reply_to and is_media(reply_to):
                await sendMedia(msg, chat_id, reply_to)
            else:
                await sendCustom(msg, chat_id)
        if len(error) > (1000 if config_dict["ENABLE_IMAGE_MODE"] else 3800):
            err_msg = await sync_to_async(
                TelePost("Download Error").create_post, error.replace("\n", "<br>")
            )
            err_msg = f'<a href="{err_msg}"><b>Details</b></a>'
        else:
            err_msg = escape(error)
        msg = f"<b>{'Clone' if self.isClone else 'Download'} Has Been Stopped!</b>\n"
        if self.name:
            msg += f"<code>{self.name}</code>\n"
        msg += (
            f"<b>Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
            f"<b>Cc:</b> {self.tag}\n"
            f"<b>Action: </b>{action(self.message)}\n"
            f"<b>Due to:</b> {err_msg}"
        )
        if listfile:
            await sendFile(self.message, listfile, msg, config_dict["IMAGE_HTML"])
        else:
            await sendingMessage(
                msg,
                self.message,
                choice(config_dict["IMAGE_COMPLETE"].split())
                if config_dict["IMAGE_COMPLETE"]
                else "",
            )

        if (
            sticker := config_dict["STICKERID_MIRROR"]
            if "already in drive" in error.lower()
            else config_dict["STICKERID_ERROR"]
        ):
            await sendSticker(sticker, self.message)

        async with queue_dict_lock:
            if self.mid in queued_dl:
                queued_dl[self.mid].set()
                del queued_dl[self.mid]
            if self.mid in queued_up:
                queued_up[self.mid].set()
                del queued_up[self.mid]
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await gather(
            start_from_queued(), clean_download(self.dir), clean_download(self.newDir)
        )

        if self.isSuperChat and (
            stime := config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
        ):
            bot_loop.create_task(
                auto_delete_message(self.message, reply_to, stime=stime)
            )

    async def onUploadError(self, error):
        async with task_dict_lock:
            task_dict.pop(self.mid, None)
            count = len(task_dict)
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id)
        if (
            self.isSuperChat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and DATABASE_URL
        ):
            await DbManager().rm_complete_task(self.message.link)

        if not isinstance(error, str):
            error = str(error)
        buttons = ButtonMaker()
        dt_date, dt_time = get_date_time(self.message)
        reply_to = self.message.reply_to_message
        TIME_ZONE_TITLE = config_dict["TIME_ZONE_TITLE"]
        if (chat_id := config_dict["LINK_LOG"]) and self.isSuperChat:
            msg = "<b>LINK LOGS</b>\n"
            if self.name:
                msg += f"<code>{self.name}</code>\n"
            msg += (
                f"<b>Cc: </b>{self.tag}\n"
                f"<b>ID: </b><code>{self.user_id}</code>\n"
                f"<b>Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
                f"<b>Action: </b>{action(self.message)}\n"
                f"<b>Status: </b>{'#done' if 'Seeding' in error else '#undone'}\n"
                f"<b>On: </b>{'#clone' if self.isClone else '#upload'}\n"
                f"<b>Source Link:</b>\n<code>{get_link(self.message, get_source=True)}</code>"
            )
            if reply_to and is_media(reply_to):
                await sendMedia(msg, chat_id, reply_to)
            else:
                await sendCustom(msg, chat_id)
        if len(error) > (1000 if config_dict["ENABLE_IMAGE_MODE"] else 3800):
            err_msg = await sync_to_async(
                TelePost("Upload Error").create_post, error.replace("\n", "<br>")
            )
            err_msg = f'<a href="{err_msg}"><b>Details</b></a>'
        else:
            err_msg = escape(error)
        msg = f"<b>{'Clone' if self.isClone else 'Upload'} Has Been Stopped!</b>\n"
        if self.name:
            msg += f"<code>{self.name}</code>\n"
        msg += (
            f"<b>Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
            f"<b>Cc:</b> {self.tag}\n"
            f"<b>Action: </b>{action(self.message)}\n"
            f"<b>Due to:</b> {err_msg}"
        )
        if self.isGofile:
            buttons.button_link("GoFile Link", self.isGofile)
            if config_dict["SAVE_MESSAGE"] and self.isSuperChat:
                buttons.button_data("Save Message", "save", "footer")
        await sendingMessage(
            msg,
            self.message,
            choice(config_dict["IMAGE_COMPLETE"].split())
            if config_dict["IMAGE_COMPLETE"]
            else "",
            buttons.build_menu(1),
        )

        if (
            sticker := config_dict["STICKERID_MIRROR"]
            if any(x in error for x in ["Seeding", "Downloaded"])
            else config_dict["STICKERID_ERROR"]
        ):
            await sendSticker(sticker, self.message)

        async with queue_dict_lock:
            if self.mid in queued_dl:
                queued_dl[self.mid].set()
                del queued_dl[self.mid]
            if self.mid in queued_up:
                queued_up[self.mid].set()
                del queued_up[self.mid]
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await gather(
            start_from_queued(), clean_download(self.dir), clean_download(self.newDir)
        )

        if self.isSuperChat and (
            stime := config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
        ):
            bot_loop.create_task(
                auto_delete_message(self.message, reply_to, stime=stime)
            )
