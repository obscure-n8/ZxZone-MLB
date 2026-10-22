from asyncio import sleep, gather
from pyrogram import Client
from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery, Message

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import action
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.modules.clone import Clone
from bot.modules.mirror_leech import Mirror
from bot.modules.video_tools import VidTools
from bot.modules.ytdlp import YtDlp


incompte_dict = {}


async def set_incomplte_task(cid, link):
    message: Message = await bot.get_messages(cid, int(link.split("/")[-1]))
    if not message.empty:
        try:
            mesg = message.text.split("\n")
            if len(mesg) > 1 and mesg[1].startswith("Tag: "):
                try:
                    id_ = int(mesg[1].split()[-1])
                    message.from_user = await bot.get_users(id_)
                except Exception as e:
                    LOGGER.error(e)
            elif message.from_user.is_bot and (reply := message.reply_to_message):
                message.from_user = reply.from_user
            uid = message.from_user.id
            incompte_dict.setdefault(uid, {"msgs": []})
            incompte_dict[uid]["msgs"].append(message)
        except Exception as e:
            LOGGER.error(e)


async def start_resume_task(client: Client, tasks: list):
    user_id = ""
    for msg in tasks:
        cmd = f"{action(msg)[1:]}{config_dict['CMD_SUFFIX']}"
        isQbit = isLeech = isYt = isJd = isClone = isVt = False

        def _check_cmd(cmds, command=cmd):
            return any(x == command for x in cmds)

        if _check_cmd(BotCommands.QbMirrorCommand):
            isQbit = True
        elif _check_cmd(BotCommands.LeechCommand):
            isLeech = True
        elif _check_cmd(BotCommands.QbLeechCommand):
            isQbit = isLeech = True
        elif _check_cmd(BotCommands.YtdlCommand):
            isYt = True
        elif _check_cmd(BotCommands.YtdlLeechCommand):
            isLeech = isYt = True
        elif _check_cmd(BotCommands.JdMirrorCommand):
            isJd = True
        elif _check_cmd(BotCommands.JdLeechCommand):
            isLeech = isJd = True
        elif _check_cmd(BotCommands.CloneCommand):
            isClone = True
        elif _check_cmd(BotCommands.MVidCommand):
            isVt = True
        elif _check_cmd(BotCommands.LVidCommand):
            isLeech = isVt = True

        message = await sendMessage(msg.text, msg.reply_to_message or msg)
        message.from_user = msg.from_user
        if not user_id:
            user_id = message.from_user.id
        if isYt:
            YtDlp(client, message, isLeech=isLeech).newEvent()
        elif isClone:
            Clone(client, message).newEvent()
        elif isVt:
            VidTools(client, message, isLeech=isLeech).newEvent()
        else:
            Mirror(client, message, isQbit, isJd, isLeech).newEvent()
        await sleep(config_dict["MULTI_TIMEGAP"])
    incompte_dict.pop(user_id, None)


@new_task
async def auto_resume_all_tasks():
    await sleep(8)
    for tasks in list(incompte_dict.values()):
        await start_resume_task(bot, tasks["msgs"])


async def resume_task(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if tasks := incompte_dict.get(user_id):
        data = query.data.split()
        if data[1] == "yes":
            await gather(query.answer(), start_resume_task(client, tasks["msgs"]))
        else:
            await query.answer("Incomplete task(s) has been cleared!", True)
            del incompte_dict[user_id]
    else:
        await query.answer("You didn't have incomplete task(s) to resume!", True)


bot.add_handler(CallbackQueryHandler(resume_task, filters=regex("^resume")))
