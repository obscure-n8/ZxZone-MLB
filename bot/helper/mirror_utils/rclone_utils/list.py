from __future__ import annotations
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import wait_for, Event, wrap_future, gather
from configparser import ConfigParser
from functools import partial
from json import loads
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery
from time import time

from bot import config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import (
    cmd_exec,
    new_thread,
    new_task,
    update_user_ldata,
)
from bot.helper.ext_utils.status_utils import get_readable_time, get_readable_file_size
from bot.helper.listeners import tasks_listener as task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import editMessage

LIST_LIMIT = 6


class RcloneList:
    def __init__(self, listener: task.TaskListener):
        self._rc_user = False
        self._rc_owner = False
        self._sections = []
        self._time = time()
        self._timeout = 240
        self.listener = listener
        self.remote = ""
        self.is_cancelled = False
        self.query_proc = False
        self.processing = False
        self.item_type = "--dirs-only"
        self.event = Event()
        self.user_rcc_path = f"rclone/{self.listener.user_id}.conf"
        self.config_path = ""
        self.path = ""
        self.list_status = ""
        self.path_list = []
        self.iter_start = 0
        self.page_step = 1

    @new_thread
    async def _event_handler(self):
        pfunc = partial(path_updates, obj=self)
        handler = self.listener.client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^rcq") & user(self.listener.user_id)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=self._timeout)
        except:
            self.path = ""
            self.remote = "Timed Out. Task has been cancelled!"
            self.is_cancelled = True
            self.event.set()
        finally:
            self.listener.client.remove_handler(*handler)

    async def get_path_buttons(self):
        items_no = len(self.path_list)
        pages = (items_no + LIST_LIMIT - 1) // LIST_LIMIT
        if items_no <= self.iter_start:
            self.iter_start = 0
        elif self.iter_start < 0 or self.iter_start > items_no:
            self.iter_start = LIST_LIMIT * (pages - 1)
        page = (self.iter_start / LIST_LIMIT) + 1 if self.iter_start != 0 else 1
        buttons = ButtonMaker()
        for index, idict in enumerate(
            self.path_list[self.iter_start : LIST_LIMIT + self.iter_start]
        ):
            orig_index = index + self.iter_start
            if idict["IsDir"]:
                ptype = "fo"
                name = idict["Path"]
            else:
                ptype = "fi"
                name = f"[{get_readable_file_size(idict['Size'])}] {idict['Path']}"
            buttons.button_data(name, f"rcq pa {ptype} {orig_index}")
        if items_no > LIST_LIMIT:
            for i in [1, 2, 4, 6, 10, 30, 50, 100]:
                buttons.button_data(i, f"rcq ps {i}", "header")
            buttons.button_data("Prev", "rcq pre", "footer")
            buttons.button_data("Next", "rcq nex", "footer")
        if self.list_status == "rcd":
            if self.item_type == "--dirs-only":
                buttons.button_data("Files", "rcq itype --files-only", "footer")
            else:
                buttons.button_data("Folders", "rcq itype --dirs-only", "footer")
        if self.list_status == "rcu" or len(self.path_list) > 0:
            buttons.button_data("This Path", "rcq cur", "footer")
        if self.list_status == "rcu":
            buttons.button_data("Set as Default", "rcq def", position="footer")
        if self.path or len(self._sections) > 1 or self._rc_user and self._rc_owner:
            buttons.button_data("<<", "rcq back pa", "footer")
        if self.path:
            buttons.button_data("Root", "rcq root", "footer")
        buttons.button_data("Cancel", "rcq cancel", "footer")
        msg = "<b>Choose Path:</b>\n"
        if items_no > LIST_LIMIT:
            msg += (
                f"Page: <b>{int(page)}/{pages}</b> | Steps: <b>{self.page_step}</b>\n\n"
            )
        if self.list_status == "rcu":
            default_path = (
                self.listener.user_dict.get("rclone_path") or config_dict["RCLONE_PATH"]
            )
            msg += f"Default Path: {default_path}\n" if default_path else ""
        msg += (
            f"Items: <b>{items_no}</b>\n"
            f"Item Type: <b>{self.item_type}</b>\n"
            f"Transfer Type: <b>{'Download' if self.list_status == 'rcd' else 'Upload'}</b>\n"
            f"Config Path: <b>{self.config_path}</b>\n"
            f"Current Path: <code>{self.remote}{self.path}</code>\n\n"
            f"<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</i>"
        )
        await editMessage(msg, self.listener.editable, buttons.build_menu(f_cols=2))

    async def get_path(self, itype=""):
        self.processing = True
        if itype:
            self.item_type == itype
        elif self.list_status == "rcu":
            self.item_type == "--dirs-only"
        cmd = [
            "wzone",
            "lsjson",
            self.item_type,
            "--fast-list",
            "--no-mimetype",
            "--no-modtime",
            "--config",
            self.config_path,
            f"{self.remote}{self.path}",
        ]
        if self.is_cancelled:
            return
        res, err, code = await cmd_exec(cmd)
        if code not in [0, -9]:
            LOGGER.error(
                "While rclone listing. Path: %s%s. Stderr: %s",
                self.remote,
                self.path,
                err,
            )
            self.remote = err
            self.path = ""
            self.event.set()
            return
        self.processing = False
        result = loads(res)
        if len(result) == 0 and itype != self.item_type and self.list_status == "rcd":
            itype = (
                "--dirs-only" if self.item_type == "--files-only" else "--files-only"
            )
            self.item_type = itype
            return await self.get_path(itype)
        self.path_list = sorted(result, key=lambda x: x["Path"])
        self.iter_start = 0
        await self.get_path_buttons()

    async def list_remotes(self):
        config = ConfigParser()
        async with aiopen(self.config_path, "r") as f:
            contents = await f.read()
            config.read_string(contents)
        if config.has_section("combine"):
            config.remove_section("combine")
        self._sections = config.sections()
        if len(self._sections) == 1:
            self.remote = f"{self._sections[0]}:"
            await self.get_path()
        else:
            msg = (
                "Choose Rclone remote:\n"
                f"Transfer Type: <b>{'Download' if self.list_status == 'rcd' else 'Upload'}</b>\n"
                f"Config Path: <b>{self.config_path}</b>\n\n"
                f"<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}.</i>"
            )
            buttons = ButtonMaker()
            [
                buttons.button_data(remote, f"rcq re {remote}:")
                for remote in self._sections
            ]
            if self._rc_user and self._rc_owner:
                buttons.button_data("<<", "rcq back re", "footer")
            buttons.button_data("Cancel", "rcq cancel", "footer")
            await editMessage(msg, self.listener.editable, buttons.build_menu(2))

    async def list_config(self):
        if self._rc_user and self._rc_owner:
            msg = (
                "Choose Rclone remote:\n"
                f"Transfer Type: <b>{'Download' if self.list_status == 'rcd' else 'Upload'}</b>\n\n"
                f"<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}.</i>"
            )
            buttons = ButtonMaker()
            buttons.button_data("Owner Config", "rcq owner")
            buttons.button_data("My Config", "rcq user")
            buttons.button_data("Cancel", "rcq cancel")
            await editMessage(msg, self.listener.editable, buttons.build_menu(2))
        else:
            self.config_path = "rclone.conf" if self._rc_owner else self.user_rcc_path
            await self.list_remotes()

    async def back_from_path(self):
        if self.path:
            path = self.path.rsplit("/", 1)
            self.path = path[0] if len(path) > 1 else ""
            await self.get_path()
        elif len(self._sections) > 1:
            await self.list_remotes()
        else:
            await self.list_config()

    async def get_rclone_path(self, status, config_path=None):
        self.list_status = status
        future = self._event_handler()
        if config_path:
            self.config_path = config_path
            await self.list_remotes()
        else:
            self._rc_user, self._rc_owner = await gather(
                aiopath.exists(self.user_rcc_path), aiopath.exists("rclone.conf")
            )
            if not self._rc_owner and not self._rc_user:
                self.event.set()
                return f"Rclone config not exists! Upload your own <b>rclone.conf</b> on /{BotCommands.UserSetCommand}."
            await self.list_config()
        await wrap_future(future)
        if self.config_path != "rclone.conf" and not self.is_cancelled:
            return f"mrcc:{self.remote}{self.path}"
        return f"{self.remote}{self.path}"


@new_task
async def path_updates(_, query: CallbackQuery, obj: RcloneList):
    if obj.processing:
        await query.answer("On progress...")
        return
    data = query.data.split()
    if data[1] != "def":
        await query.answer()
    if data[1] == "cancel":
        obj.remote = "Task has been cancelled!"
        obj.path = ""
        obj.is_cancelled = True
        obj.event.set()
        return
    if obj.query_proc:
        return
    obj.query_proc = True
    match data[1]:
        case "pre":
            obj.iter_start -= LIST_LIMIT * obj.page_step
            await obj.get_path_buttons()
        case "nex":
            obj.iter_start += LIST_LIMIT * obj.page_step
            await obj.get_path_buttons()
        case "back":
            if data[2] == "re":
                await obj.list_config()
            else:
                await obj.back_from_path()
        case "re":
            # Some remotes has space
            data = query.data.split(maxsplit=2)
            obj.remote = data[2]
            await obj.get_path()
        case "pa":
            index = int(data[3])
            obj.path += (
                f"/{obj.path_list[index]['Path']}"
                if obj.path
                else obj.path_list[index]["Path"]
            )
            if data[2] == "fo":
                await obj.get_path()
            else:
                obj.event.set()
        case "ps":
            if obj.page_step == int(data[2]):
                return
            obj.page_step = int(data[2])
            await obj.get_path_buttons()
        case "root":
            obj.path = ""
            await obj.get_path()
        case "itype":
            obj.item_type = data[2]
            await obj.get_path()
        case "cur":
            obj.event.set()
        case "def":
            path = f"{obj.remote}{obj.path}"
            if (is_rcbot := obj.config_path == "rclone.conf") and not path.startswith(
                config_dict["RCLONE_PATH"]
            ):
                await query.answer(
                    f"Set default for bot rclone only to {config_dict['RCLONE_PATH']}!",
                    True,
                )
                return
            if not is_rcbot:
                path = f"mrcc:{path}"
            if path != obj.listener.user_dict.get("rclone_path"):
                await gather(
                    query.answer(),
                    update_user_ldata(obj.listener.user_id, "rclone_path", path),
                )
                await obj.get_path_buttons()
            else:
                await query.answer(f"Default rclone already {path}!", True)
        case "owner":
            obj.config_path = "rclone.conf"
            obj.path = ""
            obj.remote = ""
            await obj.list_remotes()
        case "user":
            obj.config_path = obj.user_rcc_path
            obj.path = ""
            obj.remote = ""
            await obj.list_remotes()
    obj.query_proc = False
