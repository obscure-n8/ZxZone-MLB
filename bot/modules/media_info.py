from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from bot import bot, config_dict
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.links_utils import is_url, get_url_name, get_link, is_media
from bot.helper.ext_utils.media_utils import post_media_info
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.stream_utils.file_properties import gen_link
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    sendPhoto,
    editPhoto,
    copyMessage,
    deleteMessage,
)
from bot.helper.video_utils.executor import get_metavideo


@new_task
async def medinfo(_, message: Message):
    link, media, cmsg = get_link(message), None, None
    if (
        (reply_to := message.reply_to_message)
        and (media := is_media(reply_to))
        and (chat_id := config_dict["LEECH_LOG"])
    ):
        cmsg = await copyMessage(chat_id, reply_to)
        link = (await gen_link(cmsg or reply_to))[1]

    if link and is_url(link):
        img = config_dict["IMAGE_MEDINFO"]
        msg = await sendPhoto("<i>Processing, please wait...</i>", message, img)
        if (size := int((await get_metavideo(link))[1].get("size", 0))) and (
            result := await post_media_info(link, size, is_link=True)
        ):
            buttons = ButtonMaker()
            buttons.button_link("Media Info", result)
            if not media:
                buttons.button_link("Source", link)
            await editPhoto(
                f"<b>MEDIA INFO RESULT</b>\n<code>{get_url_name(link)}</code>\n<b>Size:</b> {get_readable_file_size(size)}",
                msg,
                img,
                buttons.build_menu(1),
            )
        else:
            await editPhoto("Error when getting info!", msg, img)
    else:
        await sendMessage(
            "Send command along with link or by reply to the link/media!", message
        )

    if cmsg:
        await deleteMessage(cmsg)


bot.add_handler(
    MessageHandler(
        medinfo, command(BotCommands.MediaInfoCommand) & CustomFilters.authorized
    )
)
