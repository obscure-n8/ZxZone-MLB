from html import escape
from psutil import virtual_memory, cpu_percent, disk_usage, net_io_counters
from pyrogram.types import Message
from time import time
from pytz import timezone

from bot import bot_name, task_dict, task_dict_lock, botStartTime, config_dict
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker


SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


class MirrorStatus:
    STATUS_ARCHIVING = "Archiving"
    STATUS_CHECKING = "Checking"
    STATUS_CLONING = "Cloning"
    STATUS_COMPRESS = "Compressing"
    STATUS_CONVERT = "Converting"
    STATUS_SUBSYNC = "Syncing"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_EXTRACTING = "Extracting"
    STATUS_MERGING = "Merging"
    STATUS_PAUSED = "Paused"
    STATUS_QUEUEDL = "QueueDl"
    STATUS_QUEUEUP = "QueueUl"
    STATUS_RMSTREAM = "Removing"
    STATUS_SAMVID = "SamVid"
    STATUS_METADATA = "Metadata"
    STATUS_SEEDING = "Seeding"
    STATUS_SPLITTING = "Splitting"
    STATUS_TRIM = "Trimming"
    STATUS_UPLOADING = "Uploading"
    STATUS_UPLOADINGTOGO = "Uploading"
    STATUS_WAIT = "Waiting"
    STATUS_WATERMARK = "Watermarking"


async def getTaskByGid(gid: str):
    async with task_dict_lock:
        return next((tk for tk in task_dict.values() if tk.gid() == gid), None)


async def getAllTasks(req_status: str):
    async with task_dict_lock:
        if req_status == "all":
            return list(task_dict.values())
        return [tk for tk in task_dict.values() if tk.status() == req_status]


def get_readable_file_size(size_in_bytes: int | str):
    if isinstance(size_in_bytes, str):
        size_in_bytes = int(size_in_bytes)
    if not size_in_bytes:
        return "0B"
    index = 0
    size = float(size_in_bytes)
    while size >= 1024 and index < len(SIZE_UNITS) - 1:
        size /= 1024
        index += 1
    return f"{size:.2f}{SIZE_UNITS[index]}"


def get_date_time(message: Message):
    dt = message.date.astimezone(timezone(config_dict["TIME_ZONE"]))
    return dt.strftime("%B %d, %Y"), dt.strftime("%H:%M:%S")


def get_readable_time(seconds):
    if not seconds or seconds < 0:
        return "0s"
    periods = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
    result = ""
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f"{int(period_value)}{period_name}"
    return result or "0s"


def speed_string_to_bytes(size_text: str):
    if not size_text:
        return 0
    size = 0
    size_text = size_text.lower().strip()
    try:
        if "k" in size_text:
            size = float(size_text.split("k")[0]) * 1024
        elif "m" in size_text:
            size = float(size_text.split("m")[0]) * 1048576
        elif "g" in size_text:
            size = float(size_text.split("g")[0]) * 1073741824
        elif "t" in size_text:
            size = float(size_text.split("t")[0]) * 1099511627776
        elif "b" in size_text:
            size = float(size_text.split("b")[0])
    except (ValueError, IndexError):
        size = 0
    return size


def get_progress_bar_string(pct: str):
    try:
        pct = float(str(pct).strip("%"))
    except (ValueError, AttributeError):
        pct = 0
    p = min(max(pct, 0), 100)
    cFull = int(p // 8.33)  # 12 blocks total
    p_str = "⬢" * cFull
    p_str += "⬡" * (12 - cFull)
    return f"❨{p_str}❩"


def action(message: Message):
    try:
        acts = message.text.split(maxsplit=1)[0]
        return (
            acts.replace("/", "#")
            .replace(f"@{bot_name}", "")
            .replace(str(config_dict["CMD_SUFFIX"]), "")
            .lower()
        )
    except (AttributeError, IndexError):
        return "unknown"


def get_status_mode(status: str):
    """Convert status to hashtag mode"""
    status_map = {
        MirrorStatus.STATUS_DOWNLOADING: "Download",
        MirrorStatus.STATUS_UPLOADING: "Upload",
        MirrorStatus.STATUS_CLONING: "Clone",
        MirrorStatus.STATUS_ARCHIVING: "Archive",
        MirrorStatus.STATUS_EXTRACTING: "Extract",
        MirrorStatus.STATUS_SPLITTING: "Split",
        MirrorStatus.STATUS_QUEUEDL: "QueueDL",
        MirrorStatus.STATUS_QUEUEUP: "QueueUL",
        MirrorStatus.STATUS_SEEDING: "Seed",
    }
    return status_map.get(
        status, status.replace("▼ ", "").replace("▲ ", "").replace("◎ ", "")
    )


def get_readable_message(
    sid: int, is_user: bool, page_no: int = 1, status: str = "All", page_step: int = 1
):
    msg = f'<b><a href="https://t.me/zxzonehubupdates">Bot Of ZxZone</a></b>\n'

    dl_speed = up_speed = 0

    if status == "All":
        tasks = (
            [tk for tk in task_dict.values() if tk.listener.user_id == sid]
            if is_user
            else list(task_dict.values())
        )
    elif is_user:
        tasks = [
            tk
            for tk in task_dict.values()
            if tk.status() == status and tk.listener.user_id == sid
        ]
    else:
        tasks = [tk for tk in task_dict.values() if tk.status() == status]

    STATUS_LIMIT = config_dict["STATUS_LIMIT"]
    tasks_no = len(tasks)
    pages = (max(tasks_no, 1) + STATUS_LIMIT - 1) // STATUS_LIMIT
    if page_no > pages:
        page_no = (page_no - 1) % pages + 1
    elif page_no < 1:
        page_no = pages - (abs(page_no) % pages)
    start_position = (page_no - 1) * STATUS_LIMIT

    for index, task in enumerate(
        tasks[start_position : STATUS_LIMIT + start_position], start=1
    ):
        tstatus = task.status()
        full_name = str(task.name())

        # Smart truncate filename
        if len(full_name) > 70:
            task_name = escape(f"{full_name[:65]}...")
        else:
            task_name = escape(full_name) or "N/A"

        # Task header with link if available
        if task.listener.isSuperChat:
            reply_to = task.listener.message.reply_to_message
            link = (
                task.listener.message.link
                if not reply_to or getattr(reply_to.from_user, "is_bot", None)
                else reply_to.link
            )
            msg += (
                f'\n<b>{index + start_position}.</b> <a href="{link}">{task_name}</a>\n'
            )
        else:
            msg += f"\n<b>{index + start_position}.</b> {task_name}\n"

        # User info
        username = task.listener.message.from_user.username
        first_name = task.listener.message.from_user.first_name or "NoNameUser"
        user_id = task.listener.message.from_user.id

        if username:
            msg += f'<b>Task By: <a href="https://t.me/{username}">{first_name}</a> » ({user_id})\n'
        else:
            msg += f'<b>Task By: <a href="tg://user?id={user_id}">{first_name}</a></b> » ({user_id})\n'
        #   msg += f'{first_name}  ({user_id})\n'

        msg += "╭"

        if tstatus not in [
            MirrorStatus.STATUS_SEEDING,
            MirrorStatus.STATUS_METADATA,
            MirrorStatus.STATUS_SUBSYNC,
        ]:
            progress_str = get_progress_bar_string(task.progress())
            msg += f"{progress_str} {task.progress()}\n"

            msg += f"├<b>Processed »</b> {task.processed_bytes()}\n"
            msg += f"├<b>Total »</b> {task.size()}\n"
            msg += f"├<b>Status »</b> {get_status_mode(tstatus)}\n"
            msg += f"├<b>Speed »</b> {task.speed()}\n"

            # Calculate elapsed and ETA
            elapsed = task.elapsed() or "0s"
            eta = task.eta() or "0s"
            total_time = (
                get_readable_time(
                    speed_string_to_bytes(
                        elapsed.replace("s", "")
                        .replace("m", "")
                        .replace("h", "")
                        .replace("d", "")
                    )
                    + speed_string_to_bytes(
                        eta.replace("s", "")
                        .replace("m", "")
                        .replace("h", "")
                        .replace("d", "")
                    )
                )
                if elapsed != "0s" and eta != "0s"
                else f"{elapsed}"
            )

            msg += f"├<b>Time »</b> {elapsed} of {total_time} ( {eta} )\n"

            # Engine info
            engine = task.engine() if hasattr(task, "engine") else "Unknown"
            msg += f"├<b>Engine »</b> {engine}\n"

            # UPDATED: In Mode and Out Mode from second code
            # In Mode - Extract from listener.mode if available, otherwise use action
            if hasattr(task.listener, "mode") and task.listener.mode:
                in_mode = task.listener.mode[0]
            else:
                in_mode = action(task.listener.message).replace("#", "").title()
            msg += f"├<b>In Mode »</b> #{in_mode}\n"

            # Out Mode - Extract from listener.mode if available, otherwise check isLeech/upDest
            if (
                hasattr(task.listener, "mode")
                and task.listener.mode
                and len(task.listener.mode) > 1
            ):
                out_mode = task.listener.mode[1]
            else:
                if task.listener.isLeech:
                    out_mode = "Leech"
                elif hasattr(task.listener, "upDest"):
                    out_mode = task.listener.upDest or "Drive"
                else:
                    out_mode = "Drive"
            msg += f"├<b>Out Mode »</b> #{out_mode}\n"

            if tstatus == MirrorStatus.STATUS_SPLITTING and task.listener.isLeech:
                msg += f"├<b>Split »</b> {get_readable_file_size(task.listener.splitSize)}\n"

            if tstatus == MirrorStatus.STATUS_WAIT:
                msg += f"├<b>Timeout »</b> {task.timeout()}\n"

            if hasattr(task, "seeders_num"):
                try:
                    msg += f"├<b>S/L »</b> {task.seeders_num()}/{task.leechers_num()}\n"
                except:
                    pass

        elif tstatus == MirrorStatus.STATUS_SEEDING:
            msg += f"\n├<b>Size »</b> {task.size()}\n"
            msg += f"├<b>Speed »</b> {task.upload_speed()}\n"
            msg += f"├<b>Uploaded »</b> {task.uploaded_bytes()}\n"
            msg += f"├<b>Ratio »</b> {task.ratio()}\n"
            msg += f"├<b>Time »</b> {task.seeding_time()}\n"
            msg += f"├<b>S/L »</b> {task.seeders_num()}/{task.leechers_num()}\n"
            msg += f"├<b>Engine »</b> {task.engine()}\n"
        else:
            msg += f"\n├<b>Size »</b> {task.size()}\n"
            msg += f"├<b>Elapsed »</b> {task.elapsed() or '~'}\n"
            msg += f"├<b>Engine »</b> {task.engine()}\n"

        msg += (
            f"<i>╰Stop »</i> "
            f"<code>/{BotCommands.CancelTaskCommand} {task.gid()}</code>\n"
        )

    if not tasks:
        if status == "All":
            return None, None
        msg += f"<b>No Active {status} Tasks!</b>\n"

    # Calculate speeds
    for task in tasks:
        tstatus = task.status()
        if tstatus == MirrorStatus.STATUS_DOWNLOADING or (
            hasattr(task, "engine") and task.engine() == "JDownloader"
        ):
            dl_speed += speed_string_to_bytes(task.speed())
        elif tstatus == MirrorStatus.STATUS_UPLOADING:
            up_speed += speed_string_to_bytes(task.speed())
        elif tstatus == MirrorStatus.STATUS_SEEDING:
            up_speed += speed_string_to_bytes(task.upload_speed())

    # System stats footer
    cpu = cpu_percent()
    ram = virtual_memory().percent
    free_disk = get_readable_file_size(disk_usage(config_dict["DOWNLOAD_DIR"]).free)
    disk_percent = disk_usage(config_dict["DOWNLOAD_DIR"]).percent
    uptime = get_readable_time(time() - botStartTime)

    msg += "\n<b>⌬BOT STATS</b>\n"
    msg += f"╭<b>CPU »</b> {cpu}%\n"
    msg += f"├<b>FREE »</b> {free_disk} [{disk_percent}%]\n"
    msg += f"├<b>RAM »</b> {ram}%\n"
    msg += f"╰<b>UP »</b> {uptime}\n"
    if pages > 1:
        msg += f"<b>Task:</b> {tasks_no} | <b>Page:</b> {page_no}/{pages}\n"

    # Buttons
    buttons = ButtonMaker()
    buttons.button_data("☲", "status 0 ov", "header")

    if pages > 1:
        buttons.button_data("⊴", f"status {sid} pre", "header")
        buttons.button_data("⊵", f"status {sid} nex", "header")

    buttons.button_data("♻️", f"status {sid} ref", "header")

    return msg, buttons.build_menu(6)
