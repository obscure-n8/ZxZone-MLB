import os
from aiofiles.os import listdir, path as aiopath
from json import dump
from random import randint
from re import search as re_search, I
from time import sleep

from bot import bot, config_dict, jd_lock, LOGGER, FFMPEG_NAME
from bot.helper.ext_utils.bot_utils import cmd_exec, new_task, sync_to_async
from myjd import Myjdapi
from myjd.exception import (
    MYJDException,
    MYJDAuthFailedException,
    MYJDEmailForbiddenException,
    MYJDEmailInvalidException,
    MYJDErrorEmailNotConfirmedException,
)

os.makedirs("/JDownloader/cfg/", exist_ok=True)


class JDownloader(Myjdapi):
    def __init__(self):
        super().__init__()
        self._username = ""
        self._password = ""
        self._device_name = ""
        self.error = "JDownloader Credentials not provided!"
        self.device = None
        self.set_app_key("mltb")

    @new_task
    async def initiate(self):
        self.device = None
        async with jd_lock:
            is_connected = await sync_to_async(self.jdconnect)
            if is_connected:
                self.boot()
                await sync_to_async(self.connectToDevice)

    @new_task
    async def boot(self, retry=0):
        await cmd_exec(["pkill", "-9", "-f", "java"])
        self.device = None
        self.error = "Connecting... Try agin after couple of seconds"
        bot_name = bot.me.username
        self._device_name = f"{bot_name.replace(re_search(r'(bot|_bot)$', bot_name, I).group(), '_')}{randint(0, 100)}"
        if (
            await aiopath.exists("/JDownloader/logs")
            and len(await listdir("/JDownloader/logs")) > 2
        ):
            LOGGER.info("Starting JDownloader... This might take up to 5 sec")
        else:
            LOGGER.info(
                "Starting JDownloader... This might take up to 15 sec and might restart once after build!"
            )
        jdata = {
            "autoconnectenabledv2": True,
            "password": config_dict["JD_PASS"],
            "devicename": self._device_name,
            "email": config_dict["JD_EMAIL"],
        }
        ffdata = {
            "binarypath": f"/usr/bin/{FFMPEG_NAME}",
            "binarypathprobe": "/usr/bin/ffprobe",
        }
        jdsetpath = "/JDownloader/cfg/org.jdownloader.api.myjdownloader.MyJDownloaderSettings.json"
        jdffpath = (
            "/JDownloader/cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.json"
        )
        with open(jdsetpath, "w") as sf, open(jdffpath, "w") as ff:
            sf.truncate(0), ff.truncate(0)
            dump(jdata, sf), dump(ffdata, ff)
        cmd = "java -Dsun.jnu.encoding=UTF-8 -Dfile.encoding=UTF-8 -Djava.awt.headless=true -jar /JDownloader/JDownloader.jar"
        _, stdrerr, code = await cmd_exec(cmd, shell=True)
        if code != -9:
            if retry < 10:
                self.boot(retry + 1)
            else:
                self.error = "Failed to start JDownloader!"
                LOGGER.error(stdrerr)

    def jdconnect(self):
        jd_email, jd_pass = config_dict["JD_EMAIL"], config_dict["JD_PASS"]
        if not jd_email or not jd_pass:
            return False
        try:
            self.connect(jd_email, jd_pass)
            LOGGER.info("JDownloader is connected to account!")
            return True
        except (
            MYJDAuthFailedException,
            MYJDEmailForbiddenException,
            MYJDEmailInvalidException,
            MYJDErrorEmailNotConfirmedException,
        ) as err:
            self.error = f"{err}".strip()
            LOGGER.info("Failed to connect with jdownloader!ERROR: %s", self.error)
            self.device = None
            return False
        except MYJDException as e:
            self.error = f"{e}".strip()
            LOGGER.info(
                "Failed to connect with jdownloader! Retrying... ERROR: %s", self.error
            )
            sleep(10)
            return self.jdconnect()

    def connectToDevice(self):
        self.error = "Connecting to device..."
        while True:
            self.device = None
            if not config_dict["JD_EMAIL"] or not config_dict["JD_PASS"]:
                return
            try:
                self.update_devices()
                if not (devices := self.list_devices()):
                    continue
                for device in devices:
                    if self._device_name == device["name"]:
                        self.device = self.get_device(f"{self._device_name}")
                        break
                else:
                    continue
            except:
                continue
            break
        self.device.enable_direct_connection()
        self.error = ""
        LOGGER.info("JDownloader have been connected on device %s!", self._device_name)


jdownloader = JDownloader()
