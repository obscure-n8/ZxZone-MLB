from aiofiles.os import path as aiopath, makedirs
from aioshutil import move
from ast import literal_eval
from asyncio import create_subprocess_exec, gather, sleep, wait_for
from asyncio.subprocess import PIPE
from os import path as ospath, cpu_count
from PIL import Image
from pyrogram.types import Message
from re import search as re_search, findall as re_findall, split as re_split
from time import time

from bot import config_dict, subprocess_lock, LOGGER, DEFAULT_SPLIT_SIZE, FFMPEG_NAME
from bot.helper.ext_utils.bot_utils import cmd_exec, sync_to_async, is_premium_user
from bot.helper.ext_utils.files_utils import (
    ARCH_EXT,
    get_mime_type,
    get_path_size,
    clean_target,
)
from bot.helper.ext_utils.links_utils import get_url_name
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.telegraph_helper import TelePost


def getSplitSizeBytes(size: str):
    size = size.lower()
    if size.endswith("mb"):
        size = size.split("mb")[0].strip()
        size = int(float(size) * 1048576)
    elif size.endswith("gb"):
        size = size.split("gb")[0].strip()
        size = int(float(size) * 1073741824)
    else:
        size = 0
    return size


async def createThumb(msg: Message, _id: int = 0):
    if not _id:
        _id = msg.id
    path = "thumbnails/"
    await makedirs(path, exist_ok=True)
    photo_dir = await msg.download()
    des_dir = f"{path}{_id}.jpg"
    await sync_to_async(Image.open(photo_dir).convert("RGB").save, des_dir, "JPEG")
    await clean_target(photo_dir)
    return des_dir


async def is_multi_streams(path):
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                path,
            ]
        )
        if res := result[1]:
            LOGGER.warning("Get Video Streams: %s", res)
    except Exception as e:
        LOGGER.error("Get Video Streams: %s. Mostly File not found!", e)
        return False
    fields = literal_eval(result[0]).get("streams")
    if fields is None:
        LOGGER.error("Get Video Streams: %s", result)
        return False
    videos = audios = 0
    for stream in fields:
        if stream.get("codec_type") == "video":
            videos += 1
        elif stream.get("codec_type") == "audio":
            audios += 1
    return videos > 1 or audios > 1


async def get_media_info(path):
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_format",
                path,
            ]
        )
        if res := result[1]:
            LOGGER.warning("Get Media Info: %s", res)
    except Exception as e:
        LOGGER.error("Get Media Info: %s. Mostly File not found!", e)
        return 0, None, None
    fields = literal_eval(result[0]).get("format")
    if fields is None:
        LOGGER.error("Get_media_info: %s", result)
        return 0, None, None
    duration = round(float(fields.get("duration", 0)))
    tags = fields.get("tags", {})
    artist = tags.get("artist") or tags.get("ARTIST") or tags.get("Artist")
    title = tags.get("title") or tags.get("TITLE") or tags.get("Title")
    return duration, artist, title


async def post_media_info(path: str, size: int, image=None, is_link=False):
    if is_link:
        name, size = get_url_name(path), get_readable_file_size(size)
    else:
        name = ospath.basename(path)
        file_size, total_size = (
            get_readable_file_size(await get_path_size(path)),
            get_readable_file_size(size),
        )
        size = f"{file_size}/{total_size}"
    telepost = TelePost("Media Info")
    img_post = config_dict["IMAGE_MEDINFO"]
    if image:
        try:
            if ipost := (await sync_to_async(telepost.image_post, image))[0]:
                img_post = ipost
        except:
            pass
    try:
        if metadata := (await cmd_exec(["mediainfo", path]))[0].replace(path, name):
            metadata = f"<img src='{img_post}' /><b>{name}<br>Size: {size}</b><br><pre>{metadata}</pre>"
            return await sync_to_async(telepost.create_post, metadata)
    except Exception as e:
        LOGGER.info(e)


async def get_document_type(path):
    is_video = is_audio = is_image = False
    if path.endswith(tuple(ARCH_EXT)) or re_search(
        r".+(\.|_)(rar|7z|zip|bin)(\.0*\d+)?$", path
    ):
        return is_video, is_audio, is_image
    mime_type = await sync_to_async(get_mime_type, path)
    if mime_type.startswith("image"):
        return False, False, True
    if mime_type.startswith("audio"):
        return False, True, False
    if not mime_type.startswith("video") and not mime_type.endswith("octet-stream"):
        return is_video, is_audio, is_image
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                path,
            ]
        )
        if res := result[1]:
            LOGGER.warning("Get Document Type: %s", res)
    except Exception as e:
        LOGGER.error("Get Document Type: %s. Mostly File not found!", e)
        return is_video, is_audio, is_image
    fields = literal_eval(result[0]).get("streams")
    if fields is None:
        LOGGER.error("Get_document_type: %s", result)
        return is_video, is_audio, is_image
    for stream in fields:
        if stream.get("codec_type") == "video":
            is_video = True
        elif not is_video and stream.get("codec_type") == "audio":
            is_audio = True
    return is_video, is_audio, is_image


async def take_ss(video_file, ss_nb) -> list:
    ss_nb = min(ss_nb, 10)
    duration = (await get_media_info(video_file))[0]
    if duration == 0:
        LOGGER.error("Take SS: Can't get the duration of video")
        return []
    dirpath, name = video_file.rsplit("/", 1)
    name, _ = ospath.splitext(name)
    dirpath = f"{dirpath}/screenshots/"
    await makedirs(dirpath, exist_ok=True)
    interval = duration // (ss_nb + 1)
    cap_time = interval
    outputs, cmds = [], []
    for i in range(ss_nb):
        output = f"{dirpath}SS.{name}_{i:02}.png"
        outputs.append(output)
        cmd = [
            FFMPEG_NAME,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{cap_time}",
            "-i",
            video_file,
            "-q:v",
            "1",
            "-frames:v",
            "1",
            output,
        ]
        cap_time += interval
        cmds.append(cmd_exec(cmd))
    try:
        results = await wait_for(gather(*cmds), timeout=15)
        if results[0][2] != 0:
            LOGGER.error(
                "Error while creating sreenshots from video. Path: %s. stderr: %s",
                video_file,
                results[0][1],
            )
            return []
    except:
        LOGGER.error(
            "Error while creating sreenshots from video. Path: %s. Error: Timeout some issues with ffmpeg with specific arch!",
            video_file,
        )
        return []
    return outputs


async def get_audio_thumb(audio_file):
    des_dir = "thumbnails"
    await makedirs(des_dir, exist_ok=True)
    des_dir = ospath.join(des_dir, f"{time()}.jpg")
    cmd = [
        FFMPEG_NAME,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        audio_file,
        "-an",
        "-vcodec",
        "copy",
        des_dir,
    ]
    status = await create_subprocess_exec(*cmd, stderr=PIPE)
    if await status.wait() != 0 or not await aiopath.exists(des_dir):
        err = (await status.stderr.read()).decode().strip()
        LOGGER.error(
            "Error while extracting thumbnail from audio. Name: %s stderr: %s",
            audio_file,
            err,
        )
        return None
    return des_dir


async def create_thumbnail(video_file, duration):
    des_dir = "thumbnails"
    await makedirs(des_dir, exist_ok=True)
    des_dir = ospath.join(des_dir, f"{time()}.jpg")
    if duration is None:
        duration = (await get_media_info(video_file))[0]
    if duration == 0:
        duration = 3
    duration = duration // 2
    cmd = [
        FFMPEG_NAME,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{duration}",
        "-i",
        video_file,
        "-vf",
        "thumbnail",
        "-frames:v",
        "1",
        des_dir,
    ]
    try:
        _, err, code = await wait_for(cmd_exec(cmd), timeout=15)
        if code != 0 or not await aiopath.exists(des_dir):
            LOGGER.error(
                "Error while extracting thumbnail from video. Name: %s stderr: %s",
                video_file,
                err,
            )
            return None
    except:
        LOGGER.error(
            "Error while extracting thumbnail from video. Name: %s. Error: Timeout some issues with ffmpeg with specific arch!",
            video_file,
        )
    return des_dir


async def split_file(
    path,
    size,
    dirpath,
    split_size,
    listener,
    obj,
    start_time=0,
    i=1,
    inLoop=False,
    multi_streams=True,
):
    if listener.seed and not listener.newDir:
        dirpath = ospath.join(dirpath, "splited_files_mltb")
        await makedirs(dirpath, exist_ok=True)
    leech_split_size = config_dict["LEECH_SPLIT_SIZE"]
    if config_dict["PREMIUM_MODE"] and not is_premium_user(listener.user_id):
        leech_split_size = DEFAULT_SPLIT_SIZE
    parts = -(-size // leech_split_size)
    if listener.equalSplits and not inLoop:
        split_size = ((size + parts - 1) // parts) + 1000
    if (await get_document_type(path))[0]:
        if multi_streams:
            multi_streams = await is_multi_streams(path)
        obj.state = "video"
        duration = (await get_media_info(path))[0]
        base_name, extension = ospath.splitext(path)
        split_size -= 5000000
        while i <= parts or start_time < duration - 4:
            out_path = f"{base_name}.part{i:03}{extension}"
            cmd = [
                FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                str(start_time),
                "-i",
                path,
                "-fs",
                str(split_size),
                "-map",
                "0",
                "-map_chapters",
                "-1",
                "-async",
                "1",
                "-strict",
                "-2",
                "-c",
                "copy",
                out_path,
            ]
            if not multi_streams:
                del cmd[10:12]
            async with subprocess_lock:
                if listener.suproc == "cancelled":
                    return False
                listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
            _, stderr = await listener.suproc.communicate()
            code = listener.suproc.returncode
            if code == -9:
                return
            if code != 0:
                stderr = stderr.decode().strip()
                await clean_target(out_path)
                if multi_streams:
                    LOGGER.warning(
                        "%s. Retrying without map, -map 0 not working in all situations. Path: %s",
                        stderr,
                        path,
                    )
                    return await split_file(
                        path,
                        size,
                        dirpath,
                        split_size,
                        listener,
                        obj,
                        start_time,
                        i,
                        True,
                        False,
                    )
                LOGGER.warning(
                    "%s. Unable to split this video, if it's size less than {MAX_SPLIT_SIZE} will be uploaded as it is. Path: %s",
                    stderr,
                    path,
                )
                return "errored"
            out_size = await get_path_size(out_path)
            if out_size > listener.maxSplitSize:
                dif = out_size - listener.maxSplitSize
                split_size -= dif + 5000000
                await clean_target(out_path)
                return await split_file(
                    path,
                    size,
                    dirpath,
                    split_size,
                    listener,
                    obj,
                    start_time,
                    i,
                    True,
                )
            lpd = (await get_media_info(out_path))[0]
            if lpd == 0:
                LOGGER.error(
                    "Something went wrong while splitting, mostly file is corrupted. Path: %s",
                    path,
                )
                break
            if duration == lpd:
                LOGGER.warning(
                    "This file has been splitted with default stream and audio, so you will only see one part with less size from orginal one because it doesn't have all streams and audios. This happens mostly with MKV videos. Path: %s",
                    path,
                )
                break
            if lpd <= 3:
                await clean_target(out_path)
                break
            start_time += lpd - 3
            i += 1
    else:
        obj.state = "archive"
        out_path = f"{path}."
        async with subprocess_lock:
            if listener.suproc == "cancelled":
                return False
            listener.suproc = await create_subprocess_exec(
                "split",
                "--numeric-suffixes=1",
                "--suffix-length=3",
                f"--bytes={split_size}",
                path,
                out_path,
                stderr=PIPE,
            )
        _, stderr = await listener.suproc.communicate()
        code = listener.suproc.returncode
        if code == -9:
            return
        if code != 0:
            LOGGER.error(stderr.decode().strip())
    listener.total_size += await get_path_size(out_path)
    return True


class FFProgress:
    def __init__(self):
        self.is_cancel = False
        self._duration = 0
        self._start_time = time()
        self._eta = 0
        self._percentage = "0%"
        self._processed_bytes = 0

    @property
    def processed_bytes(self):
        return self._processed_bytes

    @property
    def percentage(self):
        return self._percentage

    @property
    def eta(self):
        return self._eta

    @property
    def speed(self):
        return self._processed_bytes / (time() - self._start_time)

    async def readlines(self, stream):
        data = bytearray()
        while not stream.at_eof():
            lines = re_split(rb"[\r\n]+", data)
            data[:] = lines.pop(-1)
            for line in lines:
                yield line
            data.extend(await stream.read(1024))

    async def progress(self, status: str = ""):
        start_time = time()
        async for line in self.readlines(self.listener.suproc.stderr):
            if (
                self.is_cancel
                or self.listener.suproc == "cancelled"
                or self.listener.suproc.returncode is not None
            ):
                return
            if status == "direct":
                self._processed_bytes = await get_path_size(self.outfile)
                await sleep(0.5)
                continue
            if progress := dict(
                re_findall(
                    r"(frame|fps|size|time|bitrate|speed)\s*\=\s*(\S+)",
                    line.decode("utf-8"),
                )
            ):
                if not self._duration:
                    self._duration = (await get_media_info(self.path))[0]
                hh, mm, sms = progress["time"].split(":")
                time_to_second = (int(hh) * 3600) + (int(mm) * 60) + float(sms)
                self._processed_bytes = int(progress["size"].rstrip("kB")) * 1024
                self._percentage = (
                    f"{round((time_to_second / self._duration) * 100, 2)}%"
                )
                try:
                    self._eta = (
                        self._duration / float(progress["speed"].strip("x"))
                    ) - (time() - start_time)
                except:
                    pass


class SampleVideo(FFProgress):
    def __init__(self, listener, duration, partDuration, gid):
        self.listener = listener
        self.path = ""
        self.name = ""
        self.outfile = ""
        self.size = 0
        self._duration = duration
        self._partduration = partDuration
        self._gid = gid
        self._start_time = time()
        super().__init__()

    async def create(self, video_file: str, oneFile: bool = False):
        filter_complex = ""
        self.path = video_file
        dir, name = video_file.rsplit("/", 1)
        self.outfile = ospath.join(dir, f"SAMPLE.{name}")
        segments = [(0, self._partduration)]
        duration = (await get_media_info(video_file))[0]
        remaining_duration = duration - (self._partduration * 2)
        parts = (self._duration - (self._partduration * 2)) // self._partduration
        time_interval = remaining_duration // parts
        next_segment = time_interval
        for _ in range(parts):
            segments.append((next_segment, next_segment + self._partduration))
            next_segment += time_interval
        segments.append((duration - self._partduration, duration))

        for i, (start, end) in enumerate(segments):
            filter_complex += (
                f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]; "
            )
            filter_complex += (
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]; "
            )

        for i in range(len(segments)):
            filter_complex += f"[v{i}][a{i}]"

        filter_complex += f"concat=n={len(segments)}:v=1:a=1[vout][aout]"

        cmd = [
            FFMPEG_NAME,
            "-hide_banner",
            "-i",
            video_file,
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-threads",
            f"{cpu_count() // 2}",
            self.outfile,
        ]

        if self.listener.suproc == "cancelled":
            return False

        self.name, self.size = (
            ospath.basename(video_file),
            await get_path_size(video_file),
        )
        self.listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
        _, code = await gather(self.progress(), self.listener.suproc.wait())

        if code == -9:
            return False
        if code == 0:
            if oneFile:
                newDir, _ = ospath.splitext(video_file)
                await makedirs(newDir, exist_ok=True)
                await gather(
                    move(video_file, ospath.join(newDir, name)),
                    move(self.outfile, ospath.join(newDir, f"SAMPLE.{name}")),
                )
                return newDir
            return True

        LOGGER.error(
            "%s. Something went wrong while creating sample video, mostly file is corrupted. Path: %s",
            (await self.listener.suproc.stderr.read()).decode().strip(),
            video_file,
        )
        return video_file


async def createArchive(listener, scr_path, dest_path, size, pswd, mpart=False):
    cmd = [
        "7z",
        f"-v{listener.splitSize}b",
        "a",
        "-mx=0",
        f"-p{pswd}",
        dest_path,
        scr_path,
    ]
    cmd.extend(f"-xr!*.{ext}" for ext in listener.extensionFilter)
    if (
        listener.isLeech
        and int(size) > listener.splitSize
        or mpart
        and int(size) > listener.splitSize
    ):
        if not pswd:
            del cmd[4]
        LOGGER.info("Zip: orig_path: %s, zip_path: %s.0*", scr_path, dest_path)
    else:
        del cmd[1]
        if not pswd:
            del cmd[3]
        LOGGER.info("Zip: orig_path: %s, zip_path: %s", scr_path, dest_path)
    async with subprocess_lock:
        if listener.suproc == "cancelled":
            return
        listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
    _, stderr = await listener.suproc.communicate()
    code = listener.suproc.returncode
    if code == -9:
        return
    if code == 0:
        if not listener.seed:
            await clean_target(scr_path, True)
        return True
    LOGGER.error("%s. Unable to zip this path: %s", stderr.decode().strip(), scr_path)
    return True


class GenSS:
    def __init__(self, message, path):
        self._message = message
        self._path = path
        self._images = f"genss_{self._message.id}.jpg"
        self._ss_path = ospath.join("genss", str(self._message.id))
        self._name = ""
        self._error = False

    @property
    def error(self):
        return self._error

    @property
    def name(self):
        return self._name

    @property
    def rimage(self):
        return self._images

    async def _combine_image(self):
        await cmd_exec(
            [
                FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "quiet",
                "-i",
                str(ospath.join(self._ss_path, "%1d.jpg")),
                "-filter_complex",
                "scale=1920:-1,tile=3x3",
                self._images,
                "-y",
            ]
        )
        if not await aiopath.exists(self._images):
            self._images = ""

    async def _run_genss(self, duration, index):
        await makedirs(self._ss_path, exist_ok=True)
        des_dir = ospath.join(self._ss_path, f"{index}.jpg")
        cmds = [
            FFMPEG_NAME,
            "-hide_banner",
            "-loglevel",
            "error",
            "-start_at_zero",
            "-copyts",
            "-ss",
            f"{duration}",
            "-i",
            self._path,
            "-vf",
            "drawtext=fontfile=font.ttf:fontsize=70:fontcolor=white:box=1:boxcolor=black@0.7:x=(W-tw)/1.05:y=h-(2*lh):text='%{pts\\:hms}'",
            "-vframes",
            "1",
            des_dir,
            "-y",
        ]
        await cmd_exec(cmds)
        if await aiopath.exists(des_dir):
            with Image.open(des_dir) as img:
                img.convert("RGB").save(des_dir, "JPEG")
            return des_dir

    async def file_ss(self):
        min_dur, max_photo = 5, 10
        duration = (await get_media_info(self._path))[0]
        if not duration:
            self._error = "Failed fetch info from url, something wrong with url or not video in url!"
            return
        if duration > min_dur:
            cur_step = duration // max_photo
            current = cur_step
            images = []
            for x in range(max_photo):
                images.append(await self._run_genss(current, str(x)))
                current += cur_step
            if any(images):
                await self._combine_image()
        if not self._images:
            self._error = "Failed generated screenshot, something wrong with url or not video in url!"
            LOGGER.info("Failed Generating Screenshot: %s", ospath.basename(self._path))
        await clean_target(self._ss_path)

    async def ddl_ss(self):
        self._name = get_url_name(self._path)
        await self.file_ss()
