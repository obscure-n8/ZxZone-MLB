from aiofiles import open as aiopen
from aiohttp import ClientSession
from asyncio import sleep, gather, wait_for, Event
from functools import partial
from lxml.etree import HTML
from pyrogram import Client
from pyrogram.filters import command, regex, user
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from random import choice
from time import time
from urllib.parse import urlparse

from bot import bot, config_dict, user_data
from bot.helper.ext_utils.bot_utils import (
    arg_parser,
    is_pm_enabled,
    new_task,
    new_thread,
)
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.index_scrape import index_scrapper
from bot.helper.ext_utils.links_utils import get_link, is_media, is_url, is_magnet
from bot.helper.ext_utils.status_utils import get_readable_time, get_date_time, action
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    sendMedia,
    sendMessage,
    copyMessage,
    deleteMessage,
    editMessage,
    sendingMessage,
)


class ScrapeHelper:
    def __init__(self, client: Client, message: Message, scrapfile=False):
        self._client = client
        self._scrapfile = scrapfile
        self._user_id = (
            message.from_user.id if message.from_user else message.sender_chat.id
        )
        self._isSuperGroup = message.chat.type.name in ("SUPERGROUP", "CHANNEL")
        self._pm = is_pm_enabled(self._user_id)
        self._buttons = None
        self.editabale = None
        self.link = None
        self.message = message
        self.reply_to = message.reply_to_message
        self.is_cancelled = False
        self.event = Event()

    @new_thread
    async def _event_handler(self):
        pfunc = partial(stop_scrapper, obj=self)
        handler = self._client.add_handler(
            CallbackQueryHandler(pfunc, filters=regex("^scrap") & user(self._user_id)),
            group=-1,
        )
        try:
            await wait_for(self.event.wait())
        except:
            self.event.set()
        finally:
            self._client.remove_handler(*handler)

    async def _onScrapSuccess(self, totals: int, mode: str):
        self.event.set()
        log_msg = (
            "<b>SCRAPPER LOGS</b>\n"
            f"<b>╭ Cc: </b>{self.message.from_user.mention}\n"
            f"┊ ID: </b><code>{self._user_id}</code>\n"
            f"┊ Action: </b>{action(self.message)}\n"
            f"┊ Status: </b>#{'cancelled' if self.is_cancelled else 'done'}\n"
            f"{mode}"
            f"┊ Add: </b>{get_date_time(self.message)[0]}\n"
            f"┊ At: </b>{get_date_time(self.message)[1]} ({config_dict['TIME_ZONE_TITLE']})\n"
            f"┊ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
            f"╰ Total Link: </b>{totals} Link"
        )
        await deleteMessage(self.editabale)
        buttons = ButtonMaker()
        buttons.button_link("Source Link", self.link)
        if self._scrapfile:
            msg_scrap = await sendMedia(log_msg, self.message.chat.id, self.reply_to)
        else:
            msg_scrap = await sendingMessage(
                log_msg,
                self.message,
                choice(config_dict["IMAGE_COMPLETE"].split()),
                buttons.build_menu(1),
            )
        if self._pm and self._isSuperGroup:
            await copyMessage(self._user_id, msg_scrap)
        if chat_id := config_dict["OTHER_LOG"]:
            await copyMessage(chat_id, msg_scrap)
        if self._isSuperGroup and (
            stime := config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
        ):
            await auto_delete_message(self.message, self.reply_to, stime=stime)

    async def _onScrapError(self, error=""):
        self.event.set()
        if not error:
            error = f"""
<b>Send link along with command line:</b>
<code>/{BotCommands.ScrapperCommand}</code> (Link) -au username -ap password\n
<b>By replying to link/txt file:</b>
<code>/{BotCommands.ScrapperCommand}</code> -au username -ap password\n

<b>Current Support:
├ Index link
├ TXT file (.txt)
├ Torrent Site
├ <a href='https://animeremux.xyz'>Animeremux</a>
├ <a href='https://atishmkv.beauty'>Atishmkv</a>
╰ <a href='https://cinevood.mom'>Cinevood</a>

<i>NOTE: Auth and pass ONLY for index link</i>
"""
        await gather(
            editMessage(error, self.editabale),
            auto_delete_message(self.message, self.editabale, self.reply_to),
        )

    @staticmethod
    async def _resp(url):
        async with ClientSession() as session, session.get(url, ssl=False) as r:
            return await r.read()

    async def _tasks_buttons(self, index, links):
        if not self._buttons:
            buttons = ButtonMaker()
            buttons.button_data("Stop", "scrap stop")
            self._buttons = buttons.build_menu(1)
        await editMessage(
            f"Executing {index}/{len(links)} result(s)...\nClick stop button to cancel send scrapping result(s).",
            self.editabale,
            self._buttons,
        )

    async def commons(self, mode: str):
        await editMessage(
            f"<i>Scrapping from <b>{mode}</b>, palease wait...</i>", self.editabale
        )
        msg = ""
        html = HTML(await self._resp(self.link))
        links = (
            html.xpath('//div[@class="toggle tie-sc-open"]')
            or html.xpath('//div[@id="download"]//a')
            or html.xpath('//div[@class="download-btns"]')
        )
        for index, item in enumerate(links, 1):
            match mode:
                case "animeremux":
                    if len(links) > 1:
                        msg += f"⁍ <b>{item.xpath('./h3/text()')[0]}</b>\n"
                    for i, sitem in enumerate(
                        item.xpath('.//div[@class="toggle-content"]//a'), 1
                    ):
                        sinfo, link = (
                            sitem.xpath(".//text()")[0].strip(),
                            sitem.xpath(".//@href")[0],
                        )
                        link = link.rsplit("url=", 1)[-1]
                        if not is_url(link):
                            link = get_link(
                                text=sitem.xpath("./@onclick")[0].rsplit("url=", 1)[-1]
                            )
                        msg += f'{i}. <a href="{link}">{sinfo}</a>\n'
                case "atishmkv":
                    info, link = item.xpath(".//text()")[0], item.xpath(".//@href")[0]
                    lnks = "|".join(
                        f'<a href="{slink}">Link {i}</a>'
                        for i, slink in enumerate(
                            HTML(await self._resp(link)).xpath("//article//p/a/@href"),
                            1,
                        )
                    )
                    msg += f'{index}. <a href="{link}"><b>{info}</b></a>\n{lnks}\n'
                case _:
                    info = item.xpath(".//span/text()")[0]
                    link = "|".join(
                        f'<a href="{slink}">Link {i}</a>'
                        for i, slink in enumerate(item.xpath(".//a/@href"), 1)
                    )
                    msg += f"{index}. <b>{info}</b>\n{link}\n"

        if msg:
            msg = await sendMessage(msg, self.message)
            if self._pm and self._isSuperGroup:
                await copyMessage(self._user_id, msg)
            await self._onScrapSuccess(len(links), f"<b>├ Mode: </b>{mode.title()}\n")
        else:
            await self._onScrapError("ERROR: Can't find any link!")

    async def manget(self):
        self._event_handler()
        links = HTML(await self._resp(self.link)).xpath(
            '//a/@href[starts-with(., "magnet")]'
        )
        if links:
            mode = "<b>├ Mode: </b>Magnet\n"
            for index, link in enumerate(links, 1):
                await self._tasks_buttons(index, links)
                msg = await sendMessage(f"<code>{link}</code>", self.message)
                if self._pm and self._isSuperGroup:
                    await copyMessage(self._user_id, msg)
                if self.is_cancelled:
                    mode += f"<b>├ Executed: </b>{index} Link\n"
                    break
                await sleep(5)
            await self._onScrapSuccess(len(links), mode)
        else:
            arg_base = {"link": "", "-au": "", "-ap": ""}
            args = arg_parser(self.message.text.split()[1:], arg_base)
            ussr, pssw = args["-au"], args["-ap"]
            links = await index_scrapper(self.link, ussr, pssw)
            if "wrong" in links:
                await self._onScrapError(links)
                return
            if links:
                mode = "<b>┊ Mode: </b>Index\n"
                for index, link in enumerate(links, 1):
                    await self._tasks_buttons(index, links)
                    msg = await sendMessage(f"<code>{link}</code>", self.message)
                    if self._pm and self._isSuperGroup:
                        await copyMessage(self._user_id, msg)
                    if self.is_cancelled:
                        mode += f"<b>┊ Executed: </b>{index} Link\n"
                        break
                    await sleep(5)
                await self._onScrapSuccess(len(links), mode)
            else:
                await self._onScrapError("ERROR: Can't find any link!")

    async def txt_file(self):
        self._event_handler()
        start, end = 0, 1000
        file = self.reply_to.document
        is_text = file.file_name
        if not is_text.endswith(".txt"):
            await self._onScrapError("Only for document/file (.txt).")
            return
        await self.reply_to.download(file_name="./links.txt")
        async with aiopen("links.txt", "r+") as f:
            lines = await f.readlines()
        if links := [
            x.strip()
            for x in lines[start:end]
            if is_url(x.strip()) or is_magnet(x.strip())
        ]:
            mode = "<b>├ Mode: </b>TXT File\n"
            for index, link in enumerate(links, 1):
                await self._tasks_buttons(index, links)
                msg = await sendMessage(f"<code>{link}</code>", self.message)
                if self._pm and self._isSuperGroup:
                    await copyMessage(self._user_id, msg)
                if self.is_cancelled:
                    mode += f"<b>├ Executed: </b>{index} Link\n"
                    break
                await sleep(5)
            await self._onScrapSuccess(len(links), mode)
        else:
            await self._onScrapError("ERROR: Can't find any link!")


@new_task
async def scrapper(client: Client, message: Message):
    isFile = False
    reply_to = message.reply_to_message

    if fmsg := await UseCheck(message).run(forpremi=True, session=True, send_pm=True):
        await auto_delete_message(message, fmsg, reply_to)
        return

    if reply_to and is_media(reply_to):
        isFile = True
    else:
        link = get_link(message)

    scrape = ScrapeHelper(client, message, isFile)
    scrape.link = link
    scrape.editabale = await sendMessage(
        f"<i>Scrapping from {'file' if isFile else urlparse(link).netloc}, please wait...</i>",
        message,
    )

    if isFile:
        await scrape.txt_file()
    elif is_url(link):
        if any((mode := x) in link for x in ["animeremux", "atishmkv", "cinevood"]):
            await scrape.commons(mode)
        else:
            await scrape.manget()
    else:
        await scrape._onScrapError()


async def stop_scrapper(_, query: CallbackQuery, obj: ScrapeHelper):
    await query.answer("Trying to stop...")
    obj.event.set()
    obj.is_cancelled = True


bot.add_handler(
    MessageHandler(
        scrapper,
        filters=command(BotCommands.ScrapperCommand) & CustomFilters.authorized,
    )
)
