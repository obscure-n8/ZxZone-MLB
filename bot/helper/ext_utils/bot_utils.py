from aiohttp import ClientSession
from asyncio import (
    create_subprocess_shell,
    create_subprocess_exec,
    run_coroutine_threadsafe,
    gather,
    sleep,
)
from asyncio.subprocess import PIPE
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from hmac import new as hmac_new
from os import environ
from pyrogram.types import Message
from re import search as re_search, compile as re_compile, escape
from time import time

from bot import (
    bot,
    bot_loop,
    task_dict,
    task_dict_lock,
    user_data,
    config_dict,
    DATABASE_URL,
)
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.telegram_helper.button_build import ButtonMaker


THREADPOOL = ThreadPoolExecutor(max_workers=1000)


class setInterval:
    def __init__(self, interval, action, *args, **kwargs):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(self._set_interval(*args, **kwargs))

    async def _set_interval(self, *args, **kwargs):
        while True:
            await sleep(self.interval)
            await self.action(*args, **kwargs)

    def cancel(self):
        self.task.cancel()


class UserDaily:
    def __init__(self, user_id):
        self._user_id = user_id

    async def get_daily_limit(self):
        await self._check_status()
        return (
            user_data[self._user_id]["daily_limit"]
            >= config_dict["DAILY_LIMIT_SIZE"] * 1024**3
        )

    async def set_daily_limit(self, size):
        await self._check_status()
        data = user_data[self._user_id]["daily_limit"] + size
        await update_user_ldata(self._user_id, "daily_limit", data)

    async def _check_status(self):
        user = user_data.get(self._user_id, {})
        if (
            not user.get("daily_limit")
            or (user.get("reset_limit", 0) or 0) - time() <= 0
        ):
            await self._reset()

    async def _reset(self):
        await gather(
            update_user_ldata(self._user_id, "daily_limit", 1),
            update_user_ldata(self._user_id, "reset_limit", time() + 86400),
        )


def selection_pincode(id_: str) -> str:
    """Return a stable four-digit code that is not derived from the public ID."""
    secret = config_dict.get("WEB_SECRET") or config_dict.get("BOT_TOKEN")
    secret = secret or environ.get("WEB_SECRET") or environ.get("BOT_TOKEN", "")
    digest = hmac_new(
        secret.encode("utf-8"), str(id_).encode("utf-8"), "sha256"
    ).hexdigest()
    return f"{int(digest[:8], 16) % 10000:04d}"


def bt_selection_buttons(id_: str):
    gid = id_[:12] if len(id_) > 20 else id_
    pincode = selection_pincode(id_)
    buttons = ButtonMaker()
    BASE_URL = config_dict["BASE_URL"]
    if config_dict["WEB_PINCODE"]:
        buttons.button_link("Select Files", f"{BASE_URL}/app/files/{id_}")
        buttons.button_data("Pincode", f"btsel pin {gid} {pincode}")
    else:
        buttons.button_link(
            "Select Files", f"{BASE_URL}/app/files/{id_}?pin_code={pincode}"
        )
    buttons.button_data("Done Selecting", f"btsel done {gid} {id_}")
    buttons.button_data("Cancel", f"btsel canc {gid} {id_}")
    return buttons.build_menu(2)


async def get_user_task(user_id: int):
    async with task_dict_lock:
        uid_count = sum(task.listener.user_id == user_id for task in task_dict.values())
    return uid_count


def presuf_remname_name(user_dict: dict, name: str):
    if name:
        prename = user_dict.get("prename", "")
        sufname = user_dict.get("sufname", "")
        remname = user_dict.get("remname", "")
        LEECH_FILENAME_PREFIX = config_dict["LEECH_FILENAME_PREFIX"]

        name = f"{prename} {name}".strip()
        if sufname and "." in name:
            fname, ext = name.rsplit(".", maxsplit=1)
            name = f"{fname} {sufname}.{ext}"

        name = f"{LEECH_FILENAME_PREFIX} {name}".strip()
        if remname:
            remname_regex = re_compile("|".join(map(escape, remname.split("|"))))
            name = remname_regex.sub("", name)

    return name


def is_premium_user(user_id: int):
    user_dict = user_data.get(user_id, {})
    return (
        user_id == config_dict["OWNER_ID"]
        or (config_dict["PREMIUM_MODE"] and user_dict.get("is_premium"))
        or user_dict.get("is_sudo")
    )


def is_pm_enabled(user_id: int, user_dict: dict | None = None):
    user_dict = user_dict if user_dict is not None else user_data.get(user_id, {})
    return bool(config_dict["BOT_PM"] or user_dict.get("enable_pm"))


async def default_button(message: Message):
    try:
        message = await bot.get_messages(message.chat.id, message.id)
    except:
        pass
    else:
        del message.reply_markup.inline_keyboard[-1]

    return (
        message.reply_markup
        if getattr(message.reply_markup, "inline_keyboard", None)
        else None
    )


def getSizeBytes(size):
    size = size.lower()
    unit_to_factor = {"mb": 1048576, "gb": 1073741824}
    for unit, factor in unit_to_factor.items():
        if size.endswith(unit):
            size = float(size[: -len(unit)]) * factor
            return int(size)
    return 0


async def get_content_type(url):
    try:
        async with (
            ClientSession() as session,
            session.get(url, allow_redirects=True, ssl=False) as response,
        ):
            return response.headers.get("Content-Type"), response.headers.get(
                "Content-Length"
            )
    except:
        return "", ""


def arg_parser(items, arg_base):
    if not items:
        return arg_base
    bool_arg_set = ["-b", "-e", "-z", "-s", "-j", "-d", "-gf", "-vt", "-sv", "-ss"]
    i, t = 0, len(items)
    while i + 1 <= t:
        part = items[i].strip()
        if part in arg_base:
            if (
                i + 1 == t
                and part in bool_arg_set
                or part in ["-s", "-j", "-gf", "-vt"]
            ):
                arg_base[part] = True
            else:
                sub_list = []
                for j in range(i + 1, t):
                    item = items[j].strip()
                    if item in arg_base:
                        if part in bool_arg_set and not sub_list:
                            arg_base[part] = True
                        break
                    sub_list.append(item.strip())
                    i += 1
                if sub_list:
                    arg_base[part] = " ".join(sub_list)
        i += 1

    if items[0] not in arg_base:
        index_link = next(
            (i for i, part in enumerate(items) if part in arg_base), len(items)
        )
        link = items[:index_link] if index_link else items[:]
        link = " ".join(link).strip()
        pattern = r"https?:\/\/(www.)?\S+\.?[a-z]{2,6}\b(\S*)|magnet:\?xt=urn:(btih|btmh):[-a-zA-Z0-9@:%_\+.~#?&//=]*\s*"
        if match := re_search(pattern, link):
            link = match.group()
        arg_base["link"] = link
    return arg_base


async def update_user_ldata(id_: int, key: str, value):
    user_data.setdefault(id_, {})[key] = value
    if DATABASE_URL and key not in ["thumb", "rclone_config", "token_pickle"]:
        await DbManager().update_user_data(id_)


async def retry_function(attempt, func, *args, **kwargs):
    while attempt < 5:
        try:
            return await sync_to_async(func, *args, **kwargs)
        except:  # Consider specifying the exception if possible
            await sleep(0.3)
            attempt += 1
    raise Exception(
        f"Failed to execute {func.__name__}, reached max total attempts {attempt}x!"
    )


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    return stdout.decode().strip(), stderr.decode().strip(), proc.returncode


def new_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return bot_loop.create_task(func(*args, **kwargs))

    return wrapper


async def sync_to_async(func, *args, wait=True, **kwargs):
    """Run sync function in async coroutine"""
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future


def async_to_sync(func, *args, wait=True, **kwargs):
    """Run Async function in sync"""
    future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
    return future.result() if wait else future


def new_thread(func):
    @wraps(func)
    def wrapper(*args, wait=False, **kwargs):
        future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
        return future.result() if wait else future

    return wrapper
