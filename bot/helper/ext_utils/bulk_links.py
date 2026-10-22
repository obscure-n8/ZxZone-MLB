from aiofiles import open as aiopen
from pyrogram.types import Message

from bot.helper.ext_utils.files_utils import clean_target


def filterLinks(links_list: list, bulk_start: int, bulk_end: int):
    if bulk_start and bulk_end:
        links_list = links_list[bulk_start:bulk_end]
    elif bulk_start:
        links_list = links_list[bulk_start:]
    elif bulk_end:
        links_list = links_list[:bulk_end]
    return links_list


def getLinksFromMessage(text: str):
    return [item.strip() for item in text.split("\n") if len(item) != 0]


async def getLinksFromFile(message: Message):
    links_list = []
    text_file_dir = await message.download()
    async with aiopen(text_file_dir, "r+") as f:
        lines = await f.readlines()
        links_list.extend(filter(None, map(str.strip, lines)))
    await clean_target(text_file_dir)
    return links_list


async def extractBulkLinks(message: Message, bulk_start: str, bulk_end: str):
    if isinstance(bulk_start, str):
        bulk_start = int(bulk_start)
    if isinstance(bulk_end, str):
        bulk_end = int(bulk_end)
    links_list = []
    if reply_to := message.reply_to_message:
        if (file_ := reply_to.document) and (file_.mime_type == "text/plain"):
            links_list = await getLinksFromFile(reply_to)
        elif reply_to.text:
            links_list = getLinksFromMessage(reply_to.text)
    return filterLinks(links_list, bulk_start, bulk_end) if links_list else links_list
