# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

import re
import os
import warnings
from os import path as ospath

try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning, module="PTN")
        import PTN
    HAS_PTN = True
except ImportError:
    HAS_PTN = False
from aiohttp import ClientSession
from lxml.etree import HTML
from bot import LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async


class ThumbnailFetcher:
    TMDB_BASE_URL = "https://www.themoviedb.org"
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"
    VIDEO_EXTENSIONS = {
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpg",
        ".mpeg",
        ".ts",
        ".mts",
        ".m2ts",
    }

    @staticmethod
    def is_video_file(filename: str) -> bool:
        return ospath.splitext(filename)[1].lower() in ThumbnailFetcher.VIDEO_EXTENSIONS

    @staticmethod
    def parse_filename(filename: str) -> dict:
        base_name = ospath.splitext(os.path.basename(filename))[0]
        if HAS_PTN:
            try:
                ptn_result = PTN.parse(base_name)
                title = ptn_result.get("title", "").strip()
                year = ptn_result.get("year")  # returned as int by PTN
                season = ptn_result.get("season")
                episode = ptn_result.get("episode")
                episode_name = ptn_result.get("episodeName")
                is_tv = season is not None or episode is not None or bool(episode_name)
            except Exception as e:
                LOGGER.error(f"PTN parse error: {e}")
                title = ""
                year = season = episode = episode_name = None
                is_tv = False
        else:
            title = ""
            year = season = episode = episode_name = None
            is_tv = False

        # Fallback: if PTN couldn't extract a meaningful title, do basic cleaning
        if not title or len(title) < 2:
            name = base_name
            name = re.sub(r"[._\-]", " ", name)
            year_match = re.search(r"\b(19|20)\d{2}\b", name)
            yr = str(year_match.group()) if year_match else None
            if yr:
                name = name.split(yr)[0].strip()

            tv_match = re.search(
                r"\b[sS](\d+)\s*[eE](\d+)\b|\b[sS]eason\s*(\d+)\b", name, re.IGNORECASE
            )
            se = None
            is_tv = False
            if tv_match:
                is_tv = True
                groups = tv_match.groups()
                se = int(groups[0] or groups[2])
                if groups[0]:
                    name = re.split(r"\b[sS]\d+", name, flags=re.IGNORECASE)[0].strip()
                else:
                    name = re.split(r"\b[sS]eason\s*\d+", name, flags=re.IGNORECASE)[
                        0
                    ].strip()

            name = re.sub(r"\s+", " ", name).strip()
            name = re.sub(
                r"\b(360|480|720|1080|2160)[pP]\b|\b[sS][dD]\b|\b[hH][dD]\b", "", name
            )
            name = re.sub(
                r"\b(bluray|webrip|web-dl|web|dvd|brrip|bdrip|x264|x265|hevc|10bit)\b",
                "",
                name,
                flags=re.IGNORECASE,
            )
            name = re.sub(r"\s+", " ", name).strip()
            title, year, season = name, yr, se

        # PTN does not consistently recognise verbose episode labels used by
        # anime packs ("Ep. 01", "Episode 3", "Science Lesson 1", etc.).
        # Searching the full episode filename as a movie produces no result and
        # causes one network request per file.  Reduce those names to the show.
        episode_marker = re.search(
            r"\s+(?:-\s+)?(?:ep(?:isode)?\.?\s*\d+|extra\b|mv\b|pv\b|science lesson\b)",
            title,
            re.IGNORECASE,
        )
        if episode_marker:
            title = title[: episode_marker.start()].strip()
            is_tv = True

        season_match = re.search(r"\bS(\d{1,2})(?:\s*E\d+)?\b", title, re.IGNORECASE)
        if season_match:
            season = season or int(season_match.group(1))
            title = title[: season_match.start()].strip()
            is_tv = True

        return {
            "name": title,
            "year": str(year) if year else None,
            "is_tv": is_tv,
            "season": season,
        }

    @classmethod
    def cache_key(cls, filename: str, mode: str = "poster") -> tuple:
        """Return a stable key shared by split files for the same title."""
        parsed = cls.parse_filename(filename)
        return (
            parsed.get("name", "").casefold(),
            parsed.get("year"),
            bool(parsed.get("is_tv")),
            parsed.get("season"),
            mode,
        )

    @staticmethod
    async def search_tmdb(
        query: str,
        year: str = None,
        is_tv: bool = False,
        season: int = None,
        mode: str = "poster",
    ) -> str or None:
        try:
            from urllib.parse import quote

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }

            search_types = ["tv", "movie"] if is_tv else ["movie", "tv"]

            async with ClientSession() as session:
                for search_type in search_types:
                    for try_year in [year, None] if year else [None]:
                        if try_year is None and year is not None:
                            search_query = re.sub(
                                r"\b" + re.escape(str(year)) + r"\b", "", query
                            ).strip()
                        else:
                            search_query = query

                        search_url = f"{ThumbnailFetcher.TMDB_BASE_URL}/search/{search_type}?query={quote(search_query)}"

                        if try_year and search_type == "movie":
                            search_url += f"&year={try_year}"
                        elif try_year and search_type == "tv":
                            search_url += f"&first_air_date_year={try_year}"

                        LOGGER.debug(f"TMDB search URL: {search_url}")

                        async with session.get(
                            search_url, headers=headers, ssl=False, timeout=10
                        ) as resp:
                            if resp.status != 200:
                                continue
                            html_content = await resp.text()

                        html = HTML(html_content)

                        if search_type == "tv" and season:
                            show_links = [
                                l
                                for l in html.xpath(
                                    '//a[contains(@href, "/tv/")]/@href'
                                )
                                if re.search(r"/tv/\d+", l)
                            ]
                            if show_links:
                                show_path = show_links[0]

                                if mode == "backdrop":
                                    backdrop_url = (
                                        await ThumbnailFetcher._try_fetch_backdrop(
                                            session, show_path, headers
                                        )
                                    )
                                    if backdrop_url:
                                        return backdrop_url

                                season_url = f"{ThumbnailFetcher.TMDB_BASE_URL}{show_path}/season/{season}"
                                LOGGER.info(
                                    f"TMDB fetching season {season} poster from: {season_url}"
                                )

                                async with session.get(
                                    season_url, headers=headers, ssl=False, timeout=10
                                ) as season_resp:
                                    if season_resp.status == 200:
                                        season_html_content = await season_resp.text()
                                        season_html = HTML(season_html_content)

                                        season_posters = season_html.xpath(
                                            '//div[contains(@class, "poster")]//img/@src'
                                        )
                                        if not season_posters:
                                            season_posters = season_html.xpath(
                                                '//img[contains(@src, "/t/p/")]/@src'
                                            )

                                        if season_posters:
                                            poster_path = season_posters[0]
                                            poster_match = re.search(
                                                r"/t/p/[^/]+/(.+)", poster_path
                                            )
                                            if poster_match:
                                                poster_filename = poster_match.group(1)
                                                full_url = f"{ThumbnailFetcher.TMDB_IMAGE_BASE}/{poster_filename}"
                                                LOGGER.info(
                                                    f"TMDB season {season} poster URL: {full_url}"
                                                )
                                                return full_url

                        posters = html.xpath(
                            '//div[contains(@class, "poster")]//img/@src'
                        )
                        if not posters:
                            posters = html.xpath("//a[@data-id]/img/@src")
                        if not posters:
                            posters = html.xpath('//img[contains(@src, "/t/p/")]/@src')

                        if posters:
                            detail_links = [
                                l
                                for l in html.xpath(
                                    f'//a[contains(@href, "/{search_type}/")]/@href'
                                )
                                if re.search(rf"/{search_type}/\d+", l)
                            ]
                            if mode == "backdrop" and detail_links:
                                backdrop_url = (
                                    await ThumbnailFetcher._try_fetch_backdrop(
                                        session, detail_links[0], headers
                                    )
                                )
                                if backdrop_url:
                                    return backdrop_url

                            poster_path = posters[0]
                            LOGGER.debug(f"TMDB found poster path: {poster_path}")

                            poster_match = re.search(r"/t/p/[^/]+/(.+)", poster_path)
                            if poster_match:
                                poster_filename = poster_match.group(1)
                                full_url = f"{ThumbnailFetcher.TMDB_IMAGE_BASE}/{poster_filename}"
                                LOGGER.info(
                                    f"TMDB poster URL (original quality): {full_url}"
                                )
                                return full_url

                            if poster_path.startswith("http"):
                                upgraded = re.sub(
                                    r"/t/p/[^/]+/", "/t/p/original/", poster_path
                                )
                                LOGGER.info(f"TMDB poster URL (upgraded): {upgraded}")
                                return upgraded

                        if try_year is not None:
                            LOGGER.info(
                                f"TMDB: No poster with year={try_year}, retrying without year filter (query: '{search_query}')"
                            )

            return None

        except Exception as e:
            LOGGER.error(f"TMDB search error: {e}")
            return None

    @staticmethod
    async def _try_fetch_backdrop(
        session: ClientSession, detail_path: str, headers: dict
    ) -> str or None:
        """Fetch a landscape backdrop from a TMDB movie/TV detail page."""
        try:
            backdrop_url = (
                f"{ThumbnailFetcher.TMDB_BASE_URL}{detail_path}/images/backdrops"
            )
            LOGGER.info(f"TMDB fetching backdrop from: {backdrop_url}")

            async with session.get(
                backdrop_url, headers=headers, ssl=False, timeout=10
            ) as resp:
                if resp.status != 200:
                    LOGGER.debug(f"TMDB backdrop page returned {resp.status}")
                    return None
                html_content = await resp.text()

            html = HTML(html_content)

            backdrop_links = html.xpath(
                '//img[contains(@src, "w500_and_h282_face")]/ancestor::a[1]/@href'
            )
            if not backdrop_links:
                LOGGER.debug("TMDB no backdrop images found on gallery page")
                return None

            backdrop_path = backdrop_links[0]
            LOGGER.debug(f"TMDB found backdrop link: {backdrop_path}")
            LOGGER.info(f"TMDB backdrop URL: {backdrop_path}")
            return backdrop_path

        except Exception as e:
            LOGGER.error(f"TMDB backdrop fetch error: {e}")
            return None

    @staticmethod
    async def download_poster(url: str, user_id: int) -> str or None:
        try:
            import tempfile
            from PIL import Image

            fd, temp_path = tempfile.mkstemp(
                suffix=".jpg", prefix=f"aut_thumb_{user_id}_"
            )
            try:
                os.close(fd)
            except Exception:
                pass

            async with ClientSession() as session:
                async with session.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    timeout=15,
                ) as resp:
                    if resp.status != 200:
                        return None
                    content = await resp.read()

            def save_image():
                from io import BytesIO

                img = Image.open(BytesIO(content))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(temp_path, "JPEG", quality=95)
                return temp_path

            return await sync_to_async(save_image)

        except Exception as e:
            LOGGER.error(f"Poster download error: {e}")
            return None

    @classmethod
    async def fetch_thumbnail(
        cls, filename: str, user_id: int, mode: str = "poster"
    ) -> str or None:
        if not cls.is_video_file(filename):
            LOGGER.debug(f"Auto-thumbnail: Skipping non-video file: {filename}")
            return None

        parsed = cls.parse_filename(filename)
        if (
            not parsed["name"]
            or len(parsed["name"]) < 3
            or not re.search(r"[A-Za-z]", parsed["name"])
        ):
            LOGGER.debug(
                f"Auto-thumbnail: Could not extract a meaningful title from: {filename}"
            )
            return None

        is_tv = parsed.get("is_tv", False)
        season = parsed.get("season")
        if is_tv:
            query = parsed["name"]
        else:
            query = f"{parsed['name']} {parsed.get('year') or ''}".strip()

        LOGGER.info(
            f"Auto-thumbnail: Searching for '{query}' (TV: {is_tv}, Season: {season}, Year: {parsed.get('year')}, Mode: {mode})"
        )

        poster_url = await cls.search_tmdb(
            query, parsed.get("year"), is_tv=is_tv, season=season, mode=mode
        )

        if poster_url:
            thumbnail_path = await cls.download_poster(poster_url, user_id)
            if thumbnail_path:
                LOGGER.info(
                    f"Auto-thumbnail: Successfully fetched poster for '{query}'"
                )
                return thumbnail_path

        LOGGER.warning(f"Auto-thumbnail: No poster found for '{query}'")
        return None

    @staticmethod
    async def cleanup_thumbnail(thumb_path: str):
        try:
            if thumb_path and ospath.exists(thumb_path):
                from aiofiles.os import remove

                await remove(thumb_path)
                LOGGER.debug(f"Auto-thumbnail: Cleaned up {thumb_path}")
        except Exception as e:
            LOGGER.error(f"Auto-thumbnail cleanup error: {e}")
