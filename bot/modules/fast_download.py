from aiofiles.os import path as aiopath
from ast import literal_eval
from asyncio import sleep, gather
from json import loads
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from random import choice
from requests import utils as rutils

from bot import bot, config_dict
from bot.helper.ext_utils.bot_utils import (
    sync_to_async,
    new_task,
    cmd_exec,
    arg_parser,
    is_premium_user,
    is_pm_enabled,
)
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.links_utils import (
    is_url,
    is_magnet,
    get_stream_link,
    get_link,
)
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.status_utils import (
    action,
    get_date_time,
    get_readable_file_size,
)
from bot.helper.ext_utils.telegraph_helper import TelePost
from bot.helper.listeners.tasks_listener import TaskListener
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    editMessage,
    deleteMessage,
    auto_delete_message,
    sendingMessage,
    copyMessage,
)


class FastDL(TaskListener):
    def __init__(
        self,
        client: Client,
        message: Message,
        _=False,
        __=False,
        ___=None,
        ____=None,
        _____=False,
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
        super().__init__()

    @new_task
    async def newEvent(self):
        if (
            not config_dict["RCLONE_SERVE_URL"]
            or not await aiopath.exists("rclone.conf")
            or not config_dict["ENABLE_FASTDL"]
        ):
            await sendMessage("Fast download not available!", self.message)
            return

        text = self.message.text.split("\n")
        await self.getTag(text)

        if fmsg := await UseCheck(self.message).run(
            True, True, True, session=True, send_pm=True
        ):
            await auto_delete_message(self.message, fmsg, self.message.reply_to_message)
            return

        arg_base = {"link": "", "-i": 0, "-b": False}
        input_list = text[0].split(" ")
        args = arg_parser(input_list[1:], arg_base)

        self.link = args["link"]
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
                f"Upss {self.tag}, multi/bulk mode for premium user only", self.message
            )
            return

        if isBulk:
            await self.initBulk(input_list, bulk_start, bulk_end, FastDL)
            return

        if self.bulk:
            del self.bulk[0]

        self.run_multi(input_list, "", FastDL)

        self.link = self.link or get_link(self.message)

        if not is_url(self.link) and not is_magnet(self.link):
            await sendMessage(
                "Send command along with link or by reply to the link!", self.message
            )
            return

        self.editable = await sendMessage(
            "<i>Checking request, please wait...</i>", self.message
        )
        upload_path = config_dict["RCLONE_PATH"]
        rjson = await cmd_exec(
            [
                "wzone",
                "backend",
                "addurl",
                "--config",
                "rclone.conf",
                upload_path,
                self.link,
            ]
        )
        if rjson[2] != 0:
            text = (
                "The server has been terminated!"
                if "doesn't support backend" in rjson[1]
                else "Something when wrong or invalid link!"
            )
            await editMessage(text, self.editable)
            return

        url_path = upload_path.replace(":", "/")
        dt_date, dt_time = get_date_time(self.message)
        rjson: dict = literal_eval(rjson[0])
        name = rjson.get("file_name")
        text = f"<code>{name}</code>\n"
        buttons = ButtonMaker()
        if rjson.get("message") == "Saving":
            await sleep(4)
            text += (
                "<b>╭ Status:</b> Complete\n"
                f"<b>├ Size:</b> {get_readable_file_size(rjson.get('file_size'))}\n"
            )
            url = f"{config_dict['RCLONE_SERVE_URL']}/{url_path}/{rutils.quote(name)}"
            typee = await cmd_exec(
                [
                    "wzone",
                    "lsjson",
                    "--fast-list",
                    "--stat",
                    "--no-modtime",
                    "--config",
                    "rclone.conf",
                    f"{upload_path}/{name}",
                ]
            )
            res = loads(typee[0])
            if typee[2] == 0 and res["IsDir"]:
                url += "/"
                text += "<b>┊ Type:</b> Folder\n"
            else:
                text += f"<b>┊ Type:</b> {res['MimeType']}\n"
            buttons.button_link(
                "Cloud Link", await sync_to_async(short_url, url, self.user_id)
            )
            if stream_link := get_stream_link(
                res["MimeType"], f"{url_path}/{rutils.quote(name)}"
            ):
                buttons.button_link(
                    "Stream Link",
                    await sync_to_async(short_url, stream_link, self.user_id),
                )
        else:
            text += "<b>╭ Status:</b> On Progress\n"
            buttons.button_link(
                "Cloud URL",
                await sync_to_async(
                    short_url,
                    f"{config_dict['RCLONE_SERVE_URL']}/{url_path}/",
                    self.user_id,
                ),
            )
        text += (
            f"<b>┊ Cc:</b> {self.tag}\n"
            f"<b>┊ Action:</b> {action(self.message)}\n"
            f"<b>┊ Add:</b> {dt_date}\n"
            f"<b>╰ At:</b> {dt_time} ({config_dict['TIME_ZONE_TITLE']})"
        )
        if config_dict["SOURCE_LINK"]:
            if is_magnet(self.link):
                tele = TelePost(config_dict["SOURCE_LINK_TITLE"])
                mag_link = await sync_to_async(
                    tele.create_post, f"<code>{name}<br></code><br>{self.link}"
                )
                buttons.button_link("Source Link", mag_link)
            else:
                buttons.button_link("Source Link", self.link)
        _, msg = await gather(
            deleteMessage(self.editable),
            sendingMessage(
                text,
                self.message,
                choice(config_dict["IMAGE_COMPLETE"].split()),
                buttons.build_menu(2),
            ),
        )
        if self.isSuperChat and is_pm_enabled(self.user_id, self.user_dict):
            await copyMessage(self.user_id, msg)
        if log_id := config_dict["MIRROR_LOG"]:
            await copyMessage(log_id, msg)
        if self.isSuperChat and (
            stime := config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
        ):
            await auto_delete_message(
                msg, self.message, self.message.reply_to_message, stime=stime
            )


async def fastdl(client: Client, message: Message):
    FastDL(client, message).newEvent()


bot.add_handler(
    MessageHandler(
        fastdl, filters=command(BotCommands.FastDlCommand) & CustomFilters.authorized
    )
)
