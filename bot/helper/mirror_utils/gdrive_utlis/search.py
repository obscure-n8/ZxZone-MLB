from logging import getLogger
from time import time
from urllib.parse import quote as rquote

from bot import config_dict, user_data, DRIVES_NAMES, DRIVES_IDS, INDEX_URLS
from bot.helper.ext_utils.bot_utils import async_to_sync
from bot.helper.ext_utils.html_helper import hmtl_content
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.mirror_utils.gdrive_utlis.helper import GoogleDriveHelper
from bot.helper.telegram_helper.button_build import ButtonMaker


LOGGER = getLogger(__name__)


class gdSearch(GoogleDriveHelper):
    def __init__(self, stopDup=False, noMulti=False, isRecursive=True, itemType=""):
        super().__init__()
        self._stopDup = stopDup
        self._noMulti = noMulti
        self._isRecursive = isRecursive
        self._itemType = itemType

    def _drive_query(self, dirId, fileName, isRecursive):
        try:
            if isRecursive:
                if self._stopDup:
                    query = f"name = '{fileName}' and "
                else:
                    fileName = fileName.split()
                    query = "".join(
                        f"name contains '{name}' and "
                        for name in fileName
                        if name != ""
                    )
                    if self._itemType == "files":
                        query += f"mimeType != '{self.G_DRIVE_DIR_MIME_TYPE}' and "
                    elif self._itemType == "folders":
                        query += f"mimeType = '{self.G_DRIVE_DIR_MIME_TYPE}' and "
                query += "trashed = false"
                if dirId == "root":
                    return (
                        self.service.files()
                        .list(
                            q=f"{query} and 'me' in owners",
                            pageSize=200,
                            spaces="drive",
                            fields="files(id, name, mimeType, size, parents)",
                            orderBy="folder, name asc",
                        )
                        .execute()
                    )
                return (
                    self.service.files()
                    .list(
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                        driveId=dirId,
                        q=query,
                        spaces="drive",
                        pageSize=150,
                        fields="files(id, name, mimeType, size, teamDriveId, parents)",
                        corpora="drive",
                        orderBy="folder, name asc",
                    )
                    .execute()
                )

            if self._stopDup:
                query = f"'{dirId}' in parents and name = '{fileName}' and "
            else:
                query = f"'{dirId}' in parents and "
                fileName = fileName.split()
                for name in fileName:
                    if name != "":
                        query += f"name contains '{name}' and "
                if self._itemType == "files":
                    query += f"mimeType != '{self.G_DRIVE_DIR_MIME_TYPE}' and "
                elif self._itemType == "folders":
                    query += f"mimeType = '{self.G_DRIVE_DIR_MIME_TYPE}' and "
            query += "trashed = false"
            return (
                self.service.files()
                .list(
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    q=query,
                    spaces="drive",
                    pageSize=150,
                    fields="files(id, name, mimeType, size)",
                    orderBy="folder, name asc",
                )
                .execute()
            )
        except Exception as err:
            err = str(err).replace(">", "").replace("<", "")
            LOGGER.error(err)
            return {"files": []}

    def drive_list(self, fileName, target_id="", user_id="", style="html"):
        user_dict: dict = user_data.get(user_id, {})
        use_sa = user_dict.get("use_sa")
        if (
            target_id.startswith("mtp:")
            or target_id == user_dict.get("gdrive_id")
            and not use_sa
        ):
            drives = self.get_user_drive(target_id, user_id)
        elif target_id or use_sa:
            target_id = target_id.replace("tp:", "", 1)
            if target_id != config_dict["GDRIVE_ID"]:
                INDEX = user_dict["index_url"] if user_dict.get("index_url") else ""
                drives = [("User Choice", target_id, INDEX)]
            else:
                drives = [
                    ("From Owner", target_id, INDEX_URLS[0] if INDEX_URLS else "")
                ]
        else:
            drives = zip(DRIVES_NAMES, DRIVES_IDS, INDEX_URLS)
        msg = ""
        fileName = self.escapes(str(fileName))
        index, contents_count, contents_data = 1, 0, []
        Title = False
        if (
            not target_id.startswith("mtp:")
            and len(DRIVES_IDS) > 1
            and not use_sa
            or target_id.startswith("tp:")
        ):
            self.use_sa = False
        self.service = self.authorize()
        for drive_name, dir_id, index_url in drives:
            isRecur = (
                False if self._isRecursive and len(dir_id) > 23 else self._isRecursive
            )
            response = self._drive_query(dir_id, fileName, isRecur)
            if not response["files"]:
                if self._noMulti:
                    break
                continue
            if not Title:
                if style == "graph":
                    msg += f"<h4>Search Result For {fileName}</h4>"
                elif style == "html":
                    msg += (
                        '<span class="container center rfontsize">'
                        f"<h1>{config_dict['DRIVE_SEARCH_TITLE']}</h1><h4>Search Result For {fileName}</h4></span>"
                    )
                Title = True
            if drive_name:
                if style == "graph":
                    msg += (
                        f"╾────────────╼<br><b>{drive_name}</b><br>╾────────────╼<br>"
                    )
                elif style == "html":
                    msg += (
                        '<span class="container center rfontsize">'
                        f"<b>{drive_name}</b></span>"
                    )
            for file in response.get("files", []):
                mime_type = file.get("mimeType")
                if mime_type == "application/vnd.google-apps.folder":
                    furl = short_url(
                        f"https://drive.google.com/drive/folders/{file.get('id')}",
                        user_id,
                    )
                    match style:
                        case "tele":
                            msg += f"📁 <b>{file.get('name')}\n(folder)</b>\n<b><a href='{furl}'>Drive Link</a></b>"
                        case "graph":
                            msg += f"📁 <code>{file.get('name')}<br>(folder)</code><br><b><a href={furl}>Drive Link</a></b>"
                        case _:
                            msg += (
                                '<span class="container start rfontsize">'
                                f"<div>📁 {file.get('name')} (folder)</div>"
                                '<div class="dlinks">'
                                f'<span> <a class="btn btn-outline-primary btn-sm text-white" href="{furl}" target="_blank"><i class="fab fa-google-drive"></i> Drive Link</a></span>'
                            )
                    if index_url:
                        if isRecur:
                            url_path = "/".join(
                                [
                                    rquote(n, safe="")
                                    for n in self._get_recursive_list(file, dir_id)
                                ]
                            )
                        else:
                            url_path = rquote(f"{file.get('name')}", safe="")
                        url = short_url(f"{index_url}/{url_path}/", user_id)
                        if style in ["tele", "graph"]:
                            msg += f' <b>| <a href="{url}">Index Link</a></b>'
                        else:
                            msg += f'<span> <a class="btn btn-outline-primary btn-sm text-white" href="{url}" target="_blank"><i class="fas fa-bolt"></i> Index Link</a></span>'
                elif mime_type == "application/vnd.google-apps.shortcut":
                    furl = short_url(
                        f"https://drive.google.com/drive/folders/{file.get('id')}",
                        user_id,
                    )
                    if style in ["tele", "graph"]:
                        msg += f"⁍<a href='{furl}'>{file.get('name')}</a> (shortcut)"
                    else:
                        msg += (
                            '<span class="container start rfontsize">'
                            f"<div>📁 {file.get('name')} (shortcut)</div>"
                            '<div class="dlinks">'
                            f'<span> <a class="btn btn-outline-primary btn-sm text-white" href="{furl}" target="_blank"><i class="fab fa-google-drive"></i> Drive Link</a></span>'
                            "</div></span>"
                        )
                else:
                    furl = short_url(
                        f"https://drive.google.com/uc?id={file.get('id')}&export=download",
                        user_id,
                    )
                    match style:
                        case "tele":
                            msg += f"📄 <b>{file.get('name')}\n({get_readable_file_size(int(file.get('size', 0)))})</b>\n<b><a href='{furl}'>Drive Link</a></b>"
                        case "graph":
                            msg += f"📄 <code>{file.get('name')}<br>({get_readable_file_size(int(file.get('size', 0)))})</code><br><b><a href={furl}>Drive Link</a></b>"
                        case _:
                            msg += (
                                '<span class="container start rfontsize">'
                                f"<div>📄 {file.get('name')} ({get_readable_file_size(int(file.get('size', 0)))})</div>"
                                '<div class="dlinks">'
                                f'<span> <a class="btn btn-outline-primary btn-sm text-white" href="{furl}" target="_blank"><i class="fab fa-google-drive"></i> Drive Link</a></span>'
                            )
                    if index_url:
                        if isRecur:
                            url_path = "/".join(
                                rquote(n, safe="")
                                for n in self._get_recursive_list(file, dir_id)
                            )
                        else:
                            url_path = rquote(f"{file.get('name')}")
                        url = short_url(f"{index_url}/{url_path}", user_id)
                        if style in ["tele", "graph"]:
                            msg += f' <b>| <a href="{url}">Index Link</a></b>'
                        else:
                            msg += f'<span> <a class="btn btn-outline-primary btn-sm text-white" href="{url}" target="_blank"><i class="fas fa-bolt"></i> Index Link</a></span>'
                        if config_dict["VIEW_LINK"]:
                            urlv = short_url(f"{index_url}/{url_path}?a=view", user_id)
                            if style in ["tele", "graph"]:
                                msg += f' <b>| <a href="{urlv}">View Link</a></b>'
                            else:
                                msg += f'<span> <a class="btn btn-outline-primary btn-sm text-white" href="{urlv}" target="_blank"><i class="fas fa-globe"></i> View Link</a></span>'
                match style:
                    case "tele":
                        msg += "\n\n"
                    case "graph":
                        msg += "<br><br>"
                    case _:
                        msg += "</div></span>"

                contents_count += 1
                if style == "tele":
                    contents_data.append(f"{str(index).zfill(3)}. {msg}")
                    msg = ""
                elif style == "graph":
                    if len(msg.encode("utf-8")) > 39000:
                        contents_data.append(msg)
                        msg = ""
                index += 1
            if self._noMulti:
                break
        if style == "graph":
            if msg != "":
                contents_data.append(msg)
            if not contents_data:
                return "", None
            path = [
                async_to_sync(
                    telegraph.create_page, config_dict["DRIVE_SEARCH_TITLE"], content
                )["path"]
                for content in contents_data
            ]
            if len(path) > 1:
                async_to_sync(telegraph.edit_telegraph, path, contents_data)
        if contents_count == 0:
            return contents_count, ""
        if style == "tele":
            return contents_count, contents_data
        if style == "graph":
            buttons = ButtonMaker()
            buttons.button_link("View", f"https://telegra.ph/{path[0]}")
            return contents_count, buttons.build_menu(1)
        f_name = f"{fileName}_{time()}.html"
        with open(f_name, "w", encoding="utf-8") as f:
            f.write(hmtl_content.replace("{fileName}", fileName).replace("{msg}", msg))
        return contents_count, f_name

    def get_user_drive(self, target_id, user_id):
        dest_id = target_id.replace("mtp:", "", 1)
        self.token_path = f"tokens/{user_id}.pickle"
        self.use_sa = False
        user_dict = user_data.get(user_id, {})
        INDEX = user_dict["index_url"] if user_dict.get("index_url") else ""
        return [("User Choice", dest_id, INDEX)]
