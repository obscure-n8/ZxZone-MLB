from aiofiles.os import path as aiopath, makedirs, rename as aiorename
from aioshutil import move
from asyncio import sleep, gather, create_subprocess_exec
from asyncio.subprocess import PIPE
from glob import glob
from natsort import natsorted
from os import walk, path as ospath
from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import Message
from secrets import token_urlsafe

from bot import (
    bot_name,
    bot_dict,
    bot_lock,
    config_dict,
    user_data,
    multi_tags,
    task_dict,
    task_dict_lock,
    cpu_eater_lock,
    subprocess_lock,
    GLOBAL_EXTENSION_FILTER,
    LOGGER,
    DEFAULT_SPLIT_SIZE,
    FFMPEG_NAME,
)
from bot.helper.ext_utils.bot_utils import (
    new_task,
    sync_to_async,
    is_premium_user,
    update_user_ldata,
    getSizeBytes,
)
from bot.helper.ext_utils.bulk_links import extractBulkLinks
from bot.helper.ext_utils.conf_loads import intialize_savebot
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive
from bot.helper.ext_utils.files_utils import (
    is_archive,
    is_archive_split,
    is_first_archive_split,
    get_base_name,
    clean_target,
    get_path_size,
)
from bot.helper.ext_utils.links_utils import (
    is_gdrive_id,
    is_rclone_path,
    is_gdrive_link,
    is_tele_link,
)
from bot.helper.ext_utils.media_utils import (
    createThumb,
    get_document_type,
    SampleVideo,
    createArchive,
    split_file,
)
from bot.helper.mirror_utils.gdrive_utlis.list import gdriveList
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.ffmpeg_status import FFMpegStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    deleteMessage,
    sendMessage,
    sendStatusMessage,
    get_tg_link_message,
)


class TaskConfig:
    def __init__(self):
        self.mid: int = self.message.id
        self.user_id: int = None
        self.user_dict: dict = {}
        self.dir: str | dict = f"{config_dict['DOWNLOAD_DIR']}{self.mid}"
        self.link: str = ""
        self.upDest: str = ""
        self.rcFlags: str = ""
        self.tag: str = ""
        self.name: str = ""
        self.newDir: str = ""
        self.isRename: str = ""
        self.splitSize: int = 0
        self.maxSplitSize: int = 0
        self.multi: int = 0
        self.isLeech = False
        self.isQbit = False
        self.isJd = False
        self.isClone = False
        self.isYtDlp = False
        self.equalSplits: bool = False
        self.isSharer: bool = False
        self.extract: bool = False
        self.compress: bool = False
        self.select: bool = False
        self.seed: bool = False
        self.join: bool = False
        self.privateLink: bool = False
        self.stopDuplicate: bool = False
        self.sampleVideo: bool = False
        self.screenShots: bool = False
        self.as_doc: bool = False
        self.isGofile: bool = False
        self.suproc: create_subprocess_exec | str = None
        self.thumb: str = None
        self.vidMode: list = None
        self.session: Client = None
        self.editable: Message = None
        self.isSuperChat: bool = self.message.chat.type.name in (
            "SUPERGROUP",
            "CHANNEL",
        )
        self._intialize_user()

    def _intialize_user(self):
        if self.message.from_user:
            self.user_id = self.message.from_user.id
            self.user_dict = user_data.get(self.user_id, {})

        if self.user_dict.get("excluded_extensions", False):
            self.extensionFilter = self.user_dict["excluded_extensions"]
        elif "excluded_extensions" not in self.user_dict:
            self.extensionFilter = GLOBAL_EXTENSION_FILTER
        else:
            self.extensionFilter = ["aria2", "!qB"]

    def getTokenPath(self, dest: str, force: bool = False):
        use_sa = self.user_dict.get("use_sa")
        if (
            dest.startswith("mtp:")
            or force
            and not dest.startswith("tp:")
            and not dest.startswith("sa:")
            and not use_sa
        ):
            return f"tokens/{self.user_id}.pickle"
        if (
            dest.startswith("sa:")
            or (use_sa or config_dict["USE_SERVICE_ACCOUNTS"])
            and not dest.startswith("tp:")
        ):
            return "accounts"
        return "token.pickle"

    def getConfigPath(self, dest: str):
        return (
            f"rclone/{self.user_id}.conf"
            if dest.startswith("mrcc:") or dest == self.user_dict.get("rclone_path")
            else "rclone.conf"
        )

    async def isTokenExists(self, path, status):
        if is_rclone_path(path):
            config_path = self.getConfigPath(path)
            if config_path != "rclone.conf" and status == "up":
                self.privateLink = True
            if not await aiopath.exists(config_path):
                err = f"RClone config: <b>{config_path}</b> not exists! Upload your own <b>rclone.conf</b> on /{BotCommands.UserSetCommand}."
                if status == "up":
                    err += "\n\n<i>*Switch to <b>Drive API</b> engine if using <b>token.pickle</b>.</i>"
                raise ValueError(err)
        elif (
            status == "dl"
            and is_gdrive_link(path)
            or status == "up"
            and is_gdrive_id(path)
        ):
            force = (
                not await aiopath.exists("token.pickle")
                and not await aiopath.exists("accounts")
                if status == "dl"
                else path == self.user_dict.get("gdrive_id")
            )
            token_path = self.getTokenPath(path, force)
            if token_path.startswith("tokens/") and status == "up":
                self.privateLink = True
            if not await aiopath.exists(token_path):
                err = f"SAccounts or token.pickle: <b>{token_path}</b> not exists! Upload your own <b>token.pickle</b> on /{BotCommands.UserSetCommand}."
                if status == "up":
                    err += "\n\n<i>*Switch to <b>RClone</b> engine if using <b>rclone.conf</b>.</i>"
                raise ValueError(err)

    async def beforeStart(self):
        if self.user_dict.get("use_sa") and not await aiopath.exists("accounts"):
            self.user_dict["use_sa"] = False
            await update_user_ldata(self.user_id, "use_sa", False)

        if self.splitSize:
            if self.splitSize.isdigit():
                self.splitSize = int(self.splitSize)
            else:
                self.splitSize = getSizeBytes(self.splitSize)
        self.splitSize = (
            self.splitSize
            or self.user_dict.get("split_size")
            or config_dict["LEECH_SPLIT_SIZE"]
        )
        self.equalSplits = (
            self.user_dict.get("equal_splits")
            or config_dict["EQUAL_SPLITS"]
            and "equal_splits" not in self.user_dict
        )
        async with bot_lock:
            self.maxSplitSize = bot_dict["MAX_SPLIT_SIZE"]
        if (
            config_dict["PREMIUM_MODE"]
            and not is_premium_user(self.user_id)
            and self.splitSize > DEFAULT_SPLIT_SIZE
        ):
            self.splitSize = DEFAULT_SPLIT_SIZE
        self.splitSize = min(self.splitSize, self.maxSplitSize)

        if not self.isYtDlp and not self.isJd:
            if self.link not in ["rcl", "gdl"]:
                await self.isTokenExists(self.link, "dl")
            elif self.link == "rcl":
                self.link = await RcloneList(self).get_rclone_path("rcd")
                if not is_rclone_path(self.link):
                    raise ValueError(self.link)
            elif self.link == "gdl":
                self.link = await gdriveList(self).get_target_id("gdd")
                if not is_gdrive_id(self.link):
                    raise ValueError(self.link)

        if not self.isLeech:
            self.isGofile = (
                self.isGofile
                and config_dict["GOFILE"]
                and config_dict["GOFILETOKEN"]
                and config_dict["GOFILEBASEFOLDER"]
            )
            self.stopDuplicate = (
                self.user_dict.get("stop_duplicate")
                or "stop_duplicate" not in self.user_dict
                and config_dict["STOP_DUPLICATE"]
            )
            default_upload = (
                self.user_dict.get("default_upload", "")
                or config_dict["DEFAULT_UPLOAD"]
            )
            if (not self.upDest and default_upload == "rc") or self.upDest == "rc":
                self.upDest = (
                    self.user_dict.get("rclone_path") or config_dict["RCLONE_PATH"]
                )
            elif (not self.upDest and default_upload == "gd") or self.upDest == "gd":
                self.upDest = (
                    self.user_dict.get("gdrive_id") or config_dict["GDRIVE_ID"]
                )
            if not self.upDest:
                raise ValueError(
                    f"No upload destination! Try set default destination for drive or rclone on /{BotCommands.UserSetCommand} or use direct upload with arg <code>-up rcl</code> or <code>-up gdl</code>."
                )
            if not is_gdrive_id(self.upDest) and not is_rclone_path(self.upDest):
                raise ValueError(
                    "Wrong upload destination! Make sure is corrent destination (rclone path, gdrive path or gdrive id)."
                )
            if self.upDest not in ["rcl", "gdl"]:
                await self.isTokenExists(self.upDest, "up")

            if self.upDest == "rcl":
                if self.isClone:
                    if not is_rclone_path(self.link) and not is_gdrive_link(self.link):
                        raise ValueError(
                            "You can't clone from different types of tools!"
                        )
                    config_path = self.getConfigPath(self.link)
                else:
                    config_path = None
                self.upDest = await RcloneList(self).get_rclone_path("rcu", config_path)
                if not is_rclone_path(self.upDest):
                    raise ValueError(self.upDest)
            elif self.upDest == "gdl":
                if self.isClone:
                    if not is_gdrive_link(self.link):
                        raise ValueError(
                            "You can't clone from different types of tools!"
                        )
                    token_path = self.getTokenPath(
                        self.link, not await aiopath.exists("accounts")
                    )
                else:
                    token_path = None
                self.upDest = await gdriveList(self).get_target_id("gdu", token_path)
                if not is_gdrive_id(self.upDest):
                    raise ValueError(self.upDest)
            elif self.isClone:
                if is_gdrive_link(self.link) and (
                    self.getTokenPath(self.link) != self.getTokenPath(self.upDest)
                ):
                    raise ValueError("You must use the same token to clone!")
                if is_rclone_path(self.link) and (
                    self.getConfigPath(self.link) != self.getConfigPath(self.upDest)
                ):
                    raise ValueError("You must use the same config to clone!")

            if not self.privateLink:
                self.stopDuplicate = config_dict["STOP_DUPLICATE"]

            if self.user_dict.get("use_sa"):
                self.privateLink = True
        else:
            if self.upDest:
                try:
                    user = await self.client.get_chat_member(self.upDest, bot_name)
                    if user.status != ChatMemberStatus.ADMINISTRATOR:
                        raise ValueError(
                            f"Ups, requires chat admin privileges to this chat <code>{self.upDest}</code> to send leech result!"
                        )
                except:
                    raise ValueError(
                        f"Bot doesn't have permission to this chat <code>{self.upDest}</code> to send leech result!"
                    )

            self.upDest = self.upDest or self.user_dict.get("dump_ch", "") or ""
            if isinstance(self.upDest, str) and (
                self.upDest.isdigit()
                or self.upDest.startswith("-")
                and self.upDest[1:].isdigit()
            ):
                self.upDest = int(self.upDest)

            self.as_doc = self.user_dict.get("as_doc", False) or (
                config_dict["AS_DOCUMENT"] and "as_doc" not in self.user_dict
            )

            if is_tele_link(self.thumb):
                await intialize_savebot(
                    self.user_dict.get("session_string"), True, self.user_id
                )
                msg = (await get_tg_link_message(self.thumb, self.user_id))[1]
                self.thumb = await createThumb(msg) if msg.photo or msg.document else ""
                await deleteMessage(msg)

    async def getTag(self, text: list[str]):
        if len(text) > 1 and text[1].startswith("Tag: "):
            try:
                id_ = int(text[1].split()[-1])
                self.message.from_user = await self.client.get_users(id_)
                self._intialize_user()
                await self.message.unpin()
            except:
                pass
        reply = self.message.reply_to_message
        if (
            reply
            and not reply.sender_chat
            and not getattr(reply.from_user, "is_bot", None)
        ):
            self.tag = reply.from_user.mention
        else:
            self.tag = self.message.from_user.mention

    @new_task
    async def run_multi(self, input_list: list, folder_name: str, obj, retry=0):
        await sleep(config_dict["MULTI_TIMEGAP"])
        if not self.multiTag and self.multi > 1:
            self.multiTag = token_urlsafe(3)
            multi_tags.add(self.multiTag)
        elif self.multi <= 1:
            multi_tags.discard(self.multiTag)
            return
        if self.multiTag and self.multiTag not in multi_tags:
            await gather(
                sendMessage(
                    f"{self.tag}, Multi Task has been cancelled!", self.message
                ),
                sendStatusMessage(self.message),
            )
            return
        if len(self.bulk) != 0:
            msg = input_list[:1]
            msg.append(f"{self.bulk[0]} -i {self.multi - 1} {self.options}")
            msgts = " ".join(msg)
            if self.multi > 2:
                msgts += f"\nCancel Multi: <code>/{BotCommands.CancelTaskCommand} {self.multiTag}</code>"
            nextmsg = await sendMessage(msgts, self.message)
        else:
            msg = [s.strip() for s in input_list]
            index = msg.index("-i")
            msg[index + 1] = f"{self.multi - 1}"
            try:
                nextmsg = await self.client.get_messages(
                    self.message.chat.id, self.message.reply_to_message_id + 1
                )
            except Exception as e:
                LOGGER.error(e)
                await sendMessage(
                    f"Failed fetch next message to run multi, ERROR: {e}!", self.message
                )
                return
            msgts = " ".join(msg)
            if self.multi > 2:
                msgts += f"\nCancel Multi: <code>/{BotCommands.CancelTaskCommand} {self.multiTag}</code>"
            nextmsg = await sendMessage(msgts, nextmsg)
            if not nextmsg:
                if retry < 3:
                    self.message.reply_to_message_id = (
                        self.message.reply_to_message_id + 1
                    )
                    self.run_multi(input_list, folder_name, obj, retry + 1)
                else:
                    await sendMessage(
                        "Failed fetch next message to run multi, mostly have empty/invalid message between link/file!",
                        self.message,
                    )
                return
        nextmsg = await self.client.get_messages(self.message.chat.id, nextmsg.id)
        if folder_name:
            self.sameDir["tasks"].add(nextmsg.id)
        nextmsg.from_user = self.message.from_user
        obj(
            self.client,
            nextmsg,
            self.isQbit,
            self.isJd,
            self.isLeech,
            self.vidMode,
            self.sameDir,
            self.bulk,
            self.multiTag,
            self.options,
        ).newEvent()

    async def initBulk(
        self, input_list: list[str], bulk_start: str, bulk_end: str, obj
    ):
        try:
            self.bulk = await extractBulkLinks(self.message, bulk_start, bulk_end)
            if len(self.bulk) == 0:
                raise ValueError("Bulk Empty!")
            b_msg = input_list[:1]
            self.options = input_list[1:]
            index = self.options.index("-b")
            del self.options[index]
            if bulk_start or bulk_end:
                del self.options[index]
            self.options = " ".join(self.options)
            b_msg.append(f"{self.bulk[0]} -i {len(self.bulk)} {self.options}")
            nextmsg = await sendMessage(" ".join(b_msg), self.message)
            nextmsg = await self.client.get_messages(self.message.chat.id, nextmsg.id)
            nextmsg.from_user = self.message.from_user
            obj(
                self.client,
                nextmsg,
                self.isQbit,
                self.isJd,
                self.isLeech,
                self.vidMode,
                self.sameDir,
                self.bulk,
                self.multiTag,
                self.options,
            ).newEvent()
        except Exception as e:
            LOGGER.error(e)
            await sendMessage(
                "Reply to text file or to telegram message that have links seperated by new line!",
                self.message,
            )

    async def isOneFile(self, path: str):
        if ospath.isfile(path) or self.seed:
            return
        all_files = []
        for dirpath, _, files in await sync_to_async(walk, path):
            all_files.extend(
                (dirpath, file)
                for file in files
                if not file.endswith((".aria2", ".!qB"))
            )
        if len(all_files) == 1:
            dirpath, file = all_files[0]
            self.name = file
            await move(ospath.join(dirpath, file), self.dir)
            await clean_target(dirpath)
            return ospath.join(self.dir, self.name)

    async def reName(self):
        if not self.isRename:
            return
        all_files = []
        for dirpath, _, files in await sync_to_async(walk, self.dir):
            all_files.extend(
                (dirpath, file)
                for file in files
                if not file.endswith((".aria2", ".!qB"))
            )
        if all_files:
            dirpath, file = all_files[0]
            if len(all_files) == 1 and file != self.isRename:
                self.seed = False
                self.name = self.isRename
                await aiorename(
                    ospath.join(dirpath, file), ospath.join(dirpath, self.isRename)
                )

    async def preName(self, path: str):
        if self.isRename:
            return path

        prename, sufname, remname = (
            self.user_dict.get("prename"),
            self.user_dict.get("sufname"),
            self.user_dict.get("remname"),
        )

        def _rename_file(filename):
            if prename:
                filename = f"{prename} {filename}"
            if sufname:
                try:
                    fname, ext = filename.rsplit(".", maxsplit=1)
                    filename = f"{fname} {sufname}.{ext}"
                except:
                    pass
            if remname:
                for x in remname.split("|"):
                    filename = filename.replace(x, "")
            return filename

        if await aiopath.isfile(path):
            filename = ospath.basename(path)
            filedir = ospath.split(path)[0]
            new_filename = _rename_file(filename)
            newpath = ospath.join(filedir, new_filename)
            if any((prename, remname, sufname)):
                await aiorename(path, newpath)
            return newpath
        for dirpath, _, files in await sync_to_async(walk, path):
            for file in files:
                new_filename = _rename_file(file)
                if any((prename, remname, sufname)):
                    await aiorename(
                        ospath.join(dirpath, file), ospath.join(dirpath, new_filename)
                    )
        return path

    async def editMetadata(self, path: str, gid: str):
        if not (metadata := self.user_dict.get("metadata")):
            return
        self.newDir = f"{self.dir}10000"
        await makedirs(self.newDir, exist_ok=True)

        async def _run(
            base_dir: str, video_file: str, outfile: str, clean_metadata: bool = False
        ):
            if clean_metadata:
                cmd = [
                    FFMPEG_NAME,
                    "-hide_banner",
                    "-ignore_unknown",
                    "-loglevel",
                    "error",
                    "-i",
                    video_file,
                    "-fflags",
                    "+bitexact",
                    "-flags:v",
                    "+bitexact",
                    "-flags:a",
                    "+bitexact",
                    "-map_metadata",
                    "-1",
                    "-map",
                    "0:v:0?",
                    "-map",
                    "0:a:?",
                    "-map",
                    "0:s:?",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-c:s",
                    "copy",
                    outfile,
                    "-y",
                ]
            else:
                cmd = [
                    FFMPEG_NAME,
                    "-hide_banner",
                    "-ignore_unknown",
                    "-loglevel",
                    "error",
                    "-i",
                    video_file,
                    "-metadata",
                    f"title={metadata}",
                    "-metadata:s:v",
                    f"title={metadata}",
                    "-metadata:s:a",
                    f"title={metadata}",
                    "-metadata:s:s",
                    f"title={metadata}",
                    "-map",
                    "0:v:0?",
                    "-map",
                    "0:a:?",
                    # f'title={metadata}', '-map', '0:v:0?', '-map', '0:a:?',
                    "-map",
                    "0:s:?",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-c:s",
                    "copy",
                    outfile,
                    "-y",
                ]
            self.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
            _, stderr = await self.suproc.communicate()
            if self.suproc.returncode == 0:
                await clean_target(video_file)
                self.seed = False
                await move(outfile, base_dir)
            else:
                LOGGER.error(
                    "%s. Changing metadata failed, Path %s",
                    stderr.decode().strip(),
                    video_file,
                )

            if clean_metadata:
                cleaned_file = ospath.join(base_dir, ospath.basename(outfile))
                await _run(base_dir, cleaned_file, outfile)

        async with task_dict_lock:
            task_dict[self.mid] = FFMpegStatus(self, None, gid, "meta")

        clean_metadata = self.user_dict.get("clean_metadata")
        if await aiopath.isfile(path) and (await get_document_type(path))[0]:
            base_dir, file_name = ospath.split(path)
            outfile = ospath.join(self.newDir, file_name)
            await _run(base_dir, path, outfile, clean_metadata)
        elif await aiopath.isdir(path):
            for dirpath, _, files in await sync_to_async(walk, path):
                for file in files:
                    if (
                        self.suproc == "cancelled"
                        or self.suproc is not None
                        and self.suproc.returncode == -9
                    ):
                        return
                    video_file = ospath.join(dirpath, file)
                    if (await get_document_type(video_file))[0]:
                        outfile = ospath.join(self.newDir, file)
                        await _run(dirpath, video_file, outfile, clean_metadata)

    async def proceedExtract(self, dl_path: str, size: int, gid: str):
        pswd = self.extract if isinstance(self.extract, str) else ""
        try:
            LOGGER.info("Extracting: %s", self.name)
            async with task_dict_lock:
                task_dict[self.mid] = ExtractStatus(self, size, gid)
            if await aiopath.isdir(dl_path):
                if self.seed:
                    self.newDir = f"{self.dir}10000"
                    up_path = ospath.join(self.newDir, self.name)
                else:
                    up_path = dl_path
                for dirpath, _, files in await sync_to_async(
                    walk, dl_path, topdown=False
                ):
                    for file_ in natsorted(files):
                        if (
                            is_first_archive_split(file_)
                            or is_archive(file_)
                            and not file_.endswith(".rar")
                        ):
                            f_path = ospath.join(dirpath, file_)
                            t_path = (
                                dirpath.replace(self.dir, self.newDir)
                                if self.seed
                                else dirpath
                            )
                            cmd = [
                                "7z",
                                "x",
                                f"-p{pswd}",
                                f_path,
                                f"-o{t_path}",
                                "-aot",
                                "-xr!@PaxHeader",
                            ]
                            if not pswd:
                                del cmd[2]
                            async with subprocess_lock:
                                if self.suproc == "cancelled":
                                    return
                                self.suproc = await create_subprocess_exec(
                                    *cmd, stderr=PIPE
                                )
                            _, stderr = await self.suproc.communicate()
                            code = self.suproc.returncode
                            if code == -9:
                                return
                            if code != 0:
                                LOGGER.error(
                                    "%s. Unable to extract archive splits!. Path: %s",
                                    stderr.decode().strip(),
                                    f_path,
                                )
                    if (
                        not self.seed
                        and self.suproc is not None
                        and self.suproc.returncode == 0
                    ):
                        for file_ in natsorted(files):
                            if is_archive_split(file_) or is_archive(file_):
                                del_path = ospath.join(dirpath, file_)
                                if not await clean_target(del_path):
                                    return
            else:
                up_path = get_base_name(dl_path)
                if self.seed:
                    self.newDir = f"{self.dir}10000"
                    up_path = up_path.replace(self.dir, self.newDir)
                cmd = [
                    "7z",
                    "x",
                    f"-p{pswd}",
                    dl_path,
                    f"-o{up_path}",
                    "-aot",
                    "-xr!@PaxHeader",
                ]
                if not pswd:
                    del cmd[2]
                async with subprocess_lock:
                    if self.suproc == "cancelled":
                        return
                    self.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
                _, stderr = await self.suproc.communicate()
                code = self.suproc.returncode
                if code == -9:
                    return
                if code == 0:
                    LOGGER.info("Extracted Path: %s", up_path)
                    if not self.seed and not await clean_target(dl_path):
                        return
                else:
                    LOGGER.error(
                        "%s. Unable to extract archive! Uploading anyway. Path: %s",
                        stderr.decode().strip(),
                        dl_path,
                    )
                    self.newDir = ""
                    up_path = dl_path
        except NotSupportedExtractionArchive:
            LOGGER.info(
                "Not any valid archive, uploading file as it is. Path: %s", dl_path
            )
            self.newDir = ""
            up_path = dl_path

        up_path = await self.preName(up_path)
        await self.editMetadata(up_path, gid)
        return up_path

    async def proceedCompress(self, dl_path: str, size: int, gid: str):
        dl_path = await self.preName(dl_path)
        await self.editMetadata(dl_path, gid)
        self.name = ospath.basename(dl_path)
        zipmode = self.user_dict.get("zipmode", "zfolder")
        zfpart = ""
        pswd = self.compress if isinstance(self.compress, str) else ""
        if zipmode in ["zfolder", "zfpart"]:
            async with task_dict_lock:
                task_dict[self.mid] = ZipStatus(self, size, gid)
            if self.seed and self.isLeech:
                self.newDir = f"{self.dir}10000"
                up_path = ospath.join(self.newDir, f"{self.name}.zip")
            elif not self.isLeech and zipmode == "zfpart":
                self.newDir = f"{self.dir}10000"
                base_name = (
                    self.name.rsplit(".", 1)[0]
                    if await aiopath.isfile(dl_path)
                    else self.name
                )
                zfpart = ospath.join(self.newDir, base_name)
                up_path = ospath.join(zfpart, f"{self.name}.zip")
            else:
                up_path = f"{dl_path}.zip"
            res = await createArchive(
                self, dl_path, up_path, size, pswd, zipmode == "zfpart"
            )
            if not res:
                return
            return zfpart or up_path

        self.seed = False
        org_path, archived = dl_path, []
        for dirpath, _, files in await sync_to_async(walk, self.dir):
            for file_ in natsorted(files):
                if self.suproc == "cancelled":
                    return
                fpath = ospath.join(dirpath, file_)
                if file_.lower().endswith(tuple(self.extensionFilter)):
                    if self.isLeech and file_.startswith("Thumb"):
                        continue
                    await clean_target(fpath)
                    continue
                size = await get_path_size(fpath)
                self.newDir = f"{self.dir}10000"
                dest_path = ospath.join(self.newDir, f"{file_}.zip")
                async with task_dict_lock:
                    task_dict[self.mid] = ZipStatus(self, size, gid, fpath)
                if zipmode == "zeach":
                    archived.append(
                        await createArchive(self, fpath, dest_path, size, pswd)
                    )
                elif zipmode == "zpart" or (
                    zipmode == "auto" and int(size) > self.splitSize
                ):
                    archived.append(
                        await createArchive(self, fpath, dest_path, size, pswd, True)
                    )
                for item in glob(f"{self.newDir}/*"):
                    await move(item, dirpath)
                await clean_target(self.newDir)
        if archived and not all(archived):
            return
        return org_path

    async def proceedSplit(
        self, up_dir: str, m_size: list, o_files: list, size: int, gid: str
    ):
        sp = False
        self.total_size = 0
        for dirpath, _, files in await sync_to_async(walk, up_dir, topdown=False):
            for file_ in files:
                f_path = ospath.join(dirpath, file_)
                f_size = await aiopath.getsize(f_path)
                if f_size > self.splitSize:
                    if not sp:
                        sp = SplitStatus(self, size, gid)
                        async with task_dict_lock:
                            task_dict[self.mid] = sp
                        LOGGER.info("Splitting (%s): %s", self.splitSize, self.name)
                    res = await split_file(
                        f_path, f_size, dirpath, self.splitSize, self, sp
                    )
                    if not res:
                        return
                    if res == "errored":
                        if f_size <= self.maxSplitSize:
                            continue
                        if not await clean_target(f_path):
                            return
                    elif not self.seed or self.newDir:
                        if not await clean_target(f_path):
                            return
                    else:
                        m_size.append(f_size)
                        o_files.append(file_)
        return True

    async def generateSampleVideo(self, dl_path, gid):
        data = self.sampleVideo.split(":") if isinstance(self.sampleVideo, str) else ""
        if data:
            sample_duration = int(data[0]) if data[0] else 60
            part_duration = int(data[1]) if len(data) > 1 else 4
        else:
            sample_duration, part_duration = 60, 4

        samvid = SampleVideo(self, sample_duration, part_duration, gid)

        async with cpu_eater_lock:
            checked = False
            if await aiopath.isfile(dl_path):
                if (await get_document_type(dl_path))[0]:
                    if not checked:
                        checked = True
                        LOGGER.info("Creating Sample video: %s", self.name)
                    async with task_dict_lock:
                        task_dict[self.mid] = FFMpegStatus(self, samvid, gid, "sv")
                    return await samvid.create(dl_path, True)
            else:
                for dirpath, _, files in await sync_to_async(
                    walk, dl_path, topdown=False
                ):
                    for file_ in natsorted(files):
                        f_path = ospath.join(dirpath, file_)
                        if (await get_document_type(f_path))[0]:
                            if not checked:
                                checked = True
                                LOGGER.info("Creating Sample videos: %s", self.name)
                            async with task_dict_lock:
                                task_dict[self.mid] = FFMpegStatus(
                                    self, samvid, gid, "sv"
                                )
                            res = await samvid.create(f_path)
                            if not res:
                                return res
                return dl_path
