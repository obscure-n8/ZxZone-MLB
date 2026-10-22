from aiofiles.os import path as aiopath
from asyncio import wait_for, Event, wrap_future, gather
from functools import partial
from natsort import natsorted
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery
from tenacity import RetryError
from time import time

from bot import config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import new_thread, new_task, update_user_ldata
from bot.helper.ext_utils.status_utils import get_readable_file_size, get_readable_time
from bot.helper.mirror_utils.gdrive_utlis.helper import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import editMessage


LIST_LIMIT = 6


class gdriveList(GoogleDriveHelper):
    def __init__(self, listener):
        self.listener = listener
        self._token_user = False
        self._token_owner = False
        self._sa_owner = False
        self._time = time()
        self._timeout = 240
        self.drives = []
        self.query_proc = False
        self.processing = False
        self.item_type = "folders"
        self.event = Event()
        self.user_token_path = f"tokens/{self.listener.user_id}.pickle"
        self.id = ""
        self.parents = []
        self.list_status = ""
        self.items_list = []
        self.iter_start = 0
        self.page_step = 1
        super().__init__()

    @new_thread
    async def _event_handler(self):
        pfunc = partial(id_updates, obj=self)
        handler = self.listener.client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^gdq") & user(self.listener.user_id)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=self._timeout)
        except:
            self.id = "Timed Out. Task has been cancelled!"
            self.is_cancelled = True
            self.event.set()
        finally:
            self.listener.client.remove_handler(*handler)

    async def get_items_buttons(self):
        self.processing = True
        items_no = len(self.items_list)
        pages = (items_no + LIST_LIMIT - 1) // LIST_LIMIT
        if items_no <= self.iter_start:
            self.iter_start = 0
        elif self.iter_start < 0 or self.iter_start > items_no:
            self.iter_start = LIST_LIMIT * (pages - 1)
        page = (self.iter_start / LIST_LIMIT) + 1 if self.iter_start != 0 else 1
        buttons = ButtonMaker()
        for index, item in enumerate(
            self.items_list[self.iter_start : LIST_LIMIT + self.iter_start]
        ):
            orig_index = index + self.iter_start
            if item["mimeType"] == self.G_DRIVE_DIR_MIME_TYPE:
                ptype = "fo"
                name = item["name"]
            else:
                ptype = "fi"
                name = f"[{get_readable_file_size(float(item['size']))}] {item['name']}"
            buttons.button_data(name, f"gdq pa {ptype} {orig_index}")
        if items_no > LIST_LIMIT:
            for i in [1, 2, 4, 6, 10, 30, 50, 100]:
                buttons.button_data(i, f"gdq ps {i}", "header")
            buttons.button_data("<<", "gdq pre", "footer")
            buttons.button_data(">>", "gdq nex", "footer")
        if self.list_status == "gdd":
            if self.item_type == "folders":
                buttons.button_data("Files", "gdq itype files", "footer")
            else:
                buttons.button_data("Folders", "gdq itype folders", "footer")
        if self.list_status == "gdu" or len(self.items_list) > 0:
            buttons.button_data("This Path", "gdq cur", "footer")
        if self.list_status == "gdu":
            buttons.button_data("Set as Default", "gdq def", "footer")
        if (
            len(self.parents) > 1
            and len(self.drives) > 1
            or self._token_user
            and self._token_owner
        ):
            buttons.button_data("Back", "gdq back pa", "footer")
        if len(self.parents) > 1:
            buttons.button_data("Root", "gdq root", "footer")
        buttons.button_data("Cancel", "gdq cancel", "footer")
        button = buttons.build_menu(f_cols=2)
        msg = "<b>Choose Path:</b>\n\n"
        if items_no > LIST_LIMIT:
            msg += (
                f"Page: <b>{int(page)}/{pages}</b> | Step: <b>{self.page_step}</b>\n\n"
            )
        msg += f"Items: {items_no}\nTransfer Type: " + (
            "<b>Download</b>\n" if self.list_status == "gdd" else "<b>Upload</b>\n"
        )
        if self.list_status == "gdu":
            default_id = (
                self.listener.user_dict.get("gdrive_id") or config_dict["GDRIVE_ID"]
            )
            msg += f"Default GD ID: {default_id}\n" if default_id else ""
        msg += (
            f"Item Type: <b>{self.item_type}</b>\n"
            f"Token Path: <b>{self.token_path.strip()}</b>\n"
            f"Current ID: <code>{self.id}</code>\n"
            f"Current Path: <code>{('/').join(i['name'] for i in self.parents).strip()}</code>\n\n"
            f"<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</i>"
        )
        self.processing = False
        await editMessage(msg, self.listener.editable, button)

    async def get_items(self, itype=""):
        if itype:
            self.item_type == itype
        elif self.list_status == "gdu":
            self.item_type == "folders"
        try:
            files = self.getFilesByFolderId(self.id, self.item_type)
            if self.is_cancelled:
                return
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info("Total Attempts: %s", err.last_attempt.attempt_number)
                err = err.last_attempt.exception()
            err = str(err).replace(">", "").replace("<", "")
            self.id = ""
            self.event.set()
            return
        if len(files) == 0 and itype != self.item_type and self.list_status == "gdd":
            itype = "folders" if self.item_type == "files" else "files"
            self.item_type = itype
            return await self.get_items(itype)
        self.items_list = natsorted(files)
        self.iter_start = 0
        await self.get_items_buttons()

    async def list_drives(self):
        self.processing = True
        self.service = self.authorize()
        try:
            result = self.service.drives().list(pageSize="100").execute()
        except Exception as e:
            self.id = str(e)
            self.event.set()
            return
        drives = result["drives"]
        buttons = ButtonMaker()
        if len(drives) == 0 and not self.use_sa:
            self.drives = [{"id": "root", "name": "root"}]
            self.parents = [{"id": "root", "name": "root"}]
            self.id = "root"
            await self.get_items()
        elif len(drives) == 0:
            msg = "Service accounts Doesn't have access to any drive!"
            if self._token_user and self._token_owner:
                buttons.button_data("Back", "gdq back dr", "footer")
            buttons.button_data("Cancel", "gdq cancel", "footer")
            button = buttons.build_menu(2)
            await editMessage(msg, self.listener.editable, button)
        elif self.use_sa and len(drives) == 1:
            self.id = drives[0]["id"]
            self.drives = [{"id": self.id, "name": drives[0]["name"]}]
            self.parents = [{"id": self.id, "name": drives[0]["name"]}]
            await self.get_items()
        else:
            msg = "<b>Choose Drive:</b>\n"
            msg += "Transfer Type: " + (
                "<b>Download</b>\n" if self.list_status == "gdd" else "<b>Upload</b>\n"
            )
            msg += "Token Path: <b>{self.token_path.strip()}</b>\n\n"
            msg += (
                "<i>Timeout: {get_readable_time(self._timeout-(time()-self._time))}</i>"
            )
            self.drives.clear()
            self.parents.clear()
            if not self.use_sa:
                buttons.button_data("root", "gdq dr 0")
                self.drives = [{"id": "root", "name": "root"}]
            for index, item in enumerate(drives, start=1):
                self.drives.append({"id": item["id"], "name": item["name"]})
                buttons.button_data(item["name"], f"gdq dr {index}")
            if self._token_user and self._token_owner:
                buttons.button_data("Back", "gdq back dr", "footer")
            buttons.button_data("Cancel", "gdq cancel", "footer")
            self.processing = False
            button = buttons.build_menu(2)
            await editMessage(msg, self.listener.editable, button)

    async def choose_token(self):
        if (
            self._token_user
            and self._token_owner
            or self._sa_owner
            and self._token_owner
            or self._sa_owner
            and self._token_user
        ):
            msg = "<b>Choose Token:</b>\n"
            msg += "Transfer Type: " + (
                "<b>Download</b>\n" if self.list_status == "gdd" else "<b>Upload</b>\n"
            )
            msg += f"\n<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</i>"
            buttons = ButtonMaker()
            if self._token_owner:
                buttons.button_data("Owner Token", "gdq owner")
            if self._sa_owner:
                buttons.button_data("Service Accounts", "gdq sa")
            if self._token_user:
                buttons.button_data("My Token", "gdq user")
            buttons.button_data("Cancel", "gdq cancel")
            button = buttons.build_menu(2)
            await editMessage(msg, self.listener.editable, button)
        else:
            if self._token_owner:
                self.token_path = "token.pickle"
                self.use_sa = True
            elif self._token_user:
                self.token_path = self.user_token_path
                self.use_sa = True
            else:
                self.token_path = "accounts"
                self.use_sa = True
            await self.list_drives()

    async def get_pevious_id(self):
        if self.parents:
            self.parents.pop()
            if self.parents:
                self.id = self.parents[-1]["id"]
                await self.get_items()
            else:
                await self.list_drives()
        else:
            await self.list_drives()

    async def get_target_id(self, status, token_path=None):
        self.list_status = status
        future = self._event_handler()
        if not token_path:
            self._token_user, self._token_owner, self._sa_owner = await gather(
                aiopath.exists(self.user_token_path),
                aiopath.exists("token.pickle"),
                aiopath.exists("accounts"),
            )
            if not self._token_owner and not self._token_user and not self._sa_owner:
                self.event.set()
                return f"Token.pickle or service accounts not exists! Upload your own <b>token.pickle</b> on /{BotCommands.UserSetCommand}."
            await self.choose_token()
        else:
            self.token_path = token_path
            self.use_sa = self.token_path == "accounts"
            await self.list_drives()
        await wrap_future(future)
        if self.token_path == self.user_token_path and not self.is_cancelled:
            return f"mtp:{self.id}".replace(">", "").replace("<", "")
        return self.id.replace(">", "").replace("<", "")


@new_task
async def id_updates(_, query: CallbackQuery, obj: gdriveList):
    if obj.processing:
        await query.answer("On progress...")
        return
    data = query.data.split()
    if data[1] != "def":
        await query.answer()
    if data[1] == "cancel":
        obj.id = "Task has been cancelled!"
        obj.is_cancelled = True
        obj.event.set()
        return
    if obj.query_proc:
        return
    obj.query_proc = True
    match data[1]:
        case "pre":
            obj.iter_start -= LIST_LIMIT * obj.page_step
            await obj.get_items_buttons()
        case "nex":
            obj.iter_start += LIST_LIMIT * obj.page_step
            await obj.get_items_buttons()
        case "back":
            if data[2] == "dr":
                await obj.choose_token()
            else:
                await obj.get_pevious_id()
        case "dr":
            index = int(data[2])
            i = obj.drives[index]
            obj.id = i["id"]
            obj.parents = [{"id": i["id"], "name": i["name"]}]
            await obj.get_items()
        case "pa":
            index = int(data[3])
            i = obj.items_list[index]
            obj.id = i["id"]
            if data[2] == "fo":
                obj.parents.append({"id": i["id"], "name": i["name"]})
                await obj.get_items()
            else:
                obj.event.set()
        case "ps":
            if obj.page_step == int(data[2]):
                return
            obj.page_step = int(data[2])
            await obj.get_items_buttons()
        case "root":
            obj.id = obj.parents[0]["id"]
            obj.parents = [obj.parents[0]]
            await obj.get_items()
        case "itype":
            obj.item_type = data[2]
            await obj.get_items()
        case "cur":
            obj.event.set()
        case "def":
            id_ = obj.id if obj.token_path != obj.user_token_path else f"mtp:{obj.id}"
            if id_ != obj.listener.user_dict.get("gdrive_id"):
                await gather(
                    query.answer(),
                    update_user_ldata(obj.listener.user_id, "gdrive_id", id_),
                )
                await obj.get_items_buttons()
                return
            await query.answer(f"Default gdrive_path already {id_}!", True)
        case "owner":
            obj.token_path = "token.pickle"
            obj.use_sa = False
            obj.id = ""
            obj.parents = []
            await obj.list_drives()
        case "user":
            obj.token_path = obj.user_token_path
            obj.use_sa = False
            obj.id = ""
            obj.parents = []
            await obj.list_drives()
        case "sa":
            obj.token_path = "accounts"
            obj.use_sa = True
            obj.id = ""
            obj.parents = []
            await obj.list_drives()
    obj.query_proc = False
