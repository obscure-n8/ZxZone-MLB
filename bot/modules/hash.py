from aiofiles.os import makedirs
from asyncio import gather
from hashlib import md5, sha1, sha224, sha256, sha512, sha384
from os import path as ospath
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from time import time

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import is_pm_enabled, new_task
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.links_utils import is_media
from bot.helper.ext_utils.status_utils import (
    get_readable_time,
    get_readable_file_size,
    action,
    get_date_time,
)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    editMessage,
    sendMessage,
    sendMedia,
    auto_delete_message,
    copyMessage,
    deleteMessage,
)


@new_task
async def hasher(_, message: Message):
    user_id = message.from_user.id if message.from_user else message.sender_chat.id
    reply_to = message.reply_to_message
    tag = message.from_user.mention
    media = None
    isSuperGroup = message.chat.type.name in ("SUPERGROUP", "CHANNEL")

    if fmsg := await UseCheck(message).run(session=True, send_pm=True):
        await auto_delete_message(message, fmsg, reply_to)
        return

    if not reply_to or reply_to and not (media := is_media(reply_to)):
        msg = await sendMessage(f"{tag}, replying to media or file!", message)
        await auto_delete_message(message, msg)
        return

    VtPath = ospath.join("hash", str(user_id))
    await makedirs(VtPath, exist_ok=True)
    hmsg = await sendMessage("<i>Processing media/file...</i>", message)
    try:
        fname, fsize = media.file_name, media.file_size
        outpath = await bot.download_media(
            message=media, file_name=ospath.join(VtPath, media.file_name)
        )
    except Exception as e:
        LOGGER.error(e)
        await gather(
            clean_target("hash"),
            editMessage("Error when downloading. Try again later.", hmsg),
        )
        return
    try:
        hash_md5, hash_sha1, hash_sha224, hash_sha256, hash_sha512, hash_sha384 = (
            md5(usedforsecurity=False),
            sha1(usedforsecurity=False),
            sha224(),
            sha256(),
            sha512(),
            sha384(),
        )
        with open(outpath, "rb") as f:
            while chunk := f.read(8192):
                hash_md5.update(chunk)
                hash_sha1.update(chunk)
                hash_sha224.update(chunk)
                hash_sha256.update(chunk)
                hash_sha512.update(chunk)
                hash_sha384.update(chunk)
    except Exception as e:
        LOGGER.info(e)
        await gather(
            clean_target("hash"), editMessage("Hashing error. Check Logs.", hmsg)
        )
        return
    msg = (
        "<b>HASH INFO</b>\n"
        f"<code>{fname}</code>\n"
        f"<b>╭ Cc: </b>{tag}\n"
        f"<b>┊ ID: </b><code>{message.from_user.id}</code>\n"
        f"<b>┊ Size: </b>{get_readable_file_size(fsize)}\n"
        f"<b>┊ Elapsed: </b>{get_readable_time(time() - message.date.timestamp())}\n"
        f"<b>┊ Action: </b>{action(message)}\n"
        f"<b>┊ Add: </b>{get_date_time(message)[0]}\n"
        f"<b>╰ At: </b>{get_date_time(message)[1]} ({config_dict['TIME_ZONE_TITLE']})\n\n"
        f"<b>╭ MD5: </b>\n<code>{hash_md5.hexdigest()}</code>\n"
        f"<b>┊ SHA1: </b>\n<code>{hash_sha1.hexdigest()}</code>\n"
        f"<b>┊ SHA224: </b>\n<code>{hash_sha224.hexdigest()}</code>\n"
        f"<b>┊ SHA256: </b>\n<code>{hash_sha256.hexdigest()}</code>\n"
        f"<b>┊ SHA512: </b>\n<code>{hash_sha512.hexdigest()}</code>\n"
        f"<b>╰ SHA384: </b>\n<code>{hash_sha384.hexdigest()}</code>"
    )
    await deleteMessage(hmsg)
    hash_msg = await sendMedia(msg, message.chat.id, reply_to)
    await clean_target("hash")

    if chat_id := config_dict["OTHER_LOG"]:
        await copyMessage(chat_id, hash_msg)

    if is_pm_enabled(user_id) and isSuperGroup:
        await copyMessage(user_id, hash_msg)

    if isSuperGroup and (stime := config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]):
        await auto_delete_message(message, reply_to, stime=stime)


bot.add_handler(
    MessageHandler(
        hasher, filters=command(BotCommands.HashCommand) & CustomFilters.authorized
    )
)
