from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from random import choice
from time import time

from bot import bot, config_dict
from bot.helper.ext_utils.bot_utils import is_pm_enabled, sync_to_async, new_task
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.links_utils import is_gdrive_link, get_link, is_media
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_date_time,
    get_readable_time,
    action,
)
from bot.helper.mirror_utils.gdrive_utlis.count import gdCount
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    deleteMessage,
    sendMessage,
    sendingMessage,
    sendSticker,
    auto_delete_message,
    copyMessage,
)


@new_task
async def countNode(_, message: Message):
    reply_to = message.reply_to_message
    isSuperGoup = message.chat.title in ("SUPERGROUP", "CHANNEL")
    user_id = message.from_user.id if message.from_user else message.sender_chat.id
    tag = message.from_user.mention

    if fmsg := await UseCheck(message).run(send_pm=True):
        await auto_delete_message(message, fmsg, reply_to)
        return

    if (
        reply_to
        and not reply_to.sender_chat
        and not getattr(reply_to.from_user, "is_bot", None)
    ):
        tag = reply_to.from_user.mention

    if (link := get_link(message)) and is_gdrive_link(link) and not is_media(reply_to):
        TIME_ZONE_TITLE = config_dict["TIME_ZONE_TITLE"]
        dt_date, dt_time = get_date_time(message)
        msg = await sendMessage(f"<i>Counting:</i> <code>{link}</code>", message)
        name, mime_type, size, files, folders = await sync_to_async(
            gdCount().count, link, user_id
        )
        await deleteMessage(msg)
        if "not found" in name or not mime_type:
            text = (
                f"<b>{name}</b>\n"
                "<b>╭ Elapsed: </b>{get_readable_time(time() - message.date.timestamp())}\n"
            )
        else:
            text = (
                f"<code>{name}</code>\n"
                f"<b>╭ Size: </b>{get_readable_file_size(size)}\n"
                f"<b>┊ Type: </b>{mime_type}\n"
            )
            if mime_type == "Folder":
                text += f"<b>┊ SubFolders: </b>{folders}\n<b>┊ Files: </b>{files}\n"
            text += f"<b>┊ Elapsed: </b>{get_readable_time(time() - message.date.timestamp())}\n"
        text += (
            f"<b>┊ Action: </b>{action(message)}\n"
            f"<b>┊ Cc: </b>{tag}\n"
            f"<b>┊ Add: </b>{dt_date}\n"
            f"<b>╰ At: </b>{dt_time} ({TIME_ZONE_TITLE})"
        )
        if config_dict["SOURCE_LINK"]:
            buttons = ButtonMaker()
            buttons.button_link("Source", get_link(message))
        msg = await sendingMessage(
            text,
            message,
            choice(config_dict["IMAGE_COMPLETE"].split()),
            buttons.build_menu(2),
        )
        if STICKERID_COUNT := config_dict["STICKERID_COUNT"]:
            await sendSticker(STICKERID_COUNT, message)
        if is_pm_enabled(user_id) and isSuperGoup:
            await copyMessage(user_id, msg)
    else:
        msg = await sendMessage(
            "Send <b>GDrive</b> link along with command or by replying to the link by command",
            message,
        )

    if (
        reply_to
        and isSuperGoup
        and (stime := config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"])
    ):
        await auto_delete_message(message, msg, reply_to, stime=stime)


bot.add_handler(
    MessageHandler(
        countNode, filters=command(BotCommands.CountCommand) & CustomFilters.authorized
    )
)
