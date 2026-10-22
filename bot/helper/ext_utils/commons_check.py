from asyncio import gather
from pyrogram.errors import UserDeactivated
from pyrogram.types import Message
from time import time
from uuid import uuid4

from bot import bot_loop, bot_name, task_dict, task_dict_lock, config_dict, user_data
from bot.helper.ext_utils.bot_utils import (
    get_user_task,
    is_premium_user,
    is_pm_enabled,
    update_user_ldata,
    sync_to_async,
    UserDaily,
)
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendingMessage


class UseCheck:
    def __init__(self, message: Message, is_leech: bool = False):
        self._message = message
        self._is_leech = is_leech
        self._uid = message.from_user.id
        self._user_dict: dict = user_data.get(self._uid, {})
        self.isPremi = is_premium_user(self._uid)
        bot_loop.create_task(self._check_limit())

    async def run(
        self,
        limit=False,
        forpremi=False,
        daily=False,
        ml_chek=False,
        session=False,
        send_pm=False,
    ):
        msgs = []
        buttons = ButtonMaker()

        if msg := await self._force_sub(buttons):
            msgs.append(msg)
        if msg := await self._force_username():
            msgs.append(msg)
        if limit and (msg := await self._task_limiter()):
            msgs.append(msg)
        if forpremi and (msg := self._check_premium()):
            msgs.append(msg)
        if daily and (msg := await self._daily_limit()):
            msgs.append(msg)
        if ml_chek and (msg := self._check_ml()):
            msgs.append(msg)
        if session and (msg := await self._check_session(buttons)):
            msgs.append(msg)
        if (
            send_pm
            and is_pm_enabled(self._uid, self._user_dict)
            and self._message.chat.type.name in ["SUPERGROUP", "CHANNEL"]
            and (msg := await self._send_pm(buttons))
        ):
            msgs.append(msg)

        if msgs:
            return await sendingMessage(
                f"Hey there {self._message.from_user.mention}...\n\n" + "\n".join(msgs),
                self._message,
                config_dict["IMAGE_COMMONS_CHECK"],
                buttons.build_menu(2),
            )

    async def _send_pm(self, buttons):
        try:
            user = await self._message._client.get_users(self._uid)
            if user.status.name == "LONG_AGO":
                raise UserDeactivated("User is inactive!")
        except:
            buttons.button_link("Start PM", f"http://t.me/{bot_name}")
            return "⁍ I have no access to Private Message, "

    async def _force_username(self):
        if config_dict["FUSERNAME"]:
            uname = self._message.from_user.username
            if not uname:
                return "⁍ Set username: Go to <b>Settings</b> -> <b>My Account</b> -> <b>Username</b>."
            if self._user_dict.get("user_name", "") != uname:
                await update_user_ldata(
                    self._uid, "user_name", self._message.from_user.username
                )

    def _check_ml(self):
        if mode := str(config_dict["DISABLE_MIRROR_LEECH"]):
            if mode == "mirror" and not self._is_leech:
                return "⁍ Mirror mode has been disabled!"
            if mode == "leech" and self._is_leech:
                return "⁍ Leech mode has been disabled!"

    def _check_premium(self):
        if config_dict["PREMIUM_MODE"] and not self.isPremi:
            return "⁍ Feature only for <b>Premium User</b>!"

    async def _daily_limit(self):
        if (
            config_dict["DAILY_MODE"]
            and not self.isPremi
            and await UserDaily(self._uid).get_daily_limit()
        ):
            return f"⁍ Reach daily limit: ({config_dict['DAILY_LIMIT_SIZE']}GB), check ur status in /{BotCommands.UserSetCommand}"

    async def _check_session(self, buttons):
        if SESSION_TIMEOUT := config_dict["SESSION_TIMEOUT"]:
            if (
                config_dict["PREMIUM_MODE"]
                and self.isPremi
                or await CustomFilters.sudo("", self._message)
            ):
                return
            user_dict = user_data.get(self._uid, {})
            if (
                not (expire := user_dict.get("session_time"))
                or time() - expire > SESSION_TIMEOUT
            ):
                token = (
                    user_dict["session_token"]
                    if expire is None and "session_token" in user_dict
                    else str(uuid4())
                )
                if expire:
                    del user_dict["session_time"]
                await update_user_ldata(self._uid, "session_token", token)
                buttons.button_link(
                    "Get Session",
                    await sync_to_async(
                        short_url, f"https://t.me/{bot_name}?start={token}"
                    ),
                )
                return f"⁍ Session is exipred (renew every {get_readable_time(SESSION_TIMEOUT)}</i>)."

    async def _check_limit(self):
        if (
            config_dict["PREMIUM_MODE"]
            and self.isPremi
            and self._user_dict.get("premium_left", 0) - time() <= 0
        ):
            await gather(
                update_user_ldata(self._uid, "is_premium", False),
                update_user_ldata(self._uid, "premium_left", 0),
            )

        if (
            self._user_dict.get("is_sudo")
            and "sudo_left" in self._user_dict
            and self._user_dict["sudo_left"] - time() <= 0
        ):
            del user_data[self._uid]["sudo_left"]
            await update_user_ldata(self._uid, "is_sudo", False)

    async def _force_sub(self, buttons: ButtonMaker):
        if config_dict["FSUB"]:
            try:
                await self._message._client.get_chat_member(
                    config_dict["FSUB_CHANNEL_ID"], self._uid
                )
            except:
                CHANNEL_USERNAME = config_dict["CHANNEL_USERNAME"]
                buttons.button_link(
                    f"{config_dict['FSUB_BUTTON_NAME']}",
                    f"https://t.me/{CHANNEL_USERNAME}",
                )
                return f"⁍ You must join <a href='https://t.me/{CHANNEL_USERNAME}'>{CHANNEL_USERNAME}</a>."

    async def _task_limiter(self):
        if not self.isPremi:
            if USER_TASKS_LIMIT := config_dict["USER_TASKS_LIMIT"]:
                if await get_user_task(self._uid) >= USER_TASKS_LIMIT:
                    return f"⁍ Reached user task limit: {USER_TASKS_LIMIT} task!"
            if TOTAL_TASKS_LIMIT := config_dict["TOTAL_TASKS_LIMIT"]:
                async with task_dict_lock:
                    total_tasks = len(task_dict)
                if total_tasks >= TOTAL_TASKS_LIMIT:
                    return f"⁍ Reached total task limit: {TOTAL_TASKS_LIMIT} task!"
