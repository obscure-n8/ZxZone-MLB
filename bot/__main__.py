from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import create_subprocess_exec, gather
from heroku3 import from_key
from os import execl as osexecl
from platform import system, architecture, release
from psutil import (
    disk_usage,
    cpu_percent,
    swap_memory,
    cpu_count,
    virtual_memory,
    net_io_counters,
    boot_time,
)
from pyrogram import Client
from pyrogram.filters import command, regex, new_chat_members, left_chat_member
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery, BotCommand
from re import match as re_match
from signal import signal, SIGINT
from sys import executable
from time import time
from uuid import uuid4

from bot import (
    bot,
    bot_loop,
    bot_dict,
    bot_lock,
    bot_name,
    botStartTime,
    Intervals,
    user_data,
    config_dict,
    scheduler,
    LOGGER,
    DATABASE_URL,
    INCOMPLETE_TASK_NOTIFIER,
    ARIA_NAME,
    QBIT_NAME,
    FFMPEG_NAME,
)
from bot.helper.ext_utils.argo_tunnel import ping_base_route, kill_route
from bot.helper.ext_utils.bot_utils import (
    cmd_exec,
    sync_to_async,
    new_task,
    update_user_ldata,
    is_pm_enabled,
)
from bot.helper.ext_utils.conf_loads import intialize_userbot, intialize_savebot
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.files_utils import clean_all, exit_clean_up, clean_target
from bot.helper.ext_utils.help_messages import HelpString, get_help_button
from bot.helper.ext_utils.jdownloader_booter import jdownloader
from bot.helper.ext_utils.links_utils import is_media
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time,
    get_progress_bar_string,
)
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.listeners.aria2_listener import start_aria2_listener
from bot.helper.mirror_utils.rclone_utils.serve import rclone_serve_booter
from bot.helper.stream_utils.file_properties import gen_link
from bot.helper.stream_utils.web_services import start_server, server
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    limit,
    sendMessage,
    editMessage,
    sendFile,
    auto_delete_message,
    sendingMessage,
    deleteMessage,
    editMarkup,
    editPhoto,
    sendCustom,
    editCustom,
    copyMessage,
)
from bot.modules import (
    authorize,
    bot_settings,
    clone,
    exec,
    gd_count,
    gd_delete,
    multi_search,
    cancel_task,
    mirror_leech,
    speed_test,
    status,
    torrent_search,
    torrent_select,
    fast_download,
    resume_task,
    user_settings,
    ytdlp,
    shell,
    rss,
    wayback,
    hash,
    bypass,
    scrapper,
    purge,
    broadcase,
    info,
    misc_tools,
    backup,
    join_chat,
    video_tools,
    media_info,
    ddls,
    save_message,
)


@new_task
async def stats(_, message: Message):
    if await aiopath.exists(".git"):
        last_commit = await cmd_exec(
            "git log -1 --date=short --pretty=format:'%cd \n<b>➡️ From</b> %cr'", True
        )
        last_commit = last_commit[0]
    else:
        last_commit = "No UPSTREAM_REPO"
    cpu, mem, disk, swap = (
        f"{cpu_percent(interval=1)}%",
        f"{virtual_memory().percent}%",
        f"{disk_usage('/')[3]}%",
        f"{swap_memory().percent}%",
    )
    msg = f"""
<b>UPSTREAM REPO AND BOT STATUS</b>
=======================================
<b>╭Commit Date:</b> {last_commit}
<b>┊Bot Uptime:</b> {get_readable_time(time() - botStartTime)}
<b>╰OS Uptime:</b> {get_readable_time(time() - boot_time())}\n\n

<b>SYSTEM STATUS</b>
========================================
<b>╭Total Cores:</b> {cpu_count(logical=True)}
<b>╰Physical Cores:</b> {cpu_count(logical=False)}
---------------------------------------------
<b>╭Upload:</b> {get_readable_file_size(net_io_counters().bytes_sent)}
<b>╰Download:</b> {get_readable_file_size(net_io_counters().bytes_recv)}
---------------------------------------------
<b>╭Disk Free:</b> {get_readable_file_size(disk_usage("/")[2])}
<b>┊Disk Used:</b> {get_readable_file_size(disk_usage("/")[1])}
<b>╰Disk Space:</b> {get_readable_file_size(disk_usage("/")[0])}
---------------------------------------------
<b>╭Memory Free:</b> {get_readable_file_size(virtual_memory().available)}
<b>┊Memory Used:</b> {get_readable_file_size(virtual_memory().used)}
<b>┊Memory Swap:</b> {get_readable_file_size(swap_memory().total)}
<b>╰Memory Total:</b> {get_readable_file_size(virtual_memory().total)}
---------------------------------------------
<b>╭CPU:</b> {get_progress_bar_string(cpu)} {cpu}
<b>┊RAM:</b> {get_progress_bar_string(mem)} {mem}
<b>┊DISK:</b> {get_progress_bar_string(disk)} {disk}
<b>┊SWAP:</b> {get_progress_bar_string(swap)} {swap}
<b>╰OS:</b> {system()}, {architecture()[0]}, {release()}\n
"""
    statsmsg = await sendingMessage(msg, message, config_dict["IMAGE_STATS"])
    await auto_delete_message(message, statsmsg)


@new_task
async def start(client: Client, message: Message):
    buttons = ButtonMaker()
    buttons.button_link("Owner", f"{config_dict['AUTHOR_URL']}")
    buttons.button_link("Channel", f"https://t.me/{config_dict['CHANNEL_USERNAME']}")
    image = config_dict["IMAGE_AUTH"]
    user_id = message.from_user.id if message.from_user else message.sender_chat.id
    user_dict = user_data.get(user_id, {})
    if len(message.command) > 1:
        data = message.command[1]
        if "_" in data:
            try:
                chat_id, message_id, log_id = data.split("_")
                int(chat_id), int(message_id), int(log_id)
            except ValueError:
                await sendMessage("Invalid start payload.", message)
                return
            await intialize_savebot(
                user_data.get(user_id, {}).get("session_string"), True, user_id
            )
            async with bot_lock:
                userbot: Client = bot_dict[user_id]["SAVEBOT"] or bot_dict["SAVEBOT"]
            if not userbot:
                await sendMessage(
                    "Required session string or this is not your task!", message
                )
                return
            msg = await userbot.get_messages(int(chat_id), int(message_id))
            media, link, cmsg = is_media(msg), msg.link, None
            ext_msg = (
                f"You have to download manually through this link <code>{link}</code>"
            )
            if msg.chat.has_protected_content:
                await sendMessage(
                    f'Sorry this <a href="{link}">{media.file_name}</a> is protected content.\n{ext_msg}.',
                    message,
                )
                return

            if int(log_id) != message.chat.id:
                msg = cmsg = await copyMessage(int(log_id), msg)
                if not msg:
                    await sendMessage(
                        f'Upps something when wrong when getting <a href="{link}">{media.file_name}</a>\n{ext_msg}.',
                        message,
                    )
                    return

            if config_dict["LEECH_LOG"]:
                msg = await copyMessage(config_dict["LEECH_LOG"], msg)
                if not msg:
                    await sendMessage(
                        f'Upps something when wrong when getting <a href="{link}">{media.file_name}</a>\n{ext_msg}.',
                        message,
                    )
                    return
                _, msg = await gather(
                    deleteMessage(cmsg), client.get_messages(msg.chat.id, msg.id)
                )
                buttons.reset()
                save_message = config_dict["SAVE_MESSAGE"]
                for mode, link in zip(["Stream", "Download"], await gen_link(msg)):
                    if link:
                        buttons.button_link(
                            mode,
                            await sync_to_async(short_url, link, user_id),
                            "header",
                        )
                markup = buttons.build_menu(2)
                if save_message:
                    buttons.button_data("Save Message", "save", "footer")
                await editMarkup(msg, buttons.build_menu(2))
                await copyMessage(message.chat.id, msg, markup)
            else:
                await sendMessage(
                    f'Required LEECH_LOG to get content <a href="{link}">{media.file_name}</a> directly\n{ext_msg}'
                )
            return
        if data == user_dict.get("session_token"):
            await gather(
                update_user_ldata(user_id, "session_token", str(uuid4())),
                update_user_ldata(user_id, "session_time", time()),
            )
            text = f"Session has been refreshed for {get_readable_time(config_dict['SESSION_TIMEOUT'])}."
        else:
            text, image = "This seassion has been expired!", config_dict["IMAGE_UNAUTH"]
    elif await CustomFilters.authorized(client, message):
        text = f"Bot ready to use, type /{BotCommands.HelpCommand} to get a list of available commands"
    elif is_pm_enabled(user_id, user_dict):
        if start_message := config_dict["START_MESSAGE"]:
            text = start_message
        else:
            text = (
                "<b>Bot ready to use...</b>"
                "╭Back to the group and happy mirroring...\n"
                "┊All mirror and leech file(s) will send here and log channel\n\n"
                f"╰Join @{config_dict['CHANNEL_USERNAME']} for more info..."
            )
    else:
        text, image = (
            config_dict["START_MESSAGE"]
            or (
                "<b>ZXZone</b> is a powerful, modern Telegram bot for mirroring, "
                "leeching, and managing downloads to Google Drive, Telegram, or "
                "any RClone-supported cloud.\n\n"
                "Built for speed, reliability, and a beautiful user experience."
            ),
            config_dict["IMAGE_UNAUTH"],
        )
    msg = await sendingMessage(text, message, image, buttons.build_menu(2))
    await auto_delete_message(message, msg)


@new_task
async def restart(_, message: Message):
    HAPI, HNAME = config_dict["HEROKU_API_KEY"], config_dict["HEROKU_APP_NAME"]
    hrestart = hkill = False
    nodetails = not HAPI or not HNAME
    if len(message.command) > 1:
        cmd = message.command[1]
        hrestart = cmd.lower().startswith("dyno")
        hkill = cmd.lower().startswith("kill")
    if hrestart and nodetails or hkill and nodetails:
        LOGGER.info("Heroku details is missing!")
        await sendMessage(
            "<b>HEROKU_APP_NAME</b> or <b>HEROKU_API_KEY</b> not set!", message
        )
        return
    if hrestart:
        msg = await sendMessage("<i>Restarting with dyno mode...</i>", message)
        async with aiopen(".restartmsg", "w") as f:
            await f.truncate(0)
            await f.write(f"{msg.chat.id}\n{msg.id}\n")
        try:
            from_key(HAPI).app(HNAME).restart()
        except Exception as e:
            await editMessage(f"ERROR: {e}", msg)
    elif hkill:
        msg = await sendMessage("Killed Dyno.", message)
        try:
            app = from_key(HAPI).app(HNAME)
            for po in (proclist := app.process_formation()):
                proclist[po.type].scale(0)
        except Exception as e:
            await editMessage(f"ERROR: {e}", msg)
    else:
        _, msg = await gather(
            kill_route(), sendMessage("<i>Restarting with normal mode...</i>", message)
        )
        if scheduler.running:
            scheduler.shutdown(wait=False)
        if qb := Intervals["qb"]:
            qb.cancel()
        if jd := Intervals["jd"]:
            jd.cancel()
        if st := Intervals["status"]:
            for intvl in list(st.values()):
                intvl.cancel()
        await gather(sync_to_async(clean_all), server.cleanup())
        proc1 = await create_subprocess_exec(
            "pkill",
            "-9",
            "-f",
            f"gunicorn|{ARIA_NAME}|{QBIT_NAME}|{FFMPEG_NAME}|wzone|java|alass",
        )
        proc2 = await create_subprocess_exec("python3", "update.py")
        await gather(proc1.wait(), proc2.wait())
        async with aiopen(".restartmsg", "w") as f:
            await f.write(f"{msg.chat.id}\n{msg.id}\n")
        osexecl(executable, executable, "-m", "bot")


@new_task
async def ping(_, message: Message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage("Starting Ping", message)
    end_time = int(round(time() * 1000))
    await gather(
        editMessage(f"{end_time - start_time} ms", reply),
        auto_delete_message(message, reply),
    )


@new_task
async def log(_, message: Message):
    await gather(
        sendFile(message, "log.txt", thumb=config_dict["IMAGE_LOGS"]),
        auto_delete_message(message),
    )


async def help_query(_, query: CallbackQuery):
    data = query.data.split(maxsplit=2)
    message = query.message
    if int(data[1]) != query.from_user.id:
        await query.answer("Not Yours!", True)
    elif data[2] == "close":
        await query.answer()
        await deleteMessage(message, message.reply_to_message)
    else:
        await query.answer()
        text, image, buttons = get_help_button(query.from_user, data[2])
        if config_dict["ENABLE_IMAGE_MODE"]:
            await editPhoto(text, message, image, buttons)
        else:
            await editMessage(text, message, buttons)


async def bot_help(_, message: Message):
    text, image, buttons = get_help_button(message.from_user)
    await sendingMessage(text, message, image, buttons)


@new_task
async def new_member(_, message: Message):
    buttons = ButtonMaker()
    buttons.button_link("Owner", config_dict["AUTHOR_URL"])
    buttons.button_link("Channel", f"https://t.me/{config_dict['CHANNEL_USERNAME']}")
    for user in message.new_chat_members:
        try:
            image = await bot.download_media(
                user.photo.big_file_id, file_name=f"./{user.id}.png"
            )
        except:
            image = config_dict["IMAGE_WEL"]
        text = f"""
Hello there <b>{user.mention}</b>, welcome to <b>{(await bot.get_chat(message.chat.id)).title}</b> Group. Enjoy in HONEY party 😘
╭<b>ID:</b> <code>{user.id}</code>
┊<b>First Name:</b> {user.first_name}
┊<b>Last Name:</b> {user.last_name or "~"}
┊<b>Username:</b> {f"@{user.username}" if user.username else "~"}
┊<b>Language:</b> {user.language_code.upper() if user.language_code else "~"}
┊<b>DC ID:</b> {user.dc_id or "~"}
╰<b>Premium User:</b> {"Yes" if user.is_premium else "No"}"""
        newmsg = await sendingMessage(text, message, image, buttons.build_menu(2))
        if await aiopath.exists(image):
            await clean_target(image)
        await auto_delete_message(message, newmsg)


@new_task
async def leave_member(_, message: Message):
    user = message.left_chat_member
    leavemsg = await sendingMessage(
        f"Yeah... <b>{user.mention}</b>, don't come back here! 😕😕",
        message,
        config_dict["IMAGE_BYE"],
    )
    await gather(
        sendCustom("Yeah u are leaved!", user.id),
        auto_delete_message(message, leavemsg),
    )


async def set_command():
    commands = []
    for cmd in HelpString().all_commands:
        if match := re_match(r"/(\w+)[\s:](.*)", cmd):
            commands.append(
                BotCommand(
                    match.group(1).lower().strip(),
                    match.group(2).replace(":", "").strip(),
                )
            )
    await bot.set_bot_commands(commands)


async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg, reply_markup):
        if msg.startswith("Restarted Successfully!"):
            await gather(
                editCustom(msg, chat_id, msg_id, reply_markup),
                clean_target(".restartmsg"),
            )
        else:
            await sendCustom(msg, cid, reply_markup)

    notifier_dict = False
    async with bot_lock:
        premium_message = "\nPremium leech enable 😘!" if bot_dict["IS_PREMIUM"] else ""
    if (
        INCOMPLETE_TASK_NOTIFIER
        and DATABASE_URL
        and (notifier_dict := await DbManager().get_incomplete_tasks())
    ):
        buttons = ButtonMaker()
        auto_resume = config_dict["INCOMPLETE_AUTO_RESUME"]
        if not auto_resume:
            buttons.button_data("Clear", "resume no")
            buttons.button_data("Resume", "resume yes")

        for cid, data in notifier_dict.items():
            msg = "Restarted Successfully!" if cid == chat_id else "Bot Restarted!"
            msg += premium_message
            for tag, links in data.items():
                msg += f"\n\n{tag}: "
                for index, link in enumerate(links, start=1):
                    await resume_task.set_incomplte_task(cid, link)
                    msg += f" <a href='{link}'>{index}</a> |"
                    limit.text(msg)
                    if len(msg) - limit.total > 4090:
                        await send_incompelete_task_message(
                            cid, msg, buttons.build_menu(2)
                        )
                        msg = ""
            if msg:
                await send_incompelete_task_message(cid, msg, buttons.build_menu(2))

        if auto_resume:
            resume_task.auto_resume_all_tasks()

    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        msg = f"Restarted Successfully!{premium_message}"
        await gather(editCustom(msg, chat_id, msg_id), clean_target(".restartmsg"))
    elif not notifier_dict and user_data:
        for id_ in user_data:
            if (
                user_data[id_].get("is_auth")
                or user_data[id_].get("is_sudo")
                or id_ == config_dict["OWNER_ID"]
            ):
                await sendCustom(f"Bot Restarted!{premium_message}", id_)
    else:
        await sendCustom(f"Bot Restarted!{premium_message}", config_dict["OWNER_ID"])


async def main():
    jdownloader.initiate()
    bot.add_handler(MessageHandler(start, filters=command(BotCommands.StartCommand)))
    bot.add_handler(
        MessageHandler(
            log, filters=command(BotCommands.LogCommand) & CustomFilters.sudo
        )
    )
    bot.add_handler(
        MessageHandler(
            restart, filters=command(BotCommands.RestartCommand) & CustomFilters.sudo
        )
    )
    bot.add_handler(
        MessageHandler(
            ping, filters=command(BotCommands.PingCommand) & CustomFilters.authorized
        )
    )
    bot.add_handler(
        MessageHandler(
            bot_help,
            filters=command(BotCommands.HelpCommand) & CustomFilters.authorized,
        )
    )
    bot.add_handler(
        MessageHandler(
            stats, filters=command(BotCommands.StatsCommand) & CustomFilters.authorized
        )
    )
    bot.add_handler(CallbackQueryHandler(help_query, filters=regex("help")))
    bot.add_handler(MessageHandler(new_member, filters=new_chat_members))
    bot.add_handler(MessageHandler(leave_member, filters=left_chat_member))
    await gather(
        set_command(),
        start_server(),
        intialize_userbot(False),
        sync_to_async(clean_all),
        torrent_search.initiate_search_tools(),
        telegraph.create_account(),
        rclone_serve_booter(),
        sync_to_async(start_aria2_listener, wait=False),
        return_exceptions=True,
    )
    await gather(
        intialize_savebot(config_dict["SAVE_SESSION_STRING"], False),
        restart_notification(),
        ping_base_route(),
        return_exceptions=True,
    )
    LOGGER.info("Bot @%s Started!", bot_name)
    signal(SIGINT, exit_clean_up)


bot_loop.run_until_complete(main())
bot_loop.run_forever()
