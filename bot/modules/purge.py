from asyncio import gather
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from time import time

from bot import bot
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    editMessage,
    deleteMessage,
    handle_message,
)


@new_task
async def purge_message(client: Client, message: Message):
    reply_to = message.reply_to_message
    msg = await sendMessage("<i>Deleting message, please wait..</i>", message)
    if not reply_to:
        await editMessage("Reply to a message to purge from.", msg)
        return

    @handle_message
    async def _delete(mid, nolog=True):
        await client.delete_messages(message.chat.id, mid)

    await gather(*[_delete(mid) for mid in range(reply_to.id, message.id)])
    await gather(
        deleteMessage(message),
        editMessage(
            f"Purged message successfully in {get_readable_time(time() - message.date.timestamp()) or '0s'}.",
            msg,
        ),
    )


bot.add_handler(
    MessageHandler(
        purge_message, filters=command(BotCommands.PurgeCommand) & CustomFilters.owner
    )
)
