from asyncio import gather
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message

from bot import (
    aria2,
    bot,
    config_dict,
    task_dict,
    task_dict_lock,
    user_data,
    LOGGER,
    OWNER_ID,
)
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async, new_task
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.status_utils import MirrorStatus, getTaskByGid
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    deleteMessage,
    sendingMessage,
    sendMessage,
    sendStatusMessage,
)


@new_task
async def select(_, message: Message):
    if not config_dict["BASE_URL"]:
        await sendMessage("Base URL not defined!", message)
        return
    user_id = message.from_user.id
    msg = message.text.split()
    if len(msg) > 1:
        gid = msg[1]
        task = await getTaskByGid(gid)
        if not task:
            qbselmsg = await sendMessage(
                f"{message.from_user.mention}, GID: <code>{gid}</code> not found!",
                message,
            )
            await auto_delete_message(message, qbselmsg)
            return
    elif reply_to_id := message.reply_to_message_id:
        async with task_dict_lock:
            task = task_dict.get(reply_to_id)
        if not task:
            qbselmsg = await sendMessage(
                f"{message.from_user.mention}, this is not an active task!", message
            )
            await auto_delete_message(message, qbselmsg)
            return
    elif len(msg) == 1:
        msg = (
            "Reply to an active /cmd which was used to start the qb-download or add gid along with cmd\n\n"
            "This command mainly for selection incase you decided to select files from already added torrent."
            "But you can always use /cmd with arg `s` to select files before download start."
        )
        qbselmsg = await sendMessage(msg, message)
        await auto_delete_message(message, qbselmsg)
        return
    if (
        OWNER_ID != user_id
        and task.listener.user_id != user_id
        and (user_id not in user_data or not user_data[user_id].get("is_sudo"))
    ):
        qbselmsg = await sendMessage(
            f"{task.listener.tag}, this task is not for you!", message
        )
        await auto_delete_message(message, qbselmsg)
        return
    if task.status() not in {
        MirrorStatus.STATUS_DOWNLOADING,
        MirrorStatus.STATUS_PAUSED,
        MirrorStatus.STATUS_QUEUEDL,
    }:
        qbselmsg = await sendMessage(
            f"{task.listener.tag}, task should be in download or pause (incase message deleted by wrong) or queued (status incase you used torrent file)!",
            message,
        )
        await auto_delete_message(message, qbselmsg)
        return
    if task.name().startswith("[METADATA]"):
        qbselmsg = await sendMessage(
            f"{task.listener.tag}, try after downloading metadata finished!", message
        )
        await auto_delete_message(message, qbselmsg)
        return

    try:
        if task.listener.isQbit:
            id_ = task.hash()
            if not task.queued:
                await sync_to_async(task.client.torrents_pause, torrent_hashes=id_)
        else:
            id_ = task.gid()
            if not task.queued:
                try:
                    await sync_to_async(aria2.client.force_pause, id_)
                except Exception as e:
                    LOGGER.error(
                        "%s Error in pause, this mostly happens after abuse aria2", e
                    )
        task.listener.select = True
    except:
        qbselmsg = await sendMessage("This is not a bittorrent task!", message)
        await auto_delete_message(message, qbselmsg)
        return

    SBUTTONS = bt_selection_buttons(id_)
    msg = f"<code>{task.name()}</code>\n\n{task.listener.tag}, download paused. Choose files then press <b>Done Selecting</b> button to resume downloading."
    await sendingMessage(msg, message, config_dict["IMAGE_PAUSE"], SBUTTONS)


async def get_confirm(_, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    task = await getTaskByGid(data[2])
    if not task:
        await gather(
            query.answer("This task has been cancelled!", True), deleteMessage(message)
        )
        return
    if user_id != task.listener.user_id:
        await query.answer("Not Yours!", True)
        return
    match data[1]:
        case "canc":
            await query.answer("Canceling...")
            obj = task.task()
            await gather(obj.cancel_task(), deleteMessage(message))
        case "pin":
            await query.answer(data[3], True)
        case "done":
            await query.answer()
            if hasattr(task, "seeding"):
                id_ = data[3]
                if len(id_) > 20:
                    tor_info = (
                        await sync_to_async(task.client.torrents_info, torrent_hash=id_)
                    )[0]
                    path = tor_info.content_path.rsplit("/", 1)[0]
                    res = await sync_to_async(
                        task.client.torrents_files, torrent_hash=id_
                    )
                    for f in res:
                        if f.priority == 0:
                            await gather(
                                *[
                                    clean_target(f_path)
                                    for f_path in [
                                        f"{path}/{f.name}",
                                        f"{path}/{f.name}.!qB",
                                    ]
                                ]
                            )
                    if not task.queued:
                        await sync_to_async(
                            task.client.torrents_resume, torrent_hashes=id_
                        )
                else:
                    res = await sync_to_async(aria2.client.get_files, id_)
                    for f in res:
                        if f["selected"] == "false":
                            await clean_target(f["path"])
                    if not task.queued:
                        try:
                            await sync_to_async(aria2.client.unpause, id_)
                        except Exception as e:
                            LOGGER.error(
                                "%s Error in resume, this mostly happens after abuse aria2. Try to use select cmd again!",
                                e,
                            )
            await gather(sendStatusMessage(message), deleteMessage(message))
            if BotCommands.BtSelectCommand in message.reply_to_message.text:
                await deleteMessage(message.reply_to_message)


bot.add_handler(
    MessageHandler(
        select, filters=command(BotCommands.BtSelectCommand) & CustomFilters.authorized
    )
)
bot.add_handler(CallbackQueryHandler(get_confirm, filters=regex("^btsel")))
