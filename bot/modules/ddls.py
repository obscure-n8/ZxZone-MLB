from base64 import b64encode
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from re import findall as re_findall

from bot import bot, config_dict
from bot.helper.ext_utils.bot_utils import (
    new_task,
    sync_to_async,
    default_button,
    get_content_type,
    is_pm_enabled,
)
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.links_utils import is_media, get_url_name
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.stream_utils.file_properties import gen_link
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    editMarkup,
    auto_delete_message,
    copyMessage,
    deleteMessage,
)


@new_task
async def generate_ddl(_, message: Message):
    if (
        config_dict["ENABLE_STREAM_LINK"]
        and config_dict["STREAM_BASE_URL"]
        and config_dict["STREAM_PORT"]
        and config_dict["LEECH_LOG"]
    ):
        reply_to = message.reply_to_message
        supergroup = message.chat.type.name in ("SUPERGROUP", "CHANNEL")
        user_id = message.from_user.id if message.from_user else message.sender_chat.id
        if fmsg := await UseCheck(message).run(forpremi=True, session=True):
            await auto_delete_message(message, fmsg, reply_to)
            return
        buttons = ButtonMaker()
        save_message = config_dict["SAVE_MESSAGE"] and supergroup
        if save_message:
            buttons.button_data("Save Message", "save", "footer")
        is_file = is_media(reply_to)
        streams, no_data = [], False

        if reply_to and is_file:
            cmsg = await copyMessage(config_dict["LEECH_LOG"], reply_to)
            for mode, link in zip(["Stream", "Download"], await gen_link(cmsg)):
                if link:
                    buttons.button_link(
                        mode, await sync_to_async(short_url, link, user_id), "header"
                    )
            streams.append(True)
            cmsg = await editMarkup(cmsg, buttons.build_menu(2))
        else:
            for link in re_findall(
                r"([https?:\/\/(?:www\.)?\S+]{2,256}\.[a-z]{2,6}\b\S*)",
                reply_to.text if reply_to else message.text,
            ):
                typee = ""
                mime_type, size = await get_content_type(link)
                if mime_type.startswith("video"):
                    typee = "video"
                elif mime_type.startswith("audio"):
                    typee = "audio"
                if typee:
                    stream_url = b64encode(link.encode("utf-8")).decode("utf-8")
                    stream_url = await sync_to_async(
                        short_url,
                        f"{config_dict['STREAM_BASE_URL']}/stream/{stream_url}?type={typee}",
                        user_id,
                    )
                    streams.append(
                        (
                            stream_url,
                            get_url_name(link),
                            get_readable_file_size(size),
                            link,
                        )
                    )
            if streams:
                if len(streams) == 1:
                    strem_url, name, size, src_link = streams[0]
                    text = f"<code>{name}</code>\n<b>Size: </b>{size}\n\n<b>Stream Link:</b>\n<code>{strem_url}</code>"
                    buttons.button_link(
                        "Stream Link",
                        await sync_to_async(short_url, strem_url, user_id),
                    )
                    buttons.button_link("Source Link", src_link)
                else:
                    text = "<b>Stream Links:</b>\n"
                    for index, stream in enumerate(streams, 1):
                        text += f'<b>{index}.</b> <a href="{stream[0]}">{stream[1]}</a> <b>({stream[2]})</b>\n'
            else:
                text, no_data = (
                    "Send direct download link (ddl) with contain any video or audio!",
                    True,
                )
                buttons.reset()
            cmsg = await sendMessage(text, message, buttons.build_menu(2))

        if (
            config_dict["LEECH_LOG"] != message.chat.id
            and supergroup
            and is_file
            and streams
        ):
            await copyMessage(message.chat.id, cmsg)
        send_pm = is_pm_enabled(user_id)
        if send_pm and is_file or send_pm and supergroup:
            markup = await default_button(cmsg) if save_message else None
            await copyMessage(user_id, cmsg, markup)
        if not no_data:
            await deleteMessage(message, reply_to)
    else:
        await sendMessage("This mode has been disabled!", message)


bot.add_handler(
    MessageHandler(
        generate_ddl, command(BotCommands.DdlsCommand) & CustomFilters.authorized
    )
)
