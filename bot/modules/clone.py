from aiofiles.os import path as aiopath
from asyncio import gather
from json import loads
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from secrets import token_urlsafe
from urllib.parse import urlparse

from bot import bot, task_dict, task_dict_lock, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import (
    is_premium_user,
    sync_to_async,
    new_task,
    cmd_exec,
    arg_parser,
)
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.help_messages import HelpString
from bot.helper.ext_utils.links_utils import (
    is_magnet,
    is_gdrive_link,
    is_sharer_link,
    is_rclone_path,
    is_url,
    is_gdrive_id,
    get_link,
)
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.task_manager import stop_duplicate_check
from bot.helper.listeners.tasks_listener import TaskListener
from bot.helper.mirror_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)
from bot.helper.mirror_utils.gdrive_utlis.clone import gdClone
from bot.helper.mirror_utils.gdrive_utlis.count import gdCount
from bot.helper.mirror_utils.gdrive_utlis.helper import GoogleDriveHelper
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    editMessage,
    sendMessage,
    deleteMessage,
    sendStatusMessage,
    auto_delete_message,
)


class Clone(TaskListener):
    def __init__(
        self,
        client: Client,
        message: Message,
        _=False,
        __=False,
        ___=None,
        ____=None,
        _____=None,
        bulk=None,
        multiTag=None,
        options="",
    ):
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multiTag = multiTag
        self.options = options
        self.sameDir = {}
        self.bulk = bulk
        self.newname = ""
        super().__init__()
        self.isClone = True

    @new_task
    async def newEvent(self):
        text = self.message.text.split("\n")
        await self.getTag(text)

        if fmsg := await UseCheck(self.message).run(session=True):
            await auto_delete_message(self.message, fmsg, self.message.reply_to_message)
            return

        arg_base = {"link": "", "-i": 0, "-b": False, "-n": "", "-up": "", "-rcf": ""}
        input_list = text[0].split(" ")
        args = arg_parser(input_list[1:], arg_base)

        self.link = args["link"]
        self.newname = args["-n"].replace("/", "")
        self.rcFlags = args["-rcf"]
        self.upDest = args["-up"]
        self.isRename = self.newname

        isBulk = args["-b"]
        bulk_start = bulk_end = 0

        try:
            self.multi = int(args["-i"])
        except:
            self.multi = 0

        if not isinstance(isBulk, bool):
            dargs = isBulk.split(":")
            bulk_start = dargs[0] or None
            if len(dargs) == 2:
                bulk_end = dargs[1] or None
            isBulk = True

        if (
            config_dict["PREMIUM_MODE"]
            and not is_premium_user(self.user_id)
            and (self.multi > 0 or isBulk)
        ):
            await sendMessage(
                "Upss, multi/bulk mode for premium user only", self.message
            )
            return

        if isBulk:
            await self.initBulk(input_list, bulk_start, bulk_end, Clone)
            return

        self.link = self.link or get_link(self.message)

        if self.bulk:
            del self.bulk[0]

        self.run_multi(input_list, "", Clone)

        if self.link:
            LOGGER.info(self.link)

        self.editable = await sendMessage(
            "<i>Checking request, please wait...</i>", self.message
        )
        self.isSharer = is_sharer_link(self.link)
        if self.isSharer:
            await editMessage(
                f"<i>Checking {urlparse(self.link).netloc} link...</i>\n<code>{self.link}</code>",
                self.editable,
            )
            try:
                self.link = await sync_to_async(direct_link_generator, self.link)
            except DirectDownloadLinkException as e:
                await editMessage(f"{self.tag}, {e}", self.editable)
                return

        if not self.link or is_magnet(self.link):
            await gather(
                editMessage(HelpString.CLONE, self.editable),
                auto_delete_message(
                    self.message, self.editable, self.message.reply_to_message
                ),
            )
            return

        try:
            await self.beforeStart()
        except Exception as e:
            await editMessage(str(e), self.editable)
            return

        await self._proceedToClone()

    async def _proceedToClone(self):
        if (is_gdrive_link(self.link) or is_gdrive_id(self.link)) and is_gdrive_id(
            self.upDest
        ):
            self.name, mime_type, size, files, _ = await sync_to_async(
                gdCount().count, self.link, self.user_id
            )
            if not mime_type:
                await editMessage(self.name, self.editable)
                return
            file, _ = await stop_duplicate_check(self)
            if file:
                LOGGER.info("File/folder already in Drive!")
                await gather(
                    deleteMessage(self.editable),
                    self.onDownloadError("File/folder already in Drive!", file),
                )
                return
            if CLONE_LIMIT := config_dict["CLONE_LIMIT"]:
                if size > CLONE_LIMIT * 1024**3:
                    await gather(
                        deleteMessage(self.editable),
                        self.onDownloadError(
                            f"Clone limit is {CLONE_LIMIT}GB. File/folder size is {get_readable_file_size(size)}."
                        ),
                    )
                    return
            await self.onDownloadStart()
            LOGGER.info("Clone Started: Name: %s - Source: %s", self.name, self.link)
            drive = gdClone(self)
            if files <= 10:
                await editMessage(
                    f"<i>Found GDrive link to clone...</i>\n<code>{self.link}</code>",
                    self.editable,
                )
                link, size, mime_type, files, folders, dir_id = await sync_to_async(
                    drive.clone
                )
                await deleteMessage(self.editable)
            else:
                gid = token_urlsafe(12)
                async with task_dict_lock:
                    task_dict[self.mid] = GdriveStatus(self, drive, size, gid, "cl")
                await gather(
                    deleteMessage(self.editable), sendStatusMessage(self.message)
                )
                link, size, mime_type, files, folders, dir_id = await sync_to_async(
                    drive.clone
                )
            if not link:
                return
            if is_url(link):
                LOGGER.info("Cloning Done: %s", self.name)
                await self.onUploadComplete(
                    link, size, files, folders, mime_type, dir_id=dir_id
                )
            else:
                await sendMessage(link, self.message)
        elif is_rclone_path(self.upDest) and (
            is_rclone_path(self.link) or is_gdrive_link(self.link)
        ):
            user_config = f"rclone/{self.user_id}.conf"
            if self.link.startswith("mrcc:"):
                self.link = self.link.replace("mrcc:", "", 1)
                self.upDest = self.upDest.replace("mrcc:", "", 1)
                config_path = user_config
            else:
                config_path = "rclone.conf"
            if not await aiopath.exists(config_path):
                await editMessage(
                    f"RClone config: {config_path} not exists!", self.editable
                )
                return

            if is_gdrive_link(self.link):
                if self.isRename:
                    await editMessage(
                        "Clone drive link with rclone does't support rename!",
                        self.editable,
                    )
                    return
                remote = src_path = None
                drive_id = GoogleDriveHelper().getIdFromUrl(self.link, self.user_id)
                if not drive_id:
                    await editMessage(
                        "Google Drive ID could not be found in the provided link",
                        self.editable,
                    )
                    return
                await editMessage(
                    f"<i>Getting detail from</i>\n<code>{self.link}</code>",
                    self.editable,
                )
                self.name, mime_type, size, files, folders = await sync_to_async(
                    gdCount().count, self.link, self.user_id
                )
                await deleteMessage(self.editable)
                if CLONE_LIMIT := config_dict["CLONE_LIMIT"]:
                    if size > CLONE_LIMIT * 1024**3:
                        await self.onDownloadError(
                            f"Clone limit is {CLONE_LIMIT}GB. File/folder size is {get_readable_file_size(size)}."
                        )
                        return
            else:
                drive_id = None
                remote, src_path = self.link.split(":", 1)
                src_path = src_path.strip("/")
                cmd = [
                    "wzone",
                    "lsjson",
                    "--fast-list",
                    "--stat",
                    "--no-modtime",
                    "--config",
                    config_path,
                    f"{remote}:{src_path}",
                ]
                res = await cmd_exec(cmd)
                if res[2] != 0:
                    if res[2] != -9:
                        msg = f"Error: While getting rclone stat. Path: {remote}:{src_path}. Stderr: {res[1][:4000]}"
                        await editMessage(msg, self.editable)
                    return
                await deleteMessage(self.editable)
                rstat = loads(res[0])
                if rstat["IsDir"]:
                    self.name = src_path.rsplit("/", 1)[-1] if src_path else remote
                    self.upDest += (
                        self.name if self.upDest.endswith(":") else f"/{self.name}"
                    )
                    mime_type = "Folder"
                else:
                    self.name = src_path.rsplit("/", 1)[-1]
                    mime_type = rstat["MimeType"]

            await self.onDownloadStart()
            RCTransfer = RcloneTransferHelper(self)
            LOGGER.info(
                "Clone Started: Name: %s - Source: %s - Destination: %s",
                self.name,
                self.link,
                self.upDest,
            )
            gid = token_urlsafe(12)
            async with task_dict_lock:
                task_dict[self.mid] = RcloneStatus(self, RCTransfer, gid, "cl")
            if self.multi <= 1:
                await sendStatusMessage(self.message)
            link, destination = await RCTransfer.clone(
                config_path, remote, src_path, mime_type, drive_id
            )
            if not destination:
                return

            LOGGER.info("Cloning Done: %s", self.name)
            cmd1 = [
                "wzone",
                "lsf",
                "--fast-list",
                "-R",
                "--files-only",
                "--config",
                config_path,
                destination,
            ]
            cmd2 = [
                "wzone",
                "lsf",
                "--fast-list",
                "-R",
                "--dirs-only",
                "--config",
                config_path,
                destination,
            ]
            cmd3 = [
                "wzone",
                "size",
                "--fast-list",
                "--json",
                "--config",
                config_path,
                destination,
            ]
            res1, res2, res3 = await gather(
                cmd_exec(cmd1), cmd_exec(cmd2), cmd_exec(cmd3)
            )
            if res1[2] != res2[2] != res3[2] != 0:
                if res1[2] == -9:
                    return
                files = folders = None
                size = 0
                LOGGER.error(
                    "Error: While getting rclone stat. Path: %s. Stderr: %s",
                    destination,
                    res1[1][:4000],
                )
            else:
                files, folders = len(res1[0].split("\n")), len(res2[0].split("\n"))
                rsize = loads(res3[0])
                size = rsize["bytes"]
            await self.onUploadComplete(
                link, size, files, folders, mime_type, destination
            )
        else:
            await gather(
                editMessage(HelpString.CLONE, self.editable),
                auto_delete_message(
                    self.message, self.editable, self.message.reply_to_message
                ),
            )


async def clone(client: Client, message: Message):
    Clone(client, message).newEvent()


bot.add_handler(
    MessageHandler(
        clone, filters=command(BotCommands.CloneCommand) & CustomFilters.authorized
    )
)
