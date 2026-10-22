from aiofiles import open as aiopen
from aiohttp import ClientSession
from apscheduler.triggers.interval import IntervalTrigger
from asyncio import Lock, sleep, gather
from datetime import datetime, timedelta
from feedparser import parse as feedparse
from functools import partial
from pyrogram import Client
from pyrogram.filters import command, regex, create
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from re import split as re_split
from time import time

from bot import bot, scheduler, rss_dict, config_dict, LOGGER, DATABASE_URL
from bot.helper.ext_utils.bot_utils import new_thread, new_task
from bot.helper.ext_utils.help_messages import HelpString
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.exceptions import RssShutdownException
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    deleteMessage,
    editMessage,
    sendMessage,
    sendCustom,
    auto_delete_message,
    sendFile,
)


rss_dict_lock = Lock()
handler_dict = {}


@new_task
async def _auto_delete(*args, stime: int = 6):
    await auto_delete_message(*args, stime=stime)


async def rssMenu(event):
    user_id = event.from_user.id
    buttons = ButtonMaker()
    buttons.button_data("Subscribe", f"rss sub {user_id}")
    buttons.button_data("Subscriptions", f"rss list {user_id} 0")
    buttons.button_data("Get Items", f"rss get {user_id}")
    buttons.button_data("Edit", f"rss edit {user_id}")
    buttons.button_data("Pause", f"rss pause {user_id}")
    buttons.button_data("Resume", f"rss resume {user_id}")
    buttons.button_data("Unsubscribe", f"rss unsubscribe {user_id}")
    if await CustomFilters.sudo("", event):
        buttons.button_data("All Subscriptions", f"rss listall {user_id} 0")
        buttons.button_data("Pause All", f"rss allpause {user_id}")
        buttons.button_data("Resume All", f"rss allresume {user_id}")
        buttons.button_data("Unsubscribe All", f"rss allunsub {user_id}")
        buttons.button_data("Delete User", f"rss deluser {user_id}")
        if scheduler.running:
            buttons.button_data("Shutdown Rss", f"rss shutdown {user_id}")
        else:
            buttons.button_data("Start Rss", f"rss start {user_id}")
    buttons.button_data("Close", f"rss close {user_id}")
    msg = f"<b>RSS MENU</b>\n<b>Users</b>: {len(rss_dict)}\n<b>Running:</b> {scheduler.running}"
    return msg, buttons.build_menu(2)


async def updateRssMenu(query: CallbackQuery):
    msg, buttons = await rssMenu(query)
    await editMessage(msg, query.message, buttons)


@new_thread
async def getRssMenu(_, message: Message):
    msg, buttons = await rssMenu(message)
    await sendMessage(msg, message, buttons)


async def rssSub(client: Client, message: Message, query: CallbackQuery):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    tag = message.from_user.mention
    msg = ""
    smsg = None
    items = message.text.split("\n")
    for index, item in enumerate(items, start=1):
        args = item.split()
        if len(args) < 2:
            errmsg = await sendMessage(
                f"{item}. Wrong Input format. Read help message before adding new subcription!",
                message,
            )
            _auto_delete(message, errmsg)
            continue
        title = args[0].strip()
        if (user_feeds := rss_dict.get(user_id, False)) and title in user_feeds:
            errmsg = await sendMessage(
                f"This title {title} already subscribed! Choose another title!", message
            )
            _auto_delete(message, errmsg)
            continue
        feed_link = args[1].strip()
        if feed_link.startswith(("-inf", "-exf", "-c")):
            errmsg = await sendMessage(
                f"Wrong input in line {index}! Add Title! Read the example!", message
            )
            _auto_delete(message, errmsg)
            continue
        inf_lists, exf_lists = [], []
        if len(args) > 2:
            arg = item.split(" -c ", 1)
            cmd = re_split(" -inf | -exf ", arg[1])[0].strip() if len(arg) > 1 else None
            arg = item.split(" -inf ", 1)
            inf = re_split(" -c | -exf ", arg[1])[0].strip() if len(arg) > 1 else None
            arg = item.split(" -exf ", 1)
            exf = re_split(" -c | -inf ", arg[1])[0].strip() if len(arg) > 1 else None
            if inf is not None:
                filters_list = inf.split("|")
                for x in filters_list:
                    y = x.split(" or ")
                    inf_lists.append(y)
            if exf is not None:
                filters_list = exf.split("|")
                for x in filters_list:
                    y = x.split(" or ")
                    exf_lists.append(y)
        else:
            inf = exf = cmd = None
        try:
            async with (
                ClientSession() as session,
                session.get(feed_link, ssl=False) as res,
            ):
                html = await res.text()
            rss_d = feedparse(html)
            last_title = rss_d.entries[0]["title"]
            try:
                last_link = rss_d.entries[0]["links"][1]["href"]
            except IndexError:
                last_link = rss_d.entries[0]["link"]
            msg += (
                "<b>Subscribed!</b>\n"
                f"<b>╭ Title: </b><code>{title}</code>\n"
                f"<b>┊ Feed Url: </b>{feed_link}\n"
                f"<b>┊ latest record for </b>{rss_d.feed.title}:\n"
                f"<b>┊ Name: </b><code>{last_title.replace('>', '').replace('<', '')}</code>\n"
                f"<b>┊ Link: </b><code>{last_link}</code>\n"
                f"<b>┊ Command: </b><code>{cmd}</code>\n"
                f"<b>┊ Filters:-</b>\ninf: <code>{inf}</code>\n"
                f"<b>╰ exf: </b><code>{exf}<code/>"
            )
            async with rss_dict_lock:
                rss_dict.setdefault(user_id, {})
                rss_dict[user_id][title] = {
                    "link": feed_link,
                    "last_feed": last_link,
                    "last_title": last_title,
                    "inf": inf_lists,
                    "exf": exf_lists,
                    "paused": False,
                    "command": cmd,
                    "tag": tag,
                }
            LOGGER.info(
                "Rss Feed Added: id: %s - title: %s - link: %s - c: %s - inf: %s - exf: %s",
                user_id,
                title,
                feed_link,
                cmd,
                inf,
                exf,
            )
        except (IndexError, AttributeError) as e:
            emsg = f"The link: {feed_link} doesn't seem to be a RSS feed or it's region-blocked!"
            smsg = await sendMessage(f"{emsg}\n<b>Error:</b>{e}", message)
        except Exception as e:
            smsg = await sendMessage(f"<b>ERROR:</b> {e}", message)
    if not smsg and msg:
        smsg = await sendMessage(msg, message)
        if DATABASE_URL and rss_dict.get(user_id):
            await DbManager().rss_update(user_id)
        if scheduler.state == 2:
            scheduler.resume()
        elif await CustomFilters.sudo("", message) and not scheduler.running:
            addJob()
            scheduler.start()
    _auto_delete(message, smsg, stime=20)
    await updateRssMenu(query)


async def getUserId(title):
    async with rss_dict_lock:
        return next(
            (
                (True, user_id)
                for user_id, feed in list(rss_dict.items())
                if feed["title"] == title
            ),
            (False, False),
        )


async def rssUpdate(client: Client, message: Message, query: CallbackQuery, state: str):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    titles = message.text.split()
    is_sudo = await CustomFilters.sudo(client, message)
    updated = []
    for title in titles:
        title = title.strip()
        if not (res := rss_dict[user_id].get(title, False)):
            if is_sudo:
                res, user_id = await getUserId(title)
            if not res:
                user_id = message.from_user.id
                errmsg = await sendMessage(f"{title} not found!", message)
                _auto_delete(message, errmsg)
                continue
        istate = rss_dict[user_id][title].get("paused", False)
        if istate and state == "pause" or not istate and state == "resume":
            errmsg = await sendMessage(f"{title} already {state}d!", message)
            _auto_delete(message, errmsg)
            continue
        async with rss_dict_lock:
            updated.append(title)
            if state == "unsubscribe":
                del rss_dict[user_id][title]
            elif state == "pause":
                rss_dict[user_id][title]["paused"] = True
            elif state == "resume":
                rss_dict[user_id][title]["paused"] = False
        if state == "resume":
            if scheduler.state == 2:
                scheduler.resume()
            elif is_sudo and not scheduler.running:
                addJob()
                scheduler.start()
        if is_sudo and DATABASE_URL and user_id != message.from_user.id:
            await DbManager().rss_update(user_id)
        if not rss_dict[user_id]:
            async with rss_dict_lock:
                del rss_dict[user_id]
            if DATABASE_URL:
                await DbManager().rss_delete(user_id)
                if not rss_dict:
                    await DbManager().trunc_table("rss")
    if updated:
        LOGGER.info("Rss link with Title(s): %s has been %sd!", updated, state)
        msg = await sendMessage(
            f"Rss links with Title(s): <code>{updated}</code> has been {state}d!",
            message,
        )
        if DATABASE_URL and rss_dict.get(user_id):
            await DbManager().rss_update(user_id)
        _auto_delete(message, msg, stime=10)
    await updateRssMenu(query)


async def rssList(query: CallbackQuery, start: int, all_users: bool = False):
    user_id = query.from_user.id
    buttons = ButtonMaker()
    if all_users:
        list_feed = f"<b>All RSS Subscriptions\n<b>Page:</b> {start // 5 + 1} </b>"
        async with rss_dict_lock:
            keysCount = sum(len(v.keys()) for v in list(rss_dict.values()))
            index = 0
            for titles in list(rss_dict.values()):
                for index, (title, data) in enumerate(
                    list(titles.items())[start : 5 + start]
                ):
                    list_feed += (
                        f"\n\n<b>╭ Title:</b> <code>{title}</code>\n"
                        f"<b>├ Feed Url:</b> <code>{data['link']}</code>\n"
                        f"<b>├ Command:</b> <code>{data['command']}</code>\n"
                        f"<b>├ Inf:</b> <code>{data['inf']}</code>\n"
                        f"<b>├ Exf:</b> <code>{data['exf']}</code>\n"
                        f"<b>├ Paused:</b> <code>{data['paused']}</code>\n"
                        f"<b>╰ User:</b> {data['tag']}"
                    )
                    index += 1
                    if index == 5:
                        break
    else:
        list_feed = f"<b>Your RSS Subscriptions\n<b>Page:</b> {start // 5 + 1} </b>"
        async with rss_dict_lock:
            keysCount = len(rss_dict.get(user_id, {}).keys())
            for title, data in list(rss_dict[user_id].items())[start : 5 + start]:
                list_feed += (
                    f"\n\n<b>╭ Title:</b> <code>{title}</code>\n"
                    f"<b>┊ Feed Url:</b> <code>{data['link']}</code>\n"
                    f"<b>┊ Command:</b> <code>{data['command']}</code>\n"
                    f"<b>┊ Inf:</b> <code>{data['inf']}</code>\n"
                    f"<b>┊ Exf:</b> <code>{data['exf']}</code>\n"
                    f"<b>╰ Paused:</b> <code>{data['paused']}</code>"
                )
    buttons.button_data("<<", f"rss back {user_id}")
    buttons.button_data("Close", f"rss close {user_id}")
    if keysCount > 5:
        for x in range(0, keysCount, 5):
            buttons.button_data(
                f"{int(x / 5) + 1}", f"rss list {user_id} {x}", "footer"
            )
    if query.message.text.html == list_feed:
        return
    await editMessage(list_feed, query.message, buttons.build_menu(2))


async def rssGet(_, message: Message, query: CallbackQuery):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    args = message.text.split()
    if len(args) < 2:
        msg = await sendMessage(
            f"{args}. Wrong Input format. You should add number of the items you want to get. Read help message before adding new subcription!",
            message,
        )
        await updateRssMenu(query)
        _auto_delete(message, msg)
        return
    try:
        title = args[0]
        count = int(args[1])
        data = rss_dict[user_id].get(title, False)
        if data and count > 0:
            msg = await sendMessage(
                f"Getting the last <b>{count}</b> item(s) from {title}", message
            )
            try:
                async with (
                    ClientSession() as session,
                    session.get(data["link"], ssl=False) as res,
                ):
                    html = await res.text()
                rss_d = feedparse(html)
                item_info = ""
                for item_num in range(count):
                    try:
                        link = rss_d.entries[item_num]["links"][1]["href"]
                    except IndexError:
                        link = rss_d.entries[item_num]["link"]
                    item_info += (
                        f"<b>╭ Name: </b><code>{rss_d.entries[item_num]['title'].replace('>', ').replace(' < ', ')}</code>\n"
                        f"<b>╰ Link: </b><code>{link}</code>\n\n"
                    )
                item_info_ecd = item_info.encode()
                if len(item_info_ecd) > 4000:
                    filename = f"RSSGet {title} items_no. {count}.txt"
                    async with aiopen(filename, "w", encoding="utf-8") as f:
                        await f.write(f"{item_info_ecd}")
                    await gather(
                        sendFile(
                            message, filename, f"RSSGet {title} items_no. {count}"
                        ),
                        deleteMessage(msg),
                    )
                else:
                    await editMessage(item_info, msg)
            except IndexError as e:
                LOGGER.error(e)
                await editMessage(
                    "Parse depth exceeded. Try again with a lower value.", msg
                )
            except Exception as e:
                LOGGER.error(e)
                await editMessage(str(e), msg)
    except Exception as e:
        LOGGER.error(e)
        msg = await sendMessage(f"Enter a valid value!. {e}", message)
    await updateRssMenu(query)
    _auto_delete(message, msg, stime=10)


async def rssEdit(_, message: Message, query: CallbackQuery):
    user_id = message.from_user.id
    handler_dict[user_id] = updated = False
    items = message.text.split("\n")
    for item in items:
        args = item.split()
        title = args[0].strip()
        if len(args) < 2:
            msg = await sendMessage(
                f"{item}. Wrong Input format. Read help message before editing!",
                message,
            )
            _auto_delete(message, msg)
            continue
        if not rss_dict[user_id].get(title, False):
            msg = await sendMessage("Enter a valid title. Title not found!", message)
            _auto_delete(message, msg)
            continue
        updated = True
        inf_lists, exf_lists = [], []
        arg = item.split(" -c ", 1)
        cmd = re_split(" -inf | -exf ", arg[1])[0].strip() if len(arg) > 1 else None
        arg = item.split(" -inf ", 1)
        inf = re_split(" -c | -exf ", arg[1])[0].strip() if len(arg) > 1 else None
        arg = item.split(" -exf ", 1)
        exf = re_split(" -c | -inf ", arg[1])[0].strip() if len(arg) > 1 else None
        async with rss_dict_lock:
            if cmd is not None:
                if cmd.lower() == "none":
                    cmd = None
                rss_dict[user_id][title]["command"] = cmd
            if inf is not None:
                if inf.lower() != "none":
                    filters_list = inf.split("|")
                    for x in filters_list:
                        y = x.split(" or ")
                        inf_lists.append(y)
                rss_dict[user_id][title]["inf"] = inf_lists
            if exf is not None:
                if exf.lower() != "none":
                    filters_list = exf.split("|")
                    for x in filters_list:
                        y = x.split(" or ")
                        exf_lists.append(y)
                rss_dict[user_id][title]["exf"] = exf_lists
    if DATABASE_URL and updated:
        await DbManager().rss_update(user_id)
    await gather(deleteMessage(message), updateRssMenu(query))


async def rssDelete(_, message: Message, query: CallbackQuery):
    handler_dict[message.from_user.id] = False
    users = message.text.split()
    for user in users:
        user = int(user)
        async with rss_dict_lock:
            del rss_dict[user]
        if DATABASE_URL:
            await DbManager().rss_delete(user)
    await updateRssMenu(query)


async def event_handler(client: Client, query: CallbackQuery, pfunc: partial):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(
            user.id == user_id and event.chat.id == query.message.chat.id and event.text
        )

    handler = client.add_handler(MessageHandler(pfunc, create(event_filter)), group=-1)
    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await updateRssMenu(query)
    client.remove_handler(*handler)


@new_thread
async def rssListener(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    if int(data[2]) != user_id and not await CustomFilters.sudo(client, query):
        await query.answer("You don't have permission to use these buttons!", True)
        return
    match data[1]:
        case "close":
            handler_dict[user_id] = False
            await gather(
                query.answer(), deleteMessage(message, message.reply_to_message)
            )
        case "back":
            handler_dict[user_id] = False
            await gather(query.answer(), updateRssMenu(query))
        case "sub":
            handler_dict[user_id] = False
            buttons = ButtonMaker()
            buttons.button_data("<<", f"rss back {user_id}")
            buttons.button_data("Close", f"rss close {user_id}")
            pfunc = partial(rssSub, query=query)
            await gather(
                query.answer().editMessage(
                    HelpString.RSSHELP, message, buttons.build_menu(2)
                ),
                event_handler(client, query, pfunc),
            )
        case "list":
            handler_dict[user_id] = False
            if len(rss_dict.get(int(data[2]), {})) == 0:
                await query.answer("No subscriptions!", True)
            else:
                start = int(data[3])
                await gather(query.answer(), rssList(query, start))
        case "get":
            handler_dict[user_id] = False
            if len(rss_dict.get(int(data[2]), {})) == 0:
                await query.answer("No subscriptions!", True)
            else:
                buttons = ButtonMaker()
                buttons.button_data("<<", f"rss back {user_id}")
                buttons.button_data("Close", f"rss close {user_id}")
                pfunc = partial(rssGet, query=query)
                await gather(
                    query.answer().editMessage(
                        "Send one title with value separated by space get last X items.\nTitle Value\n\n<i>Timeout: 60s.</i>",
                        message,
                        buttons.build_menu(2),
                    ),
                    event_handler(client, query, pfunc),
                )
        case "unsubscribe" | "pause" | "resume" as value:
            handler_dict[user_id] = False
            if len(rss_dict.get(int(data[2]), {})) == 0:
                await query.answer("No subscriptions!", True)
            else:
                buttons = ButtonMaker()
                buttons.button_data("<<", f"rss back {user_id}")
                match value:
                    case "pause":
                        buttons.button_data(
                            "Pause AllMyFeeds", f"rss uallpause {user_id}"
                        )
                    case "resume":
                        buttons.button_data(
                            "Resume AllMyFeeds", f"rss uallresume {user_id}"
                        )
                    case "unsubscribe":
                        buttons.button_data(
                            "Unsub AllMyFeeds", f"rss uallunsub {user_id}"
                        )
                buttons.button_data("Close", f"rss close {user_id}")
                pfunc = partial(rssUpdate, query=query, state=value)
                await gather(
                    query.answer(),
                    editMessage(
                        f"Send one or more rss titles separated by space to {value}.\n\n<i>Timeout: 60s.</i>",
                        message,
                        buttons.build_menu(2),
                    ),
                    event_handler(client, query, pfunc),
                )
        case "edit":
            handler_dict[user_id] = False
            if len(rss_dict.get(int(data[2]), {})) == 0:
                await query.answer("No subscriptions!", True)
            else:
                buttons = ButtonMaker()
                buttons.button_data("<<", f"rss back {user_id}")
                buttons.button_data("Close", f"rss close {user_id}")
                msg = """Send one or more rss titles with new filters or command separated by new line.
Examples:
Title1 -c mirror -up remote:path/subdir -exf none -inf 1080 or 720
Title2 -c none -inf none -opt none
Title3 -c mirror -rcf xxx -up xxx -z pswd

Note:
1. Argument -c for command and options
2. Only what you provide will be edited, the rest will be the same like example 2: -exf will stay same as it is.

<i>Timeout: 60s.</i>
"""
                pfunc = partial(rssEdit, query=query)
                await gather(
                    query.answer(),
                    editMessage(msg, message, buttons.build_menu(2)),
                    event_handler(client, query, pfunc),
                )
        case value if value.startswith("uall"):
            handler_dict[user_id] = False
            if len(rss_dict.get(int(data[2]), {})) == 0:
                await query.answer("No subscriptions!", True)
                return
            await query.answer()
            if value.endswith("unsub"):
                async with rss_dict_lock:
                    del rss_dict[int(data[2])]
                if DATABASE_URL:
                    await DbManager().rss_delete(int(data[2]))
                await updateRssMenu(query)
            elif value.endswith("pause"):
                async with rss_dict_lock:
                    for title in list(rss_dict[int(data[2])]):
                        rss_dict[int(data[2])][title]["paused"] = True
                if DATABASE_URL:
                    await DbManager().rss_update(int(data[2]))
            elif value.endswith("resume"):
                async with rss_dict_lock:
                    for title in list(rss_dict[int(data[2])]):
                        rss_dict[int(data[2])][title]["paused"] = False
                if scheduler.state == 2:
                    scheduler.resume()
                if DATABASE_URL:
                    await DbManager().rss_update(int(data[2]))
            await updateRssMenu(query)
        case value if value.startswith("all"):
            if len(rss_dict) == 0:
                await query.answer("No subscriptions!", True)
                return
            await query.answer()
            if value.endswith("unsub"):
                async with rss_dict_lock:
                    rss_dict.clear()
                if DATABASE_URL:
                    await DbManager().trunc_table("rss")
                await updateRssMenu(query)
            elif value.endswith("pause"):
                async with rss_dict_lock:
                    for user in list(rss_dict):
                        for title in list(rss_dict[user]):
                            rss_dict[int(data[2])][title]["paused"] = True
                if scheduler.running:
                    scheduler.pause()
                if DATABASE_URL:
                    await DbManager().rss_update_all()
            elif value.endswith("resume"):
                async with rss_dict_lock:
                    for user in list(rss_dict):
                        for title in list(rss_dict[user]):
                            rss_dict[int(data[2])][title]["paused"] = False
                if scheduler.state == 2:
                    scheduler.resume()
                elif not scheduler.running:
                    addJob()
                    scheduler.start()
                if DATABASE_URL:
                    await DbManager().rss_update_all()
        case "deluser":
            if len(rss_dict) == 0:
                await query.answer("No subscriptions!", True)
            else:
                buttons = ButtonMaker()
                buttons.button_data("<<", f"rss back {user_id}")
                buttons.button_data("Close", f"rss close {user_id}")
                msg = "Send one or more user_id separated by space to delete their resources.\n\n<i>Timeout: 60s.</i>"
                pfunc = partial(rssDelete, query=query)
                await gather(
                    query.answer(),
                    editMessage(msg, message, buttons.build_menu(2)),
                    event_handler(client, query, pfunc),
                )
        case "listall":
            if not rss_dict:
                await query.answer("No subscriptions!", True)
            else:
                start = int(data[3])
                await gather(query.answer(), rssList(query, start, all_users=True))
        case "shutdown":
            if scheduler.running:
                await query.answer()
                scheduler.shutdown(wait=False)
                await sleep(0.5)
                await updateRssMenu(query)
            else:
                await query.answer("Already Stopped!", True)
        case "start":
            if not scheduler.running:
                await query.answer()
                addJob()
                scheduler.start()
                await updateRssMenu(query)
            else:
                await query.answer("Already Running!", True)


async def rssMonitor():
    if not config_dict["RSS_CHAT"]:
        LOGGER.warning("RSS_CHAT not added! Shutting down rss scheduler...")
        scheduler.shutdown(wait=False)
        return
    if len(rss_dict) == 0:
        scheduler.pause()
        return
    all_paused = True
    for user, items in list(rss_dict.items()):
        for title, data in list(items.items()):
            try:
                if data["paused"]:
                    continue
                async with (
                    ClientSession() as session,
                    session.get(data["link"], ssl=False) as res,
                ):
                    html = await res.text()
                rss_d = feedparse(html)
                try:
                    last_link = rss_d.entries[0]["links"][1]["href"]
                except IndexError:
                    last_link = rss_d.entries[0]["link"]
                finally:
                    all_paused = False
                last_title = rss_d.entries[0]["title"]
                if data["last_feed"] == last_link or data["last_title"] == last_title:
                    continue
                feed_count = 0
                while True:
                    try:
                        await sleep(10)
                    except:
                        raise RssShutdownException("Rss Monitor Stopped!")
                    try:
                        item_title = rss_d.entries[feed_count]["title"]
                        try:
                            url = rss_d.entries[feed_count]["links"][1]["href"]
                        except IndexError:
                            url = rss_d.entries[feed_count]["link"]
                        if data["last_feed"] == url or data["last_title"] == item_title:
                            break
                    except IndexError:
                        LOGGER.warning(
                            "Reached Max index no. %s for this feed: %s. Maybe you need to use less RSS_DELAY to not miss some torrents",
                            feed_count,
                            title,
                        )
                        break
                    parse = True
                    for flist in data["inf"]:
                        if all(x not in item_title for x in flist):
                            parse = False
                            feed_count += 1
                            break
                    if not parse:
                        continue
                    for flist in data["exf"]:
                        if any(x in item_title for x in flist):
                            parse = False
                            feed_count += 1
                            break
                    if not parse:
                        continue
                    if cmds := data["command"]:
                        cmd = cmds.split(maxsplit=1)
                        cmd.insert(1, url)
                        feed_msg = " ".join(cmd)
                        if not feed_msg.startswith("/"):
                            feed_msg = f"/{feed_msg}"
                    else:
                        feed_msg = f"<b>Name: </b><code>{item_title.replace('>', '').replace('<', '')}</code>\n\n"
                        feed_msg += f"<b>Link: </b><code>{url}</code>"
                    feed_msg += f"\n<b>Tag: </b>{data['tag']} <code>{user}</code>"
                    await sendCustom(feed_msg, config_dict["RSS_CHAT"])
                    feed_count += 1
                async with rss_dict_lock:
                    if user not in rss_dict or not rss_dict[user].get(title, False):
                        continue
                    rss_dict[user][title].update(
                        {"last_feed": last_link, "last_title": last_title}
                    )
                await DbManager().rss_update(user)
                LOGGER.info("Feed Name: %s", title)
                LOGGER.info("Last item: %s", last_link)
            except RssShutdownException as ex:
                LOGGER.info(ex)
                break
            except Exception as e:
                LOGGER.error(
                    "%s - Feed Name: %s - Feed Link: %s", e, title, data["link"]
                )
                continue
    if all_paused:
        scheduler.pause()


def addJob():
    scheduler.add_job(
        rssMonitor,
        trigger=IntervalTrigger(seconds=config_dict["RSS_DELAY"]),
        id="0",
        name="RSS",
        misfire_grace_time=15,
        max_instances=1,
        next_run_time=datetime.now() + timedelta(seconds=20),
        replace_existing=True,
    )


addJob()
scheduler.start()
bot.add_handler(
    MessageHandler(
        getRssMenu, filters=command(BotCommands.RssCommand) & CustomFilters.authorized
    )
)
bot.add_handler(CallbackQueryHandler(rssListener, filters=regex("^rss")))
