from aiofiles import open as aiopen
from aiohttp import ClientSession
from ast import literal_eval
from asyncio import gather, wait_for, Event, wrap_future
from html import escape
from pyrogram import Client
from pyrogram.filters import command, regex, user, text
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time
from functools import partial
from urllib.parse import quote

from bot import bot, config_dict, get_client, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task, new_thread
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.html_helper import html_template
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time,
    get_date_time,
    action,
)
from bot.helper.ext_utils.telegram_helper import TeleContent
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    editMessage,
    sendMessage,
    deleteMessage,
    sendFile,
    auto_delete_message,
    sendingMessage,
)


TELEGRAPH_LIMIT = 300
PLUGINS = []
SITES = None


async def initiate_search_tools():
    qbclient = await sync_to_async(get_client)
    qb_plugins = await sync_to_async(qbclient.search_plugins)
    if SEARCH_PLUGINS := config_dict["SEARCH_PLUGINS"]:
        globals()["PLUGINS"] = []
        src_plugins = literal_eval(SEARCH_PLUGINS)
        if qb_plugins:
            names = [plugin["name"] for plugin in qb_plugins]
            await sync_to_async(qbclient.search_uninstall_plugin, names=names)
        await sync_to_async(qbclient.search_install_plugin, src_plugins)
    elif qb_plugins:
        for plugin in qb_plugins:
            await sync_to_async(qbclient.search_uninstall_plugin, names=plugin["name"])
        globals()["PLUGINS"] = []
    await sync_to_async(qbclient.auth_log_out)
    if SEARCH_API_LINK := config_dict["SEARCH_API_LINK"]:
        global SITES
        try:
            async with (
                ClientSession() as session,
                session.get(f"{SEARCH_API_LINK}/api/v1/sites", ssl=False) as res,
            ):
                data = await res.json()
            SITES = {
                str(site): str(site).capitalize() for site in data["supported_sites"]
            }
            SITES["all"] = "All"
        except Exception as e:
            LOGGER.error(
                "%s Can't fetching sites from SEARCH_API_LINK make sure use latest version of API",
                e,
            )
            SITES = None


async def getResult(
    search_results: list, key: str, message: Message, method: str, style: str
):
    TSEARCH_TITLE = config_dict["TSEARCH_TITLE"]
    if style in ("tele", "graph"):
        contents = []
        match method:
            case "apirecent":
                msg = "<h4>API Recent Results</h4>"
            case "apisearch":
                msg = f"<h4>API Search Result(s) For {key}</h4>"
            case "apitrend":
                msg = "<h4>API Trending Results</h4>"
            case _:
                msg = f"<h4>PLUGINS Search Result(s) For {key}</h4>"
        if style == "tele":
            msg = ""
        for index, result in enumerate(search_results, start=1):
            if method.startswith("api"):
                try:
                    if "name" in result.keys():
                        if style == "tele":
                            msg += f"<a href='{result['url']}'>{escape(result['name'])}</a><br>"
                        else:
                            msg += f"<code><a href='{result['url']}'>{escape(result['name'])}</a></code><br>"
                    if "torrents" in result.keys():
                        for subres in result["torrents"]:
                            msg += (
                                f"<b>Quality: </b>{subres['quality']} | <b>Type: </b>{subres['type']} | "
                                f"<b>Size: </b>{subres['size']}<br>"
                            )
                            if "torrent" in subres.keys():
                                msg += (
                                    f"<a href='{subres['torrent']}'>Direct Link</a><br>"
                                )
                            elif "magnet" in subres.keys():
                                msg += "<b>Share Magnet to</b><a href='http://t.me/share/url?url={subres['magnet']}'>Telegram</a><br>"
                        msg += "<br>"
                    else:
                        msg += f"<b>Size: </b>{result['size']}<br>"
                        try:
                            msg += f"<b>Seeders: </b>{result['seeders']} | <b>Leechers: </b>{result['leechers']}<br>"
                        except:
                            pass
                        if "torrent" in result.keys():
                            msg += (
                                f"<a href='{result['torrent']}'>Direct Link</a><br><br>"
                            )
                        elif "magnet" in result.keys():
                            msg += "<b>Share Magnet to</b><a href='http://t.me/share/url?url={quote(result['magnet'])}'>Telegram</a><br><br>"
                        else:
                            msg += "<br>"
                except:
                    continue
            else:
                msg += (
                    f"<a href='{result.descrLink}'>{escape(result.fileName)}</a><br>"
                    f"<b>Size: </b>{get_readable_file_size(result.fileSize)}<br>"
                    f"<b>Seeders: </b>{result.nbSeeders} | <b>Leechers: </b>{result.nbLeechers}<br>"
                )
                link = result.fileUrl
                if link.startswith("magnet:"):
                    msg += f"<b>Share Magnet to</b> <a href='http://t.me/share/url?url={quote(link)}'>Telegram</a><br><br>"
                else:
                    msg += f"<a href='{link}'>Direct Link</a><br><br>"

            if style == "tele":
                contents.append(str(index).zfill(3) + ". " + msg.replace("<br>", "\n"))
                msg = ""
            elif len(msg.encode("utf-8")) > 39000:
                contents.append(msg)
                msg = ""

            if index == TELEGRAPH_LIMIT:
                break

        if style == "tele":
            return contents

        if msg != "":
            contents.append(msg)

        await editMessage(
            f"<i>Creating {len(contents)} telegraph pages...</i>", message
        )
        path = [
            (await telegraph.create_page(TSEARCH_TITLE, content))["path"]
            for content in contents
        ]
        if len(path) > 1:
            await gather(
                editMessage(
                    f"<i>Editing {len(contents)} telegraph pages...</i>", message
                ),
                telegraph.edit_telegraph(path, contents),
            )
        return f"https://telegra.ph/{path[0]}"
    match method:
        case "apirecent":
            msg = f'<span class="container center rfontsize"><h1>{TSEARCH_TITLE}</h1><h4>Recent Results</h4></span>'
        case "apisearch":
            msg = f'<span class="container center rfontsize"><h1>{TSEARCH_TITLE}</h1><h4>Search Results For {key}</h4></span>'
        case "apitrend":
            msg = f'<span class="container center rfontsize"><h1>{TSEARCH_TITLE}</h1><h4>Trending Results</h4></span>'
        case _:
            msg = f'<span class="container center rfontsize"><h1>{TSEARCH_TITLE}</h1><h4>Search Results For {key}</h4></span>'
    for result in search_results:
        msg += '<span class="container start rfontsize">'
        if method.startswith("api"):
            try:
                if "name" in result:
                    msg += f"<div> <a class='withhover' href='{result['url']}'>{escape(result['name'])}</a></div>"
                if "torrents" in result:
                    for subres in result["torrents"]:
                        msg += (
                            f"<span class='topmarginsm'><b>Quality: </b>{subres['quality']} | "
                            f"<b>Type: </b>{subres['type']} | <b>Size: </b>{subres['size']}</span>"
                        )
                        if "torrent" in subres:
                            msg += "<span class='topmarginxl'><a class='withhover' href='{subres['torrent']}'>Direct Link</a></span>"
                        elif "magnet" in subres:
                            msg += "<span><b>Share Magnet to</b> <a class='withhover' href='http://t.me/share/url?url={subres['magnet']}'>Telegram</a></span>"
                    msg += "<br>"
                else:
                    msg += f"<span class='topmarginsm'><b>Size: </b>{result['size']}</span>"
                    try:
                        msg += (
                            f"<span class='topmarginsm'><b>Seeders: </b>{result['seeders']} | "
                            "<b>Leechers: </b>{result['leechers']}</span>"
                        )
                    except:
                        pass
                    if "torrent" in result:
                        msg += "<span class='topmarginxl'><a class='withhover' href='{result['torrent']}'>Direct Link</a></span>"
                    elif "magnet" in result:
                        msg += "<span class='topmarginxl'><b>Share Magnet to</b> <a class='withhover' href='http://t.me/share/url?url={quote(result['magnet'])}'>Telegram</a></span>"
            except:
                continue
        else:
            msg += (
                f"<div> <a class='withhover' href='{result.descrLink}'>{escape(result.fileName)}</a></div>"
                f"<span class='topmarginsm'><b>Size: </b>{get_readable_file_size(result.fileSize)}</span>"
                f"<span class='topmarginsm'><b>Seeders: </b>{result.nbSeeders} | "
                f"<b>Leechers: </b>{result.nbLeechers}</span>"
            )
            link = result.fileUrl
            if link.startswith("magnet:"):
                msg += "<span class='topmarginxl'><b>Share Magnet to</b> <a class='withhover' href='http://t.me/share/url?url={quote(link)}'>Telegram</a></span>"
            else:
                msg += f"<span class='topmarginxl'><a class='withhover' href='{link}'>Direct Link</a></span>"
        msg += "</span>"
    return msg


class TorSeacrh:
    def __init__(self, client: Client, message: Message, query: str = ""):
        self._client = client
        self._message = message
        self._tag = self._message.from_user.mention
        self._reply_to = None
        self._searching = False
        self.changeQuery = False
        self.query = query
        self.method = ""
        self.site = ""
        self.style = ""
        self.is_cancelled = ""
        self.content = {}
        self.event = Event()
        self.query_event = Event()
        self.tele_list = TeleContent(self._message, direct=False)

    @new_thread
    async def _event_handler(self):
        pfunc = partial(torsearch_upadte, obj=self)
        handler = self._client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^torser") & user(self._message.from_user.id)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=180)
        except:
            self.is_cancelled = "Timeout, torrent search has been canceled!"
            self.event.set()
        finally:
            self._client.remove_handler(*handler)

    @new_thread
    async def change_query_handler(self):
        pfunc = partial(change_query, obj=self)
        handler = self._client.add_handler(
            MessageHandler(pfunc, filters=text & user(self._message.from_user.id)),
            group=-1,
        )
        try:
            await wait_for(self.query_event.wait(), timeout=60)
        except:
            self.query_event.set()
        finally:
            self.query_event.clear()
            self._client.remove_handler(*handler)

    def reset(self):
        self.site = ""
        self.style = ""
        self.method = ""
        self.changeQuery = False
        self._searching = False

    async def send_list_message(self, msg: str, buttons: ButtonMaker = None):
        if not self._reply_to:
            self._reply_to = await sendMessage(msg, self._message, buttons)
        else:
            await editMessage(msg, self._reply_to, buttons)

    async def search(self):
        dt_date, dt_time = get_date_time(self._message)
        TIME_ZONE_TITLE = config_dict["TIME_ZONE_TITLE"]
        if self.method.startswith("api"):
            SEARCH_API_LINK = config_dict["SEARCH_API_LINK"]
            SEARCH_LIMIT = config_dict["SEARCH_LIMIT"]
            match self.method:
                case "apisearch":
                    LOGGER.info("API Searching: %s from %s", self.query, self.site)
                    if self.site == "all":
                        api = f"{SEARCH_API_LINK}/api/v1/all/search?query={self.query}&limit={SEARCH_LIMIT}"
                    else:
                        api = f"{SEARCH_API_LINK}/api/v1/search?site={self.site}&query={self.query}&limit={SEARCH_LIMIT}"
                case "apitrend":
                    LOGGER.info("API Trending from %s", self.site)
                    if self.site == "all":
                        api = f"{SEARCH_API_LINK}/api/v1/all/trending?limit={SEARCH_LIMIT}"
                    else:
                        api = f"{SEARCH_API_LINK}/api/v1/trending?site={self.site}&limit={SEARCH_LIMIT}"
                case "apirecent":
                    LOGGER.info("API Recent from %s", self.site)
                    if self.site == "all":
                        api = (
                            f"{SEARCH_API_LINK}/api/v1/all/recent?limit={SEARCH_LIMIT}"
                        )
                    else:
                        api = f"{SEARCH_API_LINK}/api/v1/recent?site={self.site}&limit={SEARCH_LIMIT}"
            try:
                async with (
                    ClientSession() as session,
                    session.get(api, ssl=False) as res,
                ):
                    search_results = await res.json()
                if "error" in search_results or search_results["total"] == 0:
                    buttons = ButtonMaker()
                    buttons.button_data("<<", "torser can_query")
                    buttons.button_data("Cancel", "torser cancel")
                    await self.send_list_message(
                        f"Search not found for <i>{self.query}</i> in <i>{SITES.get(self.site).title()}</i>",
                        buttons.build_menu(2),
                    )
                    return
                cap = (
                    "<b>Torrent Search Result:</b>\n"
                    f"<b>╭ Found: </b>{search_results['total']}\n"
                    f"<b>┊ Elapsed: </b>{get_readable_time(time() - self._message.date.timestamp())}\n"
                    f"<b>┊ Cc: </b>{self._message.from_user.mention}\n"
                    f"<b>┊ Action: </b>{action(self._message)}\n"
                    f"<b>┊ Add: </b>{dt_date}\n"
                    f"<b>┊ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n"
                    "<b>┊ Mode: </b>API\n"
                )
                match self.method:
                    case "apitrend":
                        cap += (
                            "<b>┊ Category: </b>Trending\n"
                            f"<b>╰ Torrent Site: </b><i>{SITES.get(self.site).title()}</i>"
                        )
                    case "apirecent":
                        cap += (
                            "<b>┊ Category: </b>Recent\n"
                            f"<b>╰ Torrent Site: </b><i>{SITES.get(self.site).title()}</i>"
                        )
                    case _:
                        cap += (
                            f"<b>┊ Torrent Site: </b><i>{SITES.get(self.site).title()}</i>\n"
                            f"<b>╰ Input Key: </b><code>{self.query.title()}</code>"
                        )
                search_results = search_results["data"]
            except Exception as e:
                await self.send_list_message(str(e))
        else:
            LOGGER.info("PLUGINS Searching: %s from %s", self.query, self.site)
            client = await sync_to_async(get_client)
            search = await sync_to_async(
                client.search_start,
                pattern=self.query,
                plugins=self.site,
                category="all",
            )
            search_id = search.id
            while True:
                result_status = await sync_to_async(
                    client.search_status, search_id=search_id
                )
                status = result_status[0].status
                if status != "Running":
                    break
            dict_search_results = await sync_to_async(
                client.search_results, search_id=search_id, limit=TELEGRAPH_LIMIT
            )
            search_results = dict_search_results.results
            total_results = dict_search_results.total
            if total_results == 0:
                buttons = ButtonMaker()
                buttons.button_data("<<", "torser can_query")
                buttons.button_data("Cancel", "torser cancel")
                await self.send_list_message(
                    f"Search not found for <i>{self.query}</i> in <i>{self.site.title()}</i>",
                    buttons.build_menu(2),
                )
                return
            cap = (
                "<b>Torrent Search Result:</b>\n"
                f"<b>╭ Found: </b>{total_results}\n"
                f"<b>┊ Elapsed: </b>{get_readable_time(time() - self._message.date.timestamp())}\n"
                f"<b>┊ Cc: </b>{self._tag}\n"
                f"<b>┊ Action: </b>{action(self._message)}\n"
                f"<b>┊ Add: </b>{dt_date}\n"
                f"<b>┊ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n"
                "<b>┊ Mode: </b>Plugin\n"
                f"<b>┊ Torrent Site: </b><i>{self.site.title()}</i>\n"
                f"<b>╰ Input Key: </b><code>{self.query.title()}</code>"
            )
            await sync_to_async(client.search_delete, search_id=search_id)
            await sync_to_async(client.auth_log_out)

        cur_content: dict = self.content.get(self.query, {})
        if (saved_content := cur_content.get("data")) and cur_content.get(
            "mode"
        ) == self.mode:
            hmsg = saved_content
        else:
            hmsg = await getResult(
                search_results, self.query, self._reply_to, self.method, self.style
            )
        self.content.setdefault(self.query, {})
        self.content.update(
            {self.query: {"data": hmsg, "style": self.style, "cap": cap}}
        )

        match self.style:
            case "tele":
                self.tele_list.set_data(hmsg, cap)
                text, buttons = await self.tele_list.get_content(
                    "torser", extra_buttons=[("Change Query", "change")]
                )
                await self.send_list_message(text, buttons)
            case "graph":
                self.event.set()
                buttons = ButtonMaker()
                buttons.button_link("View", hmsg)
                await gather(
                    sendingMessage(
                        cap,
                        self._message,
                        config_dict["IMAGE_SEARCH"],
                        buttons.build_menu(1),
                    ),
                    deleteMessage(self._reply_to),
                )
            case _:
                self.event.set()
                name = f"{self.method.title()}_{str(self.query).title()}_{self.site.upper()}_{time()}.html"
                async with aiopen(name, "w", encoding="utf-8") as f:
                    await f.write(
                        html_template.replace("{msg}", hmsg).replace(
                            "{title}", f"{self.method}_{self.query}_{self.site}"
                        )
                    )
                await gather(
                    sendFile(self._message, name, cap, config_dict["IMAGE_HTML"]),
                    deleteMessage(self._reply_to),
                )
        if (
            self._message.chat.type.name in ("SUPERGROUP", "CHANNEL")
            and config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
        ):
            await auto_delete_message(
                self._message, stime=config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
            )

    async def _generate_buttons(self, no_button=False):
        buttons = ButtonMaker()
        if self.changeQuery:
            buttons.button_data("<<", "torser can_query")
            buttons.button_data("Cancel", "torser cancel")
            return buttons.build_menu(2)
        if not self.is_cancelled and not self._searching and not no_button:
            buttons.button_data("Change Query", "torser change", "header")
            SEARCH_PLUGINS = config_dict["SEARCH_PLUGINS"]
            if self.method == "plugin" and not self.site:
                if not PLUGINS:
                    qbclient = await sync_to_async(get_client)
                    pl = await sync_to_async(qbclient.search_plugins)
                    for name in pl:
                        PLUGINS.append(name["name"])
                    await sync_to_async(qbclient.auth_log_out)
                for siteName in PLUGINS:
                    buttons.button_data(siteName.title(), f"torser {siteName} plugin")
                buttons.button_data("All", "torser all plugin")
                if SITES and SEARCH_PLUGINS:
                    buttons.button_data("<<", "torser dualmode")
            elif self.method == "dualmode":
                buttons.button_data("Api", "torser apisearch")
                buttons.button_data("Plugins", "torser plugin")
            elif self.method and self.site:
                buttons.button_data("HTML", "torser html")
                buttons.button_data("Telegraph", "torser graph")
                buttons.button_data("Telegram", "torser tele")
                buttons.button_data("<<", f"torser {self.method}")
            elif self.method == "noargs":
                buttons.button_data("Trending", "torser apitrend")
                buttons.button_data("Recent", "torser apirecent")
            elif self.method.startswith("api"):
                for data, name in SITES.items():
                    buttons.button_data(name, f"torser {data} {self.method}")
                if SITES and SEARCH_PLUGINS:
                    buttons.button_data(
                        "<<", f"torser {'dualmode' if self.query else 'noargs'}"
                    )
            buttons.button_data("Cancel", "torser cancel")
        return (
            buttons.build_menu(3)
            if self.site and self.method != "dualmode"
            else buttons.build_menu(2)
        )

    async def list_buttons(self):
        SEARCH_PLUGINS = config_dict["SEARCH_PLUGINS"]
        no_button = False
        if self.is_cancelled:
            no_button = True
            msg = f"{self._tag}, Torrent search has been canceled!"
        elif self.changeQuery:
            msg = f"{self._tag}, send new query to search..\n\n<i>Current query is <b>{self.query}</b></i>"
        elif self.style:
            self._searching = True
            type_dict = {
                "html": "html style",
                "graph": "telegraph style",
                "tele": "telegram style",
                "key": self.query.title(),
            }
            if self.method.startswith("api"):
                if not self.query:
                    if self.method == "apirecent":
                        self.query = endpoint = "recent"
                    elif self.method == "apitrend":
                        self.query = endpoint = "trending"
                    msg = f"<i>Searching <b>{endpoint}</b> items in {SITES.get(self.site).title()} with {type_dict[self.style]}...</i>"
                else:
                    msg = f"<i>Searching for <b>{self.query.title()}</b> in {SITES.get(self.site).title()} with {type_dict[self.style]}...</i>"
            else:
                msg = f"<i>Searching for <b>{self.query.title()}</b> in {self.site.title()} with {type_dict[self.style]}...</i>"
        elif SEARCH_PLUGINS and not SITES and self.query or self.method == "plugin":
            self.method, msg = (
                "plugin",
                f"{self._tag}, Choose Site to Search (Plugin Mode) <b>{self.query.title()}</b>",
            )
        elif self.method.startswith("api"):
            msg = f"{self._tag}, Choose Site to Search (API Mode) <b>{self.query.title()}</b>"
        elif not SITES and not SEARCH_PLUGINS:
            msg = "No API link or search PLUGINS added for this function!"
            no_button = True
        elif not self.query and not SITES:
            msg = f"{self._tag}, send a search key along with command"
            no_button = True
        elif not self.query:
            self.method, msg = (
                "noargs",
                f"{self._tag}, Send a search key along with command or by reply with command!",
            )
        elif SEARCH_PLUGINS or self.method == "dualmode":
            self.method, msg = (
                "dualmode",
                f"{self._tag}, Choose Tool to Search <b>{self.query.title()}</b>.",
            )
        else:
            self.method, msg = (
                "apisearch",
                f"{self._tag}, Choose Site to Search <b>{self.query.title()}</b>.",
            )

        await self.send_list_message(msg, await self._generate_buttons(no_button))

    async def get_buttons(self):
        await gather(self.list_buttons(), wrap_future(self._event_handler()))
        if self.is_cancelled == "close":
            await deleteMessage(
                self._message, self._message.reply_to_message, self._reply_to
            )


@new_task
async def torsearch_upadte(_, query: CallbackQuery, obj: TorSeacrh):
    data = query.data.split()
    tele_data = ["pre", "nex", "foot", "close", "page"]
    if data[1] == "cancel":
        obj.is_cancelled = "Torrent search has been canceled!"
        obj.event.set()
        await gather(query.answer(), obj.list_buttons())
    elif data[1] == "change":
        obj.changeQuery = True
        await obj.list_buttons()
        obj.change_query_handler()
    elif data[1] == "can_query":
        obj.changeQuery = False
        obj.query_event.set()
        if (cur_content := obj.content.get(obj.query)) and obj.style == "tele":
            obj.tele_list.set_data(cur_content["data"], cur_content["cap"])
            text, buttons = await obj.tele_list.get_content(
                "torser", extra_buttons=[("Change Query", "change")]
            )
            await obj.send_list_message(text, buttons)
            return
        await obj.list_buttons()
    elif len(data) == 3 and data[1] not in tele_data:
        obj.method = data[2]
        obj.site = data[1]
        await gather(query.answer(), obj.list_buttons())
    elif data[1].startswith("api") or data[1] in ["plugin", "apisearch", "dualmode"]:
        obj.method = data[1]
        obj.site = ""
        await gather(query.answer(), obj.list_buttons())
    elif data[1] == "noargs":
        obj.method = ""
        await gather(query.answer(), obj.list_buttons())
    elif data[1] in ["tele", "graph", "html"]:
        obj.style = data[1]
        await gather(query.answer(), obj.list_buttons())
        await obj.search()
    elif data[2] == "page":
        await query.answer(f"Total Page ~ {obj.tele_list.pages}", True)
    elif data[2] in ["pre", "nex", "foot"]:
        tdata = int(data[4]) if data[2] == "foot" else int(data[3])
        text, buttons = await obj.tele_list.get_content(
            "torser", data[2], tdata, [("Change Query", "change")]
        )
        if not buttons:
            await query.answer(text, True)
            return
        await gather(query.answer(), obj.send_list_message(text, buttons))
    elif data[2] == "close":
        await query.answer("Closing torrent search...")
        obj.is_cancelled = "close"
        obj.event.set()


async def change_query(_, message: Message, obj: TorSeacrh):
    obj.reset()
    obj.query_event.set()
    obj.query = message.text.strip()
    await gather(deleteMessage(message), obj.list_buttons())


@new_task
async def torrentSearch(client: Client, message: Message):
    reply_to = message.reply_to_message
    key = ""

    if fmsg := await UseCheck(message).run(session=True):
        await auto_delete_message(message, fmsg, reply_to)
        return

    if reply_to and reply_to.text:
        key = reply_to.text.strip()
    elif not reply_to and len(args := message.text.split(maxsplit=1)) != 1:
        key = args[1]

    await TorSeacrh(client, message, key).get_buttons()


bot.add_handler(
    MessageHandler(
        torrentSearch,
        filters=command(BotCommands.SearchCommand) & CustomFilters.authorized,
    )
)
