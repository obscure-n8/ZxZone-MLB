from __future__ import annotations

from aiofiles.os import path as aiopath, listdir
from aiohttp import ClientSession
from mimetypes import guess_type
from os import path as ospath
from requests import post as rpost
from requests_toolbelt import MultipartEncoder
from requests_toolbelt.multipart.encoder import MultipartEncoderMonitor
from time import time

from bot import config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.listeners import tasks_listener as task


class GoFileUploader:
    def __init__(self, listener: task.TaskListener):
        self._listener = listener
        self._temp_size = 0
        self._start_time = time()
        self._server = 2
        self._folderpathd = []
        self._is_dir = False
        self._token = config_dict["GOFILETOKEN"]
        self.is_cancelled = False
        self.uploaded_bytes = 0
        self._bytes_read = 0
        self._bytes_temp = 0

    @property
    def speed(self):
        try:
            return self.uploaded_bytes / (time() - self._start_time)
        except ZeroDivisionError:
            return 0

    def _callback(self, monitor, chunk=(1024 * 1024 * 30)):
        self._bytes_read += monitor.bytes_read
        self._bytes_temp += monitor.bytes_read
        if self._bytes_temp > chunk:
            self.uploaded_bytes = self._bytes_read + self._temp_size
            self._bytes_temp = 0

    async def _get_server(self):
        async with (
            ClientSession() as session,
            session.get("https://api.gofile.io/getServer", ssl=False) as r,
        ):
            server = (await r.json())["data"]["server"]
            server = int(server.split("e", maxsplit=1)[1])
            if server != 5:
                self._server = server
        LOGGER.info("GoFile running in server %s", self._server)

    async def _verify(self):
        async with (
            ClientSession() as session,
            session.get(
                f"https://api.gofile.io/getAccountDetails?token={self._token}&allDetails=true",
                ssl=False,
            ) as resp,
        ):
            if (await resp.json())["status"] == "ok":
                return True

    async def _create_folder(self, foldername, parentfolderid):
        LOGGER.info("Created Folder %s", foldername)
        data = {
            "folderName": foldername,
            "token": self._token,
            "parentFolderId": parentfolderid,
        }
        async with (
            ClientSession() as session,
            session.put(
                "https://api.gofile.io/createFolder", data=data, ssl=False
            ) as resp,
        ):
            res = await resp.json()
            if res["status"] == "ok":
                return res["data"]

    def _upload_file(self, file, parentfolderid):
        mpart = MultipartEncoder(
            fields={
                "file": (ospath.basename(file), open(file, "rb"), guess_type(file)),
                "token": self._token,
                "folderId": parentfolderid,
            }
        )
        monitor = MultipartEncoderMonitor(mpart, self._callback)
        resp = rpost(
            f"https://store{self._server}.gofile.io/uploadFile",
            data=monitor,
            headers={"Content-Type": monitor.content_type},
            timeout=60,
        ).json()
        self._temp_size = self.uploaded_bytes
        if resp["status"] == "ok":
            return resp["data"]["downloadPage"]

    async def _upload_folder(self, path, createdfolderid):
        self._folderpathd.append(createdfolderid)
        files = await listdir(path)
        for file in files:
            file_path = ospath.join(path, file)
            if await aiopath.isfile(file_path):
                dl_url = await sync_to_async(
                    self._upload_file, file_path, self._folderpathd[-1]
                )
                if len(file) == 1 and not self._listener.isGofile:
                    self._listener.isGofile = dl_url
            elif await aiopath.isdir(file_path):
                folder = await self._create_folder(file, self._folderpathd[-1])
                if not folder:
                    return
                if not self._listener.isGofile:
                    self._listener.isGofile = f"https://gofile.io/d/{folder['code']}"
                await self._upload_folder(file_path, folder["id"])
        del self._folderpathd[-1]

    async def goUpload(self):
        self._listener.isGofile = False
        if not await self._verify():
            return
        await self._get_server()
        file_path = ospath.join(self._listener.dir, self._listener.name)
        if await aiopath.isfile(file_path):
            self._listener.isGofile = await sync_to_async(
                self._upload_file, file_path, config_dict["GOFILEBASEFOLDER"]
            )
            return
        await self._upload_folder(file_path, config_dict["GOFILEBASEFOLDER"])

    async def cancel_task(self):
        self.is_cancelled = True
        LOGGER.info("Cancelling Upload: %s", self._listener.name)
        await self._listener.onUploadError("Upload stopped by user!")
