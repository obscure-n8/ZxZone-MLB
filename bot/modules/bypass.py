from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from random import choice
from time import time
from urllib.parse import urlparse

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import (
    sync_to_async,
    new_task,
    arg_parser,
    is_premium_user,
    is_pm_enabled,
)
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.links_utils import is_url, get_link
from bot.helper.ext_utils.status_utils import get_readable_time, action, get_date_time
from bot.helper.listeners.tasks_listener import TaskListener
from bot.helper.mirror_utils.download_utils.direct_link_generator import (
    sites,
    direct_link_generator,
)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    limit,
    auto_delete_message,
    sendMessage,
    editMessage,
    copyMessage,
    deleteMessage,
    sendPhoto,
)


class Bypass(TaskListener):
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
        text = self.message.text.split("\n")
        await self.getTag(text)

        if fmsg := await UseCheck(self.message).run(forpremi=True, session=True):
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
            await self.initBulk(input_list, bulk_start, bulk_end, Bypass)
            return

        if self.bulk:
            del self.bulk[0]

        self.run_multi(input_list, "", Bypass)

        self.link = self.link or get_link(self.message)

        if not is_url(self.link):
            text = f"<b>Send link along with command or by replying to the link by command\nSITES:</b>\n{' | '.join(sites.all)}\n\n"
            msg = await sendMessage(text, self.message)
            await auto_delete_message(self.message, msg)
            return

        LOGGER.info("Bypassing: %s", self.link)

        self.editable = await sendMessage(
            f"<i>Bypassing {urlparse(self.link).netloc} link, please wait...</i>",
            self.message,
        )
        result, start_time = "", time()

        try:
            result = await sync_to_async(direct_link_generator, self.link)
        except DirectDownloadLinkException as err:
            LOGGER.info("Failed to bypass: %s", self.link)
            if str(err).startswith("ERROR:"):
                err = str(err).replace(
                    "trying to generate direct", "when trying bypass"
                )
            elif "No direct link function" in str(err):
                err = str(err).replace(
                    "No direct link function found for", "Unsupport site for"
                )
            await editMessage(f"{self.tag}, {err}", self.editable)
            return

        if (
            "filecrypt.co" not in self.link
            and "psa." not in self.link
            and all(x not in self.link for x in sites.FEMBED)
        ):
            if isinstance(result, dict):
                contents = result["contents"]
                if len(contents) == 1:
                    result = f"<code>{contents[0]['url']}</code>"
                else:
                    result = "\n".join(
                        [
                            f"<b>{i}.</b> <code>{res['url']}</code>"
                            for i, res in enumerate(contents, 1)
                        ]
                    )
            elif isinstance(result, tuple):
                result = f"<code>{result[0]}</code>"
            else:
                result = f"<code>{result}</code>"

        dt_date, dt_time = get_date_time(self.message)
        msg = (
            "<b>BYPASS RESULT</b>\n"
            f"<b>╭Cc: </b>{self.tag}\n"
            f"<b>┊ID: </b><code>{self.user_id}</code>\n"
            f"<b>┊Action: </b>{action(self.message)}\n"
            f"<b>┊Add: </b>{dt_date}\n"
            f"<b>┊At: </b>{dt_time} ({config_dict['TIME_ZONE_TITLE']})\n"
            f"<b>┊Elapsed: </b>{get_readable_time(time() - start_time) or '1s'}\n"
            f"<b>╰Bypass Result:</b>\n{result}"
        )
        buttons = ButtonMaker()
        buttons.button_link("Source Link", self.link)

        if config_dict["ENABLE_IMAGE_MODE"]:
            limit.caption(msg)
            if len(msg) - limit.total > 1024:
                await editMessage(msg, self.editable, buttons.build_menu(1))
            else:
                await deleteMessage(self.editable)
                self.editable = await sendPhoto(
                    msg,
                    self.message,
                    choice(config_dict["IMAGE_COMPLETE"].split()),
                    buttons.build_menu(1),
                )
        else:
            await editMessage(msg, self.editable, buttons.build_menu(1))

        if chat_id := config_dict["OTHER_LOG"]:
            await copyMessage(chat_id, self.editable, buttons.build_menu(1))

        if is_pm_enabled(self.user_id, self.user_dict) and self.isSuperChat:
            await copyMessage(self.user_id, self.editable, buttons.build_menu(1))

        if self.isSuperChat and (
            stime := config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
        ):
            await auto_delete_message(
                self.message, self.message.reply_to_message, stime=stime
            )


async def bypass(client: Client, message: Message):
    Bypass(client, message).newEvent()


bot.add_handler(
    MessageHandler(
        bypass, filters=command(BotCommands.BypassCommand) & CustomFilters.authorized
    )
)
