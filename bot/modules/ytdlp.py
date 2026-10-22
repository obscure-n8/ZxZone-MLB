from aiohttp import ClientSession
from ast import literal_eval
from asyncio import wait_for, Event, wrap_future, sleep, gather
from functools import partial
from os import path as ospath
from pyrogram import Client
from pyrogram.filters import command, regex, user
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message
from time import time
from yt_dlp import YoutubeDL

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import (
    is_premium_user,
    sync_to_async,
    new_task,
    new_thread,
    arg_parser,
)
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.links_utils import is_url, get_link
from bot.helper.ext_utils.status_utils import get_readable_file_size, get_readable_time
from bot.helper.listeners.tasks_listener import TaskListener
from bot.helper.mirror_utils.download_utils.yt_dlp_download import YoutubeDLHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    editMessage,
    auto_delete_message,
    deleteMessage,
)
from bot.helper.video_utils.selector import SelectMode


class YtSelection:
    def __init__(self, listener):
        self._listener = listener
        self._is_m4a = False
        self._time = time()
        self._timeout = 120
        self._is_playlist = False
        self._main_buttons = None
        self.is_cancelled = False
        self.event = Event()
        self.formats = {}
        self.qual = None

    @new_thread
    async def _event_handler(self):
        pfunc = partial(select_format, obj=self)
        handler = self._listener.client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^ytq") & user(self._listener.user_id)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=self._timeout)
        except:
            await editMessage(
                "Timed Out. Task has been cancelled!", self._listener.editable
            )
            self.qual = None
            self.is_cancelled = True
            self.event.set()
        finally:
            self._listener.client.remove_handler(*handler)

    async def get_quality(self, result):
        future = self._event_handler()
        buttons = ButtonMaker()
        if "entries" in result:
            self._is_playlist = True
            for i in ["144", "240", "360", "480", "720", "1080", "1440", "2160"]:
                video_format = f"bv*[height<=?{i}][ext=mp4]+ba[ext=m4a]/b[height<=?{i}]"
                b_data = f"{i}|mp4"
                self.formats[b_data] = video_format
                buttons.button_data(f"{i}-mp4", f"ytq {b_data}")
                video_format = f"bv*[height<=?{i}][ext=webm]+ba/b[height<=?{i}]"
                b_data = f"{i}|webm"
                self.formats[b_data] = video_format
                buttons.button_data(f"{i}-webm", f"ytq {b_data}")
            buttons.button_data("MP3", "ytq mp3")
            buttons.button_data("Audio Formats", "ytq audio")
            buttons.button_data("Best Videos", "ytq bv*+ba/b")
            buttons.button_data("Best Audios", "ytq ba/b")
            buttons.button_data("Cancel", "ytq cancel", "footer")
            self._main_buttons = buttons.build_menu(3)
            msg = f"Choose Available Playlist Videos Quality:\n\n<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</i>"
        else:
            format_dict = result.get("formats")
            if format_dict is not None:
                for item in format_dict:
                    if item.get("tbr"):
                        format_id = item["format_id"]

                        if item.get("filesize"):
                            size = item["filesize"]
                        elif item.get("filesize_approx"):
                            size = item["filesize_approx"]
                        else:
                            size = 0

                        if item.get("video_ext") == "none" and (
                            item.get("resolution") == "audio only"
                            or item.get("acodec") != "none"
                        ):
                            if item.get("audio_ext") == "m4a":
                                self._is_m4a = True
                            b_name = f"{item['acodec']}-{item['ext']}"
                            v_format = format_id
                        elif item.get("height"):
                            height = item["height"]
                            ext = item["ext"]
                            fps = item["fps"] if item.get("fps") else ""
                            b_name = f"{height}p{fps}-{ext}"
                            ba_ext = (
                                "[ext=m4a]" if self._is_m4a and ext == "mp4" else ""
                            )
                            v_format = f"{format_id}+ba{ba_ext}/b[height=?{height}]"
                        else:
                            continue

                        self.formats.setdefault(b_name, {})[f"{item['tbr']}"] = [
                            size,
                            v_format,
                        ]

                for b_name, tbr_dict in self.formats.items():
                    if len(tbr_dict) == 1:
                        tbr, v_list = next(iter(tbr_dict.items()))
                        buttonName = f"{b_name} ({get_readable_file_size(v_list[0])})"
                        buttons.button_data(buttonName, f"ytq sub {b_name} {tbr}")
                    else:
                        buttons.button_data(b_name, f"ytq dict {b_name}")
            buttons.button_data("MP3", "ytq mp3")
            buttons.button_data("Audio Formats", "ytq audio")
            buttons.button_data("Best Video", "ytq bv*+ba/b")
            buttons.button_data("Best Audio", "ytq ba/b")
            buttons.button_data("Cancel", "ytq cancel", "footer")
            self._main_buttons = buttons.build_menu(2)
            msg = f"Choose Available Video Quality:\n\n<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</i>"
        await gather(
            editMessage(msg, self._listener.editable, self._main_buttons),
            wrap_future(future),
        )
        return self.qual

    async def back_to_main(self):
        time_out = f"<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</i>"
        if self._is_playlist:
            msg = f"Choose Available Playlist Videos Quality:\n\n{time_out}"
        else:
            msg = f"Choose Available Video Quality:\n\n{time_out}"
        await editMessage(msg, self._listener.editable, self._main_buttons)

    async def qual_subbuttons(self, b_name):
        buttons = ButtonMaker()
        tbr_dict = self.formats[b_name]
        for tbr, d_data in tbr_dict.items():
            button_name = f"{tbr}K ({get_readable_file_size(d_data[0])})"
            buttons.button_data(button_name, f"ytq sub {b_name} {tbr}")
        buttons.button_data("Back", "ytq back", "footer")
        buttons.button_data("Cancel", "ytq cancel", "footer")
        msg = f"Choose available Bit rate for <b>{b_name}</b>:\n\n<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</i>"
        await editMessage(msg, self._listener.editable, buttons.build_menu(2))

    async def mp3_subbuttons(self):
        i = "s" if self._is_playlist else ""
        buttons = ButtonMaker()
        audio_qualities = [64, 128, 320]
        for q in audio_qualities:
            audio_format = f"ba/b-mp3-{q}"
            buttons.button_data(f"{q}K-mp3", f"ytq {audio_format}")
        buttons.button_data("Back", "ytq back")
        buttons.button_data("Cancel", "ytq cancel")
        msg = f"Choose mp3 Audio{i} Bitrate:\n\n<i>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</i>"
        await editMessage(msg, self._listener.editable, buttons.build_menu(3))

    async def audio_format(self):
        i = "s" if self._is_playlist else ""
        buttons = ButtonMaker()
        for frmt in ["aac", "alac", "flac", "m4a", "opus", "vorbis", "wav"]:
            audio_format = f"ba/b-{frmt}-"
            buttons.button_data(frmt, f"ytq aq {audio_format}")
        buttons.button_data("Back", "ytq back", "footer")
        buttons.button_data("Cancel", "ytq cancel", "footer")
        msg = f"Choose Audio{i} Format:\n\n<b>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</b>"
        await editMessage(msg, self._listener.editable, buttons.build_menu(3))

    async def audio_quality(self, formats):
        i = "s" if self._is_playlist else ""
        buttons = ButtonMaker()
        for qual in range(11):
            audio_format = f"{formats}{qual}"
            buttons.button_data(qual, f"ytq {audio_format}")
        buttons.button_data("Back", "ytq aq back")
        buttons.button_data("Cancel", "ytq aq cancel")
        subbuttons = buttons.build_menu(5)
        msg = f"Choose Audio{i} Qaulity:\n0 is best and 10 is worst\n\n<b>Timeout: {get_readable_time(self._timeout - (time() - self._time))}</b>"
        await editMessage(msg, self._listener.editable, subbuttons)


@new_task
async def select_format(_, query: CallbackQuery, obj: YtSelection):
    data = query.data.split()
    message = query.message
    await query.answer()
    match data[1]:
        case "dict":
            b_name = data[2]
            await obj.qual_subbuttons(b_name)
        case "mp3":
            await obj.mp3_subbuttons()
        case "audio":
            await obj.audio_format()
        case "aq":
            if data[2] == "back":
                await obj.audio_format()
            else:
                await obj.audio_quality(data[2])
        case "back":
            await obj.back_to_main()
        case "cancel":
            await editMessage("Task has been cancelled.", message)
            obj.qual = None
            obj.is_cancelled = True
            obj.event.set()
        case value:
            if value == "sub":
                obj.qual = obj.formats[data[2]][data[3]][1]
            elif "|" in value:
                obj.qual = obj.formats[value]
            else:
                obj.qual = value
            obj.event.set()


def extract_info(link, options):
    with YoutubeDL(options) as ydl:
        result = ydl.extract_info(link, download=False)
        if result is None:
            raise ValueError("Info result is None")
        return result


async def _mdisk(link: str, name: str):
    key = link.split("/")[-1]
    async with (
        ClientSession() as session,
        session.get(
            f"https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={key}",
            ssl=False,
        ) as resp,
    ):
        if resp.status == 200:
            resp_json = await resp.json()
            link = resp_json["source"]
            if not name:
                name = resp_json["filename"]
        return name, link


class YtDlp(TaskListener):
    def __init__(
        self,
        client: Client,
        message: Message,
        _=False,
        __=False,
        isLeech=False,
        vidMode=None,
        sameDir=None,
        bulk=None,
        multiTag=None,
        options="",
    ):
        if sameDir is None:
            sameDir = {}
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multiTag = multiTag
        self.options = options
        self.sameDir = sameDir
        self.bulk = bulk
        super().__init__()
        self.isYtDlp = True
        self.isLeech = isLeech
        self.vidMode = vidMode

    @new_task
    async def newEvent(self):
        text = self.message.text.split("\n")
        await self.getTag(text)

        if fmsg := await UseCheck(self.message, self.isLeech).run(
            True, daily=True, ml_chek=True, session=True, send_pm=True
        ):
            self.removeFromSameDir()
            await auto_delete_message(self.message, fmsg, self.message.reply_to_message)
            return

        arg_base = {
            "-i": 0,
            "-sp": 0,
            "-b": False,
            "-gf": False,
            "-s": False,
            "-ss": False,
            "-sv": False,
            "-vt": False,
            "-z": False,
            "-m": "",
            "-n": "",
            "-opt": "",
            "-rcf": "",
            "-t": "",
            "-up": "",
            "link": "",
        }
        input_list = text[0].split(" ")
        args = arg_parser(input_list[1:], arg_base)

        self.compress = args["-z"]
        self.isGofile = args["-gf"]
        self.link = args["link"]
        self.name = args["-n"].replace("/", "")
        self.rcFlags = args["-rcf"]
        self.screenShots = args["-ss"]
        self.sampleVideo = args["-sv"]
        self.select = args["-s"]
        self.splitSize = args["-sp"]
        self.thumb = args["-t"]
        self.upDest = args["-up"]
        self.isRename = self.name

        folder_name = args["-m"].replace("/", "")
        isBulk = args["-b"]
        opt = args["-opt"]
        vidTool = args["-vt"]
        bulk_start = bulk_end = 0
        qual = ""

        try:
            self.multi = int(args["-i"])
        except:
            self.multi = 0

        if not isinstance(isBulk, bool):
            dargs = isBulk.split(":")
            bulk_start = dargs[0] or None
            if len(dargs) == 2:
                bulk_end = dargs[1] or None
            isBulk = True

        if (
            config_dict["PREMIUM_MODE"]
            and not is_premium_user(self.user_id)
            and (self.multi > 0 or isBulk)
        ):
            await sendMessage(
                "Upss, multi/bulk mode for premium user only", self.message
            )
            return

        if not isBulk:
            if folder_name:
                if not self.sameDir:
                    self.sameDir = {
                        "total": self.multi,
                        "tasks": set(),
                        "name": folder_name,
                    }
                self.sameDir["tasks"].add(self.mid)
            elif self.sameDir:
                self.sameDir["total"] -= 1
        else:
            if vidTool and not self.vidMode and self.sameDir:
                self.vidMode = await SelectMode(self).get_buttons()
                if not self.vidMode:
                    self.removeFromSameDir()
                    return
            await self.initBulk(input_list, bulk_start, bulk_end, YtDlp)
            return

        if self.bulk:
            del self.bulk[0]

        if vidTool and (not self.vidMode or not self.sameDir):
            self.vidMode = await SelectMode(self).get_buttons()
            if not self.vidMode:
                self.removeFromSameDir()
                return

        path = ospath.join(f"{config_dict['DOWNLOAD_DIR']}{self.mid}", folder_name)

        self.link = self.link or get_link(self.message)

        if not is_url(self.link):
            msg = await sendMessage(
                f"Invalid argument, type /{BotCommands.HelpCommand} for more details.",
                self.message,
            )
            await auto_delete_message(self.message, msg)
            self.removeFromSameDir()
            self.run_multi(input_list, folder_name, YtDlp)
            return

        if "mdisk.me" in self.link:
            self.name, self.link = await _mdisk(self.link, self.name)

        self.editable = await sendMessage(
            "<i>Checking for <b>YT-DLP</b> link, please wait...</i>", self.message
        )
        if self.link:
            await sleep(0.5)

        try:
            await self.beforeStart()
        except Exception as e:
            await editMessage(str(e), self.editable)
            self.removeFromSameDir()
            return

        options = {"usenetrc": True, "cookiefile": "cookies.txt"}

        opt = (
            opt
            or self.user_dict.get("yt_opt")
            or (config_dict["YT_DLP_OPTIONS"] if "yt_opt" not in self.user_dict else "")
        )

        if opt:
            yt_opts = opt.split("|")
            for ytopt in yt_opts:
                if ":" not in ytopt:
                    continue
                key, value = map(str.strip, ytopt.split(":", 1))
                if key == "postprocessors":
                    continue
                if key == "format" and not self.select:
                    if value.startswith("ba/b-"):
                        qual = value
                        continue
                    qual = value
                if value.startswith("^"):
                    if "." in value or value == "^inf":
                        value = float(value.split("^")[1])
                    else:
                        value = int(value.split("^")[1])
                elif value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.startswith(("{", "[", "(")) and value.endswith(
                    ("}", "]", ")")
                ):
                    value = literal_eval(value)
                options[key] = value
            options["playlist_items"] = "0"

        try:
            result = await sync_to_async(extract_info, self.link, options)
        except Exception as e:
            e = str(e).replace("<", " ").replace(">", " ")
            await editMessage(f"{self.tag} {e}", self.editable)
            self.removeFromSameDir()
            return
        finally:
            self.run_multi(input_list, folder_name, YtDlp)

        if not qual:
            qual = await YtSelection(self).get_quality(result)
        if not qual:
            self.removeFromSameDir()
            return

        await deleteMessage(self.editable)
        LOGGER.info("Downloading with YT-DLP: %s", self.link)
        playlist = "entries" in result
        ydl = YoutubeDLHelper(self)
        await ydl.add_download(path, qual, playlist, opt)


async def ytdl(client: Client, message: Message):
    YtDlp(client, message).newEvent()


async def ytdlleech(client: Client, message: Message):
    YtDlp(client, message, isLeech=True).newEvent()


bot.add_handler(
    MessageHandler(
        ytdl, filters=command(BotCommands.YtdlCommand) & CustomFilters.authorized
    )
)
bot.add_handler(
    MessageHandler(
        ytdlleech,
        filters=command(BotCommands.YtdlLeechCommand) & CustomFilters.authorized,
    )
)
