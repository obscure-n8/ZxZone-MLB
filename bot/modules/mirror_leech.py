from aiofiles.os import path as aiopath
from asyncio import sleep, gather
from base64 import b64encode
from os import path as ospath
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from re import match as re_match
from urllib.parse import urlparse

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import (
    get_content_type,
    is_premium_user,
    sync_to_async,
    new_task,
    arg_parser,
)
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.conf_loads import intialize_savebot
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.links_utils import (
    get_link,
    is_url,
    is_magnet,
    is_mega_link,
    is_media,
    is_gdrive_link,
    is_sharer_link,
    is_gdrive_id,
    is_tele_link,
    is_rclone_path,
)
from bot.helper.listeners.tasks_listener import TaskListener
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.direct_downloader import add_direct_download
from bot.helper.mirror_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)
from bot.helper.mirror_utils.download_utils.gd_download import add_gd_download
from bot.helper.mirror_utils.download_utils.jd_download import add_jd_download
from bot.helper.mirror_utils.download_utils.qbit_download import add_qb_torrent
from bot.helper.mirror_utils.download_utils.rclone_download import add_rclone_download
from bot.helper.mirror_utils.download_utils.telegram_download import (
    TelegramDownloadHelper,
)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    deleteMessage,
    auto_delete_message,
    editMessage,
    get_tg_link_message,
)
from bot.helper.video_utils.selector import SelectMode
from myjd.exception import MYJDException


class Mirror(TaskListener):
    def __init__(
        self,
        client: Client,
        message: Message,
        isQbit=False,
        isJd=False,
        isLeech=False,
        vidMode=None,
        sameDir=None,
        bulk=None,
        multiTag=None,
        options="",
    ):
        if sameDir is None:
            sameDir = {}
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multiTag = multiTag
        self.options = options
        self.sameDir = sameDir
        self.bulk = bulk
        super().__init__()
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.vidMode = vidMode
        self.isJd = isJd

    @new_task
    async def newEvent(self):
        text = self.message.text.split("\n")
        await self.getTag(text)

        reply_to = self.message.reply_to_message
        if fmsg := await UseCheck(self.message, self.isLeech).run(
            True, daily=True, ml_chek=True, session=True, send_pm=True
        ):
            self.removeFromSameDir()
            await auto_delete_message(self.message, fmsg, reply_to)
            return

        arg_base = {
            "-i": 0,
            "-sp": 0,
            "-b": False,
            "-d": False,
            "-e": False,
            "-gf": False,
            "-j": False,
            "-s": False,
            "-ss": False,
            "-sv": False,
            "-vt": False,
            "-z": False,
            "-ap": "",
            "-au": "",
            "-h": "",
            "-m": "",
            "-n": "",
            "-rcf": "",
            "-t": "",
            "-up": "",
            "link": "",
        }

        input_list = text[0].split(" ")
        args = arg_parser(input_list[1:], arg_base)

        self.compress = args["-z"]
        self.extract = args["-e"]
        self.isGofile = args["-gf"]
        self.join = args["-j"]
        self.link = args["link"]
        self.name = args["-n"].replace("/", "")
        self.rcFlags = args["-rcf"]
        self.sampleVideo = args["-sv"]
        self.screenShots = args["-ss"]
        self.seed = args["-d"]
        self.select = args["-s"]
        self.splitSize = args["-sp"]
        self.thumb = args["-t"]
        self.upDest = args["-up"]
        self.isRename = self.name

        folder_name = args["-m"].replace("/", "")
        headers = args["-h"]
        isBulk = args["-b"]
        vidTool = args["-vt"]
        file_ = ratio = seed_time = None
        bulk_start = bulk_end = 0

        try:
            self.multi = int(args["-i"])
        except:
            self.multi = 0

        if not isinstance(self.seed, bool):
            dargs = self.seed.split(":")
            ratio = dargs[0] or None
            if len(dargs) == 2:
                seed_time = dargs[1] or None
            self.seed = True

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
                f"Upss {self.tag}, multi/bulk mode for premium user only", self.message
            )
            return

        if not isBulk:
            if folder_name:
                self.seed = False
                ratio = seed_time = None
                if not self.sameDir:
                    self.sameDir = {
                        "total": self.multi,
                        "tasks": set(),
                        "name": folder_name,
                    }
                self.sameDir["tasks"].add(self.mid)
            elif self.sameDir:
                self.sameDir["total"] -= 1
        else:
            if vidTool and not self.vidMode and self.sameDir:
                self.vidMode = await SelectMode(self).get_buttons()
                if not self.vidMode:
                    return
            await self.initBulk(input_list, bulk_start, bulk_end, Mirror)
            return

        if self.bulk:
            del self.bulk[0]

        if vidTool and (not self.vidMode or not self.sameDir):
            self.vidMode = await SelectMode(self).get_buttons()
            if not self.vidMode:
                self.removeFromSameDir()
                return

        self.run_multi(input_list, folder_name, Mirror)

        path = ospath.join(f"{config_dict['DOWNLOAD_DIR']}{self.mid}", folder_name)

        self.link = self.link or get_link(self.message)

        self.editable = await sendMessage(
            "<i>Checking request, please wait...</i>", self.message
        )
        if self.link:
            await sleep(0.5)

        if self.link and is_tele_link(self.link):
            try:
                await intialize_savebot(
                    self.user_dict.get("session_string"), True, self.user_id
                )
                self.session, reply_to = await get_tg_link_message(
                    self.link, self.user_id
                )
            except Exception as e:
                LOGGER.error(e, exc_info=True)
                await editMessage(f"ERROR: {e}", self.editable)
                self.removeFromSameDir()
                return

        if isinstance(reply_to, list):
            self.bulk = reply_to
            self.sameDir = {}
            b_msg = input_list[:1]
            self.options = " ".join(input_list[1:]).replace(self.link, "")
            b_msg.append(f"{self.bulk[0]} -i {len(self.bulk)} {self.options}")
            nextmsg = await sendMessage(" ".join(b_msg), self.message)
            nextmsg = await self.client.get_messages(self.message.chat.id, nextmsg.id)
            if self.message.from_user:
                nextmsg.from_user = self.message.from_user
            else:
                nextmsg.sender_chat = self.message.sender_chat
            Mirror(
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
            await deleteMessage(self.editable)
            return

        if reply_to:
            file_ = is_media(reply_to)
            if reply_to.document and (
                file_.mime_type == "application/x-bittorrent"
                or file_.file_name.endswith(".torrent")
            ):
                self.link = await reply_to.download()
                file_ = None

        if (
            not is_url(self.link)
            and not is_magnet(self.link)
            and not await aiopath.exists(self.link)
            and not is_rclone_path(self.link)
            and not is_gdrive_id(self.link)
            and not file_
        ):
            await gather(
                editMessage(
                    f"Where Are Links/Files, type /{BotCommands.HelpCommand} for more details.",
                    self.editable,
                ),
                auto_delete_message(self.message, self.editable),
            )
            self.removeFromSameDir()

            return

        if self.link:
            LOGGER.info(self.link)

        if self.isGofile:
            await editMessage("<i>GoFile upload has been enabled!</i>", self.editable)
            await sleep(0.5)

        try:
            await self.beforeStart()
        except Exception as e:
            await editMessage(str(e), self.editable)
            self.removeFromSameDir()
            return

        if is_mega_link(self.link) and not self.isJd:
            # There is no active MEGA SDK download branch in this module.  Do
            # not pass a MEGA page URL to aria2: it downloads the landing page
            # as a tiny extensionless file and reports a false success.  The
            # JDownloader commands can resolve MEGA links correctly.
            await editMessage(
                f"{self.tag}, MEGA links require the JDownloader command.",
                self.editable,
            )
            self.removeFromSameDir()
            return

        if is_magnet(self.link):
            self.isJd = False

        if (
            not self.isJd
            and not self.isQbit
            and not is_magnet(self.link)
            and not is_rclone_path(self.link)
            and not is_gdrive_link(self.link)
            and not self.link.endswith(".torrent")
            and not is_gdrive_id(self.link)
            and not file_
        ):
            self.isSharer = is_sharer_link(self.link)
            content_type = (await get_content_type(self.link))[0]
            if not content_type or re_match(r"text/html|text/plain", content_type):
                host = urlparse(self.link).netloc
                await editMessage(
                    f"<i>Generating direct link from {host}, please wait...</i>",
                    self.editable,
                )
                try:
                    self.link = await sync_to_async(direct_link_generator, self.link)
                    LOGGER.info("Generated link: %s", self.link)
                    if isinstance(self.link, dict):
                        contents = self.link["contents"]
                        if len(contents) == 1:
                            msg = f"<i>Found direct link:</i>\n<code>{contents[0]['url']}</code>"
                        else:
                            msg = "<i>Found folder ddl link...</i>"
                    elif isinstance(self.link, tuple):
                        if len(self.link) == 3:
                            self.link, self.name, headers = self.link
                        else:
                            self.link, headers = self.link
                        msg = f"<i>Found direct link:</i>\n<code>{self.link}</code>"
                    else:
                        msg = f"<i>Found {'drive' if 'drive.google.com' in self.link else 'direct'} link:</i>\n<code>{self.link}</code>"
                    await editMessage(msg, self.editable)
                    await sleep(1)
                except DirectDownloadLinkException as e:
                    if str(e).startswith("ERROR:"):
                        await editMessage(f"{self.tag}, {e}", self.editable)
                        self.removeFromSameDir()
                        return
        if not self.isJd:
            await deleteMessage(self.editable)

        if file_:
            await TelegramDownloadHelper(self).add_download(reply_to, path)
        elif isinstance(self.link, dict):
            await add_direct_download(self, path)
        elif self.isJd:
            try:
                await add_jd_download(self, f"{path}/")
            except (Exception, MYJDException) as e:
                LOGGER.error(e)
                await editMessage(f"{e}".strip(), self.editable)
                self.removeFromSameDir()
                return
        elif is_rclone_path(self.link):
            await add_rclone_download(self, path)
        elif is_gdrive_link(self.link) or is_gdrive_id(self.link):
            await add_gd_download(self, path)

        elif self.isQbit:
            await add_qb_torrent(self, path, ratio, seed_time)
        else:
            ussr, pssw = args["-au"], args["-ap"]
            if ussr or pssw:
                auth = f"{ussr}:{pssw}"
                headers += (
                    f" authorization: Basic {b64encode(auth.encode()).decode('ascii')}"
                )
            if "static.romsget.io" in self.link:
                headers = "Referer: https://www.romsget.io/"
            await add_aria2c_download(self, path, headers, ratio, seed_time)


async def mirror(client: Client, message: Message):
    Mirror(client, message).newEvent()


async def qb_mirror(client: Client, message: Message):
    Mirror(client, message, isQbit=True).newEvent()


async def leech(client: Client, message: Message):
    Mirror(client, message, isLeech=True).newEvent()


async def qb_leech(client: Client, message: Message):
    Mirror(client, message, isQbit=True, isLeech=True).newEvent()


async def jd_mirror(client: Client, message: Message):
    Mirror(client, message, isJd=True).newEvent()


async def jd_leech(client: Client, message: Message):
    Mirror(client, message, isLeech=True, isJd=True).newEvent()


bot.add_handler(
    MessageHandler(
        mirror, filters=command(BotCommands.MirrorCommand) & CustomFilters.authorized
    )
)
bot.add_handler(
    MessageHandler(
        qb_mirror,
        filters=command(BotCommands.QbMirrorCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(
    MessageHandler(
        leech, filters=command(BotCommands.LeechCommand) & CustomFilters.authorized
    )
)
bot.add_handler(
    MessageHandler(
        qb_leech, filters=command(BotCommands.QbLeechCommand) & CustomFilters.authorized
    )
)
bot.add_handler(
    MessageHandler(
        jd_mirror,
        filters=command(BotCommands.JdMirrorCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(
    MessageHandler(
        jd_leech, filters=command(BotCommands.JdLeechCommand) & CustomFilters.authorized
    )
)
