from re import match as re_match, search as re_search
from pyrogram.types import Message
from urllib.parse import unquote, urlparse, unquote_plus

from bot import config_dict


def get_url_name(url: str):
    return unquote_plus(unquote(urlparse(url).path.rpartition("/")[-1]))


def is_magnet(url: str):
    return bool(re_match(r"magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*\s*", url))


def is_url(url: str):
    return bool(
        re_match(
            r"^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$",
            url,
        )
    )


def is_gdrive_link(url: str):
    return "drive.google.com" in url


def is_tele_link(url: str):
    return url.startswith(("https://t.me/", "tg://openmessage?user_id="))


def is_sharer_link(url: str):
    return bool(
        re_match(
            r"https?:\/\/.+\.gdtot\.\S+|https?:\/\/(filepress|filebee|appdrive|gdflix)\.\S+",
            url,
        )
    )


def is_mega_link(url: str):
    return "mega.nz" in url or "mega.co.nz" in url


def is_rclone_path(path: str):
    return bool(
        re_match(
            r"^(mrcc:)?(?!(magnet:|mtp:|sa:|tp:))(?![- ])[a-zA-Z0-9_\. -]+(?<! ):(?!.*\/\/).*$|^rcl$",
            path,
        )
    )


def is_gdrive_id(id_: str):
    return bool(
        re_match(
            r"^(tp:|sa:|mtp:)?(?:[a-zA-Z0-9-_]{33}|[a-zA-Z0-9_-]{19})$|^gdl$|^root$",
            id_,
        )
    )


def get_mega_link_type(url: str):
    return "folder" if "folder" in url or "/#F!" in url else "file"


def is_media(message: Message):
    if not message:
        return
    return (
        message.document
        or message.photo
        or message.video
        or message.audio
        or message.voice
        or message.video_note
        or message.sticker
        or message.animation
        or None
    )


def get_stream_link(mime_type: str, url_path: str):
    if all(
        config_dict[key]
        for key in ["ENABLE_STREAM_LINK", "STREAM_BASE_URL", "STREAM_PORT", "LEECH_LOG"]
    ):
        if mime_type.startswith("video"):
            return f"{config_dict['STREAM_BASE_URL']}/stream/{url_path}?type=video"
        elif mime_type.startswith("audio"):
            return f"{config_dict['STREAM_BASE_URL']}/stream/{url_path}?type=audio"


def get_link(message: Message = None, text: str = "", get_source: bool = False):
    link = ""
    pattern = r"https?:\/\/(www.)?\S+\.?[a-z]{2,6}\b(\S*)|magnet:\?xt=urn:(btih|btmh):[-a-zA-Z0-9@:%_\+.~#?&//=]*\s*"
    if match := re_search(pattern, text or message.text.strip()):
        link = match.group()
    if message and (reply_to := message.reply_to_message):
        media = is_media(reply_to)
        if media and get_source:
            link = f"Source is media/file: {getattr(media, 'mime_type', 'image/photo')}"
        elif text := reply_to.text or (reply_to.caption and not media):
            if match := re_search(pattern, text.strip()):
                link = match.group()
                link = link if is_magnet(link) or is_url(link) else ""
    return link
