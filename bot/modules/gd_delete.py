from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from bot import bot, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task
from bot.helper.ext_utils.links_utils import is_gdrive_link, get_link
from bot.helper.mirror_utils.gdrive_utlis.delete import gdDelete
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage


@new_task
async def deletefile(_, message: Message):
    link = get_link(message)
    if is_gdrive_link(link):
        LOGGER.info(link)
        msg = await sync_to_async(
            gdDelete().deletefile,
            link,
            message.from_user.id if message.from_user else message.sender_chat.id,
        )
    else:
        msg = "Send <b>GDrive</b> link along with command or by replying to the link by command"
    msg = await sendMessage(msg, message)
    await auto_delete_message(message, msg, message.reply_to_message)


bot.add_handler(
    MessageHandler(
        deletefile,
        filters=command(BotCommands.DeleteCommand) & CustomFilters.authorized,
    )
)
