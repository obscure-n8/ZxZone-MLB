from aiofiles.os import path as aiopath, makedirs
from aiohttp import ClientSession
from asyncio import sleep, gather, Event, wrap_future, wait_for
from functools import partial
from gtts import gTTS
from os import path as ospath
from PIL import Image
from pyrogram import Client
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from telegraph import upload_file
from urllib.parse import quote_plus

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import (
    ButtonMaker,
    is_premium_user,
    sync_to_async,
    new_task,
    new_thread,
)
from bot.helper.ext_utils.files_utils import clean_target, download_content
from bot.helper.ext_utils.help_messages import HelpString
from bot.helper.ext_utils.links_utils import is_url
from bot.helper.ext_utils.media_utils import GenSS
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    editMessage,
    deleteMessage,
    sendPhoto,
    sendSticker,
)


class MiscTool:
    def __init__(self):
        self.reply_to = self.message.reply_to_message
        self.file = ""
        self.error = ""
        self.lang = "en"
        self._doc = None

    async def _get_content(self, url):
        self.error = ""
        async with ClientSession() as session, session.get(url, ssl=False) as r:
            if r.status == 200:
                return await r.json()
            self.error = f"Got respons {r.status}"

    def _is_animated(self):
        self.error = ""
        if self.reply_to.sticker and not self.reply_to.sticker.is_animated:
            self._doc = self.reply_to
        else:
            self.error = "ERROR: Invalid reply!"

    async def _download_image(self):
        await self._doc.download(file_name=f"./{self.file}")

    def is_image(self):
        if self.reply_to.photo:
            self._doc = self.reply_to
        elif self.reply_to.document and "image" in self.reply_to.document.mime_type:
            self._doc = self.reply_to
        if not self._doc or self.reply_to.video:
            self.error = "ERROR: Invalid reply!"
        return self._doc

    async def translator(self, text):
        url = f"https://script.google.com/macros/s/AKfycbyhNk6uVgrtJLEFRUT6y5B2pxETQugCZ9pKvu01-bE1gKkDRsw/exec?q={text}&target={self.lang}"
        return (await self._get_content(url))["text"].strip()

    async def webss(self, url, mode="webss"):
        if mode == "webss":
            LOGGER.info("Generated Screemshot: %s", url)
            url = f"https://webss.yasirapi.eu.org/api?url={url}&width=1080&height=720"
            self.file = f"Webss_{self.message.id}.png"
        if not await download_content(url, self.file):
            self.error = f"Failed to download {self.file}"
            return
        return self.file

    async def vidss(self, url):
        vidss = GenSS(self.message, url)
        await vidss.ddl_ss()
        if vidss.error:
            self.error = vidss.error
            return
        self.file = vidss.rimage
        return vidss

    async def thumb(self, title):
        url = f"https://yasirapi.eu.org/justwatch?q={quote_plus(title)}&locale=US"
        json_data = await self._get_content(url)
        if not json_data:
            return None, None
        files, base_dir = [], ospath.join("downloads", f"{self.message.id}")
        await makedirs(base_dir, exist_ok=True)
        for item in json_data["results"]["data"]["popularTitles"]["edges"][:3]:
            name = item["node"]["content"]["title"]
            try:
                url = "https://images.justwatch.com" + item["node"]["content"][
                    "posterUrl"
                ].format(profile="s592", format="webp")
                self.file = ospath.join(base_dir, f"{name}.webp")
                await self.webss(url, "thumb")
                if await aiopath.exists(self.file):
                    img = Image.open(self.file).convert("RGB")
                    png_image = ospath.join(base_dir, f"{name}.png")
                    img.save(png_image, "png")
                    await clean_target(self.file)
                    files.append(png_image)
            except Exception as e:
                LOGGER.error(e)
        return files, base_dir

    async def pahe_search(self, title):
        url = f"https://yasirapi.eu.org/pahe?q={title}"
        result = await self._get_content(url)
        if self.error:
            return
        return result["result"]

    async def image_ocr(self):
        if not self.is_image():
            return ""
        self.file = ospath.join("downloads", f"{self.message.id}.jpg")
        await self._download_image()
        res = await sync_to_async(upload_file, self.file)
        img_url = f"https://telegra.ph{res[0]}"
        url = f"https://script.google.com/macros/s/AKfycbwURISN0wjazeJTMHTPAtxkrZTWTpsWIef5kxqVGoXqnrzdLdIQIfLO7jsR5OQ5GO16/exec?url={img_url}"
        result = (await self._get_content(url))["text"].strip()
        await clean_target(self.file)
        return result

    async def image_sticker(self):
        self.is_image()
        is_image = True
        if self.error:
            is_image = False
            self._is_animated()
        if self.error:
            return
        ext = ".webp" if is_image else ".jpg"
        self.file = ospath.join("downloads", f"{self.message.id}{ext}")
        await self._download_image()
        return self.file

    async def tts(self, text):
        self.file = ospath.join("downloads", f"tts_{self.message.id}.aac")
        try:
            tts = gTTS(text, lang=self.lang)
            await sync_to_async(tts.save, self.file)
            return self.file
        except Exception as err:
            self.error = f"ERROR: <code>{err}</code>"

    @property
    def languages(self):
        return [
            "af",
            "am",
            "ar",
            "az",
            "be",
            "bg",
            "bn",
            "bs",
            "ca",
            "ceb",
            "co",
            "cs",
            "cy",
            "da",
            "de",
            "el",
            "en",
            "eo",
            "es",
            "et",
            "eu",
            "fa",
            "fi",
            "fr",
            "fy",
            "ga",
            "gd",
            "gl",
            "gu",
            "ha",
            "haw",
            "hi",
            "hmn",
            "hr",
            "ht",
            "hu",
            "hy",
            "id",
            "ig",
            "is",
            "it",
            "iw",
            "ja",
            "jw",
            "ka",
            "kk",
            "km",
            "kn",
            "ko",
            "ku",
            "ky",
            "la",
            "lb",
            "lo",
            "lt",
            "lv",
            "mg",
            "mi",
            "mk",
            "ml",
            "mn",
            "mr",
            "ms",
            "mt",
            "my",
            "ne",
            "nl",
            "no",
            "ny",
            "pa",
            "pl",
            "ps",
            "pt",
            "ro",
            "ru",
            "sd",
            "si",
            "sk",
            "sl",
            "sm",
            "sn",
            "so",
            "sq",
            "sr",
            "st",
            "su",
            "sv",
            "sw",
            "ta",
            "te",
            "tg",
            "th",
            "tl",
            "tr",
            "uk",
            "ur",
            "uz",
            "vi",
            "xh",
            "yi",
            "yo",
            "zh",
            "zh_CN",
            "zh_TW",
            "zu",
        ]


class Misc(MiscTool):
    def __init__(self, client: Client, message: Message):
        self._client: Client = client
        self._timeout = 240
        self.message = message
        self.tag = self.message.from_user.mention
        self.editable: Message = None
        self.event = Event()
        self.query = ""
        self.status = ""
        super().__init__()

    @new_thread
    async def _event_handler(self):
        pfunc = partial(misc_callback, obj=self)
        handler = self._client.add_handler(
            CallbackQueryHandler(pfunc, filters=regex("^misc")), group=-1
        )
        try:
            await wait_for(self.event.wait(), timeout=500)
        except:
            self.event.set()
        finally:
            self._client.remove_handler(*handler)

    async def _verify_message(self):
        if self.reply_to and not self.reply_to.text:
            self.query = await self.image_ocr()
            if self.error:
                return

        lang = self.message.text.rsplit(maxsplit=1)[-1]
        if lang.lower() in self.languages:
            self.lang = lang.lower()

        if not self.query:
            text = (
                self.reply_to.text or self.reply_to.caption
                if self.reply_to
                else self.message.text
            )
            self.query = text.split(maxsplit=1)[-1].replace("\n", ". ")
            if self.lang:
                self.query = self.query.rstrip(lang)

    async def list_message(self):
        buttons = ButtonMaker()
        if not self.status:
            but_dict = {
                "OCR": "misc ocr",
                "TTS": "misc tts",
                "Webss": "misc wss",
                "Vidss": "misc vss",
                "Pahe": "misc pahe",
                "Translate": "misc tr",
                "Convert": "misc conv",
                "Thumb": "misc thumb",
                "Close": "misc close",
            }
            [buttons.button_data(key, value) for key, value in but_dict.items()]
            text = f"Task For ~ {self.tag}\n{HelpString.MISC}"

        if self.status:
            buttons.button_data("<<", "misc back")
            buttons.button_data("Close", "misc close")

        match self.status:
            case "pahe":
                await editMessage("<i>Processing pahe search...</i>", self.editable)
                if not self.query or is_url(self.query):
                    text = "Send valid title!"
                else:
                    await editMessage(
                        f"<i>Searching <b>{self.query.title()}</b>, please wait...</i>",
                        self.editable,
                    )
                    result = await self.pahe_search(self.query)
                    if self.error or not result:
                        text = f"Not found Pahe search for <b>{self.query.title()}</b>."
                        if self.error:
                            text += f"\nERROR: {self.error}"
                    else:
                        text = f"<b>Search Pahe For {self.query.upper()}</b>\n\n"
                        text += "".join(
                            f"{count}. <a href='{x['link']}'>{x['judul']}</a>\n"
                            for count, x in enumerate(result, start=1)
                        )
            case "thumb":
                await editMessage(
                    "<i>Getting thumbnail(s), please wait...</i>", self.editable
                )
                text = self.query.replace(".", " ").replace("  ", " ")
                pngs, dirpath = await self.thumb(text)
                if pngs:
                    text = f"Sucsesfully generating thumbnail poster for <b>{text.title()}</b>."
                    await editMessage(
                        f"{text}. <i>Sending the files...</i>", self.editable
                    )
                    for png in pngs:
                        buttons = ButtonMaker()
                        buttons.button_data("Set as Thumb", "misc setthumb")
                        await sendPhoto(
                            f"<code>{ospath.basename(png)}</code>",
                            self.message,
                            png,
                            buttons.build_menu(1),
                        )
                        if len(pngs) > 1:
                            await sleep(5)
                    await clean_target(dirpath)
                else:
                    text = f"Failed getting thumbnail for <b>{text.title()}</b>!\n{self.error}"
            case "ocr":
                text = self.error or f"OCR Result:\n\n{self.query}"
            case "conv":
                await editMessage("<i>Converting, please wait...</i>", self.editable)
                result = await self.image_sticker()
                if self.error:
                    text = self.error
                else:
                    text = ""
                    self.event.set()
                    await deleteMessage(self.editable)
                    if result.endswith(".jpg"):
                        await sendPhoto("", self.message, result)
                    else:
                        await sendSticker(result, self.message, True)
                    await clean_target(self.file)
            case "tr" | "tts" as value:
                text = (
                    "<i>Translating, please wait...</i>"
                    if value == "tr"
                    else "<i>Converting, please wait...</i>"
                )
                await editMessage(text, self.editable)
                if self.query and not self.error:
                    if value == "tr":
                        result = await self.translator(self.query)
                        text = f"Translate to -> {self.lang.upper()}\n\n{result}"
                    else:
                        self.event.set()
                        result = await self.tts(await self.translator(self.query))
                        if self.error:
                            text = self.error
                        else:
                            text = ""
                            await gather(
                                deleteMessage(self.editable),
                                self.message.reply_audio(
                                    result,
                                    quote=True,
                                    caption=f"Text to Speech -> {self.lang.upper()}\n\n<b>Original Text:</b>\n<code>{self.query}</code>",
                                ),
                            )
                        await clean_target(self.file)
                else:
                    text = self.error
            case "wss" | "vss" as value:
                await editMessage(
                    "<i>Generated screenshot, please wait...</i>", self.editable
                )
                if value == "wss":
                    photo = await self.webss(self.query)
                    caption = "Web Screenshot Generated."
                else:
                    vidss = await self.vidss(self.query)
                    if vidss:
                        photo = vidss.rimage
                        caption = (
                            f"Video Screenshot Generated:\n<code>{vidss.name}</code>"
                        )
                if self.error:
                    text = self.error
                else:
                    text = ""
                    self.event.set()
                    buttons.reset()
                    buttons.button_link("Source", self.query)
                    await gather(
                        sendPhoto(caption, self.message, photo, buttons.build_menu(1)),
                        deleteMessage(self.editable),
                    )
                await clean_target(self.file)

        if text:
            await editMessage(text, self.editable, buttons.build_menu(2))

    @new_task
    async def newEvent(self):
        if config_dict["PREMIUM_MODE"] and not is_premium_user(
            self.message.from_user.id
            if self.message.from_user
            else self.message.sender_chat.id
        ):
            await sendMessage(
                "This feature only for <b>Premium User</b>!", self.message
            )
            return
        if not self.reply_to and len(self.message.command) == 1:
            await sendMessage(
                f"Send command with a message or reply to a message.\n{HelpString.MISC}",
                self.message,
            )
            return
        future = self._event_handler()
        self.editable, _ = await gather(
            sendMessage("<i>Checking request, please wait...</i>", self.message),
            self._verify_message(),
        )
        await gather(self.list_message(), wrap_future(future))


@new_task
async def misc_callback(_, query: CallbackQuery, obj: Misc):
    data = query.data.split()
    match data[1]:
        case "close":
            obj.event.set()
            await gather(
                query.answer(), deleteMessage(obj.editable, obj.message, obj.reply_to)
            )
            return
        case "setthumb":
            user_id = query.from_user.id
            msg = query.message
            if msg.photo:
                await query.answer("Downloading photo...")
                dest_path = ospath.join("thumbnails", f"{user_id}.jpg")
                await makedirs("thumbnails", exist_ok=True)
                await msg.download(file_name=dest_path)
                from PIL import Image
                from bot import DATABASE_URL
                from bot.helper.ext_utils.db_handler import DbManager
                from bot.helper.ext_utils.bot_utils import update_user_ldata

                def convert_image():
                    with Image.open(dest_path) as img:
                        img.convert("RGB").save(dest_path, "JPEG")

                await sync_to_async(convert_image)
                await update_user_ldata(user_id, "thumb", dest_path)
                if DATABASE_URL:
                    await DbManager().update_user_doc(user_id, "thumb", dest_path)
                await query.answer("Photo set as custom thumbnail successfully!", True)
            else:
                await query.answer("No photo found in this message!", True)
            return
        case "back":
            obj.status = ""
            obj.error = ""
            await query.answer()
        case value:
            obj.status = value
            if value in ("ocr", "conv"):
                if not obj.reply_to or obj.reply_to.text or obj.reply_to.video:
                    text = "Upss, reply to a photo"
                    if value == "conv":
                        text += " or static sticker"
                    await query.answer(f"{text}!", True)
                    return
            elif value in ("wss", "vss"):
                if not is_url(obj.query):
                    await query.answer("SS utils only for url/link!", True)
                    return
            elif value not in ["wss", "vss", "ocr", "conv"] and not obj.query:
                await query.answer(obj.error or "Please provide a query!", True)
                return
    await gather(query.answer(), obj.list_message())


async def misc_tools(client: Client, message: Message):
    Misc(client, message).newEvent()


bot.add_handler(
    MessageHandler(
        misc_tools, filters=command(BotCommands.MiscCommand) & CustomFilters.authorized
    )
)
