from aiofiles import open as aiopen
from aiofiles.os import rename, path as aiopath
from asyncio import create_subprocess_exec, create_subprocess_shell, sleep, gather
from dotenv import load_dotenv
from functools import partial
from os import chmod, environ, getcwd, path as ospath, walk
from pyrogram import Client
from pyrogram.filters import command, regex, create
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time
from zipfile import BadZipFile, ZipFile


from bot import (
    bot,
    bot_dict,
    bot_lock,
    aria2,
    config_dict,
    Intervals,
    aria2_options,
    aria2c_global,
    task_dict,
    qbit_options,
    get_client,
    LOGGER,
    DATABASE_URL,
    DRIVES_IDS,
    DRIVES_NAMES,
    INDEX_URLS,
    GLOBAL_EXTENSION_FILTER,
    SHORTENERES,
    SHORTENER_APIS,
)
from bot.helper.ext_utils.argo_tunnel import ping_base_route, kill_route
from bot.helper.ext_utils.bot_utils import (
    setInterval,
    sync_to_async,
    new_thread,
    cmd_exec,
)
from bot.helper.ext_utils.conf_loads import (
    default_values,
    load_config,
    intialize_userbot,
    intialize_savebot,
)
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.jdownloader_booter import jdownloader
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_utils.rclone_utils.serve import rclone_serve_booter
from bot.helper.stream_utils.web_services import server, start_server
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendFile,
    sendMessage,
    sendingMessage,
    editMessage,
    editPhoto,
    deleteMessage,
    update_status_message,
)
from bot.modules.rss import addJob
from bot.modules.torrent_search import initiate_search_tools


START = 0
STATE = "view"
handler_dict = {}
unauth_config = [
    "TELEGRAM_HASH",
    "TELEGRAM_API",
    "ARGO_TOKEN",
    "ENABLE_FASTDL",
    "CLOUD_LINK_FILTERS",
    "OWNER_ID",
    "DATABASE_URL",
    "HEROKU_APP_NAME",
    "HEROKU_API_KEY",
    "UPSTREAM_REPO",
    "UPSTREAM_BRANCH",
    "CLOUD_LINK",
]


async def get_buttons(key=None, edit_type=None):
    buttons = ButtonMaker()
    if key is None:
        buttons.button_data("Bot Variables", "botset var")
        buttons.button_data("Private Files", "botset private")
        buttons.button_data("Qbit Settings", "botset qbit")
        buttons.button_data("Aria2c Settings", "botset aria")
        buttons.button_data("JDownloader", "botset jd")
        buttons.button_data("Close", "botset close", "footer")
        msg = "<b>BOT SETTINGS</b>"
        image = config_dict["IMAGE_CONSET"]
    elif edit_type is not None:
        image = config_dict["IMAGE_CONEDIT"]
        if edit_type == "botvar":
            msg = ""
            buttons.button_data("<<", "botset var")
            if key not in ["TELEGRAM_HASH", "TELEGRAM_API", "OWNER_ID", "BOT_TOKEN"]:
                buttons.button_data("Default", f"botset resetvar {key}")
            buttons.button_data("Close", "botset close")
            if key in [
                "SUDO_USERS",
                "CMD_SUFFIX",
                "OWNER_ID",
                "USER_SESSION_STRING",
                "TELEGRAM_HASH",
                "TELEGRAM_API",
                "AUTHORIZED_CHATS",
                "DATABASE_URL",
                "BOT_TOKEN",
                "DOWNLOAD_DIR",
            ]:
                msg += "Restart required for this edit to take effect!\n\n"
            msg += f"Send a valid value for <b>{key}</b>.\nCurrent value is <b>{config_dict[key]}</b>.\n\n<i>Timeout: 60s.</i>"
        elif edit_type == "ariavar":
            buttons.button_data("<<", "botset aria")
            if key != "newkey":
                buttons.button_data("Default", f"botset resetaria {key}")
                buttons.button_data("Empty String", f"botset emptyaria {key}")
            buttons.button_data("Close", "botset close")
            if key == "newkey":
                msg = "Send a key with value. Example: https-proxy-user:value"
            else:
                msg = f"Send a valid value for <b>{key}</b>.\nCurrent value is <b>{aria2_options[key]}</b>.\n\n<i>Timeout: 60s.</i>"
        elif edit_type == "qbitvar":
            buttons.button_data("<<", "botset qbit")
            buttons.button_data("Empty String", f"botset emptyqbit {key}")
            buttons.button_data("Close", "botset close")
            msg = f"Send a valid value for <b>{key}</b>.\nCurrent value is <b>{qbit_options[key]}</b>.\n\n<i>Timeout: 60s.</i>"
    elif key == "var":
        for k in list(config_dict)[START : 20 + START]:
            buttons.button_data(k, f"botset botvar {k}")
        if STATE == "view":
            buttons.button_data("Edit", "botset edit var")
            image = config_dict["IMAGE_CONVIEW"]
        else:
            buttons.button_data("View", "botset view var")
            image = config_dict["IMAGE_CONEDIT"]
        if config_dict["USER_SESSION_STRING"]:
            buttons.button_data("Restart Userbot", "botset restartubot", "header")
        if config_dict["SAVE_SESSION_STRING"]:
            buttons.button_data("Restart Savebot", "botset restartsbot", "header")
        buttons.button_data("<<", "botset back")
        buttons.button_data("Close", "botset close")
        for x in range(0, len(config_dict), 20):
            buttons.button_data(int(x / 20) + 1, f"botset start var {x}", "footer")
        msg = f"<b>BOT VARIABLES ~ {int(START / 20) + 1}\nState:</b> {STATE.title()}"
    elif key == "private":
        buttons.button_data("<<", "botset back")
        buttons.button_data("Close", "botset close")
        msg = (
            "<b>PRIVATE FILES</b>\n"
            "<b>╭</b> <code>config.env</code>\n"
            "<b>┊</b> <code>credentials.json</code>\n"
            "<b>┊</b> <code>token.pickle</code>\n"
            "<b>┊</b> <code>accounts.zip</code>\n"
            "<b>┊</b> <code>list_drives.txt</code>\n"
            "<b>┊</b> <code>cookies.txt</code>\n"
            "<b>┊</b> <code>terabox.txt</code>\n"
            "<b>┊</b> <code>shorteners.txt</code>\n"
            "<b>┊</b> <code>rclone.conf</code>\n"
            "<b>╰</b> <code>.netrc</code>\n\n"
            "<i>To delete private file send the name of the file only as text message.\nTimeout: 60s.</i>"
        )
        image = config_dict["IMAGE_CONPRIVATE"]
    elif key == "aria":
        for k in list(aria2_options)[START : 20 + START]:
            buttons.button_data(k, f"botset ariavar {k}")
        if STATE == "view":
            buttons.button_data("Edit", "botset edit aria")
            image = config_dict["IMAGE_CONVIEW"]
        else:
            buttons.button_data("View", "botset view aria")
            image = config_dict["IMAGE_CONEDIT"]
        buttons.button_data("Add new key", "botset ariavar newkey")
        buttons.button_data("<<", "botset back")
        buttons.button_data("Close", "botset close")
        for x in range(0, len(aria2_options), 20):
            buttons.button_data(int(x / 20) + 1, f"botset start aria {x}", "footer")
        msg = f"<b>ARIA OPTION ~ {int(START / 20) + 1}\nState:</b> {STATE.title()}"
    elif key == "qbit":
        for k in list(qbit_options)[START : 20 + START]:
            buttons.button_data(k, f"botset qbitvar {k}")
        if STATE == "view":
            buttons.button_data("Edit", "botset edit qbit")
            image = config_dict["IMAGE_CONVIEW"]
        else:
            buttons.button_data("View", "botset view qbit")
            image = config_dict["IMAGE_CONEDIT"]
        buttons.button_data("<<", "botset back")
        buttons.button_data("Close", "botset close")
        for x in range(0, len(qbit_options), 20):
            buttons.button_data(int(x / 20) + 1, f"botset start qbit {x}", "footer")
        msg = f"<b>QBITTORRENT OPTIONS ~ {int(START / 20) + 1}\nState:</b> {STATE.title()}"
    elif key == "jd":
        image = config_dict["IMAGE_JD"]
        buttons.button_data("JD Reboot", "botset rebootjd")
        if jdownloader.device:
            buttons.button_data("JD Shutdown", "botset shutdownjd")
            buttons.button_data("JD Sync", "botset syncjd")
        buttons.button_data("<<", "botset back")
        buttons.button_data("Close", "botset close")
        msg = "<b>JDOWNLOADER OPTIONS</b>\nSelect available options below!"

    return msg, image, buttons.build_menu(2)


async def update_buttons(message: Message, key: str = None, edit_type: str = None):
    msg, image, buttons = await get_buttons(key, edit_type)
    if config_dict["ENABLE_IMAGE_MODE"]:
        await editPhoto(msg, message, image, buttons)
    else:
        await editMessage(msg, message, buttons)


async def edit_variable(_, message: Message, omsg: Message, key: str):
    handler_dict[message.chat.id] = False
    value = message.text.strip()
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
        if key == "INCOMPLETE_TASK_NOTIFIER" and DATABASE_URL:
            await DbManager().trunc_table("tasks")
    elif key == "DOWNLOAD_DIR":
        if not value.endswith("/"):
            value += "/"
    elif key == "STATUS_UPDATE_INTERVAL":
        value = int(value)
        if len(task_dict) != 0 and (st := Intervals["status"]):
            for skey, intvl in list(st.items()):
                intvl.cancel()
                Intervals["status"][skey] = setInterval(
                    value, update_status_message, skey
                )
    elif key == "TORRENT_TIMEOUT":
        value = int(value)
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {"bt-stop-timeout": f"{value}"},
                    )
                except Exception as e:
                    LOGGER.error(e)
        aria2_options["bt-stop-timeout"] = f"{value}"
    elif key == "LEECH_SPLIT_SIZE":
        async with bot_lock:
            value = min(int(value), bot_dict["MAX_SPLIT_SIZE"])
    elif key == "BASE_URL":
        await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
        await create_subprocess_shell(
            f"gunicorn web.wserver:app --bind 0.0.0.0:{environ.get('TORRENT_PORT')} --worker-class gevent"
        )
    elif key == "TORRENT_PORT":
        value = int(value)
        if config_dict["BASE_URL"]:
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
            await create_subprocess_shell(
                f"gunicorn web.wserver:app --bind 0.0.0.0:{value} --worker-class gevent"
            )
    elif key == "EXTENSION_FILTER":
        fx = value.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.extend(["aria2", "!qB"])
        for x in fx:
            x = x.lstrip(".")
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())
    elif key == "GDRIVE_ID":
        if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
            DRIVES_IDS[0] = value
        else:
            DRIVES_IDS.insert(0, value)
    elif key == "INDEX_URL":
        value = value.rstrip("/")
        if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
            INDEX_URLS[0] = value
        else:
            INDEX_URLS.insert(0, value)
    elif value.isdigit() or value.startswith("-1"):
        value = int(value)
    config_dict[key] = value
    if key == "SAVE_SESSION_STRING":
        await intialize_savebot(value)
    elif key == "USER_SESSION_STRING":
        await intialize_userbot()
    LOGGER.info("Change var %s = %s: %s", key, value.__class__.__name__.upper(), value)
    await gather(update_buttons(omsg, "var"), deleteMessage(message))
    if DATABASE_URL:
        await DbManager().update_config({key: value})
    if key in ("SEARCH_PLUGINS", "SEARCH_API_LINK"):
        await initiate_search_tools()
    elif key in ["STREAM_BASE_URL", "STREAM_PORT", "ENABLE_STREAM_LINK"]:
        await server.cleanup()
        enable_stream = config_dict["ENABLE_STREAM_LINK"]
        is_stream = (
            config_dict["BASE_URL"] == config_dict["STREAM_BASE_URL"]
            and config_dict["LEECH_LOG"]
        )
        if not enable_stream and is_stream:
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
            await create_subprocess_shell(
                f"gunicorn web.wserver:app --bind 0.0.0.0:{environ.get('TORRENT_PORT')} --worker-class gevent"
            )
        elif enable_stream and is_stream:
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
        if key != "STREAM_PORT" and not config_dict["ARGO_TOKEN"]:
            config_dict["STREAM_PORT"] = environ.get("PORT")
        await sleep(2)
        await start_server()
    elif key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()
    elif key in [
        "RCLONE_SERVE_URL",
        "RCLONE_SERVE_PORT",
        "RCLONE_SERVE_USER",
        "RCLONE_SERVE_PASS",
    ]:
        await rclone_serve_booter()
    elif key in ("JD_EMAIL", "JD_PASS"):
        jdownloader.initiate()
    elif key == "RSS_DELAY":
        addJob()
    elif key == "ARGO_TOKEN":
        await kill_route()
        await ping_base_route(True)


async def edit_aria(_, message: Message, omsg: Message, key: str):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "newkey":
        key, value = [x.strip() for x in value.split(":", 1)]
    elif value.lower() == "true":
        value = "true"
    elif value.lower() == "false":
        value = "false"
    if key in aria2c_global:
        await sync_to_async(aria2.set_global_options, {key: value})
    else:
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option, download.gid, {key: value}
                    )
                except Exception as e:
                    LOGGER.error(e)
    aria2_options[key] = value
    await gather(update_buttons(omsg, "aria"), deleteMessage(message))
    if DATABASE_URL:
        await DbManager().update_aria2(key, value)


async def edit_qbit(_, message: Message, omsg: Message, key: str):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif key == "max_ratio":
        value = float(value)
    elif value.isdigit() or value.startswith("-"):
        value = int(value)
    qbit_options[key] = value
    await gather(
        sync_to_async(get_client().app_set_preferences, {key: value}),
        update_buttons(omsg, "qbit"),
        deleteMessage(message),
    )
    if DATABASE_URL:
        await DbManager().update_qbittorrent(key, value)


async def sync_jdownloader():
    if DATABASE_URL and jdownloader.device is not None:
        await gather(
            sync_to_async(jdownloader.device.system.exit_jd), clean_target("cfg.zip")
        )
        await sleep(2)
        await (
            await create_subprocess_exec("7z", "a", "cfg.zip", "/JDownloader/cfg")
        ).wait()
        await DbManager().update_private_file("cfg.zip")
        await sync_to_async(jdownloader.connectToDevice)


async def update_private_file(_, message: Message, omsg: Message):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        fn = file_name.rsplit(".zip", 1)[0]
        if file_name != "config.env":
            await clean_target(fn)
        if fn == "accounts":
            await gather(clean_target("accounts"), clean_target("rclone_sa"))
            config_dict["USE_SERVICE_ACCOUNTS"] = False
            if DATABASE_URL:
                await DbManager().update_config({"USE_SERVICE_ACCOUNTS": False})
        elif file_name in [".netrc", "netrc"]:
            await (await create_subprocess_exec("touch", ".netrc")).wait()
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        elif file_name == "shorteners.txt":
            SHORTENERES.clear()
            SHORTENER_APIS.clear()
        LOGGER.info("Removed private file: %s", fn)
        await deleteMessage(message)
    elif doc := message.document:
        tmsg = await sendMessage("<i>Processing, please wait...</i>", message)
        file_name = doc.file_name or ""
        safe_file_name = ospath.basename(file_name.replace("\\", "/"))
        if not file_name or safe_file_name != file_name:
            await gather(
                deleteMessage(message, tmsg),
                sendMessage("Invalid private file name.", message),
            )
            return
        file_name = safe_file_name
        await message.download(file_name=ospath.join(getcwd(), file_name))
        if file_name == "accounts.zip":
            await gather(clean_target("accounts"), clean_target("rclone_sa"))
            try:
                with ZipFile("accounts.zip") as archive:
                    accounts_root = ospath.realpath("accounts")
                    for member in archive.infolist():
                        member_name = member.filename
                        if not (
                            member_name.startswith("accounts/")
                            and member_name.endswith(".json")
                        ):
                            continue
                        member_path = ospath.realpath(ospath.join(".", member_name))
                        if (
                            ospath.commonpath((accounts_root, member_path))
                            != accounts_root
                        ):
                            LOGGER.warning(
                                "Skipping unsafe archive member: %s", member_name
                            )
                            continue
                        archive.extract(member, ".")
                for dirpath, _, filenames in walk("accounts"):
                    chmod(dirpath, 0o700)
                    for filename in filenames:
                        chmod(ospath.join(dirpath, filename), 0o600)
            except (BadZipFile, OSError) as e:
                LOGGER.error("Failed to import accounts.zip: %s", e)
                config_dict["USE_SERVICE_ACCOUNTS"] = False
            else:
                config_dict["USE_SERVICE_ACCOUNTS"] = True
            if DATABASE_URL:
                await DbManager().update_config(
                    {"USE_SERVICE_ACCOUNTS": config_dict["USE_SERVICE_ACCOUNTS"]}
                )
        elif file_name == "config.env":
            load_dotenv("config.env", override=True)
            await load_config()
        elif file_name in (".netrc", "netrc"):
            if file_name == "netrc":
                await rename("netrc", ".netrc")
                file_name = ".netrc"
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        elif file_name == "list_drives.txt":
            DRIVES_IDS.clear()
            DRIVES_NAMES.clear()
            INDEX_URLS.clear()
            if GDRIVE_ID := config_dict["GDRIVE_ID"]:
                DRIVES_NAMES.append("Main")
                DRIVES_IDS.append(GDRIVE_ID)
                INDEX_URLS.append(config_dict["INDEX_URL"])
            async with aiopen("list_drives.txt", "r+") as f:
                for line in await f.readlines():
                    temp = line.strip().split()
                    DRIVES_IDS.append(temp[1])
                    DRIVES_NAMES.append(temp[0].replace("_", " "))
                    if len(temp) > 2:
                        INDEX_URLS.append(temp[2])
                    else:
                        INDEX_URLS.append("")
        elif file_name == "shorteners.txt":
            SHORTENERES.clear()
            SHORTENER_APIS.clear()
            with open("shorteners.txt", "r+") as f:
                lines = f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    if len(temp) == 2:
                        SHORTENERES.append(temp[0])
                        SHORTENER_APIS.append(temp[1])
        if "@github.com" in config_dict["UPSTREAM_REPO"]:
            buttons = ButtonMaker()
            msg = "Push to <b>UPSTREAM_REPO</b>?"
            buttons.button_data("Yes", f"botset push {file_name}")
            buttons.button_data("No", "botset close")
            await editMessage(msg, tmsg, buttons.build_menu(2))
        else:
            await deleteMessage(message, tmsg)
        LOGGER.info("Added private file: %s", file_name)
    if file_name == "rclone.conf":
        await rclone_serve_booter()
    await update_buttons(omsg)
    if DATABASE_URL:
        await DbManager().update_private_file(file_name)
    await clean_target("accounts.zip")


async def event_handler(
    client: Client, query: CallbackQuery, pfunc: partial, rfunc: partial, document=False
):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(
            user.id == query.from_user.id
            and event.chat.id == chat_id
            and (event.text or event.document and document)
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )
    while handler_dict[chat_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[chat_id] = False
            await rfunc()
    client.remove_handler(*handler)


@new_thread
async def edit_bot_settings(client: Client, query: CallbackQuery):
    message = query.message
    data = query.data.split()
    handler_dict[message.chat.id] = False
    if data[1] == "close":
        await gather(query.answer(), deleteMessage(message, message.reply_to_message))
    elif data[1] == "back":
        await query.answer()
        globals()["START"] = 0
        await update_buttons(message, None)
    elif data[1] in ["syncjd", "rebootjd", "shutdownjd"]:
        if not config_dict["JD_EMAIL"] or not config_dict["JD_PASS"]:
            await query.answer("No email or password provided!", True)
            return
        if data[1] == "rebootjd":
            jdownloader.initiate()
            await query.answer(
                "JDownloader will get restarted. It takes up to 5 sec!", True
            )
        elif data[1] == "shutdownjd":
            jdownloader.device = None
            await gather(
                query.answer("Shutting down JDownloader...!", True),
                cmd_exec(["pkill", "-9", "-f", "java"]),
            )
            await update_buttons(message, "jd")
        else:
            await gather(
                query.answer(
                    "Syncronization Started. JDownloader will get restarted. It takes up to 5 sec!",
                    True,
                ),
                sync_jdownloader(),
            )
    elif data[1] == "restartubot":
        await gather(query.answer("Restarting Userbot!", True), intialize_userbot())
    elif data[1] == "restartsbot":
        await gather(
            query.answer("Restarting Savebot!", True),
            intialize_savebot(config_dict["SAVE_SESSION_STRING"]),
        )
    elif data[1] in ["var", "aria", "qbit", "jd"]:
        await gather(query.answer(), update_buttons(message, data[1]))
    elif data[1] == "resetvar":
        if data[2] in unauth_config and query.from_user.id != config_dict["OWNER_ID"]:
            await query.answer("This setting only available for owner!", True)
            return
        await query.answer()
        value = ""
        if data[2] in default_values:
            value = default_values[data[2]]
            if data[2] == "LEECH_SPLIT_SIZE":
                async with bot_lock:
                    value = bot_dict["MAX_SPLIT_SIZE"]
            if (
                data[2] == "STATUS_UPDATE_INTERVAL"
                and len(task_dict) != 0
                and (st := Intervals["status"])
            ):
                for key, intvl in list(st.items()):
                    intvl.cancel()
                    Intervals["status"][key] = setInterval(
                        value, update_status_message, key
                    )
        elif data[2] == "ARGO_TOKEN":
            await kill_route()
        elif data[2] == "EXTENSION_FILTER":
            GLOBAL_EXTENSION_FILTER.clear()
            GLOBAL_EXTENSION_FILTER.extend(["aria2", "!qB"])
        elif data[2] == "TORRENT_TIMEOUT":
            downloads = await sync_to_async(aria2.get_downloads)
            for download in downloads:
                if not download.is_complete:
                    try:
                        await sync_to_async(
                            aria2.client.change_option,
                            download.gid,
                            {"bt-stop-timeout": "0"},
                        )
                    except Exception as e:
                        LOGGER.error(e)
            aria2_options["bt-stop-timeout"] = "0"
            if DATABASE_URL:
                await DbManager().update_aria2("bt-stop-timeout", "0")
        elif data[2] == "BASE_URL":
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
        elif data[2] in ("STREAM_BASE_URL", "ENABLE_STREAM_LINK"):
            await server.cleanup()
        elif data[2] == "TORRENT_PORT":
            value = 1000 if config_dict["ARGO_TOKEN"] else environ.get("PORT")
            if config_dict["BASE_URL"]:
                await (
                    await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")
                ).wait()
                await create_subprocess_shell(
                    f"gunicorn web.wserver:app --bind 0.0.0.0:{value} --worker-class gevent"
                )
        elif data[2] == "STREAM_PORT":
            await server.cleanup()
            await start_server()
        elif data[2] == "GDRIVE_ID":
            if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
                DRIVES_NAMES.pop(0)
                DRIVES_IDS.pop(0)
                INDEX_URLS.pop(0)
        elif data[2] == "INDEX_URL":
            value = value.rstrip("/")
            if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
                INDEX_URLS[0] = ""
        elif data[2] == "INCOMPLETE_TASK_NOTIFIER" and DATABASE_URL:
            await DbManager().trunc_table("tasks")
        elif data[2] in ("JD_EMAIL", "JD_PASS"):
            jdownloader.device = None
        config_dict[data[2]] = value
        LOGGER.info(
            "Change var %s = %s: %s", data[2], value.__class__.__name__.upper(), value
        )
        if data[2] == "USER_SESSION_STRING":
            await intialize_userbot()
        await update_buttons(message, "var")
        if DATABASE_URL:
            await DbManager().update_config({data[2]: value})
        if data[2] in ("SEARCH_PLUGINS", "SEARCH_API_LINK"):
            await initiate_search_tools()
        elif data[2] in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
            await start_from_queued()
        elif data[2] in [
            "RCLONE_SERVE_URL",
            "RCLONE_SERVE_PORT",
            "RCLONE_SERVE_USER",
            "RCLONE_SERVE_PASS",
        ]:
            await rclone_serve_booter()
    elif data[1] == "resetaria":
        aria2_defaults = await sync_to_async(aria2.client.get_global_option)
        if aria2_defaults[data[2]] == aria2_options[data[2]]:
            await query.answer("Value already same as you added in aria.sh!")
            return
        value = aria2_defaults[data[2]]
        aria2_options[data[2]] = value
        await gather(query.answer(), update_buttons(message, "aria"))
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option, download.gid, {data[2]: value}
                    )
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            await DbManager().update_aria2(data[2], value)
    elif data[1] == "emptyaria":
        aria2_options[data[2]] = ""
        _, __, downloads = await gather(
            query.answer(),
            update_buttons(message, "aria"),
            sync_to_async(aria2.get_downloads),
        )
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option, download.gid, {data[2]: ""}
                    )
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            await DbManager().update_aria2(data[2], "")
    elif data[1] == "emptyqbit":
        qbit_options[data[2]] = ""
        await gather(
            query.answer(),
            sync_to_async(get_client().app_set_preferences, {data[2]: ""}),
            update_buttons(message, "qbit"),
        )
        if DATABASE_URL:
            await DbManager().update_qbittorrent(data[2], "")
    elif data[1] == "private":
        pfunc = partial(update_private_file, omsg=message)
        rfunc = partial(update_buttons, message)
        await gather(
            query.answer(),
            update_buttons(message, data[1]),
            event_handler(client, query, pfunc, rfunc, True),
        )
    elif data[1] == "botvar" and STATE == "edit":
        if data[2] in unauth_config and query.from_user.id != config_dict["OWNER_ID"]:
            await query.answer("This setting only available for owner!", True)
            return
        pfunc = partial(edit_variable, omsg=message, key=data[2])
        rfunc = partial(update_buttons, message, "var")
        await gather(
            query.answer(),
            update_buttons(message, data[2], data[1]),
            event_handler(client, query, pfunc, rfunc),
        )
    elif data[1] == "botvar" and STATE == "view":
        if data[2] in unauth_config and query.from_user.id != config_dict["OWNER_ID"]:
            await query.answer("This setting only available for owner!", True)
            return
        value = config_dict[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            filename = f"{data[2]}.txt"
            async with aiopen(filename, "w", encoding="utf-8") as f:
                await f.write(f"{value}")
            await sendFile(
                message,
                filename,
                filename.split(".", maxsplit=1)[0],
                config_dict["IMAGE_TXT"],
            )
            return
        if value == "":
            value = None
        await query.answer(f"{value.__class__.__name__.upper()}: {value}", True)
    elif data[1] == "ariavar" and (STATE == "edit" or data[2] == "newkey"):
        pfunc = partial(edit_aria, omsg=message, key=data[2])
        rfunc = partial(update_buttons, message, "aria")
        await gather(
            query.answer(),
            update_buttons(message, data[2], data[1]),
            event_handler(client, query, pfunc, rfunc),
        )
    elif data[1] == "ariavar" and STATE == "view":
        value = aria2_options[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            filename = f"{data[2]}.txt"
            async with aiopen(filename, "w", encoding="utf-8") as f:
                await f.write(f"{value}")
            await sendFile(
                message,
                filename,
                filename.split(".", maxsplit=1)[0],
                config_dict["IMAGE_TXT"],
            )
            return
        if value == "":
            value = None
        await query.answer(f"{value.__class__.__name__.upper()}: {value}", True)
    elif data[1] == "qbitvar" and STATE == "edit":
        pfunc = partial(edit_qbit, omsg=message, key=data[2])
        rfunc = partial(update_buttons, message, "var")
        await gather(
            query.answer(),
            update_buttons(message, data[2], data[1]),
            event_handler(client, query, pfunc, rfunc),
        )
    elif data[1] == "qbitvar" and STATE == "view":
        value = qbit_options[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            filename = f"{data[2]}.txt"
            async with aiopen(filename, "w", encoding="utf-8") as f:
                await f.write(f"{value}")
            await sendFile(
                message,
                filename,
                filename.split(".", maxsplit=1)[0],
                config_dict["IMAGE_TXT"],
            )
            return
        if value == "":
            value = None
        await query.answer(f"{value.__class__.__name__.upper()}: {value}", True)
    elif data[1] == "edit":
        globals()["STATE"] = "edit"
        await gather(query.answer(), update_buttons(message, data[2]))
    elif data[1] == "view":
        globals()["STATE"] = "view"
        await gather(query.answer(), update_buttons(message, data[2]))
    elif data[1] == "start":
        await query.answer()
        if START != int(data[3]):
            globals()["START"] = int(data[3])
            await update_buttons(message, data[2])
    elif data[1] == "push":
        await query.answer()
        if query.from_user.id == config_dict["OWNER_ID"]:
            filename = data[2].rsplit(".zip", 1)[0]
            if await aiopath.exists(filename):
                await (
                    await create_subprocess_shell(
                        f"git add -f {filename} \
                                                    && git commit -sm botsettings -q \
                                                    && git push origin {config_dict['UPSTREAM_BRANCH']} -qf"
                    )
                ).wait()
            else:
                await (
                    await create_subprocess_shell(
                        f"git rm -r --cached {filename} \
                                                    && git commit -sm botsettings -q \
                                                    && git push origin {config_dict['UPSTREAM_BRANCH']} -qf"
                    )
                ).wait()
            LOGGER.info("Push update to UPSTREAM_REPO")
        await deleteMessage(message, message.reply_to_message)


@new_thread
async def bot_settings(_, message: Message):
    handler_dict[message.chat.id] = False
    msg, image, buttons = await get_buttons()
    await sendingMessage(msg, message, image, buttons)


bot.add_handler(
    MessageHandler(
        bot_settings, filters=command(BotCommands.BotSetCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    CallbackQueryHandler(
        edit_bot_settings, filters=regex("^botset") & CustomFilters.sudo
    )
)
