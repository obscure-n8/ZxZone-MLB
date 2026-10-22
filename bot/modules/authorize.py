from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from time import time

from bot import bot, user_data
from bot.helper.ext_utils.bot_utils import update_user_ldata, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, auto_delete_message


@new_task
async def authorize(_, message: Message):
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id if reply_to.from_user else reply_to.sender_chat.id
    else:
        id_ = message.chat.id
    if id_ in user_data and user_data.get(id_, {}).get("is_auth"):
        msg = "Already Authorized!"
    else:
        await update_user_ldata(id_, "is_auth", True)
        msg = "Authorized Successfully."
    msg = await sendMessage(msg, message)
    await auto_delete_message(message, msg)


@new_task
async def unauthorize(_, message: Message):
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id if reply_to.from_user else reply_to.sender_chat.id
    else:
        id_ = message.chat.id
    if id_ not in user_data or user_data.get(id_, {}).get("is_auth"):
        await update_user_ldata(id_, "is_auth", False)
        msg = "Unauthorized Successfully."
    else:
        msg = "Already Unauthorized!"
    msg = await sendMessage(msg, message)
    await auto_delete_message(message, msg)


@new_task
async def addSudo(_, message: Message):
    id_ = day = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
        if len(msg) > 2 and msg[2].isdigit():
            day = int(msg[2])
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id if reply_to.from_user else reply_to.sender_chat.id
        if len(msg) > 1 and msg[1].isdigit():
            day = int(msg[1])
    if id_:
        if day:
            await update_user_ldata(
                id_, "sudo_left", int(time() + (86400 * int(msg[2])))
            )
        if user_data.get(id_, {}).get("is_sudo"):
            msg = "Already Sudo!"
        else:
            await update_user_ldata(id_, "is_sudo", True)
            msg = "Promoted as Sudo."
    else:
        msg = "Give ID or Reply To message of whom you want to Promote."
    msg = await sendMessage(msg, message)
    await auto_delete_message(message, msg)


@new_task
async def removeSudo(_, message: Message):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id if reply_to.from_user else reply_to.sender_chat.id
    if id_:
        if user_data.get(id_, {}).get("is_sudo"):
            user_data[id_].pop("sudo_left", None)
            await update_user_ldata(id_, "is_sudo", False)
            msg = "Demoted!"
        else:
            msg = "Currently not sudo!"
    else:
        msg = "Give ID or Reply To message of whom you want to remove from Sudo."
    msg = await sendMessage(msg, message)
    await auto_delete_message(message, msg)


bot.add_handler(
    MessageHandler(
        authorize, filters=command(BotCommands.AuthorizeCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    MessageHandler(
        unauthorize,
        filters=command(BotCommands.UnAuthorizeCommand) & CustomFilters.sudo,
    )
)
bot.add_handler(
    MessageHandler(
        addSudo, filters=command(BotCommands.AddSudoCommand) & CustomFilters.owner
    )
)
bot.add_handler(
    MessageHandler(
        removeSudo, filters=command(BotCommands.RmSudoCommand) & CustomFilters.owner
    )
)
