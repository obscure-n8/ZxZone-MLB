from asyncio import sleep, gather
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message

from bot import (
    bot,
    task_dict,
    task_dict_lock,
    user_data,
    config_dict,
    multi_tags,
    OWNER_ID,
)
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import getTaskByGid, getAllTasks, MirrorStatus
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    sendingMessage,
    auto_delete_message,
    deleteMessage,
    editPhoto,
    editMessage,
)


@new_task
async def cancel_task(_, message: Message):
    user_id = message.from_user.id if message.from_user else message.sender_chat.id
    msg = message.text.split()
    if len(msg) > 1:
        gid = msg[1]
        if len(gid) == 4:
            multi_tags.discard(gid)
            return
        task = await getTaskByGid(gid)
        if not task:
            cancelmsg = await sendMessage(
                f"{message.from_user.mention}, GID: <code>{gid}</code> not found.",
                message,
            )
            await auto_delete_message(message, cancelmsg)
            return
    elif reply_to_id := message.reply_to_message_id:
        async with task_dict_lock:
            task = task_dict.get(reply_to_id)
        if not task:
            cancelmsg = await sendMessage(
                f"{message.from_user.mention}, this is not an active task!", message
            )
            await auto_delete_message(message, cancelmsg)
            return
    elif len(msg) == 1:
        cancelmsg = f"Reply to an active <code>/{BotCommands.MirrorCommand}</code> message which was used to start the download or send <code>/{BotCommands.CancelTaskCommand} GID</code> to cancel it!"
        cancelmsg = await sendMessage(cancelmsg, message)
        await auto_delete_message(message, cancelmsg)
        return

    if (
        OWNER_ID != user_id
        and task.listener.user_id != user_id
        and (user_id not in user_data or not user_data[user_id].get("is_sudo"))
    ):
        cancelmsg = await sendMessage(
            f"{message.from_user.mention}, this task is not for you!", message
        )
        await auto_delete_message(message, cancelmsg)
        return

    obj = task.task()
    await gather(obj.cancel_task(), auto_delete_message(message))


async def cancel_multi(_, query: CallbackQuery):
    data = query.data.split()
    user_id = query.from_user.id
    if user_id != int(data[1]) and not await CustomFilters.sudo("", query):
        await query.answer("Not Yours!", True)
        return
    tag = int(data[2])
    if tag in multi_tags:
        multi_tags.discard(int(data[2]))
        msg = "Stopped!"
    else:
        msg = "Already Stopped/Finished!"
    await gather(query.answer(msg, True), deleteMessage(query.message))


async def cancel_all(message: Message, status: str, user_id: int):
    matches = await getAllTasks(status)
    if matches:
        success = 0
        for task in matches:
            if user_id and task.listener.user_id != user_id:
                continue
            obj = task.task()
            await obj.cancel_task()
            success += 1
            await sleep(1)
        text = (
            f"Successfully cancelled {len(matches)} task for <b>{status}</b>."
            if success
            else f"No any active tasks for <b>{status}</b>."
        )
    else:
        text = f"No any active tasks for <b>{status}</b>."
    await gather(sendMessage(text, message.reply_to_message), deleteMessage(message))


def create_cancel_buttons(user_id: int):
    buttons = ButtonMaker()
    [
        buttons.button_data(name, f"canall {user_id} ms {name}")
        for stats, name in MirrorStatus.__dict__.items()
        if stats.startswith("STATUS")
    ]
    buttons.button_data("All (USER)", f"canall {user_id} ms user")
    buttons.button_data("All (SUDO)", f"canall {user_id} ms all")
    buttons.button_data("Close", f"canall {user_id} close", "footer")
    return buttons.build_menu(2)


async def cancell_all_buttons(_, message: Message):
    async with task_dict_lock:
        if len(task_dict) == 0:
            await sendMessage("No any active tasks to cancel!", message)
            return
    await sendingMessage(
        "Choose tasks to cancel.",
        message,
        config_dict["IMAGE_CANCEL"],
        create_cancel_buttons(message.from_user.id),
    )


@new_task
async def cancel_all_update(_, query: CallbackQuery):
    message = query.message
    data = query.data.split()
    user_id = int(data[1])
    if user_id != query.from_user.id:
        await query.answer("Not yours!", True)
        return
    if data[2] == "all" and not await CustomFilters.sudo("", message.reply_to_message):
        await query.answer("What are you doing? It's say for sudo!!", True)
        return
    await query.answer()
    match data[2]:
        case "close":
            await deleteMessage(message, message.reply_to_message)
        case "back":
            await editMessage(
                "Choose tasks to cancel.", message, create_cancel_buttons(user_id)
            )
        case "ms":
            buttons = ButtonMaker()
            buttons.button_data("Yes!", f"canall {user_id} {data[3]}")
            buttons.button_data("<<", f"canall {user_id} back")
            buttons.button_data("Close", f"canall {user_id} close")
            await editMessage(
                f"Are you sure you want to cancel all <b>{data[3]}</b> tasks!",
                message,
                buttons.build_menu(2),
            )
        case value:
            if value == "all":
                user_id = 0
            elif value == "user":
                value = "all"

            if config_dict["ENABLE_IMAGE_MODE"]:
                await editPhoto(
                    f"<i>Canceling {value.replace('...', '')} task(s), please wait...</i>",
                    message,
                    config_dict["IMAGE_CANCEL"],
                )
            else:
                await editMessage(
                    f"<i>Canceling {value.replace('...', '')} task(s), please wait...</i>",
                    message,
                )
            await cancel_all(message, value, user_id)


bot.add_handler(
    MessageHandler(
        cancel_task,
        filters=command(BotCommands.CancelTaskCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(
    MessageHandler(
        cancell_all_buttons,
        filters=command(BotCommands.CancelAllCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(cancel_all_update, filters=regex("^canall")))
