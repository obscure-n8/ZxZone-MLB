from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import gather, Event, wait_for, wrap_future, sleep
from configparser import ConfigParser
from functools import partial
from json import loads as jsonloads
from os import path as ospath
from pyrogram import Client
from pyrogram.enums import MessagesFilter
from pyrogram.filters import command, regex, user, text
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time

from bot import bot, bot_dict, bot_lock, config_dict, user_data, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task, new_thread, cmd_exec
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.conf_loads import intialize_savebot
from bot.helper.ext_utils.links_utils import is_media
from bot.helper.ext_utils.status_utils import (
    get_date_time,
    action,
    get_readable_time,
    get_readable_file_size,
)
from bot.helper.ext_utils.telegram_helper import TeleContent
from bot.helper.mirror_utils.gdrive_utlis.search import gdSearch
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    editMessage,
    auto_delete_message,
    sendFile,
    deleteMessage,
    sendPhoto,
)


class MultiSerach:
    def __init__(self, clinet: Client, message: Message, editable: Message, query: str):
        self._client: Client = clinet
        self._reply_to = None
        self._timeout = 240
        self._content = {}
        self.message = message
        self.user_id = self.message.from_user.id
        self.style = ""
        self.tag = self.message.from_user.mention
        self.engine: Client = None
        self.config_path = ""
        self.mode = ""
        self.type = ""
        self.editable = editable
        self.query = query
        self.is_cancelled = False
        self.changeQuery = False
        self.isRecursive = False
        self.search = False
        self.user_dict: dict = user_data.get(self.user_id, {})
        self.event = Event()
        self.query_event = Event()
        self.tele_list = TeleContent(self.message, direct=False)

    @new_thread
    async def _event_handler(self):
        pfunc = partial(cb, obj=self)
        handler = self._client.add_handler(
            CallbackQueryHandler(pfunc, filters=regex("^list") & user(self.user_id)),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=500)
        except:
            self.is_cancelled = True
            self.event.set()
        finally:
            self._client.remove_handler(*handler)

    @new_thread
    async def change_query_handler(self):
        pfunc = partial(change_query, obj=self)
        handler = self._client.add_handler(
            MessageHandler(pfunc, filters=text & user(self.user_id)), group=-1
        )
        try:
            await wait_for(self.query_event.wait(), timeout=self._timeout)
        except:
            self.query_event.set()
        finally:
            self.query_event.clear()
            self._client.remove_handler(*handler)

    def reset(self):
        self.type = ""
        self.mode = ""
        self.config_path = ""
        self.search = False
        self.changeQuery = False

    async def search_files(self):
        cur_content: dict = self._content.get(self.query, {})
        if (saved_content := cur_content.get("data")) and cur_content.get(
            "mode"
        ) == self.mode:
            contents = saved_content
        else:
            count = None
            if self.mode == "telegram":
                contents, index = [], 1
                async for message in self.engine.search_global(
                    self.query,
                    (
                        MessagesFilter.DOCUMENT
                        or MessagesFilter.PHOTO_VIDEO
                        or MessagesFilter.AUDIO
                    ),
                    150,
                ):
                    media, msg = is_media(message), ""
                    if not media:
                        continue
                    name = (
                        getattr(media, "file_name", media.file_unique_id)
                        or media.file_unique_id
                    )
                    msg += (
                        f'{str(index).zfill(3)}. <a href="{message.link}">{name}</a>\n'
                        f"<b>Size:</b> {get_readable_file_size(media.file_size)}\n"
                        f"<b>Type:</b> {media.mime_type}\n"
                        f"<b>Source:</b> {message.chat.title}\n"
                        f'<a href="https://t.me/{bot.me.username}?start={message.chat.id}_{message.id}_{self.message.chat.id}">Get File</a>\n\n'
                    )
                    index += 1
                    contents.append(msg)
            elif self.mode == "gdrive":
                if self.config_path.startswith("tokens/") or self.user_dict.get(
                    "use_sa"
                ):
                    target_id = self.user_dict.get("gdrive_id", "") or ""
                    LOGGER.info("Using user drive: %s2", target_id)
                else:
                    target_id = ""
                count, contents = await sync_to_async(
                    gdSearch(
                        isRecursive=self.isRecursive, itemType=self.type
                    ).drive_list,
                    self.query,
                    target_id,
                    self.user_id,
                    self.style,
                )
            elif self.mode == "rclone":
                config = ConfigParser()
                async with aiopen(self.config_path, "r") as f:
                    config.read_string(await f.read())
                if config.has_section("combine"):
                    config.remove_section("combine")

                for remote in config.sections():
                    isdir = self.type == "folders"
                    typee = "--dirs-only" if isdir else "--files-only"
                    cmd = [
                        "wzone",
                        "lsjson",
                        typee,
                        "--fast-list",
                        "--no-modtime",
                        "--ignore-case",
                        "-R",
                        "--include",
                        f"*{self.query}*",
                        "--config",
                        self.config_path,
                        f"{remote}:",
                    ]
                    out, _, code = await cmd_exec(cmd)
                    contents = []
                    if code == 0:
                        msg, files = "", jsonloads(out)
                        if files:
                            index = 1
                            for file in files:
                                name, size, mime, msg = (
                                    file["Name"],
                                    file["Size"],
                                    file["MimeType"],
                                    "",
                                )
                                if isdir and self.query.lower() not in name.lower():
                                    continue
                                cmd = [
                                    "wzone",
                                    "link",
                                    "--config",
                                    self.config_path,
                                    f"{remote}:{file['Path']}",
                                ]
                                link, _, code = await cmd_exec(cmd)
                                number = str(index).zfill(3)
                                if code == 0:
                                    msg += f'{number}. <a href="{link}">{name}</a>\n'
                                else:
                                    msg += f"{number}. <code>{name}</code>\n"
                                if size > 0:
                                    msg += (
                                        f"<b>Size:</b> {get_readable_file_size(size)}\n"
                                    )
                                if not file["IsDir"]:
                                    msg += f"<b>Type:</b> {mime}\n"
                                index += 1
                                contents.append(f"{msg}\n")

            self._content.setdefault(self.query, {})
            self._content.update({self.query: {"data": contents, "mode": self.mode}})

        dt_date, dt_time = get_date_time(self.message)
        cap = (
            f"<b>{self.mode.title()} Search Result:</b>\n"
            f"<b>╭ Found: </b>{count if self.mode == 'gdrive' else len(contents)}\n"
            f"<b>┊ Cc: </b>{self.tag}\n"
            f"<b>┊ Action: </b>{action(self.message)}\n"
            f"<b>┊ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
            f"<b>┊ Add: </b>{dt_date}\n"
            f"<b>┊ At: </b>{dt_time} ({config_dict['TIME_ZONE_TITLE']})\n"
        )

        if self.mode != "telegram":
            cap += f"<b>┊ Type: </b>{self.type.title() if self.type != 'both' else 'Folders & Files'}\n"
        if self.mode == "gdrive":
            cap += (
                f"<b>┊ Recursive: </b>{'Enable' if self.isRecursive else 'Disable'}\n"
            )
        cap += f"<b>╰ Key Input: </b><code>{self.query.title()}</code>"

        if self.mode == "gdrive":
            if contents:
                if self.style == "graph" and config_dict["ENABLE_IMAGE_MODE"]:
                    await gather(
                        sendPhoto(
                            cap, self.message, config_dict["IMAGE_SEARCH"], contents
                        ),
                        deleteMessage(self.editable),
                    )
                    self.event.set()
                    return
                if self.style == "html":
                    await gather(
                        sendFile(
                            self.message, contents, cap, config_dict["IMAGE_HTML"]
                        ),
                        deleteMessage(self.editable),
                    )
                    self.event.set()
                    return
            elif self.style != "tele":
                await self.list_buttons()

        self.tele_list.set_data(contents or [], cap)

    async def list_buttons(self):
        buttons = ButtonMaker()
        buttons.button_data("Cancel", "list cancel", "footer")
        if self.changeQuery:
            buttons.button_data("<<", "list can_query")
            msg, buttons = (
                f"{self.tag}, send new query to search..\n\n<i>Current query is <b>{self.query}</b></i>",
                buttons.build_menu(1),
            )
        elif not self.mode and not self.search:
            buttons.button_data("Change Query", "list change", "header")
            buttons.button_data("GDrive", "list gdrive _")
            buttons.button_data("RClone", "list rclone _")
            buttons.button_data("Telegram", "list telegram _")
            msg, buttons = (
                f"{self.tag}, search list for <b>{self.query}</b>?",
                buttons.build_menu(3),
            )
        elif not self.search and self.mode == "rclone":
            user_config = self.config_path.startswith(("rclone/", "tokens/"))
            buttons.button_data("Change Query", "list change", "header")
            buttons.button_data(
                f"{'✅ ' if user_config else ''}User Config", "list uc _", "header"
            )
            buttons.button_data("Files", "list files _")
            buttons.button_data("Folders", "list folders _")
            buttons.button_data("<<", "list back", "footer")
            msg, buttons = (
                f"{self.tag}, select type rclone for search <b>{self.query}</b>?",
                buttons.build_menu(2),
            )
        elif not self.search and self.mode == "gdrive":
            if self.type:
                buttons.button_data("HTML", "list html _")
                buttons.button_data("Telegraph", "list graph _")
                buttons.button_data("Telegram", "list tele _")
                buttons.button_data("<<", "list back", "footer")
                msg, buttons = (
                    f"{self.tag}, select style for search <b>{self.query}</b>?",
                    buttons.build_menu(3),
                )
            else:
                user_config = self.config_path.startswith(("rclone/", "tokens/"))
                buttons.button_data("Change Query", "list change", "header")
                buttons.button_data(
                    f"{'✅ ' if self.isRecursive else ''}Recursive",
                    "list rec",
                    "header",
                )
                buttons.button_data(
                    f"{'✅ ' if user_config else ''}User Token", "list ut _", "header"
                )
                buttons.button_data("Files", "list files")
                buttons.button_data("Folders", "list folders")
                buttons.button_data("Both", "list both")
                buttons.button_data("<<", "list back", "footer")
                msg, buttons = (
                    f"{self.tag}, select options for search <b>{self.query}</b>?",
                    buttons.build_menu(3),
                )
        elif self.search:
            msg, buttons = await self.tele_list.get_content(
                "list", extra_buttons=[("Change Query", "change")]
            )
            if not msg:
                self.search = False
                msg = f"Search for <b>{self.query}</b> not found!"
                buttons = ButtonMaker()
                buttons.button_data("<<", "list back")
                buttons = buttons.build_menu(1)
        await editMessage(msg, self.editable, buttons)

    async def get_rclone_path(self):
        future = self._event_handler()
        await gather(self.list_buttons(), wrap_future(future))
        if isinstance(self.is_cancelled, str):
            return self.is_cancelled


async def change_query(_, message: Message, obj: MultiSerach):
    obj.reset()
    obj.query_event.set()
    obj.query = message.text.strip()
    await gather(deleteMessage(message), obj.list_buttons())


@new_task
async def cb(_, query: CallbackQuery, obj: MultiSerach):
    data = query.data.split()
    if len(data) == 2:
        await query.answer()
    if data[1] == "back":
        if obj.type:
            obj.type = ""
        elif not obj.changeQuery:
            obj.reset()
        await obj.list_buttons()
    match data[1]:
        case "cancel":
            obj.is_cancelled = f"{obj.tag}, list has been cancelled!"
            obj.query_event.set()
            obj.event.set()
        case "change":
            obj.changeQuery = True
            await obj.list_buttons()
            obj.change_query_handler()
        case "can_query":
            obj.changeQuery = False
            obj.query_event.set()
            await obj.list_buttons()
        case "html" | "graph" | "tele" as value:
            if not await aiopath.exists(obj.config_path) and not obj.user_dict.get(
                "use_sa"
            ):
                await query.answer(
                    f"{obj.config_path or 'Token.pickle'} not exists!", True
                )
                return
            obj.style, obj.search = value, True
            await gather(
                query.answer(),
                obj.search_files(),
                editMessage(
                    f"<i>Listing drive search for <b>{obj.query}</b>, palease wait...</i>",
                    obj.editable,
                ),
            )
            if value != "tele":
                return
            await obj.list_buttons()
        case "ut" | "uc" | "rec" as value:
            if value == "rec":
                obj.isRecursive = not obj.isRecursive
            else:
                if not obj.config_path.startswith(("rclone/", "tokens/")):
                    dirpath, extension = (
                        ("tokens", "pickle") if value == "ut" else ("rclone", "conf")
                    )
                    config = ospath.join(dirpath, f"{obj.user_id}.{extension}")
                else:
                    dirpath = config = (
                        "token.pickle" if value == "ut" else "rclone.conf"
                    )
                if not await aiopath.isfile(config):
                    await query.answer(f"User {config} not found!", True)
                    return
                obj.config_path = config
            await gather(query.answer(), obj.list_buttons())
        case "gdrive" | "rclone" | "telegram" as value:
            obj.mode = value
            if value == "telegram":
                await intialize_savebot(
                    obj.user_dict.get("session_string"), True, obj.user_id
                )
                async with bot_lock:
                    userbot: Client = (
                        bot_dict[obj.user_id]["SAVEBOT"] or bot_dict["SAVEBOT"]
                    )
                if not userbot:
                    await query.answer("Telegram search required session string!", True)
                    return
                obj.engine, obj.search = userbot, True
                await gather(
                    editMessage(
                        f"<i>Listing telegram search for <b>{obj.query}</b>, palease wait...</i>",
                        obj.editable,
                    ),
                    obj.search_files(),
                )
            await gather(query.answer(), obj.list_buttons())
        case "files" | "folders" | "both" as value:
            obj.type = value
            if obj.mode == "rclone":
                if not obj.config_path.endswith(".conf") and await aiopath.exists(
                    "rclone.conf"
                ):
                    obj.config_path = "rclone.conf"
                if not obj.config_path:
                    await query.answer(
                        f"{obj.config_path or 'Rclone.conf'} not exists!", True
                    )
                    return
                obj.search = True
                await gather(
                    query.answer(),
                    editMessage(
                        f"<i>Listing rclone search for <b>{obj.query}</b>, palease wait...</i>",
                        obj.editable,
                    ),
                    obj.search_files(),
                )
            await obj.list_buttons()
        case _ if len(data) > 2:
            if data[2] == "close":
                await gather(
                    query.answer(),
                    deleteMessage(query.message, obj.message, obj.editable),
                )
                obj.event.set()
                return
            if data[2] == "page":
                await query.answer(f"Total Page ~ {obj.pages}", True)
                return
            tdata = int(data[4]) if data[2] == "foot" else int(data[3])
            msg, buttons = await obj.tele_list.get_content(
                "list", data[2], tdata, [("Change Query", "change")]
            )
            if not buttons:
                await query.answer(msg, True)
                return
            await gather(query.answer(), editMessage(msg, obj.editable, buttons))


@new_task
async def multi_search(client: Client, message: Message):
    reply_to = message.reply_to_message
    if fmsg := await UseCheck(message).run(session=True):
        await auto_delete_message(message, fmsg, reply_to)
        return

    if reply_to and is_media(reply_to) or not reply_to and len(message.command) == 1:
        msg = await sendMessage(
            f"{message.from_user.mention}, send a search key along with command or by reply with command.",
            message,
        )
        await auto_delete_message(message, msg, reply_to)
        return

    query = reply_to.text.strip() if reply_to else " ".join(message.command[1:])
    msg = await sendMessage(f"<i>Searcing <b>{query}</b>...</i>", message)
    await sleep(0.5)
    res = await MultiSerach(client, message, msg, query).get_rclone_path()
    if res:
        await editMessage(res, msg)


bot.add_handler(
    MessageHandler(
        multi_search,
        filters=command(BotCommands.ListCommand) & CustomFilters.authorized,
    )
)
