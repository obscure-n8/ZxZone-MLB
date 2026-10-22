from __future__ import annotations
from google.oauth2 import service_account
from googleapiclient.discovery import build
from os import path as ospath, listdir
from pickle import load as pload
from random import randrange
from re import search as re_search
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)
from urllib.parse import parse_qs, urlparse

from bot import config_dict, user_data, LOGGER
from bot.helper.ext_utils.links_utils import is_gdrive_id


class GoogleDriveHelper:
    def __init__(self):
        self._OAUTH_SCOPE = ["https://www.googleapis.com/auth/drive"]
        self.token_path = "token.pickle"
        self.G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.G_DRIVE_BASE_DOWNLOAD_URL = (
            "https://drive.google.com/uc?id={}&export=download"
        )
        self.G_DRIVE_DIR_BASE_DOWNLOAD_URL = "https://drive.google.com/drive/folders/{}"
        self.is_uploading = False
        self.is_downloading = False
        self.is_cloning = False
        self.is_cancelled = False
        self.sa_index = 0
        self.sa_count = 1
        self.sa_number = 100
        self.alt_auth = False
        self.service = None
        self.total_files = 0
        self.total_folders = 0
        self.file_processed_bytes = 0
        self.proc_bytes = 0
        self.total_time = 0
        self.status = None
        self.update_interval = 3
        self.use_sa = config_dict["USE_SERVICE_ACCOUNTS"]

    @property
    def speed(self):
        try:
            return self.proc_bytes / self.total_time
        except:
            return 0

    @property
    def processed_bytes(self):
        return self.proc_bytes

    async def progress(self):
        if self.status is not None:
            chunk_size = (
                self.status.total_size * self.status.progress()
                - self.file_processed_bytes
            )
            self.file_processed_bytes = self.status.total_size * self.status.progress()
            self.proc_bytes += chunk_size
            self.total_time += self.update_interval

    def authorize(self):
        credentials = None
        if self.use_sa:
            json_files = listdir("accounts")
            self.sa_number = len(json_files)
            self.sa_index = randrange(self.sa_number)
            LOGGER.info(
                "Authorizing with %s service account", json_files[self.sa_index]
            )
            credentials = service_account.Credentials.from_service_account_file(
                f"accounts/{json_files[self.sa_index]}", scopes=self._OAUTH_SCOPE
            )
        elif ospath.exists(self.token_path):
            if self.token_path.startswith("tokens/"):
                user_id = getattr(getattr(self, "listener", None), "user_id", None)
                if user_id != config_dict["OWNER_ID"] and not user_data.get(
                    user_id, {}
                ).get("is_sudo"):
                    raise PermissionError(
                        "User token authorization is restricted to sudo users."
                    )
            LOGGER.info("Authorize with %s", self.token_path)
            with open(self.token_path, "rb") as f:
                credentials = pload(f)
        else:
            LOGGER.error("Token.pickle not found!")
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    def switchServiceAccount(self):
        if self.sa_index == self.sa_number - 1:
            self.sa_index = 0
        else:
            self.sa_index += 1
        self.sa_count += 1
        LOGGER.info("Switching to %s index", self.sa_index)
        self.service = self.authorize()

    def getIdFromUrl(self, link: str, user_id: int = ""):
        use_sa = user_data.get(user_id, {}).get("use_sa")
        user_token = f"tokens/{user_id}.pickle"
        if (
            user_id
            and link.startswith("mtp:")
            or (
                hasattr(self, "listener")
                and getattr(self.listener, "privateLink", None)
            )
            and not use_sa
        ):
            self.use_sa = False
            self.token_path = user_token
            link = link.replace("mtp:", "", 1)
        elif link.startswith("sa:") or use_sa:
            self.use_sa = True
            link = link.replace("sa:", "", 1)
        elif link.startswith("tp:"):
            self.use_sa = False
            link = link.replace("tp:", "", 1)
        if not ospath.exists(self.token_path) and ospath.exists(user_token):
            self.token_path = user_token
        if is_gdrive_id(link):
            return link
        if "folders" in link or "file" in link:
            regex = r"https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)"
            res = re_search(regex, link)
            if res is None:
                raise IndexError("G-Drive ID not found.")
            return res.group(3)
        parsed = urlparse(link)
        return parse_qs(parsed.query)["id"][0]

    @retry(
        wait=wait_exponential(multiplier=2, min=3, max=6),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    def set_permission(self, file_id):
        permissions = {
            "role": "reader",
            "type": "anyone",
            "value": None,
            "withLink": True,
        }
        return (
            self.service.permissions()
            .create(fileId=file_id, body=permissions, supportsAllDrives=True)
            .execute()
        )

    @retry(
        wait=wait_exponential(multiplier=2, min=3, max=6),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    def getFileMetadata(self, file_id):
        return (
            self.service.files()
            .get(
                fileId=file_id,
                supportsAllDrives=True,
                fields="name, id, mimeType, size",
            )
            .execute()
        )

    @retry(
        wait=wait_exponential(multiplier=2, min=3, max=6),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    def getFilesByFolderId(self, folder_id, item_type=""):
        page_token = None
        files = []
        if not item_type:
            q = f"'{folder_id}' in parents and trashed = false"
        elif item_type == "folders":
            q = f"'{folder_id}' in parents and mimeType = '{self.G_DRIVE_DIR_MIME_TYPE}' and trashed = false"
        else:
            q = f"'{folder_id}' in parents and mimeType != '{self.G_DRIVE_DIR_MIME_TYPE}' and trashed = false"
        while True:
            response = (
                self.service.files()
                .list(
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    q=q,
                    spaces="drive",
                    pageSize=200,
                    fields="nextPageToken, files(id, name, mimeType, size, shortcutDetails)",
                    orderBy="folder, name",
                    pageToken=page_token,
                )
                .execute()
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if page_token is None:
                break
        return files

    @retry(
        wait=wait_exponential(multiplier=2, min=3, max=6),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    def create_directory(self, directory_name, dest_id):
        file_metadata = {
            "name": directory_name,
            "description": config_dict["GD_INFO"],
            "mimeType": self.G_DRIVE_DIR_MIME_TYPE,
        }
        if dest_id is not None:
            file_metadata["parents"] = [dest_id]
        file = (
            self.service.files()
            .create(body=file_metadata, supportsAllDrives=True)
            .execute()
        )
        file_id = file.get("id")
        if not config_dict["IS_TEAM_DRIVE"]:
            self.set_permission(file_id)
        LOGGER.info(
            "Created G-Drive Folder:\nName: %s\nID: %s", file.get("name"), file_id
        )
        return file_id

    @staticmethod
    def escapes(estr):
        chars = ["\\", """, """, r"\a", r"\b", r"\f", r"\n", r"\r", r"\t"]
        for char in chars:
            estr = estr.replace(char, f"\\{char}")
        return estr.strip()

    async def cancel_task(self):
        self.is_cancelled = True
        if self.is_downloading:
            LOGGER.info("Cancelling Download: %s", self.listener.name)
            await self.listener.onDownloadError("Download stopped by user!")
        elif self.is_cloning:
            LOGGER.info("Cancelling Clone: %s", self.listener.name)
            await self.listener.onUploadError(
                "Your clone has been stopped and cloned data has been deleted!"
            )
        elif self.is_uploading:
            LOGGER.info("Cancelling Upload: %s", self.listener.name)
            await self.listener.onUploadError(
                "Your upload has been stopped and uploaded data has been deleted!"
            )
