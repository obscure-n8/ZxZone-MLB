from asyncio import sleep, gather
from functools import wraps
from pyrogram import Client
from pyrogram.errors import (
    FloodWait,
    UserBlocked,
    UserDeactivatedBan,
    UserDeactivated,
    UserIsBlocked,
    InputUserDeactivated,
)
from pyrogram.types import Message, InlineKeyboardMarkup, InputMediaPhoto
from re import match as re_match, findall as re_findall
from time import time

from bot import (
    bot,
    bot_dict,
    bot_lock,
    bot_loop,
    Intervals,
    config_dict,
    task_dict_lock,
    status_dict,
    DATABASE_URL,
    LOGGER,
)
from bot.helper.ext_utils.bot_utils import setInterval, sync_to_async
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.exceptions import TgLinkException
from bot.helper.ext_utils.files_utils import clean_target, download_content
from bot.helper.ext_utils.status_utils import get_readable_message
from bot.helper.telegram_helper.bot_commands import BotCommands


class Limits:
    def __init__(self):
        self.total = 0

    def _extracted_text(self, msg: str, lmax: int):
        self.total = 0
        if match := re_findall(r'(</?\S{,4}>|<a\s?href=[\'"]\S+[\'"]|>)', msg):
            self.total = len("".join(match))
        limit = self.total + lmax
        space = msg[:limit].count(" ")
        return msg.strip()[: limit - space]

    def caption(self, caption: str):
        return self._extracted_text(caption, 1024)

    def text(self, text: str):
        return self._extracted_text(text, 4096)


limit = Limits()


def handle_message(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        try:
            return await func(*args, **kwargs)
        except FloodWait as f:
            LOGGER.error("%s(): %s", func_name, f)
            await sleep(f.value * 1.2)
            return await wrapper(*args, **kwargs)
        except (
            UserBlocked,
            UserDeactivatedBan,
            UserDeactivated,
            UserIsBlocked,
            InputUserDeactivated,
        ):
            if DATABASE_URL:
                user_id = args[0] if func_name == "copyMessage" else args[1]
                await DbManager().delete_user(user_id)
        except Exception as e:
            if not kwargs.get("nolog"):
                LOGGER.error("%s(): %s", func_name, e)
            if func_name == "editMessage":
                return str(e)

    return wrapper


async def sendingMessage(
    text: str, message: Message, photo, reply_markup: InlineKeyboardMarkup = None
):
    # Image mode disabled — always send text only
    return await sendMessage(limit.text(text), message, reply_markup)


@handle_message
async def sendMessage(
    text: str, message: Message, reply_markup: InlineKeyboardMarkup = None, block=True
):
    return await message.reply_text(
        limit.text(text),
        quote=True,
        reply_markup=reply_markup,
        disable_notification=True,
        disable_web_page_preview=True,
    )


@handle_message
async def sendMedia(
    caption: str,
    chat_id: int,
    reply_to: Message,
    reply_markup: InlineKeyboardMarkup = None,
):
    caption = limit.caption(caption)
    if not reply_to or getattr(reply_to, "empty", False) or not reply_to.chat:
        return await bot.send_message(
            chat_id,
            caption,
            reply_markup=reply_markup,
            disable_notification=True,
            disable_web_page_preview=True,
        )
    try:
        return await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=reply_to.chat.id,
            message_id=reply_to.id,
            caption=caption,
            reply_markup=reply_markup,
            disable_notification=True,
        )
    except Exception as error:
        if "empty messages cannot be copied" not in str(error).lower():
            raise
        return await bot.send_message(
            chat_id,
            caption,
            reply_markup=reply_markup,
            disable_notification=True,
            disable_web_page_preview=True,
        )


@handle_message
async def sendSticker(fileid: str, message: Message, is_misc=False):
    msgsticker = await message.reply_sticker(
        fileid, quote=True, disable_notification=True
    )
    if not is_misc and config_dict["STICKER_DELETE_DURATION"]:
        bot_loop.create_task(
            auto_delete_message(
                msgsticker, stime=config_dict["STICKER_DELETE_DURATION"]
            )
        )


@handle_message
async def sendCustom(
    text: str,
    chat_id: str | int,
    reply_markup: InlineKeyboardMarkup = None,
    nolog=False,
):
    return await bot.send_message(
        chat_id, limit.text(text), reply_markup=reply_markup, disable_notification=True
    )


@handle_message
async def editCustom(text: str, chat_id: int, message_id: int, reply_markup=None):
    return await bot.edit_message_text(
        chat_id,
        message_id,
        limit.text(text),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


@handle_message
async def editMessage(
    text: str, message: Message, reply_markup: InlineKeyboardMarkup = None, block=True
):
    return await message.edit_text(
        limit.text(text), reply_markup=reply_markup, disable_web_page_preview=True
    )


@handle_message
async def copyMessage(
    chat_id: int,
    message: Message,
    reply_markup: InlineKeyboardMarkup = None,
    nolog=False,
):
    if not reply_markup:
        if (markup := message.reply_markup) and markup.inline_keyboard:
            reply_markup = markup
    return await bot.copy_message(
        chat_id=chat_id,
        from_chat_id=message.chat.id,
        message_id=message.id,
        disable_notification=True,
        reply_markup=reply_markup,
    )


@handle_message
async def sendPhoto(
    caption: str, message: Message, photo, reply_markup: InlineKeyboardMarkup = None
):
    # Photo disabled — fallback to text message
    return await message.reply_text(
        limit.text(caption),
        quote=True,
        reply_markup=reply_markup,
        disable_notification=True,
        disable_web_page_preview=True,
    )


@handle_message
async def editPhoto(
    caption: str, message: Message, photo, reply_markup: InlineKeyboardMarkup = None
):
    # Photo disabled — fallback to text edit
    return await message.edit_text(
        limit.text(caption),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


@handle_message
async def editMarkup(message: Message, reply_markup: InlineKeyboardMarkup = None):
    return await message.edit_reply_markup(reply_markup)


@handle_message
async def deleteMessage(*args: Message):
    await gather(*[msg.delete() for msg in args if isinstance(msg, Message)])


@handle_message
async def sendFile(message: Message, doc: str, caption: str = "", thumb=None):
    thumbnail = None
    if thumb and await download_content(thumb, "thumb.png"):
        thumbnail = "thumb.png"
    await message.reply_document(
        doc, caption=limit.caption(caption), quote=True, thumb=thumbnail
    )
    await gather(
        *[clean_target(file) for file in [doc, "thumb.png"] if file != "log.txt"]
    )


async def auto_delete_message(*args, stime=config_dict["AUTO_DELETE_MESSAGE_DURATION"]):
    if stime:
        await sleep(stime)
        await deleteMessage(*args)


async def delete_status():
    async with task_dict_lock:
        for key, data in list(status_dict.items()):
            try:
                del status_dict[key]
                await deleteMessage(data["message"])
            except Exception as e:
                LOGGER.error(str(e))


async def get_tg_link_message(link: str, user_id: int):
    links, message = [], None
    if link.startswith("https://t.me/"):
        private = False
        msg = re_match(
            r"https:\/\/t\.me\/(?:c\/)?([^\/]+)(?:\/[^\/]+)?\/([0-9-]+)", link
        )
    else:
        private = True
        msg = re_match(
            r"tg:\/\/openmessage\?user_id=([0-9]+)&message_id=([0-9-]+)", link
        )
    chat, msg_id = msg.group(1), msg.group(2)
    async with bot_lock:
        userbot: Client = bot_dict[user_id]["SAVEBOT"] or bot_dict["SAVEBOT"]
        save_bot = bot_dict["SAVEBOT"]

    if "-" in msg_id:
        start_id, end_id = msg_id.split("-")
        msg_id = start_id = int(start_id)
        end_id = int(end_id)
        btw = end_id - start_id
        if private:
            link = link.split("&message_id=")[0]
            links.append(f"{link}&message_id={start_id}")
            for _ in range(btw):
                start_id += 1
                links.append(f"{link}&message_id={start_id}")
        else:
            link = link.rsplit("/", 1)[0]
            links.append(f"{link}/{start_id}")
            for _ in range(btw):
                start_id += 1
                links.append(f"{link}/{start_id}")
    else:
        msg_id = int(msg_id)

    if chat.isdigit():
        chat = int(chat) if private else int(f"-100{chat}")
    try:
        await bot.get_chat(chat)
    except:
        private = True
        if not userbot:
            raise TgLinkException(
                f"User session required for this private link! Try add user session /{BotCommands.UserSetCommand}"
            )
    if private:
        if (message := await userbot.get_messages(chat, msg_id)) and not message.empty:
            return (userbot, links) if links else (userbot, message)
        raise TgLinkException("Mostly message has been deleted!")
    if (
        userbot
        and (message := await userbot.get_messages(chat, msg_id))
        and not message.empty
    ):
        return (userbot, links) if links else (userbot, message)
    if (
        not userbot
        and (message := await bot.get_messages(chat, msg_id))
        and not message.empty
    ):
        return (bot, links) if links else (bot, message)
    raise TgLinkException(
        "Failed getting data from link. Mostly message has been deleted or member chat required"
        + (f" try /{BotCommands.JoinChatCommand}!" if userbot == save_bot else "!")
    )


async def update_status_message(sid, force=False):
    async with task_dict_lock:
        if not status_dict.get(sid):
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
            return
        if not force and time() - status_dict[sid]["time"] < 3:
            return
        status_dict[sid]["time"] = time()
        page_no = status_dict[sid]["page_no"]
        status = status_dict[sid]["status"]
        is_user = status_dict[sid]["is_user"]
        page_step = status_dict[sid]["page_step"]
        text, buttons = await sync_to_async(
            get_readable_message, sid, is_user, page_no, status, page_step
        )
        if text is None:
            del status_dict[sid]
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
            return
        if status_dict[sid]["message"] and text != status_dict[sid]["message"].text:
            message = await editMessage(text, status_dict[sid]["message"], buttons)
            if not message or isinstance(message, str):
                if message.startswith("Telegram says: [400"):
                    del status_dict[sid]
                    if obj := Intervals["status"].get(sid):
                        obj.cancel()
                        del Intervals["status"][sid]
                else:
                    LOGGER.error(
                        "Status with id: %s haven't been updated. Error: %s",
                        sid,
                        message,
                    )
                return
            if not isinstance(message, str) and message:
                status_dict[sid]["message"].text = text
            status_dict[sid]["time"] = time()


async def sendStatusMessage(msg, user_id=0):
    async with task_dict_lock:
        sid = user_id or msg.chat.id
        is_user = bool(user_id)
        if sid in list(status_dict):
            page_no = status_dict[sid]["page_no"]
            status = status_dict[sid]["status"]
            page_step = status_dict[sid]["page_step"]
            text, buttons = await sync_to_async(
                get_readable_message, sid, is_user, page_no, status, page_step
            )
            if text is None:
                del status_dict[sid]
                if obj := Intervals["status"].get(sid):
                    obj.cancel()
                    del Intervals["status"][sid]
                return
            message = status_dict[sid]["message"]
            _, message = await gather(
                deleteMessage(message), sendMessage(text, msg, buttons, block=False)
            )
            if not isinstance(message, str) and message:
                message.text = text
                status_dict[sid].update({"message": message, "time": time()})
        else:
            text, buttons = await sync_to_async(get_readable_message, sid, is_user)
            if text is None:
                return
            message = await sendMessage(text, msg, buttons, block=False)
            if not isinstance(message, str) and message:
                message.text = text
                status_dict[sid] = {
                    "message": message,
                    "time": time(),
                    "page_no": 1,
                    "page_step": 1,
                    "status": "All",
                    "is_user": is_user,
                }
    if not Intervals["status"].get(sid):
        Intervals["status"][sid] = setInterval(
            config_dict["STATUS_UPDATE_INTERVAL"], update_status_message, sid
        )
