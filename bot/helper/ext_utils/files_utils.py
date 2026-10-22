from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, listdir
from aiohttp import ClientSession
from aioshutil import rmtree as aiormtree, disk_usage
from magic import Magic
from os import walk, path as ospath, makedirs
from re import split as re_split, search as re_search, escape, I
from subprocess import run as srun
from sys import exit as sexit

from bot import (
    aria2,
    config_dict,
    get_client,
    DOWNLOAD_DIR,
    LOGGER,
    ARIA_NAME,
    QBIT_NAME,
    FFMPEG_NAME,
)
from bot.helper.ext_utils.bot_utils import sync_to_async, async_to_sync
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive


ARCH_EXT = [
    ".tar.bz2",
    ".tar.gz",
    ".bz2",
    ".gz",
    ".tar.xz",
    ".tar",
    ".tbz2",
    ".tgz",
    ".lzma2",
    ".zip",
    ".7z",
    ".z",
    ".rar",
    ".iso",
    ".wim",
    ".cab",
    ".apm",
    ".arj",
    ".chm",
    ".cpio",
    ".cramfs",
    ".deb",
    ".dmg",
    ".fat",
    ".hfs",
    ".lzh",
    ".lzma",
    ".mbr",
    ".msi",
    ".mslz",
    ".nsis",
    ".ntfs",
    ".rpm",
    ".squashfs",
    ".udf",
    ".vhd",
    ".xar",
]

FIRST_SPLIT_REGEX = r"(\.|_)part0*1\.rar$|(\.|_)7z\.0*1$|(\.|_)zip\.0*1$|^(?!.*(\.|_)part\d+\.rar$).*\.rar$"

SPLIT_REGEX = r"\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$"


def is_first_archive_split(file):
    return bool(re_search(FIRST_SPLIT_REGEX, file))


def is_archive(file):
    return file.endswith(tuple(ARCH_EXT))


def is_archive_split(file):
    return bool(re_search(SPLIT_REGEX, file))


async def clean_target(path, log=False):
    if not await aiopath.exists(str(path)):
        return False
    if log:
        LOGGER.info("Cleaning Target: %s", path)
    if await aiopath.isdir(path):
        await aiormtree(path)
    else:
        await aioremove(path)
    return True


async def clean_download(path):
    if await aiopath.exists(path):
        LOGGER.info("Cleaning Download: %s", path)
        await clean_target(path)


def clean_all():
    aria2.remove_all(True)
    get_client().torrents_delete(torrent_hashes="all")
    CURRENT_DIR = config_dict["DOWNLOAD_DIR"]
    async_to_sync(clean_target, CURRENT_DIR)
    if DOWNLOAD_DIR != CURRENT_DIR:
        async_to_sync(clean_target, DOWNLOAD_DIR)
    makedirs(DOWNLOAD_DIR, exist_ok=True)


def exit_clean_up(_, __):
    try:
        LOGGER.info("Please wait, while we clean up and stop the running downloads")
        clean_all()
        srun(
            [
                "pkill",
                "-9",
                "-f",
                f"gunicorn|{ARIA_NAME}|{QBIT_NAME}|{FFMPEG_NAME}|wzone|java|alass",
            ],
            check=True,
        )
        sexit(0)
    except KeyboardInterrupt:
        LOGGER.warning("Force Exiting before the cleanup finishes!")
        sexit(1)


async def clean_unwanted(path):
    LOGGER.info("Cleaning unwanted files/folders: %s", path)
    for dirpath, _, files in await sync_to_async(walk, path, topdown=False):
        for filee in files:
            if filee.endswith(".!qB") or (
                filee.endswith(".parts") and filee.startswith(".")
            ):
                await clean_target(ospath.join(dirpath, filee))
        if (
            dirpath.endswith((".unwanted", "splited_files_mltb", "copied_mltb"))
            or not files
        ):
            await clean_target(dirpath)


async def get_path_size(path):
    if await aiopath.isfile(path):
        return await aiopath.getsize(path)
    total_size = 0
    for root, _, files in await sync_to_async(walk, path):
        for f in files:
            abs_path = ospath.join(root, f)
            total_size += await aiopath.getsize(abs_path)
    return total_size


async def count_files_and_folders(path, extensionFilter):
    total_files = total_folders = 0
    for _, dirs, files in await sync_to_async(walk, path):
        total_files += len(files)
        for f in files:
            if f.endswith(tuple(extensionFilter)):
                total_files -= 1
        total_folders += len(dirs)
    return total_folders, total_files


async def check_storage_threshold(size: int, arch=False, alloc=False):
    STORAGE_THRESHOLD, DOWNLOAD_DIR = (
        config_dict["STORAGE_THRESHOLD"],
        config_dict["DOWNLOAD_DIR"],
    )
    if not alloc:
        if not arch:
            if (
                await disk_usage(DOWNLOAD_DIR)
            ).free - size < STORAGE_THRESHOLD * 1024**3:
                return False
        elif (await disk_usage(DOWNLOAD_DIR)).free - (
            size * 2
        ) < STORAGE_THRESHOLD * 1024**3:
            return False
    elif not arch:
        if (await disk_usage(DOWNLOAD_DIR)).free < STORAGE_THRESHOLD * 1024**3:
            return False
    elif (await disk_usage(DOWNLOAD_DIR)).free - size < STORAGE_THRESHOLD * 1024**3:
        return False
    return True


def get_base_name(orig_path):
    extension = next((ext for ext in ARCH_EXT if orig_path.lower().endswith(ext)), "")
    if extension != "":
        return re_split(f"{extension}$", orig_path, maxsplit=1, flags=I)[0]
    raise NotSupportedExtractionArchive("File format not supported for extraction")


def get_mime_type(file_path):
    mime = Magic(mime=True)
    mime_type = mime.from_file(file_path)
    mime_type = mime_type or "text/plain"
    return mime_type


async def download_content(url: str, name: str):
    try:
        async with ClientSession() as session, session.get(url, ssl=False) as r:
            if r.status == 200:
                async with aiopen(name, "wb") as f:
                    async for data in r.content.iter_chunked(1024):
                        await f.write(data)
                return True
            LOGGER.error("Failed to download %s, got response %s.", name, r.status)
    except Exception as e:
        LOGGER.error(e)


async def join_files(path):
    files = await listdir(path)
    results = []
    for file_ in files:
        if not re_search(r"\.0+2$", file_):
            continue
        if (
            await sync_to_async(get_mime_type, ospath.join(path, file_))
            != "application/octet-stream"
        ):
            continue

        final_name = file_.rsplit(".", 1)[0]
        fname = ospath.join(path, final_name)
        parts = sorted(
            part
            for part in files
            if re_search(rf"^{escape(final_name)}\.0[0-9]+$", part)
        )
        if not parts:
            continue
        try:
            async with aiopen(fname, "wb") as output:
                for part in parts:
                    async with aiopen(ospath.join(path, part), "rb") as source:
                        while chunk := await source.read(1024 * 1024):
                            await output.write(chunk)
            results.append((final_name, parts))
        except OSError as e:
            LOGGER.error("Failed to join %s: %s", final_name, e)

    if results:
        LOGGER.info("Join Completed!")
        for final_name, parts in results:
            for file_ in parts:
                await aioremove(ospath.join(path, file_))
