from __future__ import annotations
from ast import literal_eval
from os import path as ospath, listdir
from random import SystemRandom
from re import search as re_search
from string import ascii_letters, digits
from yt_dlp import YoutubeDL, DownloadError

from bot import (
    task_dict,
    task_dict_lock,
    non_queued_dl,
    queue_dict_lock,
    LOGGER,
    FFMPEG_NAME,
)
from bot.helper.ext_utils.bot_utils import sync_to_async, async_to_sync
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    check_limits_size,
)
from bot.helper.listeners import tasks_listener as task
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.yt_dlp_download_status import (
    YtDlpDownloadStatus,
)
from bot.helper.telegram_helper.message_utils import sendStatusMessage


class MyLogger:
    def __init__(self, obj: YoutubeDLHelper, listener: task.TaskListener):
        self._obj = obj
        self._listener = listener

    def debug(self, msg):
        # Hack to fix changing extension
        if not self._obj.is_playlist:
            if match := re_search(
                r".Merger..Merging formats into..(.*?).$", msg
            ) or re_search(r".ExtractAudio..Destination..(.*?)$", msg):
                LOGGER.info(msg)
                newname = match.group(1)
                newname = newname.rsplit("/", 1)[-1]
                self._listener.name = newname

    @staticmethod
    def warning(msg):
        LOGGER.warning(msg)

    @staticmethod
    def error(msg):
        if msg != "ERROR: Cancelling...":
            LOGGER.error(msg)


class YoutubeDLHelper:
    def __init__(self, listener: task.TaskListener):
        self._last_downloaded = 0
        self._size = 0
        self._progress = 0
        self._downloaded_bytes = 0
        self._download_speed = 0
        self._eta = "~"
        self._gid = ""
        self._ext = ""
        self._listener = listener
        self._is_cancelled = False
        self._downloading = False
        self._playlist_index = 0
        self._playlist_count = 0
        self.is_playlist = False
        self.opts = {
            "progress_hooks": [self._onDownloadProgress],
            "logger": MyLogger(self, self._listener),
            "usenetrc": True,
            "cookiefile": "cookies.txt",
            "allow_multiple_video_streams": True,
            "allow_multiple_audio_streams": True,
            "noprogress": True,
            "allow_playlist_files": True,
            "overwrites": True,
            "writethumbnail": True,
            "trim_file_name": 220,
            "ffmpeg_location": f"/usr/bin/{FFMPEG_NAME}",
            "retry_sleep_functions": {
                "http": lambda n: 3,
                "fragment": lambda n: 3,
                "file_access": lambda n: 3,
                "extractor": lambda n: 3,
            },
        }

    @property
    def download_speed(self):
        return self._download_speed

    @property
    def downloaded_bytes(self):
        return self._downloaded_bytes

    @property
    def size(self):
        return self._size

    @property
    def progress(self):
        return self._progress

    @property
    def eta(self):
        return self._eta

    @property
    def gid(self):
        return self._gid

    @property
    def listener(self):
        return self._listener

    def _onDownloadProgress(self, d):
        self._downloading = True
        if self._is_cancelled:
            raise ValueError("Cancelling...")
        if d["status"] == "finished":
            if self.is_playlist:
                self._last_downloaded = 0
        elif d["status"] == "downloading":
            self._download_speed = d["speed"]
            if self.is_playlist:
                downloadedBytes = d["downloaded_bytes"]
                chunk_size = downloadedBytes - self._last_downloaded
                self._last_downloaded = downloadedBytes
                self._downloaded_bytes += chunk_size
                self._playlist_index = d.get("info_dict", {}).get(
                    "playlist_index", self._playlist_index
                )
            else:
                if d.get("total_bytes"):
                    self._size = d["total_bytes"]
                elif d.get("total_bytes_estimate"):
                    self._size = d["total_bytes_estimate"]
                self._downloaded_bytes = d["downloaded_bytes"]
                self._eta = d.get("eta", "~") or "~"
            try:
                self._progress = (self._downloaded_bytes / self._size) * 100
            except:
                pass

    async def _onDownloadStart(self, from_queue=False):
        async with task_dict_lock:
            task_dict[self._listener.mid] = YtDlpDownloadStatus(
                self._listener, self, self._gid
            )
        if not from_queue:
            await self._listener.onDownloadStart()
            if self._listener.multi <= 1:
                await sendStatusMessage(self._listener.message)

    def _onDownloadError(self, error, listfile=None):
        self._is_cancelled = True
        async_to_sync(self._listener.onDownloadError, error, listfile)

    def extractMetaData(self):
        if self._listener.link.startswith(("rtmp", "mms", "rstp", "rtmps")):
            self.opts["external_downloader"] = "ffmpeg"
        with YoutubeDL(self.opts) as ydl:
            try:
                result = ydl.extract_info(self._listener.link, download=False)
                if result is None:
                    raise ValueError("Info result is None")
            except Exception as e:
                self._onDownloadError(str(e))
                return
            if self.is_playlist:
                self._playlist_count = result.get("playlist_count", 0)
            if "entries" in result:
                for entry in result["entries"]:
                    if not entry:
                        continue
                    if "filesize_approx" in entry:
                        self._size += entry["filesize_approx"]
                    elif "filesize" in entry:
                        self._size += entry["filesize"]
                    if not self._listener.name:
                        outtmpl_ = "%(series,playlist_title,channel)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d.%(ext)s"
                        self._listener.name, ext = ospath.splitext(
                            ydl.prepare_filename(entry, outtmpl=outtmpl_)
                        )
                        if not self._ext:
                            self._ext = ext
            else:
                outtmpl_ = "%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s"
                realName = ydl.prepare_filename(result, outtmpl=outtmpl_)
                ext = ospath.splitext(realName)[-1]
                self._listener.name = (
                    f"{self._listener.name}{ext}" if self._listener.name else realName
                )
                if not self._ext:
                    self._ext = ext
                if result.get("filesize"):
                    self._size = result["filesize"]
                elif result.get("filesize_approx"):
                    self._size = result["filesize_approx"]

    def _download(self, path):
        try:
            with YoutubeDL(self.opts) as ydl:
                try:
                    ydl.download([self._listener.link])
                except DownloadError as e:
                    LOGGER.error(e)
                    if not self._is_cancelled:
                        self._onDownloadError(str(e))
                    return
            if self.is_playlist and (
                not ospath.exists(path) or len(listdir(path)) == 0
            ):
                self._onDownloadError(
                    "No video available to download from this playlist. Check logs for more details"
                )
                return
            if self._is_cancelled:
                raise ValueError
            try:
                async_to_sync(self._listener.onDownloadComplete)
            except Exception as e:
                self._onDownloadError(e)
                return
        except ValueError:
            self._onDownloadError("Download stopped by user!")

    async def add_download(self, path, qual, playlist, options):
        if playlist:
            self.opts["ignoreerrors"] = True
            self.is_playlist = True
        self._gid = "".join(SystemRandom().choices(ascii_letters + digits, k=10))
        await self._onDownloadStart()
        self.opts["postprocessors"] = [
            {
                "add_chapters": True,
                "add_infojson": "if_exists",
                "add_metadata": True,
                "key": "FFmpegMetadata",
            }
        ]
        if qual.startswith("ba/b-"):
            audio_info = qual.split("-")
            qual = audio_info[0]
            audio_format = audio_info[1]
            rate = audio_info[2]
            self.opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": rate,
                }
            )
            if audio_format == "vorbis":
                self._ext = ".ogg"
            elif audio_format == "alac":
                self._ext = ".m4a"
            else:
                self._ext = f".{audio_format}"
        if options:
            self._set_options(options)
        self.opts["format"] = qual
        await sync_to_async(self.extractMetaData)
        if self._is_cancelled:
            return
        base_name, ext = ospath.splitext(self._listener.name)
        trim_name = self._listener.name if self.is_playlist else base_name
        if len(trim_name.encode()) > 200:
            self._listener.name = (
                self._listener.name[:200]
                if self.is_playlist
                else f"{base_name[:200]}{ext}"
            )
            base_name = ospath.splitext(self._listener.name)[0]
        if self.is_playlist:
            self.opts["outtmpl"] = {
                "default": f"{path}/{self._listener.name}/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s",
                "thumbnail": f"{path}/yt-dlp-thumb/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s",
            }
        elif any(
            key in options
            for key in [
                "writedescription",
                "writeinfojson",
                "writeannotations",
                "writedesktoplink",
                "writewebloclink",
                "writeurllink",
                "writesubtitles",
                "writeautomaticsub",
            ]
        ):
            self.opts["outtmpl"] = {
                "default": f"{path}/{base_name}/{self._listener.name}",
                "thumbnail": f"{path}/yt-dlp-thumb/{base_name}.%(ext)s",
            }
        else:
            self.opts["outtmpl"] = {
                "default": f"{path}/{self._listener.name}",
                "thumbnail": f"{path}/yt-dlp-thumb/{base_name}.%(ext)s",
            }

        if qual.startswith("ba/b"):
            self._listener.name = f"{base_name}{self._ext}"

        if self._listener.isLeech:
            self.opts["postprocessors"].append(
                {
                    "format": "jpg",
                    "key": "FFmpegThumbnailsConvertor",
                    "when": "before_dl",
                }
            )
        if self._ext in [
            ".mp3",
            ".mkv",
            ".mka",
            ".ogg",
            ".opus",
            ".flac",
            ".m4a",
            ".mp4",
            ".mov",
            ".m4v",
        ]:
            self.opts["postprocessors"].append(
                {
                    "already_have_thumbnail": self._listener.isLeech,
                    "key": "EmbedThumbnail",
                }
            )
        elif not self._listener.isLeech:
            self.opts["writethumbnail"] = False

        file, name = await stop_duplicate_check(self._listener)
        if file:
            self._listener.name = name
            LOGGER.info("File/folder already in Drive!")
            self._is_cancelled = True
            await self._listener.onDownloadError("File/folder already in Drive!", file)
            return

        if msg := await check_limits_size(
            self._listener, self._size, self.is_playlist, self._playlist_count
        ):
            if "Only" not in msg:
                LOGGER.info("File/folder size over the limit size!")
                msg += f". File/folder size is {get_readable_file_size(self._size)}."
            self._is_cancelled = True
            await self._listener.onDownloadError(msg)
            return

        add_to_queue, event = await check_running_tasks(self._listener.mid)
        if add_to_queue:
            LOGGER.info("Added to Queue/Download: %s", self._listener.name)
            async with task_dict_lock:
                task_dict[self._listener.mid] = QueueStatus(
                    self._listener, self._size, self._gid, "dl"
                )
            await event.wait()
            async with task_dict_lock:
                if self._listener.mid not in task_dict:
                    return
            LOGGER.info("Start Queued Download from YT_DLP: %s", self._listener.name)
            await self._onDownloadStart(True)
        else:
            LOGGER.info("Download with YT_DLP: %s", self._listener.name)
        async with queue_dict_lock:
            non_queued_dl.add(self._listener.mid)
        self.org_size = self._size
        await sync_to_async(self._download, path)

    async def cancel_task(self):
        self._is_cancelled = True
        LOGGER.info("Cancelling Download: %s", self._listener.name)
        if not self._downloading:
            await self._listener.onDownloadError("Download Cancelled by User!")

    def _set_options(self, options):
        options = options.split("|")
        for opt in options:
            if ":" not in opt:
                continue
            key, value = map(str.strip, opt.split(":", 1))
            if value.startswith("^"):
                if "." in value or value == "^inf":
                    value = float(value.split("^", 1)[1])
                else:
                    value = int(value.split("^", 1)[1])
            elif value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.startswith(("{", "[", "(")) and value.endswith(("}", "]", ")")):
                value = literal_eval(value)

            if key == "postprocessors":
                if isinstance(value, list):
                    self.opts[key].extend(tuple(value))
                elif isinstance(value, dict):
                    self.opts[key].append(value)
            else:
                self.opts[key] = value
