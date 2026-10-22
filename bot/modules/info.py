from aiofiles.os import makedirs
from aiohttp import ClientSession
from asyncio import gather, Event, wait_for, wrap_future
from functools import partial
from json import loads as jsonloads
from lxml.etree import HTML
from os import path as ospath
from pyrogram import enums, Client
from pyrogram.filters import command, regex, text, user
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery, InputMediaPhoto
from random import choice
from re import findall as re_findall, match as re_match
from urllib.parse import quote_plus, quote

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import new_task, new_thread
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.files_utils import clean_target, download_content
from bot.helper.ext_utils.links_utils import get_url_name
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    limit,
    editPhoto,
    sendPhoto,
    deleteMessage,
    auto_delete_message,
    handle_message,
)


info_dict = {}


anime_query = """
    query ($id: Int,$search: String) {
        Media (id: $id, type: ANIME,search: $search) {
            id
            title {
            romaji
            english
            native
        }
        description (asHtml: false)
        startDate{
            year
        }
        episodes
        season
        type
        format
        status
        duration
        siteUrl
        studios{
            nodes{
                name
            }
        }
        trailer{
            id
            site
            thumbnail
        }
        averageScore
        genres
        bannerImage
    }
}
"""
character_query = """
    query ($query: String) {
        Character (search: $query) {
            id
            name {
                first
                last
                full
            }
            siteUrl
            image {
                large
            }
            description
    }
}
"""

manga_query = """
query ($id: Int,$search: String) {
    Media (id: $id, type: MANGA,search: $search) {
        id
        title {
            romaji
            english
            native
        }
        description (asHtml: false)
        startDate{
            year
        }
        type
        format
        status
        siteUrl
        averageScore
        genres
        bannerImage
    }
}
"""

GENRES_EMOJI = {
    "Action": "👊",
    "Adventure": choice(["🪂", "🧗‍♀", "🌋"]),
    "#Action & Adventure": choice(["👊", "🪂", "🧗‍♀", "🌋"]),
    "Comedy": "🤣",
    "Drama": "🎭",
    "Crime": choice(["🔪", "💰", "💼"]),
    "Ecchi": choice(["💋", "🥵"]),
    "Family": "👨‍",
    "Fantasy": choice(["🧞", "🧞‍♂", "🧞‍♀", "🌗"]),
    "Hentai": "🔞",
    "History": "📜",
    "Horror": "☠",
    "Mahou Shoujo": "☯",
    "Mecha": "🤖",
    "Music": "🎸",
    "Musical": "🎸",
    "Mystery": "🔮",
    "Politics": "🏛️",
    "Psychological": "♟",
    "Romance": "💞",
    "Sci-Fi": "🛸",
    "Sci-Fi & Fantasy": "🛸",
    "Slice of Life": choice(["☘", "🍁"]),
    "Sports": "⚽️",
    "Supernatural": "🫧",
    "Thriller": choice(["🥶", "🔪", "🤯"]),
}


class Info:
    def __init__(self, clinet: Client, message: Message, query: str):
        self._client: Client = clinet
        self._message = message
        self._content = {
            "base": {"tmdb": {}, "imdb": {}, "mdl": {}},
            "content": {},
            "preposter": {},
            "mdl": {},
        }
        self._tmbd_url = "https://www.themoviedb.org"
        self._tag = self._message.from_user.mention
        self._anitag = f"[{self._message.from_user.first_name}](tg://user?id={self._message.from_user.id})"
        self._path = ospath.join(config_dict["DOWNLOAD_DIR"], str(self._message.id))
        self.query = query.lower()
        self.editable: Message = None
        self.event = Event()
        self.query_event = Event()
        self.status = ""
        self.onRun = False

    @new_thread
    async def _event_handler(self):
        pfunc = partial(info_callback, obj=self)
        handler = self._client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^info") & user(self._message.from_user.id)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=240)
        except:
            self.event.set()
        finally:
            self._client.remove_handler(*handler)
            await clean_target(self._path)

    @new_thread
    async def change_query_handler(self):
        pfunc = partial(change_query, obj=self)
        handler = self._client.add_handler(
            MessageHandler(pfunc, filters=text & user(self._message.from_user.id)),
            group=-1,
        )
        try:
            await wait_for(self.query_event.wait(), timeout=60)
        except:
            self.query_event.set()
            await self.list_message()
        finally:
            self.query_event.clear()
            self._client.remove_handler(*handler)

    @staticmethod
    @handle_message
    async def _editAnime(caption: str, message: Message, photo: str, reply_markup=None):
        return await bot.edit_message_media(
            message.chat.id,
            message.id,
            media=InputMediaPhoto(
                photo, limit.caption(caption), parse_mode=enums.ParseMode.MARKDOWN
            ),
            reply_markup=reply_markup,
        )

    @handle_message
    async def _sendAllPoster(self, media: list[InputMediaPhoto]):
        await self._message.reply_media_group(
            media, quote=True, disable_notification=True
        )

    @staticmethod
    async def _anim_content(template, variables):
        async with (
            ClientSession() as session,
            session.post(
                "https://graphql.anilist.co",
                json={"query": template, "variables": variables},
            ) as r,
        ):
            return (await r.json())["data"]

    @staticmethod
    async def _get_content(url, is_json=True):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
        }
        async with (
            ClientSession() as session,
            session.get(url, headers=headers, ssl=False) as res,
        ):
            if res.status == 200:
                return await res.json() if is_json else await res.text()

    @staticmethod
    def _list_to_str(datas: list | dict, type: str = None):
        if not datas:
            return ""

        match type:
            case "tags" | "lang":
                return ", ".join(
                    f"#{x.title()}".replace(" ", "").replace("-", "").strip()
                    for x in datas
                )
            case "link" | "url" | "person":
                if type == "person":
                    return ", ".join(
                        f"<a href='{x['url']}'>{x['name']}</a>"
                        for x in datas
                        if x["@type"] == "Person"
                    )
                return ", ".join(f'<a href="{x[type]}">{x["name"]}</a>' for x in datas)
            case "mono":
                return ", ".join(f"<code>{x}</code>" for x in datas)
            case "normal":
                return ", ".join(datas)
            case _:
                return ", ".join(
                    f"{GENRES_EMOJI.get(i, '')} #{i.strip()}".strip() for i in datas
                )

    @staticmethod
    def _shorten(description, info="anilist.co"):
        msg = ""
        if len(description) > 700:
            description = f"{description[:500]}..."
            msg += f"**Description**: __{description}__[Read More]({info})"
        else:
            msg += f"\n**Description**: __{description}__"
        return msg

    async def _get_poster(self, url: str):
        poster_path = ospath.join(self._path, get_url_name(url))
        if await download_content(url, poster_path):
            return poster_path

    async def _set_list_content(self, image: str):
        if self._content["base"][self.status].get(self.query):
            return
        await editPhoto(
            f"<i>Seaching <b>{self.query.title()}</b> from database, please wait...</i>",
            self.editable,
            image,
        )
        if self.status == "tmdb":
            self._content["base"][self.status][self.query] = []
            url = f"{self._tmbd_url}/search?query={quote(self.query)}"
            html = await self._get_content(url, False)
            if html:
                html = HTML(html)
                for name, info, url in zip(
                    html.xpath("//a[@data-id]/h2/text()"),
                    html.xpath('//div[@class="title"]/span/text()'),
                    html.xpath("//a[@data-id]/img/../@href"),
                ):
                    self._content["base"][self.status][self.query].append(
                        (f"{name} ~ <b>{info.rsplit(maxsplit=1)[-1]}</b>", url)
                    )
        elif self.status == "imdb":
            try:
                self._content["base"][self.status][self.query] = (
                    await self._get_content(
                        f"https://v3.sg.media-imdb.com/suggestion/titles/x/{quote_plus(self.query)}.json"
                    )
                ).get("d")
            except Exception as e:
                LOGGER.error(e)
        else:
            self._content["base"][self.status][self.query] = (
                await self._get_content(
                    f"https://kuryana.vercel.app/search/q/{quote_plus(self.query)}"
                )
            )["results"]["dramas"]

    async def _set_tmdb_content(self, content_id: str):
        if self._content["content"].get(content_id):
            return
        self._content["content"].update({content_id: {}})
        content = self._content["content"][content_id]

        data = {}
        html = HTML(await self._get_content(self._tmbd_url + content_id, False))
        if item := html.xpath('//section[@id="original_header"]'):
            item = item[0]
            name = item.xpath(".//h2//text()")
            title = " ".join(list(filter(lambda x: x.strip(), name)))
            if score := item.xpath('.//div[@class="user_score_chart"]/@data-percent'):
                data["rating"] = f"⭐️ <code>{score[0]}</code>"
            data["genre"] = self._list_to_str(
                item.xpath('.//span[@class="genres"]/a/text()')
            )
            overview = (
                item.xpath('.//div[@class="overview"][@dir="auto"]/p/text()')
                or ["Not available!"]
            )[0]
            content["summary"] = f"<b>OVERVIEW</b>\n{overview}"

            profiles = []
            for people in item.xpath('.//ol[@class="people no_image"]/li'):
                name, act, lnk = (
                    people.xpath("./p/a/text()"),
                    people.xpath("./p[2]/text()"),
                    people.xpath("./p/a/@href"),
                )
                if all([name, act, lnk]):
                    profiles.append(
                        f'<a href="{self._tmbd_url + lnk[0]}">{name[0]} ({act[0]})</a>'
                    )
            data["profile"] = self._list_to_str(profiles, "normal")

            img_poster = config_dict["IMAGE_UNKNOW"]
            if poster := item.xpath(
                './/div[contains(@class, "image_content")]//img/@src'
            ):
                if poster_path := await self._get_poster(
                    f"https://image.tmdb.org/t/p/original/{poster[0].rsplit('/', 1)[-1]}"
                ):
                    img_poster = poster_path
            content["poster"] = img_poster

            if provider := item.xpath('.//div[@class="provider"]//@alt'):
                data["provider"] = f"<code>{provider[0]}</code>"
            if trailer := item.xpath('.//a[@class="no_click play_trailer"]/@data-id'):
                content["trailer"] = f"https://youtu.be/{trailer[0]}"

        cast = []
        for cst in html.xpath('//ol[contains(@class, "people scroller")]/li'):
            cp, lnk = cst.xpath("./p/text()"), cst.xpath(".//@href")[0]
            if cp:
                cast.append(f'<a href="{self._tmbd_url + lnk}">{cp[0].strip()}</a>')
            else:
                content["full_cast"] = self._tmbd_url + lnk
        data["cast"] = self._list_to_str(cast, "normal")

        if keywords := html.xpath(
            '//section[@class="keywords right_column"]//li/a/text()'
        ):
            data["keywords"] = self._list_to_str(keywords, "tags")
        if season := html.xpath('//section[@class="panel season"]'):
            data["season"] = f"<code>{season[0].xpath('.//h2//text()')[0]}</code>"
            if info := season[0].xpath(".//h4//text()"):
                data["info"] = f"<code>{info[-1].strip()}</code>"
            if alls := season[0].xpath('.//p[@class="new_button"]/a/@href'):
                content["season"] = self._tmbd_url + alls[0]

        if item := html.xpath('//section[@class="facts left_column"]'):
            item = item[0]
            if org_name := item.xpath(
                './/text()[contains(., "Original Name")]/ancestor::p/text()'
            ):
                data["aka"] = f"<code>{org_name[-1].strip()}</code>"
            if status := item.xpath(
                './/text()[contains(., "Status")]/ancestor::p//text()'
            ):
                data["status"] = f"<code>{status[-1].strip()}</code>"
            if network := item.xpath('.//ul[@class="networks"]'):
                net, lnk = network[0].xpath(".//@alt"), network[0].xpath(".//@href")
                if net:
                    data["network"] = (
                        f'<a href="{self._tmbd_url + lnk[0]}">{net[0].strip(".")}</a>'
                    )
            if type := item.xpath('.//text()[contains(., "Type")]/ancestor::p//text()'):
                data["type"] = f"<code>{type[-1].strip()}</code>"
            if lang := item.xpath(
                './/text()[contains(., "Original Language")]/ancestor::p//text()'
            ):
                data["language"] = f"#{lang[-1].strip()}"
            if budget := item.xpath(
                './/text()[contains(., "Budget")]/ancestor::p//text()'
            ):
                data["budget"] = f"<code>{budget[-1].strip()}</code>"
            if venue := item.xpath(
                './/text()[contains(., "Revenue")]/ancestor::p//text()'
            ):
                data["venue"] = f"<code>{venue[-1].strip()}</code>"

        text = f"<b>TMDB RESULT ~ {self._message.from_user.mention}</b>\n\n"
        text += f'<a href="{self._tmbd_url}{content_id}"><b>{title}</b></a>\n\n'

        template = [
            "aka",
            "rating",
            "genre",
            "profile",
            "language",
            "provider",
            "network",
            "status",
            "season",
            "info",
            "type",
            "budget",
            "venue",
        ]
        for key in template:
            if value := data.get(key):
                text += (
                    f"<b>{key.upper() if key == 'aka' else key.title()}:</b> {value}\n"
                )
        if cast := data.get("cast"):
            text += f"\n<b>CAST</b>\n{cast}\n"
        if keywords := data.get("keywords"):
            text += f"\n<b>KEYWORDS</b>\n{keywords}"

        content["caption"] = text
        content["web_page"] = self._tmbd_url + content_id

    async def _set_imdb_content(self, content_id: str):
        if self._content["content"].get(content_id):
            return
        self._content["content"].update({content_id: {}})
        content = self._content["content"][content_id]
        url = f"https://www.imdb.com/title/tt{content_id}/"
        html = HTML(await self._get_content(url, False))
        imdata = jsonloads(
            html.xpath('//script[@type="application/ld+json"]//text()')[0]
        )
        text = f"<b>IMDb RESULT</b> ~ {self._tag}\n\n"
        typee = f"~ {imdata['@type']}" if imdata.get("@type") else ""
        year = "N/A"
        if years := html.xpath('//h1[@data-testid="hero__pageTitle"]/..//ul//text()'):
            year = list(filter(lambda x: re_match(r"\d{4}", x), years))[0]
        text += (
            f"<a href='{url}'><b>{imdata['name']} ({year})</b></a> <b>{typee}</b>\n\n"
        )
        if aliases := html.xpath(
            '//li[@data-testid="title-details-akas"]//span/text()'
        ):
            text += f"<b>AKA:</b> {self._list_to_str(aliases, 'mono')}\n"
        if runtime := html.xpath(
            '//li[@data-testid="title-techspec_runtime"]/..//div/text()'
        ):
            text += f"<b>Duration:</b> <code>{''.join(runtime)}</code>\n"
        if contenrating := imdata.get("contentRating"):
            text += f"<b>Catrgory:</b> <code>{contenrating}</code>\n"
        if agreerating := imdata.get("aggregateRating"):
            text += f"<b>Rating:</b> ⭐️ <code>{agreerating['ratingValue']}</code> ~ <code>{agreerating['ratingCount']}</code> Vote\n"
        if releases := html.xpath(
            '//li[@data-testid="title-details-releasedate"]//li/a'
        ):
            date, url = (
                releases[0].xpath("./text()")[0],
                releases[0].xpath("./@href")[0],
            )
            text += f"<b>Release:</b> <a href='https://www.imdb.com{url}'>{date}</a>\n"
        if genre := imdata.get("genre"):
            text += f"<b>Genre:</b> {self._list_to_str(genre)}\n"
        if countries := html.xpath(
            '//li[@data-testid="title-details-origin"]//li/a/text()'
        ):
            text += f"<b>Country:</b> {self._list_to_str(countries, 'lang')}\n"
        if languages := html.xpath(
            '//li[@data-testid="title-details-languages"]//li/a/text()'
        ):
            text += f"<b>Language:</b> {self._list_to_str(languages)}\n"
        if directors := imdata.get("director"):
            text += f"<b>Director:</b> {self._list_to_str(directors, 'url')}\n"
        if creators := imdata.get("creator"):
            if creator := self._list_to_str(creators, "person").strip():
                text += f"<b>Writter:</b> {creator}\n"
        if companies := html.xpath(
            '//li[@data-testid="title-details-companies"]//li/a/text()'
        ):
            text += f"<b>Production:</b> {self._list_to_str(companies, 'mono')}\n"
        if official := html.xpath('//li[@data-testid="details-officialsites"]//li'):
            text += f"<b>Original:</b> <a href='{official[0].xpath('./a/@href')[0]}'>{official[0].xpath('./a/text()')[0]}</a>\n"
        if awards := html.xpath('//li[@data-testid="award_information"]/a/text()'):
            text += f"<b>Awards:</b> {self._list_to_str(awards, 'mono')}\n"
        if wins := html.xpath('//li[@data-testid="award_information"]//span/text()'):
            text += f"<b>Wins:</b>{self._list_to_str(wins, 'mono')}\n"
        if cast := imdata.get("actor"):
            text += f"\n<b>CAST:</b>\n{self._list_to_str(cast, 'url')}\n"
        if keywords := imdata.get("keywords"):
            text += (
                f"\n<b>KEYWORDS</b>\n{self._list_to_str(keywords.split(','), 'tags')}"
            )
        content["web_page"] = imdata["url"]
        content["summary"] = (
            f"<b>SUMMARY</b>\n{imdata.get('description', 'Not available!')}"
        )
        if trailer := imdata.get("trailer"):
            content["trailer"] = trailer["url"]
        content["caption"] = text.replace("&apos;", "'")
        img_poster = config_dict["IMAGE_UNKNOW"]

        if imdata.get("image"):
            if poster_path := await self._get_poster(imdata["image"]):
                img_poster = poster_path
        content["poster"] = img_poster

    async def _set_mdl_content(self, content_id: str):
        if self._content["content"].get(content_id):
            return
        self._content["content"].update({content_id: {}})
        content = self._content["content"][content_id]
        data = (
            await self._get_content(
                f"https://kuryana.vercel.app/id/{self._content['mdl'][content_id]}"
            )
        ).get("data", {})
        details, others = data.get("details", {}), data.get("others", {})
        text = (
            f"╭ <b>MYDRAMALIST RESULT</b> ~ {self._tag}\n\n"
            f"├ <a href='{data['link']}'><b>{data['complete_title']}</b></a>\n\n"
            f"├ <b>AKA:</b> {self._list_to_str(others['also_known_as'], 'mono')}\n"
            f"├ <b>Rating:</b> ⭐️ <code>{details['score']}</code>\n"
            f"╰ <b>Genre:</b> {self._list_to_str(others['genres'])}\n"
        )
        if duration := details.get("duration"):
            text += f"├ <b>Duration:</b> <code>{duration}</code>\n"
        text += (
            f"├ <b>Content:</b> <code>{details['content_rating']}</code>\n"
            f"├ <b>Type:</b> <code>{details['type']}</code>\n"
            f"├ <b>Country:</b> #{details['country'].replace(' ', '')}</code>\n"
        )
        if details["type"] == "Movie":
            text += f"├ <b>Release Date:</b> <code>{details['release_date']}</code>\n"
        elif details["type"] == "Drama":
            text += (
                f"├ <b>Episode:</b> <code>{details['episodes']}</code> Episode\n"
                f"├ <b>Aired:</b> <code>{details['aired']}</code>\n"
            )
            if episode := details.get("episodes"):
                text += f"├ <b>Episode:</b> <code>{episode}</code>\n"
            if aired := details.get("aired_on"):
                text += f"├ <b>Aired on:</b> <code>{aired}</code>\n"
            if org_network := details.get("original_network"):
                text += f"├ <b>Network:</b> <code>{org_network}</code>\n"
        text += (
            f"├ <b>CAST</b>\n{self._list_to_str(data['casts'], 'link')}"
            f"\n╰ <b>KEYWORDS</b>\n{self._list_to_str(others['tags'], 'tags')}"
        )
        content["caption"] = text

        img_poster = config_dict["IMAGE_UNKNOW"]
        if img := data.get("poster"):
            index = img.index("https")
            if poster_path := await self._get_poster(img[index:]):
                img_poster = poster_path

        content["poster"] = img_poster
        content["web_page"] = data["link"]
        content["summary"] = f"<b>SYNOPSIS</b>\n{data['synopsis']}"

    async def _set_preposter(self, content_id: str):
        if not self._content["preposter"].get(content_id):
            self.onRun = True
            self._content["preposter"].update({content_id: []})
            html = HTML(
                await self._get_content(
                    f"{self._tmbd_url}{content_id}/images/posters", False
                )
            )
            for item in html.xpath('//ul[@id="image_menu"]/li'):
                lang = item.xpath("./a/text()")[0].split(";")[0].strip()
                code = item.xpath("./a/@href")[0].rsplit("=")[-1]
                count = item.xpath(".//span/text()")[0].rsplit("=")[-1]
                self._content["preposter"][content_id].append((lang, count, code))
            self.onRun = False

    async def _send_poster(self, content_id: str, code: str):
        html = HTML(
            await self._get_content(
                f"{self._tmbd_url}{content_id}/images/posters?image_language={code}",
                False,
            )
        )
        media = []
        for i, img in enumerate(
            html.xpath('//div[contains(@class, "image_content")]/a/@href')[:10], 1
        ):
            cap = html.xpath('//div[contains(@class, "title ott")]/h2/a/text()')[
                0
            ].strip()
            img_path = ospath.join(self._path, f"{i}. {code.upper()} {cap}.jpg")
            await download_content(img, img_path)
            media.append(
                InputMediaPhoto(
                    img_path, f"<b>{i}. {code.upper()}</b> <code>{cap}</code>"
                )
            )

        if media:
            await self._sendAllPoster(media)

    async def list_message(self, content_id: str = "", code: str = ""):
        image, bnum = config_dict["IMAGE_INFO"], 2
        buttons = ButtonMaker()
        match self.status:
            case "":
                buttons.button_data("Change Query", "info|query", "header")
                buttons.button_data("Anime", "info|anime")
                buttons.button_data("Manga", "info|manga")
                buttons.button_data("Character", "info|char")
                buttons.button_data("IMDb", "info|imdb")
                buttons.button_data("TMDb", "info|tmdb")
                buttons.button_data("MyDrama", "info|mdl")
                buttons.button_data("User Info", "info|user")
                text = f"{self._tag}, Choose Available Options Below!"
                if self.query:
                    text += f"<b>Query:</b> {self.query.title()}"
            case "query":
                text = f"{self._tag}, send new query to search..." + (
                    f"\n\n<i>Current query is <b>{self.query}</b></i>"
                    if self.query
                    else ""
                )
            case "anime":
                json = (
                    await self._anim_content(anime_query, {"search": self.query})
                ).get("Media")
                text = f"Not found Anime for **{self.query.title()}**."
                if json:
                    text = (
                        f"**ANIME RESULT** ~ {self._anitag}\n\n(`{native}`)\n"
                        if (native := json.get("title", {}).get("native"))
                        else "\n"
                        f"**{json['title']['romaji']}** "
                        f"**Type:** `{json['format']}`\n"
                        f"**Status:** `{json['status']}`\n"
                        f"**Episodes:** `{json.get('episodes', 'N/A')}`\n"
                        f"**Duration:** `{json.get('duration', 'N/A')}`\n"
                        f"**Score:** `{json['averageScore']}`\n"
                        "**Genres:** "
                        + ", ".join(f"`{x}`" for x in json["genres"])
                        + "\n"
                        "**Studios:** "
                        + ", ".join(f"`{x['name']}`" for x in json["studios"]["nodes"])
                        + "\n"
                    )
                    trailer = json.get("trailer")
                    if trailer and trailer.get("site") == "youtube":
                        trailer = f"https://youtu.be/{trailer.get('id')}"
                    description = (
                        json.get("description", "N/A")
                        .replace("<i>", "")
                        .replace("</i>", "")
                        .replace("<br>", "")
                    )
                    text += self._shorten(description, json.get("siteUrl"))
                    if trailer:
                        buttons.button_link("Trailer", trailer)
                    buttons.button_link("More Info", json.get("siteUrl"))
                    if json.get("bannerImage"):
                        image = json["bannerImage"]
            case "manga":
                text = f"Not found Manga for **{self.query.title()}**."
                json = (
                    await self._anim_content(manga_query, {"search": self.query})
                ).get("Media")
                if json:
                    text = f"**MANGA RESULT** ~ {self._anitag}\n\n"
                    if name := json.get("title", {}).get("romaji"):
                        text += f"**{name}** "
                    if native := json.get("title", {}).get("native"):
                        text += f"(`{native}`)"
                    if start_date := json.get("startDate", {}).get("year"):
                        text += f"\n**Start Date**: `{start_date}`"
                    if status := json.get("status"):
                        text += f"\n**Status**: `{status}`"
                    if score := json.get("averageScore"):
                        text += f"\n**Score**: `{score}`"
                    text += (
                        "\n**Genres**: "
                        + ", ".join(f"`{x}`" for x in json.get("genres", []))
                        + "\n"
                        f"__{json.get('description').replace('<br><br>', '')}__"
                    )
                    image = (
                        json["bannerImage"]
                        if json.get("bannerImage")
                        else config_dict["IMAGE_UNKNOW"]
                    )
            case "char":
                json = (
                    await self._anim_content(character_query, {"query": self.query})
                ).get("Character")
                text = f"Not found Character for **{self.query.title()}**."
                if json:
                    text = (
                        f"**CHARACTER RESULT** ~ {self._anitag}\n\n"
                        f"**{json.get('name').get('full')}**"
                        f"(`{native})`\n"
                        if (native := json.get("name").get("native"))
                        else "\n"
                    )
                    description = f"{json['description']}"
                    text += self._shorten(description, json.get("siteUrl"))
                    buttons.button_link("More info", json.get("siteUrl"))
                    image = (
                        json["image"]["large"]
                        if json.get("image", {}).get("large")
                        else config_dict["IMAGE_UNKNOW"]
                    )
            case "user":
                self.onRun = True
                user_id = (
                    self._message.reply_to_message.from_user.id
                    if self._message.reply_to_message
                    else self._message.from_user.id
                )
                user = await self._client.get_users(user_id)
                try:
                    image = await self._client.download_media(
                        user.photo.big_file_id, file_name=f"./{user.id}.png"
                    )
                except:
                    image = config_dict["IMAGE_UNKNOW"]
                try:
                    user_member = await self._client.get_chat_member(
                        self._message.chat.id, user_id
                    )
                    user_member = (
                        f"<b>┊ Status:</b> {user_member.status.name.title()}\n"
                    )
                    user_member += (
                        f"<b>┊ Joined:</b> {user_member.joined_date or '~'}\n"
                    )
                except:
                    user_member = ""
                text = (
                    "<b>USER INFO</b>\n"
                    f"<b>╭ ID:</b> <code>{user.id}</code>\n"
                    f"<b>┊ First Name:</b> {user.first_name}\n"
                    f"<b>┊ Last Name:</b> {user.last_name or '~'}\n"
                    f"<b>┊ Username:</b> {f'@{user.username}' or '~'}\n"
                    f"<b>┊ Language:</b> {user.language_code.upper() if user.language_code else '~'}\n"
                    f"{user_member}"
                    f"<b>┊ Premium User:</b> {'Yes' if user.is_premium else 'No'}\n"
                    f"<b>╰ DC ID:</b> {user.dc_id or '~'}"
                )
                if user.username:
                    buttons.button_link("Details", f"https://t.me/{user.username}")
                self.onRun = False
            case "tmdb" | "imdb" | "mdl" as value:
                await self._set_list_content(image)
                if base_data := self._content["base"][self.status].get(self.query):
                    text = f"Found {len(base_data)} Result(s) For <b>{self.query}</b> ~ {self._tag}\n\n"
                    match value:
                        case "tmdb":
                            image, bnum = config_dict["IMAGE_TMDB"], 6
                            for index, (name, id_) in enumerate(base_data[:24], 1):
                                text += f"<b>{index}.</b> {name}\n"
                                buttons.button_data(index, f"info|tmdbdata|{id_}")
                        case "imdb":
                            image, bnum = config_dict["IMAGE_IMDB"], 4
                            for count, movie in enumerate(base_data, start=1):
                                mname = movie.get("l")
                                year = f"({movie['y']})" if movie.get("y") else "N/A"
                                typee = (
                                    movie.get("q", "N/A")
                                    .replace("feature", "movie")
                                    .capitalize()
                                )
                                movieid = re_findall(r"tt(\d+)", movie.get("id"))[0]
                                text += f"{count}. <b>{mname} {year} ~ {typee}</b>\n"
                                buttons.button_data(count, f"info|imdbdata|{movieid}")
                        case _:
                            image, bnum = config_dict["IMAGE_MDL"], 5
                            for index, movie in enumerate(base_data, start=1):
                                slugid = movie["slug"].split("-", maxsplit=1)[0]
                                self._content["mdl"][slugid] = movie["slug"]
                                text += f"{index}. <b>{movie['title']} ({movie['year']}) ~ ({movie['type']})</b>\n"
                                buttons.button_data(index, f"info|mdldata|{slugid}")
                else:
                    text = f"Search not found for <b>{self.query}</b>!"
            case "tmdbdata" | "imdbdata" | "mdldata" as value:
                func_dict = {
                    "tmdbdata": ("tmdb", self._set_tmdb_content),
                    "imdbdata": ("imdb", self._set_imdb_content),
                    "mdldata": ("mdl", self._set_mdl_content),
                }

                self.onRun = True
                cb, func = func_dict[value]
                await func(content_id)
                self.onRun = False

                content = self._content["content"][content_id]
                text, image = content["caption"], content["poster"]
                if content.get("trailer"):
                    buttons.button_link("Trailer", content["trailer"], "header")
                if content.get("season"):
                    buttons.button_link("All Season", content["season"], "header")
                if content.get("full_cast"):
                    buttons.button_link("Full Cast", content["full_cast"], "header")
                if content.get("web_page"):
                    buttons.button_link("Go Site", content["web_page"], "header")
                if self.status == "tmdbdata":
                    buttons.button_data("Poster", f"info|preposter|{content_id}")
                if self.status in ["tmdbdata", "imdbdata"]:
                    buttons.button_data("Set Poster", f"info|setthumb|{content_id}")
                buttons.button_data(
                    "Summary", f"info|summary|{content_id}|{self.status}"
                )
                buttons.button_data("<<", f"info|{cb}|home", "footer")
            case "preposter":
                content = self._content["content"][content_id]
                text, image = content["caption"], content["poster"]
                await self._set_preposter(content_id)
                for lang, count, mcode in self._content["preposter"][content_id]:
                    buttons.button_data(
                        f"{lang} ({count})", f"info|poster|{content_id}|{mcode}"
                    )
                buttons.button_data("<<", f"info|tmdbdata|{content_id}", "footer")
            case "summary":
                content = self._content["content"][content_id]
                text, image = content["summary"], content["poster"]
                buttons.button_data("<<", f"info|{code}|{content_id}", "footer")
            case "poster":
                content = self._content["content"][content_id]
                text, image = content["caption"], content["poster"]
                await gather(
                    editPhoto(
                        "<i>Generating poster, please wait...</i>", self.editable, image
                    ),
                    self._send_poster(content_id, code),
                )
                self.status = "preposter"
                await self.list_message(content_id, code)
                return

        if self.status and self.status not in [
            "mdldata",
            "imdbdata",
            "tmdbdata",
            "preposter",
            "summary",
        ]:
            buttons.button_data("<<", "info|back", "footer")
        if self.status != "query":
            buttons.button_data("Close", "info|close", "footer")
        editData = (
            self._editAnime if self.status in {"anime", "manga", "char"} else editPhoto
        )
        if not await editData(text, self.editable, image, buttons.build_menu(bnum, 3)):
            await editData(
                text,
                self.editable,
                config_dict["IMAGE_INFO"],
                buttons.build_menu(bnum, 3),
            )

    @new_task
    async def newEvent(self):
        future = self._event_handler()
        self.editable = await sendPhoto(
            "<i>Checking for request, please wait...</i>",
            self._message,
            config_dict["IMAGE_INFO"],
        )
        await gather(
            makedirs(self._path, exist_ok=True),
            self.list_message(),
            wrap_future(future),
        )


async def change_query(_, message: Message, obj: Info):
    obj.status = ""
    obj.query_event.set()
    obj.query = message.text.lower().strip()
    await gather(deleteMessage(message), obj.list_message())


@new_task
async def info_callback(_, query: CallbackQuery, obj: Info):
    data = query.data.split("|")
    if obj.onRun:
        await query.answer()
        return
    if data[1] == "setthumb":
        content_id = data[2]
        content = obj._content["content"].get(content_id)
        if (
            content
            and content.get("poster")
            and content["poster"] != config_dict["IMAGE_UNKNOW"]
        ):
            from PIL import Image
            from bot import DATABASE_URL
            from bot.helper.ext_utils.bot_utils import update_user_ldata, sync_to_async
            from bot.helper.ext_utils.db_handler import DbManager
            from aiofiles.os import makedirs

            user_id = query.from_user.id
            poster_path = content["poster"]
            dest_path = ospath.join("thumbnails", f"{user_id}.jpg")
            await makedirs("thumbnails", exist_ok=True)

            def save_thumb():
                with Image.open(poster_path) as img:
                    img.convert("RGB").save(dest_path, "JPEG")

            await sync_to_async(save_thumb)
            await update_user_ldata(user_id, "thumb", dest_path)
            if DATABASE_URL:
                await DbManager().update_user_doc(user_id, "thumb", dest_path)
            await query.answer("Poster set as custom thumbnail successfully!", True)
        else:
            await query.answer("No valid poster found to set as thumbnail!", True)
        return
    if data[1] == "close":
        await query.answer()
        obj.event.set()
        await deleteMessage(
            obj.editable, obj.editable.reply_to_message, obj._message.reply_to_message
        )
        return
    if data[1] in ["anime", "manga", "char", "imdb", "mdl", "tmdb"] and not obj.query:
        await query.answer("Upss, give a query to continue!", True)
        return
    await query.answer()
    if data[1] == "back":
        obj.query_event.set()
        obj.query_event.clear()
        obj.status = ""
    else:
        obj.status = data[1]
    code = data[3] if data[1] in ("poster", "summary") else ""
    id_ = data[2] if len(data) > 2 else ""
    await obj.list_message(id_, code)
    if obj.status == "query":
        obj.change_query_handler()


@new_task
async def search_info(client: Client, message: Message):
    reply_to = message.reply_to_message

    if fmsg := await UseCheck(message).run():
        await auto_delete_message(message, fmsg, reply_to)
        return
    query = reply_to.text if reply_to else " ".join(message.command[1:])
    Info(client, message, query).newEvent()


bot.add_handler(
    MessageHandler(
        search_info, filters=command(BotCommands.InfoCommand) & CustomFilters.authorized
    )
)
