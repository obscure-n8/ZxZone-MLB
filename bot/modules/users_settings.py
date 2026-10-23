from aiofiles.os import path as aiopath, makedirs
from ast import literal_eval
from asyncio import sleep, gather, Event, wait_for, wrap_future
from functools import partial
from html import escape
from os import path as ospath, getcwd
from pyrogram import Client
from pyrogram.filters import command, regex, create, user
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message
from time import time

from bot import (
    bot,
    bot_loop,
    bot_dict,
    bot_lock,
    user_data,
    config_dict,
    DATABASE_URL,
    GLOBAL_EXTENSION_FILTER,
)
from bot.helper.ext_utils.bot_utils import (
    update_user_ldata,
    UserDaily,
    new_thread,
    new_task,
    is_premium_user,
    is_pm_enabled,
)
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.conf_loads import intialize_savebot
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.help_messages import UsetString
from bot.helper.ext_utils.media_utils import createThumb
from bot.helper.ext_utils.status_utils import get_readable_time, get_readable_file_size
from bot.helper.ext_utils.telegram_helper import TeleContent
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    auto_delete_message,
    sendPhoto,
    editPhoto,
    deleteMessage,
    editMessage,
    sendCustom,
)


handler_dict = {}


async def get_user_settings(from_user, data: str, uset_data: str):
    buttons = ButtonMaker()
    user_id = from_user.id
    thumbpath = ospath.join("thumbnails", f"{user_id}.jpg")
    rclone_path = ospath.join("rclone", f"{user_id}.conf")
    token_pickle = ospath.join("tokens", f"{user_id}.pickle")
    user_dict = user_data.get(user_id, {})
    premium_left = status_user = daily_limit = ""
    image = None

    if not data:
        sendpm, buttonkey = (
            (" ✓", "✓ Send PM")
            if is_pm_enabled(user_id, user_dict)
            else (" ✘", "Send PM")
        )
        buttons.button_data(buttonkey, f"userset {user_id} enable_pm")

        sendss, buttonkey = (
            (" ✓", "✓ Screenshot")
            if user_dict.get("enable_ss")
            else (" ✘", "Screenshot")
        )
        buttons.button_data(buttonkey, f"userset {user_id} enable_ss")

        AD = config_dict["AS_DOCUMENT"]
        ltype, buttonkey = (
            ("Document", "✓ As Document")
            if not user_dict and AD or user_dict.get("as_doc")
            else ("Media", "As Document")
        )
        buttons.button_data(buttonkey, f"userset {user_id} as_doc")

        MG = config_dict["MEDIA_GROUP"]
        mediagroup, buttonkey = (
            (" ✓", "✓ As Group")
            if user_dict.get("media_group") or "media_group" not in user_dict and MG
            else (" ✘", "As Group")
        )
        buttons.button_data(buttonkey, f"userset {user_id} media_group")

        premsg, buttonkey = (
            (prename, "✓ Prename")
            if (prename := user_dict.get("prename"))
            else (" ✘", "Prename")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata prename")

        sufmsg, buttonkey = (
            (sufname, "✓ Sufname")
            if (sufname := user_dict.get("sufname"))
            else (" ✘", "Sufname")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata sufname")

        rmmsg, buttonkey = (
            (" ✓", "✓ Remname") if user_dict.get("remname") else (" ✘", "Remname")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata remname")

        thumbmsg, buttonkey = (
            (" ✓", "✓ Thumbnail")
            if await aiopath.exists(thumbpath)
            else (" ✘", "Thumbnail")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata thumb")

        auto_thumb = user_dict.get("auto_thumbnail", config_dict["AUTO_THUMBNAIL"])
        if auto_thumb == "poster":
            autothumb_msg = "Poster"
            buttonkey = "Poster 🖼️"
        elif auto_thumb == "backdrop":
            autothumb_msg = "Backdrop"
            buttonkey = "Backdrop 🌄"
        else:
            autothumb_msg = "Disable"
            buttonkey = "AutoThumb ✘"
        buttons.button_data(buttonkey, f"userset {user_id} auto_thumb")

        HDTH = config_dict.get("HD_THUMBNAIL", False)
        hdthumb = user_dict.get("hd_thumb")
        if user_dict and "hd_thumb" in user_dict:
            hdthumb_msg, buttonkey = (
                (" ✓", "✓ HD Thumbnail") if hdthumb else (" ✘", "HD Thumbnail")
            )
        else:
            hdthumb_msg, buttonkey = (
                (" ✓", "✓ HD Thumbnail") if HDTH else (" ✘", "HD Thumbnail")
            )
        buttons.button_data(buttonkey, f"userset {user_id} hd_thumb")

        dumpch, buttonkey = (
            (f"<code>{user_dict.get('dump_ch')}</code>", " Dump CH")
            if user_dict.get("dump_ch")
            else (" ✘", "Dump CH")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata dump_ch")

        gdxmsg, buttonkey = (
            (" ✓", "✓ Custom GDX")
            if await aiopath.exists(token_pickle)
            else (" ✘", "Custom GDX")
        )
        buttons.button_data(buttonkey, f"userset {user_id} gdtool")

        rccmsg, buttonkey = (
            (" ✓", "✓ RClone")
            if await aiopath.exists(rclone_path)
            else (" ✘", "RClone")
        )
        buttons.button_data(buttonkey, f"userset {user_id} rctool")

        metadata, buttonkey = (
            (" ✓", "✓ Metadata") if user_dict.get("metadata") else (" ✘", "Metadata")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata metadata")

        default_upload = (
            user_dict.get("default_upload", "") or config_dict["DEFAULT_UPLOAD"]
        )
        du = "GDrive API" if default_upload == "gd" else "RClone"
        dub = "GDRIVE" if default_upload != "gd" else "RCLONE"
        buttons.button_data(
            f"Engine {dub}", f"userset {user_id} {default_upload}", "header"
        )

        YOPT = config_dict["YT_DLP_OPTIONS"]
        buttonkey = "✓ YT-DLP"
        if user_dict.get("yt_opt"):
            yto = f"\n<b><code>{escape(user_dict['yt_opt'])}</code></b>"
        elif "yt_opt" not in user_dict and (YOPT := config_dict["YT_DLP_OPTIONS"]):
            yto = f"\n<b><code>{escape(YOPT)}</code></b>"
        else:
            buttonkey = "YT-DLP"
            yto = " ✘"
        buttons.button_data(buttonkey, f"userset {user_id} setdata yt_opt")

        capmode = user_dict.get("caption_style", "mono")
        buttons.button_data(
            "✓ Caption" if user_dict.get("captions") else "Caption",
            f"userset {user_id} capmode",
        )

        buttons.button_data("Zip Mode", f"userset {user_id} zipmode")

        sesmsg, buttonkey = (
            (" ✓", "✓ Session String")
            if user_dict.get("session_string")
            else (" ✘", "Session String")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata session_string")

        if ext_filters := user_dict.get("excluded_extensions"):
            ex_ex = f"<code>{', '.join(ext_filters)}</code>"
        elif "excluded_extensions" not in user_dict and GLOBAL_EXTENSION_FILTER:
            ex_ex = f"<code>{', '.join(GLOBAL_EXTENSION_FILTER)}</code>"
        else:
            ex_ex = ""
        buttons.button_data(
            "✓ Extensions Filters" if ex_ex else "Extensions Filters",
            f"userset {user_id} setdata excluded_extensions",
        )

        custom_cap = " ✓" if user_dict.get("captions") else " ✘"
        if config_dict["PREMIUM_MODE"]:
            if (user_premi := is_premium_user(user_id)) and (
                time_data := user_dict.get("premium_left")
            ):
                if time_data - time() <= 0:
                    await gather(
                        update_user_ldata(user_id, "is_premium", False),
                        update_user_ldata(user_id, "premium_left", 0),
                    )
                else:
                    premium_left = f"┊<b>Premium Left:</b> <b>{get_readable_time(time_data - time())}</b>\n"
            if user_id != config_dict["OWNER_ID"]:
                status_user = (
                    "┊<b>Status:</b> <b>PREMIUM</b>\n"
                    if user_premi
                    else "┊<b>Status:</b> <b>NORMAL</b>\n"
                )
        if config_dict["DAILY_MODE"] and not is_premium_user(user_id):
            await UserDaily(user_id).get_daily_limit()
            daily_limit = f"┊<b>Daily Limit:</b> <b>{get_readable_file_size(user_data[user_id]['daily_limit'])}/{config_dict['DAILY_LIMIT_SIZE']}GB</b>\n"
            daily_limit += f"┊<b>Reset Time:</b> <b>{get_readable_time(user_data[user_id]['reset_limit'] - time())}</b>\n"
        text = (
            "<b>USER SETTINGS</b>\n\n"
            f"╭<b>Settings For:</b> <b>{from_user.mention}</b>\n{status_user}{premium_left}{daily_limit}"
            f"┊<b>Leech Type:</b>{ltype}\n"
            f"┊<b>As Group:</b>{mediagroup}\n"
            f"┊<b>Thumbnail:</b>{thumbmsg}\n"
            f"┊<b>Auto Thumbnail:</b> {autothumb_msg}\n"
            f"┊<b>HD Thumbnail:</b> {hdthumb_msg}\n"
            f"┊<b>DM Mode:</b>{sendpm}\n"
            f"┊<b>SS Mode:</b>{sendss}\n"
            f"┊<b>RClone:</b>{rccmsg}\n"
            f"┊<b>Caption:</b>{capmode.upper()}\n"
            f"┊<b>Prename:</b>{premsg}\n"
            f"┊<b>Sufname:</b>{sufmsg}\n"
            f"┊<b>Remname:</b>{rmmsg}\n"
            f"┊<b>Metadata:</b>{metadata}\n"
            f"┊<b>UserDump/Tds:</b> {dumpch}\n"
            f"┊<b>Custom GDrive:</b>{gdxmsg}\n"
            f"┊<b>Custom Caption:</b>{custom_cap}\n"
            f"┊<b>Session String:</b>{sesmsg}\n"
            f"┊<b>Default Upload:</b>{du}\n"
            f"╰<b>YT-DLP Options:</b> {yto}\n"
        )
        text += f"<i>Leech Split Size ~ {get_readable_file_size(config_dict['LEECH_SPLIT_SIZE'])}</i>"
        if user_dict.get("rclone_path", "").startswith(
            "mrcc"
        ) and not await aiopath.exists(rclone_path):
            text += "\n<i>Using custom rclone path but user rclone not found, mirror upload will fail!</i>"

    elif data == "capmode":
        ex_cap = "Thor: Love and Thunder (2022) 1080p.mkv"
        if user_dict.get("prename"):
            ex_cap = f"{user_dict.get('prename')} {ex_cap}"
        if user_dict.get("sufname"):
            fname, ext = ex_cap.rsplit(".", maxsplit=1)
            ex_cap = f"{fname} {user_dict.get('sufname')}.{ext}"

        user_cap = user_dict.get("caption_style", "mono")
        user_capmode = user_cap.upper()
        match user_cap:
            case "italic":
                image, ex_cap = config_dict["IMAGE_ITALIC"], f"<i>{ex_cap}</i>"
            case "bold":
                image, ex_cap = config_dict["IMAGE_BOLD"], f"<b>{ex_cap}</b>"
            case "normal":
                image = config_dict["IMAGE_NORMAL"]
            case "mono":
                image, ex_cap = config_dict["IMAGE_MONO"], f"<code>{ex_cap}</code>"

        cap_modes = ["mono", "italic", "bold", "normal"]
        cap_modes.remove(user_cap)
        caption, fnamecap = user_dict.get("captions"), user_dict.get("fnamecap", True)
        if not user_dict or fnamecap:
            [
                buttons.button_data(mode.title(), f"userset {user_id} cap{mode}")
                for mode in cap_modes
            ]
        buttons.button_data(
            "✅ Custom Caption" if caption else "Custom Caption",
            f"userset {user_id} setdata setcap",
        )
        buttons.button_data("Back", f"userset {user_id} back")
        if caption:
            buttons.button_data(
                "✅ FCaption" if fnamecap else "FCaption", f"userset {user_id} fnamecap"
            )
            custom_cap = f"\n<code>{escape(caption)}</code>"
            if fnamecap:
                fname_cup = "┊<b>FName Caption:</b> <b>ENABLE</b>\n"
            else:
                fname_cup = "╰<b>FName Caption:</b> <b>DISABLE</b>\n"
                user_capmode, image, ex_cap = (
                    "DISABLE",
                    config_dict["IMAGE_CAPTION"],
                    "<b>DISABLE</b>",
                )
        else:
            custom_cap, fname_cup = "<b>DISABLE</b>", ""
        text = (
            "<b>CAPTION SETTINGS</b>\n"
            f"╭<b>Caption Settings:</b> <b>{from_user.mention}</b>\n"
            f"┊<b>Caption Mode:</b> <b>{user_capmode}</b>\n"
            f"┊{fname_cup}"
            f"╰<b>Custom Caption:</b> {custom_cap}\n\n"
            f"<b>Example:</b> {ex_cap}"
        )

    elif data == "rctool":
        rccmsg, buttonkey = (
            ("EXISTS ✅", "✅ RClone Config")
            if await aiopath.exists(rclone_path)
            else ("NOT SET", "RClone Config")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata rclone_config")

        rcpathmsg, buttonkey = (
            (f"<code>{rc_path}</code>", "✅ RClone Path")
            if (rc_path := user_dict.get("rclone_path"))
            else ("<b>NOT SET</b>", "RClone Path")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata rclone_path")

        buttons.button_data("Back", f"userset {user_id} back")

        image = config_dict["IMAGE_RCLONE"]
        text = (
            "<b>RCLONE SETTINGS</b>\n"
            + f"╭<b>RClone Config:</b> <b>{rccmsg}</b>\n"
            + f"╰<b>Rclone Path:</b> {rcpathmsg}\n"
        )

    elif data == "gdtool":
        gdrive_id, buttonkey = (
            (f"<code>{gd_id}</code>", "✅ Drive ID")
            if (gd_id := user_dict.get("gdrive_id"))
            else ("<b>DISABLE</b>", "Drive ID")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata gdrive_id")

        index_url, buttonkey = (
            (f"<code>{index}</code>", "✅ Index URL")
            if (index := user_dict.get("index_url"))
            else ("<b>DISABLE</b>", "Index URL")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata index_url")

        token_pickle, buttonkey = (
            ("EXISTS ✅", "✅ Token Pickle")
            if await aiopath.exists(token_pickle)
            else ("NOT SET", "Token Pickle")
        )
        buttons.button_data(buttonkey, f"userset {user_id} setdata token_pickle")

        stop_dup = (
            user_dict.get("stop_duplicate")
            or "stop_duplicate" not in user_dict
            and config_dict["STOP_DUPLICATE"]
        )
        stop_dup_msg, buttonkey = (
            ("ENABLE ✅", "✅ Stop Duplicate")
            if stop_dup
            else ("DISABLE", "Stop Duplicate")
        )
        buttons.button_data(
            buttonkey, f"userset {user_id} stop_duplicate {stop_dup}", "header"
        )

        if await aiopath.exists("accounts"):
            use_sa, buttonkey = (
                ("ENABLE ✅", "✅ Use SA")
                if user_dict.get("use_sa")
                else ("DISABLE", "Use SA")
            )
            buttons.button_data(
                buttonkey, f"userset {user_id} use_sa {use_sa}", "header"
            )
        else:
            use_sa = "NOT AVAILABLE"

        buttons.button_data("Back", f"userset {user_id} back")

        image = config_dict["IMAGE_GD"]
        text = (
            "<b>User GDRIVE SETTING</b>\n"
            f"╭<b>GDrive ID:</b> {gdrive_id}\n"
            f"┊<b>Index URL:</b> {index_url}\n"
            f"┊<b>Use SA:</b> <b>{use_sa}</b>\n"
            f"┊<b>Token Pickle:</b> <b>{token_pickle}</b>\n"
            f"╰<b>Stop Duplicate:</b> <b>{stop_dup_msg}</b>"
        )

    elif data == "zipmode":
        but_dict = {
            "zfolder": ["Folders", f"userset {user_id} zipmode zfolder"],
            "zfpart": ["Cloud Part", f"userset {user_id} zipmode zfpart"],
            "zeach": ["Each Files", f"userset {user_id} zipmode zeach"],
            "zpart": ["Part Mode", f"userset {user_id} zipmode zpart"],
            "auto": ["Auto Mode", f"userset {user_id} zipmode auto"],
        }
        def_data = but_dict[uset_data][0]
        but_dict[uset_data][0] = f"✅ {def_data}"
        [buttons.button_data(key, value) for key, value in but_dict.values()]
        buttons.button_data("Back", f"userset {user_id} back")
        part_size = get_readable_file_size(config_dict["LEECH_SPLIT_SIZE"])
        image = config_dict["IMAGE_ZIP"]
        text = (
            "<b>ZIP MODE SETTINGS</b>\n"
            f"╭ <b>Folders/Default:</b> Zip file/folder\n"
            f"┊ <b>Cloud Part:</b> Zip file/folder as part {part_size} (Mirror Cmds)\n"
            f"┊ <b>Each Files:</b> Zip each file in folder/subfolder\n"
            f"┊ <b>Part Mode:</b> Zip each file in folder/subfolder as part if size more than {part_size} (Mirror Cmds)\n"
            f"┊ <b>Auto Mode:</b> Zip only file in folder/subfolder if size more than {part_size}\n\n"
            f"╰ <b>Current Mode:</b> {def_data}\n\n"
            " Seed torrent only working in <b>Deafult Mode</b>"
        )

    elif data == "setdata":
        if uset_data in {"thumb", "rclone_config", "token_pickle"}:
            file_dict = {
                "thumb": (
                    thumbpath,
                    "Thumbnail",
                    "Send a photo to save it as custom thumbnail.",
                    "",
                    "",
                ),
                "rclone_config": (
                    rclone_path,
                    "RClone",
                    "Send a valid *.conf file for <b>config.conf</b>.",
                    config_dict["IMAGE_RCLONE"],
                    "rctool",
                ),
                "token_pickle": (
                    token_pickle,
                    "Token",
                    "Send a valid *.pickle file for <b>token.pickle</b>.",
                    config_dict["IMAGE_GD"],
                    "gdtool",
                ),
            }
            file_path, butkey, text, image, qdata = file_dict[uset_data]
            if await aiopath.exists(file_path):
                buttons.button_data(
                    f"Change {butkey}", f"userset {user_id} prepare {uset_data}"
                )
                buttons.button_data(
                    f"Delete {butkey}", f"userset {user_id} rem_{uset_data}"
                )
            else:
                buttons.button_data(
                    f"Set {butkey}", f"userset {user_id} prepare {uset_data}"
                )
        else:
            uset_dict = {
                "excluded_extensions": (
                    "excluded_extensions",
                    "Extension",
                    UsetString.EXT,
                    config_dict["IMAGE_EXTENSION"],
                    "",
                ),
                "setcap": (
                    "captions",
                    "Caption",
                    UsetString.CAP,
                    config_dict["IMAGE_CAPTION"],
                    "capmode",
                ),
                "rctool": (
                    "captions",
                    "Caption",
                    UsetString.CAP,
                    config_dict["IMAGE_CAPTION"],
                    "rctool",
                ),
                "rclone_path": (
                    "rclone_path",
                    "RClone Path",
                    UsetString.RCP,
                    config_dict["IMAGE_RCLONE"],
                    "rctool",
                ),
                "dump_ch": (
                    "dump_ch",
                    "Dump",
                    UsetString.DUMP,
                    config_dict["IMAGE_DUMP"],
                    "",
                ),
                "gdrive_id": (
                    "gdrive_id",
                    "ID",
                    UsetString.GDID,
                    config_dict["IMAGE_GD"],
                    "gdtool",
                ),
                "index_url": (
                    "index_url",
                    "Index",
                    UsetString.INDX,
                    config_dict["IMAGE_GD"],
                    "gdtool",
                ),
                "prename": (
                    "prename",
                    "Prename",
                    UsetString.PRE,
                    config_dict["IMAGE_PRENAME"],
                    "",
                ),
                "sufname": (
                    "sufname",
                    "Sufname",
                    UsetString.SUF,
                    config_dict["IMAGE_SUFNAME"],
                    "",
                ),
                "remname": (
                    "remname",
                    "Remname",
                    UsetString.REM.format(user_dict.get("remname") or "~"),
                    config_dict["IMAGE_REMNAME"],
                    "",
                ),
                "metadata": (
                    "metadata",
                    "Metadata",
                    UsetString.META.format(user_dict.get("metadata") or "~"),
                    config_dict["IMAGE_METADATA"],
                    "",
                ),
                "session_string": (
                    "session_string",
                    "Session",
                    UsetString.SES,
                    config_dict["IMAGE_USER"],
                    "",
                ),
                "yt_opt": (
                    "yt_opt",
                    "YT-DLP",
                    UsetString.YT,
                    config_dict["IMAGE_YT"],
                    "",
                ),
            }
            if uset_data == "dump_ch":
                log_title = user_dict.get("log_title")
                buttons.button_data(
                    "✅ Log Title" if log_title else "Log Title",
                    f"userset {user_id} setdata dump_ch {not log_title}",
                )
            elif uset_data == "metadata":
                clean_meta = user_dict.get("clean_metadata")
                buttons.button_data(
                    "✅ Clean" if clean_meta else "✅ Overwrite",
                    f"userset {user_id} setdata metadata {not clean_meta}",
                )

            key, butkey, text, image, qdata = uset_dict[uset_data]
            if user_dict.get(key) or key == "yt_opt" and config_dict["YT_DLP_OPTIONS"]:
                buttons.button_data(
                    f"Change {butkey}", f"userset {user_id} prepare {key}"
                )
                buttons.button_data(f"Remove {butkey}", f"userset {user_id} rem_{key}")
            else:
                buttons.button_data(f"Set {butkey}", f"userset {user_id} prepare {key}")
        if qdata:
            buttons.button_data("Back", f"userset {user_id} {qdata}")
        text = text.replace("Timeout: 60s.", "")
        if uset_data not in [
            "setcap",
            "index_url",
            "token_pickle",
            "gdrive_id",
            "rclone_path",
            "rclone_config",
        ]:
            buttons.button_data("Back", f"userset {user_id} back")

    elif data == "prepare":
        msg_thumb = (
            "Send a photo to to change current thumbnail.\n\n<i>Timeout: 60s.</i>"
            if await aiopath.exists(thumbpath)
            else "Send a photo to save it as custom thumbnail.\n\n<i>Timeout: 60s.</i>"
        )
        msg_rclone = (
            "Send new valid *.conf file to change current <b>config.conf</b>.\n\n<i>Timeout: 60s.</i>"
            if await aiopath.exists(rclone_path)
            else "Send a valid *.conf file for <b>config.conf</b>.\n\n<i>Timeout: 60s.</i>"
        )
        msg_token = (
            "Send new valid *.pickle file to change current <b>token.pickle</b>.\n\n<i>Timeout: 60s.</i>"
            if await aiopath.exists(token_pickle)
            else "Send a valid *.pickle file for <b>token.pickle</b>.\n\n<i>Timeout: 60s.</i>"
        )
        prepare_dict = {
            "thumb": (msg_thumb, image),
            "rclone_config": (msg_rclone, config_dict["IMAGE_RCLONE"]),
            "token_pickle": (msg_token, config_dict["IMAGE_GD"]),
            "dump_ch": (UsetString.DUMP, config_dict["IMAGE_DUMP"]),
            "rclone_path": (UsetString.RCP, config_dict["IMAGE_RCLONE"]),
            "gdrive_id": (UsetString.GDID, config_dict["IMAGE_GD"]),
            "index_url": (UsetString.INDX, config_dict["IMAGE_GD"]),
            "excluded_extensions": (UsetString.EXT, config_dict["IMAGE_EXTENSION"]),
            "captions": (UsetString.CAP, config_dict["IMAGE_CAPTION"]),
            "prename": (UsetString.PRE, config_dict["IMAGE_PRENAME"]),
            "sufname": (UsetString.SUF, config_dict["IMAGE_SUFNAME"]),
            "remname": (
                UsetString.REM.format(user_dict.get("remname") or "~"),
                config_dict["IMAGE_REMNAME"],
            ),
            "metadata": (
                UsetString.META.format(user_dict.get("metadata") or "~"),
                config_dict["IMAGE_METADATA"],
            ),
            "session_string": (UsetString.SES, config_dict["IMAGE_USER"]),
            "yt_opt": (UsetString.YT, config_dict["IMAGE_YT"]),
        }
        text, image = prepare_dict[uset_data]
        buttons.button_data("Back", f"userset {user_id} setdata {uset_data}")

    buttons.button_data("Close", f"userset {user_id} close")
    return text, image, buttons.build_menu(2)


async def update_user_settings(
    query: CallbackQuery, data: str = None, uset_data: str = None
):
    text, image, button = await get_user_settings(query.from_user, data, uset_data)
    if not image:
        if await aiopath.exists(
            thumb := ospath.join("thumbnails", f"{query.from_user.id}.jpg")
        ):
            image = thumb
        else:
            image = config_dict["IMAGE_USETIINGS"]
    await editPhoto(text, query.message, image, button)


async def set_user_settings(_, message: Message, query: CallbackQuery, key: str):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value: str = message.text
    if key == "dump_ch" and (
        value.isdigit() or value.startswith("-100") and value[1:].isdigit()
    ):
        value = int(value)
    elif key == "excluded_extensions":
        fx = value.split()
        value = ["aria2", "!qB"]
        for x in fx:
            x = x.lstrip(".")
            value.append(x.strip().lower())
    await gather(update_user_ldata(user_id, key, value), deleteMessage(message))
    if key == "dump_ch":
        await update_user_settings(query, "setdata", "dump_ch")
    else:
        match key:
            case "index_url" | "token_pickle" | "gdrive_id":
                data = "gdtool"
            case "captions":
                data = "capmode"
            case "rclone_path":
                data = "rctool"
            case _:
                data = ""
        if key == "session_string":
            await intialize_savebot(value, True, user_id)
            async with bot_lock:
                save_bot = bot_dict[user_id]["SAVEBOT"]
            if not save_bot:
                msg = await sendMessage(
                    "Something went wrong, or invalid string!", message
                )
                await update_user_ldata(user_id, key, "")
                bot_loop.create_task(auto_delete_message(message, msg, stime=5))
        await update_user_settings(query, data)


async def set_thumb(_, message: Message, query: CallbackQuery):
    user_id = query.from_user.id
    handler_dict[user_id] = False
    msg = await sendMessage("<i>Processing, please wait...</i>", message)
    des_dir = await createThumb(message, user_id)
    await gather(
        update_user_ldata(user_id, "thumb", des_dir),
        deleteMessage(message, msg),
        update_user_settings(query),
    )
    if DATABASE_URL:
        await DbManager().update_user_doc(user_id, "thumb", des_dir)


async def add_rclone_pickle(_, message: Message, query: CallbackQuery, key: str):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    file_path, ext_file = (
        ("rclone", ".conf") if key == "rclone_config" else ("tokens", ".pickle")
    )
    fpath = ospath.join(getcwd(), file_path)
    await makedirs(fpath, exist_ok=True)
    if message.document.file_name.endswith(ext_file):
        des_dir = ospath.join(fpath, f"{user_id}{ext_file}")
        msg = await sendMessage("<i>Processing, please wait...</i>", message)
        await message.download(file_name=des_dir)
        qdata = "rctool" if key == "rclone_config" else "gdtool"
        await gather(
            update_user_ldata(
                user_id, file_path, ospath.join(file_path, f"{user_id}{ext_file}")
            ),
            deleteMessage(message, msg),
            update_user_settings(query, qdata),
        )
        if DATABASE_URL:
            await DbManager().update_user_doc(user_id, key, des_dir)
    else:
        msg = await sendMessage(f"Invalid *{ext_file} file!", message)
        await gather(
            update_user_settings(query, "setdata", key),
            auto_delete_message(message, msg, stime=5),
        )


@new_thread
async def edit_user_settings(client: Client, query: CallbackQuery):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    user_dict = user_data.get(user_id, {})
    premi_features = [
        "caption",
        "dump_ch",
        "gdrive_id",
        "media_group",
        "prename",
        "sufname",
        "remname",
        "metadata",
        "session_string",
        "enable_pm",
        "enable_ss",
    ]
    pre_data = data[3] if data[2] == "setdata" else data[2]
    if (
        config_dict["PREMIUM_MODE"]
        and not is_premium_user(user_id)
        and pre_data in premi_features
    ):
        await query.answer("Upss, Premium User Required!", True)
        is_modified = False
        for key in premi_features:
            if user_dict.get(key):
                is_modified = True
                await update_user_ldata(user_id, key, False)
        if is_modified:
            await update_user_settings(query)
        return
    if user_id != int(data[1]):
        await query.answer("Not Yours!", True)
        return
    match data[2]:
        case "setdata":
            handler_dict[user_id] = False
            await query.answer()
            if data[3] in ("dump_ch", "metadata") and len(data) == 5:
                key = "log_title" if data[3] == "dump_ch" else "clean_metadata"
                await update_user_ldata(user_id, key, literal_eval(data[4]))
            await update_user_settings(query, "setdata", data[3])
        case "gd" | "rc" as value:
            du = "rc" if value == "gd" else "gd"
            await gather(
                query.answer(), update_user_ldata(user_id, "default_upload", du)
            )
            await update_user_settings(query)
        case "back":
            handler_dict[user_id] = False
            await gather(query.answer(), update_user_settings(query))
        case (
            "rem_prename"
            | "rem_sufname"
            | "rem_dump_ch"
            | "rem_remname"
            | "rem_metadata"
            | "rem_session_string"
            | "rem_yt_opt"
            | "rem_index_url"
            | "rem_gdrive_id"
            | "rem_captions"
            | "rem_excluded_extensions"
            | "rem_rclone_path" as value
        ):
            qdata = uset_data = ""
            match value:
                case "rem_dump_ch":
                    await update_user_ldata(user_id, "log_title", False)
                case "rem_session_string":
                    if savebot := bot_dict[user_id]["SAVEBOT"]:
                        await savebot.stop()
                case "rem_captions":
                    qdata = "capmode"
                    await update_user_ldata(user_id, "fnamecap", True)
                case "rem_rclone_path":
                    qdata = "rctool"
                case "rem_index_url" | "rem_gdrive_id":
                    qdata = "gdtool"
            if value in ("rem_rclone_path", "rem_gdrive_id") and value in user_data.get(
                user_id, {}
            ):
                del user_data[user_id][value]
                if DATABASE_URL:
                    await DbManager().update_user_data(user_id)
            else:
                await update_user_ldata(user_id, value[4:], "")
            await gather(query.answer(), update_user_settings(query, qdata, uset_data))
        case (
            "enable_pm"
            | "enable_ss"
            | "as_doc"
            | "media_group"
            | "fnamecap"
            | "stop_duplicate"
            | "use_sa" as value
        ):
            qdata = uset_data = ""
            if value == "enable_pm" and config_dict["BOT_PM"]:
                await query.answer("Send PM is enabled by BOT_PM for all users.")
                await update_user_settings(query, qdata, uset_data)
                return
            await update_user_ldata(user_id, value, not user_dict.get(value, False))
            if value == "fnamecap":
                qdata = "capmode"
            if value in ("stop_duplicate", "use_sa"):
                qdata = "gdtool"
            await gather(query.answer(), update_user_settings(query, qdata, uset_data))
        case "capmode" | "gdtool" | "rctool" as value:
            await gather(query.answer(), update_user_settings(query, value))
        case "auto_thumb":
            auto_thumb = user_dict.get("auto_thumbnail", config_dict["AUTO_THUMBNAIL"])
            if auto_thumb == "poster":
                next_mode = "backdrop"
            elif auto_thumb == "backdrop":
                next_mode = "disabled"
            else:
                next_mode = "poster"
            await gather(
                query.answer(f"Auto Thumbnail set to {next_mode.title()}"),
                update_user_ldata(user_id, "auto_thumbnail", next_mode),
            )
            if DATABASE_URL:
                await DbManager().update_user_data(user_id)
            await update_user_settings(query)
        case "hd_thumb":
            curr_hd = user_dict.get("hd_thumb", config_dict.get("HD_THUMBNAIL", False))
            await gather(
                query.answer(f"HD Thumbnail set to {not curr_hd}"),
                update_user_ldata(user_id, "hd_thumb", not curr_hd),
            )
            if DATABASE_URL:
                await DbManager().update_user_data(user_id)
            await update_user_settings(query)
        case "zipmode":
            try:
                zmode = data[3]
            except:
                zmode = user_dict.get("zipmode", "zfolder")
            if zmode == user_dict.get("zipmode", "") and len(data) == 4:
                await query.answer("Already Selected!", True)
                return
            await gather(query.answer(), update_user_ldata(user_id, "zipmode", zmode))
            await update_user_settings(query, "zipmode", zmode)
        case "capmono" | "capitalic" | "capbold" | "capnormal" as value:
            await update_user_ldata(user_id, "caption_style", value.lstrip("cap"))
            await gather(query.answer(), update_user_settings(query, "capmode"))
        case "close":
            handler_dict[user_id] = False
            await gather(
                query.answer(), deleteMessage(message, message.reply_to_message)
            )
        case "rem_thumb" | "rem_rclone_config" | "rem_token_pickle" as value:
            match value:
                case "rem_thumb":
                    path = ospath.join("thumbnails", f"{user_id}.jpg")
                case "rem_rclone_config":
                    path = ospath.join("rclone", f"{user_id}.conf")
                case _:
                    path = ospath.join("tokens", f"{user_id}.pickle")
            key = value.lstrip("rem_")
            await update_user_ldata(user_id, key, "")
            if await aiopath.exists(path):
                await gather(query.answer(), clean_target(path))
                await update_user_settings(query)
                if DATABASE_URL:
                    await DbManager().update_user_doc(user_id, key)
            else:
                await gather(
                    query.answer("Old Settings", True), update_user_settings(query)
                )
        case "prepare":
            match data[3]:
                case "token_pickle":
                    if not (
                        user_id == config_dict["OWNER_ID"]
                        or user_data.get(user_id, {}).get("is_sudo")
                    ):
                        await query.answer(
                            "Token upload is restricted to the owner or sudo users.",
                            True,
                        )
                        return
                    await query.answer()
                    photo, document = False, True
                    pfunc = partial(add_rclone_pickle, query=query, key=data[3])
                case "rclone_config":
                    await query.answer()
                    photo, document = False, True
                    pfunc = partial(add_rclone_pickle, query=query, key=data[3])
                case "thumb":
                    await query.answer()
                    photo, document = True, False
                    pfunc = partial(set_thumb, query=query)
                case _:
                    handler_dict[user_id] = True
                    await query.answer(
                        "Don't forget add me to your chat!", True
                    ) if data[3] == "dump_ch" else await query.answer()
                    photo = document = False
                    pfunc = partial(set_user_settings, query=query, key=data[3])
            await gather(
                update_user_settings(query, data[2], data[3]),
                event_handler(client, query, pfunc, photo, document),
            )


async def event_handler(
    client: Client,
    query: CallbackQuery,
    pfunc: partial,
    photo: bool = False,
    document: bool = False,
):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        if photo:
            mtype = event.photo
        elif document:
            mtype = event.document
        else:
            mtype = event.text
        user = event.from_user or event.sender_chat
        return bool(
            user.id == user_id and event.chat.id == query.message.chat.id and mtype
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )
    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await update_user_settings(query)
    client.remove_handler(*handler)


@new_task
async def user_settings(_, message: Message):
    from_user = message.from_user
    handler_dict[from_user.id] = False
    if fmsg := await UseCheck(message).run():
        await auto_delete_message(message, fmsg)
        return
    msg, image, buttons = await get_user_settings(from_user, None, None)
    if await aiopath.exists(
        thumb := ospath.join("thumbnails", f"{message.from_user.id}.jpg")
    ):
        image = thumb
    await sendPhoto(msg, message, image or config_dict["IMAGE_USETIINGS"], buttons)


@new_task
async def set_premium_users(_, message: Message):
    if not config_dict["PREMIUM_MODE"]:
        await sendMessage("<b>Premium Mode</b> is disable!", message)
        return
    reply_to = message.reply_to_message
    args = message.text.split()
    text = "Reply to a user or send user ID with options (add/del) and duration time in day(s)"
    if not reply_to and len(args) == 1:
        await sendMessage(text, message)
        return
    if reply_to and len(args) > 1:
        premi_id = reply_to.from_user.id
        if args[1] == "add":
            day = int(args[2])
    elif len(args) > 2:
        premi_id = int(args[2])
        if args[1] == "add":
            day = int(args[3])
    elif len(args) == 2 and args[1] == "list":
        text = "Premium List:\n"
        i = 1
        for id_, value in user_data.items():
            if (
                value.get("is_premium")
                and (time_left := value["premium_left"]) - time() > 1
            ):
                text += f"{i}. @{value.get('user_name')} (<code>{id_}</code>) ~ {get_readable_time(time_left - time())}\n"
                i += 1
    else:
        await sendMessage(text, message)
        return

    user_text = ""
    if args[1] == "add":
        duartion = int(time() + (86400 * day))
        text = f"😘 Yeay, <b>{premi_id}</b> has been added as <b>Premium User</b> for {day} day(s)."
        user_text = f"Yeay 😘, you have been added as <b>Premium User</b> for {day}(s)."
        await gather(
            update_user_ldata(premi_id, "premium_left", duartion),
            update_user_ldata(premi_id, "is_premium", True),
        )
    elif args[1] == "del":
        text = f"😑 Hmm, <b>{premi_id}</b> has been remove as <b>Premium User</b>!"
        user_text = "Huhu 😑, you have been deleted as <b>Premium User</b>!"
        await gather(
            update_user_ldata(premi_id, "premium_left", 0),
            update_user_ldata(premi_id, "is_premium", False),
        )
    msg = await sendMessage(text, message)
    if user_text:
        await sendCustom(user_text, premi_id)
    await auto_delete_message(message, msg)


@new_task
async def reset_daily_limit(_, message: Message):
    reply_to = message.reply_to_message
    args = message.text.split()
    if not reply_to and len(args) == 1:
        await sendMessage(
            "Reply to a user or send user ID to reset daily limit.", message
        )
        return
    if reply_to:
        user_id = reply_to.from_user.id
    elif len(args) > 1:
        user_id = int(args[1])
    await gather(
        update_user_ldata(user_id, "daily_limit", 1),
        update_user_ldata(user_id, "reset_limit", time() + 86400),
    )
    msg = await sendMessage("Daily limit has been reset.", message)
    await auto_delete_message(message, msg)


@new_task
async def send_users_settings(client: Client, message: Message):
    contents = []
    msg = ""
    if len(user_data) == 0:
        await sendMessage("No user data!", message)
        return
    for index, (uid, data) in enumerate(user_data.items(), start=1):
        if (
            data.get("is_sudo")
            and "sudo_left" in data
            and data["sudo_left"] - time() <= 0
        ):
            del user_data[uid]["sudo_left"]
            await update_user_ldata(uid, "is_sudo", False)
        uname = user_data[uid].get("user_name")
        msg += f'<b><a href="https://t.me/{uname}">{uname}</a></b>\n'
        msg += f"⁍ <b>User ID:</b> <code>{uid}</code>\n"
        for key, value in data.items():
            if key in ("session_token", "session_time") or value == "":
                continue
            if key == "reset_limit":
                value -= time()
                value = get_readable_time(0 if value <= 1 else value)
            elif key == "daily_limit":
                value = f"{get_readable_file_size(value)}/{config_dict['DAILY_LIMIT_SIZE']}GB"
            elif key in ("premium_left", "sudo_left"):
                value = f"{get_readable_time(value - time())}"
            elif key in ("caption_style", "zipmode"):
                value = str(value).title()
            elif key in ["thumb", "rclone_config", "token_pickle"]:
                value = "Exists" if value else "Not Exists"
            elif key in [
                "dump_ch",
                "yt_opt",
                "index_url",
                "gdrive_id",
                "prename",
                "sufname",
                "metadata",
                "auto_thumbnail",
            ]:
                value = f"<code>{value}</code>"
            elif str(value).lower() == "true" or (
                key in ["session_string", "remname", "captions"] and value
            ):
                value = "Yes"
            elif str(value).lower() == "false":
                value = "No"
            if key != "user_name" and value != "":
                msg += f"⁍ <b>{key.replace('_', ' ').title()}:</b> {value}\n"
        contents.append(f"{str(index).zfill(3)}. {msg}\n")
        msg = ""
    tele = TeleContent(message, max_page=5, direct=False)
    tele.set_data(contents, f"<b>FOUND {len(contents)} USERS SETTINGS DATA</b>")
    text, buttons = await tele.get_content("usettings")
    msg = await sendMessage(text, message, buttons)
    event = Event()

    @new_thread
    async def __event_handler():
        pfunc = partial(users_handler, event=event, tele=tele)
        handler = client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^usettings") & user(message.from_user.id)
            ),
            group=-1,
        )
        try:
            await wait_for(event.wait(), timeout=180)
        except:
            pass
        finally:
            client.remove_handler(*handler)

    await wrap_future(__event_handler())
    await deleteMessage(msg, message)


async def users_handler(_, query: CallbackQuery, event=Event, tele=TeleContent):
    message = query.message
    data = query.data.split()
    if data[2] == "close":
        event.set()
        if tele:
            tele.cancel()
        await deleteMessage(message, message.reply_to_message)
    else:
        tdata = int(data[4]) if data[2] == "foot" else int(data[3])
        text, buttons = await tele.get_content("usettings", data[2], tdata)
        if data[2] == "page":
            await query.answer(f"Total Page ~ {tele.pages}", True)
            return
        if not buttons:
            await query.answer(text, True)
            return
        await gather(query.answer(), editMessage(text, message, buttons))


bot.add_handler(
    MessageHandler(
        set_premium_users,
        filters=command(BotCommands.UserSetPremiCommand) & CustomFilters.sudo,
    )
)
bot.add_handler(
    MessageHandler(
        send_users_settings,
        filters=command(BotCommands.UsersCommand) & CustomFilters.sudo,
    )
)
bot.add_handler(
    MessageHandler(
        reset_daily_limit,
        filters=command(BotCommands.DailyResetCommand) & CustomFilters.sudo,
    )
)
bot.add_handler(
    MessageHandler(user_settings, filters=command(BotCommands.UserSetCommand))
)
bot.add_handler(CallbackQueryHandler(edit_user_settings, filters=regex("^userset")))
