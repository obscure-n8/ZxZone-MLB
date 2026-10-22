from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery

from bot import bot, config_dict
from bot.helper.ext_utils.bot_utils import is_premium_user, default_button
from bot.helper.telegram_helper.message_utils import copyMessage


async def save_handler(_, query: CallbackQuery):
    message = query.message
    user_id = query.from_user.id
    if config_dict["PREMIUM_MODE"] and not is_premium_user(user_id):
        await query.answer("Upss, for premium user only!!", True)
        return
    buttons = await default_button(message)
    if not await copyMessage(user_id, message, buttons):
        await query.answer("Upss, start me in PM and try agian!", True)
    else:
        await query.answer("Saving message...")


bot.add_handler(CallbackQueryHandler(save_handler, filters=regex("^save")))
