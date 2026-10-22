from asyncio import gather
from psutil import cpu_percent, virtual_memory, disk_usage, net_io_counters
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time

from bot import (
    bot,
    task_dict,
    task_dict_lock,
    status_dict,
    botStartTime,
    Intervals,
    config_dict,
)
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time,
    MirrorStatus,
)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    deleteMessage,
    auto_delete_message,
    sendStatusMessage,
    sendingMessage,
    update_status_message,
)


@new_task
async def mirror_status(_, message: Message):
    async with task_dict_lock:
        count = len(task_dict)
    if count:
        text = message.text.split()
        if len(text) > 1:
            user_id = message.from_user.id if text[1] == "me" else int(text[1])
            if status_dict[user_id]:
                del status_dict[user_id]
            if obj := Intervals["status"].get(user_id):
                obj.cancel()
                del Intervals["status"][user_id]
        else:
            user_id = 0
            sid = message.chat.id
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
        await gather(sendStatusMessage(message, user_id), deleteMessage(message))
    else:
        msg = (
            "No Active Downloads!\n"
            f"<b>╭ My status:</b> <code>/{BotCommands.StatusCommand} me</code>\n"
            f"<b>╰ User status:</b> <code>/{BotCommands.StatusCommand} user_id</code>\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"<b>╭ CPU:</b> {cpu_percent()}% | <b>RAM:</b> {virtual_memory().percent}% | <b>FREE:</b> {get_readable_file_size(disk_usage(config_dict['DOWNLOAD_DIR']).free)}\n"
            f"<b>╰ IN:</b> {get_readable_file_size(net_io_counters().bytes_recv)}<b> | OUT:</b> {get_readable_file_size(net_io_counters().bytes_sent)} | {get_readable_time(time() - botStartTime)}"
        )
        statusmsg = await sendingMessage(msg, message, config_dict["IMAGE_STATUS"])
        await auto_delete_message(message, statusmsg)


@new_task
async def status_pages(_, query: CallbackQuery):
    data = query.data.split()
    key = int(data[1])
    try:
        async with task_dict_lock:
            count = len(task_dict)
            if not count:
                await gather(
                    query.answer("Old status! Closing in 2s..."),
                    auto_delete_message(query.message, stime=2),
                )
                return
        match data[2]:
            case "ref":
                await gather(query.answer(), update_status_message(key, force=True))
            case "nex" | "pre":
                await query.answer()
                async with task_dict_lock:
                    if data[2] == "nex":
                        status_dict[key]["page_no"] += status_dict[key]["page_step"]
                    else:
                        status_dict[key]["page_no"] -= status_dict[key]["page_step"]
            case "cls":
                if query.from_user.id in (key, config_dict["OWNER_ID"]):
                    if obj := Intervals["status"].get(key):
                        obj.cancel()
                        del Intervals["status"][key]
                    await gather(query.answer(), deleteMessage(query.message))
                    return
                await query.answer("This in no yout task!", True)
            case "ps":
                await query.answer()
                async with task_dict_lock:
                    status_dict[key]["page_step"] = int(data[3])
            case "st":
                await query.answer()
                async with task_dict_lock:
                    status_dict[key]["status"] = data[3]
                await update_status_message(key, force=True)
            case "ov":
                upload = download = clone = queuedl = queueul = pause = check = (
                    archive
                ) = extract = split = seed = samvid = 0
                async with task_dict_lock:
                    for task in task_dict.values():
                        match task.status():
                            case MirrorStatus.STATUS_DOWNLOADING:
                                download += 1
                            case MirrorStatus.STATUS_UPLOADING:
                                upload += 1
                            case MirrorStatus.STATUS_SEEDING:
                                seed += 1
                            case MirrorStatus.STATUS_ARCHIVING:
                                archive += 1
                            case MirrorStatus.STATUS_EXTRACTING:
                                extract += 1
                            case MirrorStatus.STATUS_SPLITTING:
                                split += 1
                            case MirrorStatus.STATUS_QUEUEDL:
                                queuedl += 1
                            case MirrorStatus.STATUS_QUEUEUP:
                                queueul += 1
                            case MirrorStatus.STATUS_CLONING:
                                clone += 1
                            case MirrorStatus.STATUS_CHECKING:
                                check += 1
                            case MirrorStatus.STATUS_PAUSED:
                                pause += 1
                            case MirrorStatus.STATUS_SAMVID:
                                samvid += 1

                msg = f"""
Tasks ({count})
ZIP: {archive} | UZIP: {extract} | SPL: {split} | DL: {download} | UL {upload} | QDL: {queuedl} | QUL: {queueul} | PS: {pause} | SD: {seed} | CL: {clone} | SV: {samvid}

Limits
DL: {config_dict.get("TORRENT_DIRECT_LIMIT", "~ ")}GB | Z/U: {config_dict.get("ZIP_UNZIP_LIMIT", "~ ")}GB | MG: {config_dict.get("MEGA_LIMIT", "~ ")}GB
"""
                await query.answer(msg, True)
    except:
        pass


bot.add_handler(
    MessageHandler(
        mirror_status,
        filters=command(BotCommands.StatusCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(status_pages, filters=regex("^status")))
