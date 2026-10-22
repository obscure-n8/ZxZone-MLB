from base64 import b64decode
from cloudscraper import create_scraper
from hashlib import sha256
from http.cookiejar import MozillaCookieJar
from json import loads as jsonloads
from lxml.etree import HTML
from natsort import natsorted
from os import path as ospath
from re import findall as re_findall, match as re_match, search as re_search, DOTALL
from requests import Session, session as req_session, post as rpost
from requests.adapters import HTTPAdapter
from time import sleep
from urllib.parse import parse_qs, urlparse, unquote, urljoin
from urllib3.util.retry import Retry
from uuid import uuid4

from bot import config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import getSizeBytes
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.help_messages import HelpString
from bot.helper.ext_utils.links_utils import is_sharer_link, is_gdrive_link
from bot.helper.ext_utils.status_utils import get_readable_time, speed_string_to_bytes


_caches = {}


class siteList:
    DOOD = [
        "dood.watch",
        "doodstream.com",
        "dood.to",
        "dood.so",
        "dood.cx",
        "dood.la",
        "dood.ws",
        "dood.sh",
        "doodstream.co",
        "dood.pm",
        "dood.wf",
        "d0o0d.com",
        "do0od.com",
        "dood.re",
        "dood.video",
        "dooood.com",
        "dood.yt",
        "doods.yt",
        "dood.stream",
        "doods.pro",
        "ds2play.com",
        "dood.zip",
        "poops.media",
        "ds2video.com",
        "d0000d.com",
    ]
    HOSTER = [
        "1fichier.com",
        "antfiles.com",
        "github.com",
        "gofile.io",
        "hxfile.co",
        "krakenfiles.com",
        "letsupload.io",
        "mdisk.me",
        "mediafire.com",
        "onedrive.com",
        "osdn.net",
        "pixeldrain.com",
        "racaty.net",
        "romsget.io",
        "send.cm",
        "sfile.mobi",
        "solidfiles.com",
        "sourceforge.net",
        "uploadbaz.me",
        "upload.ee",
        "uploadhaven.com",
        "uppit.com",
        "uptobox.com",
        "userscloud.com",
        "wetransfer.com",
        "yandex.com",
        "zippyshare.com",
        "racaty.io",
    ]
    LBOX = ["linkbox.to", "lbx.to", "teltobx.net", "telbx.net"]
    LIION_WISH = [
        "vidhide.com",
        "vidhidepro.com",
        "filelions.site",
        "filelions.live",
        "filelions.to",
        "filelions.online",
        "cabecabean.lol",
        "embedwish.com",
        "streamwish.com",
        "kitabmarkaz.xyz",
        "wishfast.top",
        "streamwish.to",
    ]
    TERA = [
        "terabox.com",
        "nephobox.com",
        "4funbox.com",
        "mirrobox.com",
        "momerybox.com",
        "teraboxapp.com",
        "1024tera.com",
        "terabox.app",
        "gibibox.com",
    ]
    GSHARER = ["appdrive", "gdtot", "gdflix", "sharer"]
    FEMBED = [
        "fembed.net",
        "fembed.com",
        "femax20.com",
        "fcdn.stream",
        "feurl.com",
        "layarkacaxxi.icu",
        "naniplay.nanime.in",
        "naniplay.nanime.biz",
        "naniplay.com",
        "mm9842.comjavcl.me",
        "asianclub.tv",
        "javhdfree.icu",
        "sexhd.co",
        "vanfem.com",
    ]
    STAPE = [
        "streamtape.com",
        "streamtape.co",
        "streamtape.cc",
        "streamtape.to",
        "streamtape.net",
        "streamta.pe",
        "streamtape.xyz",
    ]
    RCL = [
        "edytjedhgmdhm.abfhaqrhbnf.workers.dev",
        "odd-bird-1319.zwuhygoaqe.workers.dev",
        "hello-world-flat-violet-6291.wstnjewyeaykmdg.workers.dev",
        "worker-mute-fog-66ae.ihrqljobdq.workers.dev",
        "worker-square-heart-580a.uieafpvtgl.workers.dev",
        "worker-little-bread-2c2f.wqwmiuvxws.workers.dev",
    ]
    if config_dict["RCLONE_SERVE_URL"]:
        RCL.append(config_dict["RCLONE_SERVE_URL"])

    @property
    def all(self):
        return natsorted(
            self.DOOD
            + self.HOSTER
            + self.LIION_WISH
            + self.TERA
            + self.GSHARER
            + self.FEMBED
            + self.STAPE
        )


sites = siteList()


def direct_link_generator(link: str):
    domain = urlparse(link).hostname
    if not domain:
        raise DirectDownloadLinkException("ERROR: Invalid URL")
    if "youtube.com" in domain or "youtu.be" in domain:
        raise DirectDownloadLinkException("ERROR: Use ytdl cmds for YouTube links!")
    # File Hoster
    if "1fichier.com" in domain:
        return fichier(link)
    if any(x in domain for x in ["akmfiles.com", "akmfls.xyz"]):
        return akmfiles(link)
    if any(x in domain for x in sites.DOOD):
        return doods(link)
    if "easyupload.io" in domain:
        return easyupload(link)
    if any(x in domain for x in sites.LIION_WISH):
        return filelions_and_streamwish(link)
    if "github.com" in domain:
        return github(link)
    if "gofile.io" in domain:
        return gofile(link)
    if "hxfile.co" in domain:
        return hxfile(link)
    if "krakenfiles.com" in domain:
        return krakenfiles(link)
    if any(x in domain for x in sites.LBOX):
        return linkBox(link)
    if "mdisk.me" in domain:
        return mdisk(link)
    if "mediafire.com" in domain:
        return mediafire(link)
    if "1drv.ms" in domain:
        return onedrive(link)
    if "osdn.net" in domain:
        return osdn(link)
    if "u.pcloud.link" in domain:
        return pcloud(link)
    if "pixeldrain.com" in domain:
        return pixeldrain(link)
    if "qiwi.gg" in domain:
        return qiwi(link)
    if "racaty" in domain:
        return racaty(link)
    if any(x in link for x in sites.RCL):
        return rc(link)
    if "send.cm" in domain:
        return sendcm(link)
    if "shrdsk.me" in domain:
        return shrdsk(link)
    if "solidfiles.com" in domain:
        return solidfiles(link)
    if any(x in domain for x in ["streamhub.ink", "streamhub.to"]):
        return streamhub(link)
    if "streamvid.net" in domain:
        return streamvid(link)
    if "tmpsend.com" in domain:
        return tmpsend(link)
    if any(x in domain for x in sites.TERA):
        return terabox(link)
    if "uploadbaz.me" in domain:
        return uploadbaz(link)
    if "upload.ee" in domain:
        return uploadee(link)
    if "uptobox.com" in domain:
        raise DirectDownloadLinkException("ERROR: Uptobox currently DEAD!")
    if "userscloud.com" in domain:
        return userscloud(link)
    if any(x in domain for x in ["wetransfer.com", "we.tl"]):
        return wetransfer(link)
    # Video Hoster
    if any(x in domain for x in sites.FEMBED):
        return fembed(link)
    if "mp4upload.com" in domain:
        return mp4upload(link)
    if any(x in domain for x in sites.STAPE):
        return streamtape(link)
    # GDrive Sharer
    if is_sharer_link(link):
        if is_gdrive_link(link):
            return link
        if "gdtot" in domain:
            return gdtot(link)
        if any(x in domain for x in ["filepress", "onlystream"]):
            return filepress(link)
        return sharerpw(link) if "sharer.pw" in domain else sharer_scraper(link)
    raise DirectDownloadLinkException(f"No direct link function found for {link}")


def cf_bypass(url):
    """DO NOT ABUSE THIS"""
    try:
        data = {"cmd": "request.get", "url": url, "maxTimeout": 60000}
        _json = rpost(
            "https://cf.jmdkh.eu.org/v1",
            headers={"Content-Type": "application/json"},
            json=data,
            timeout=60,
        ).json()
        if _json["status"] == "ok":
            return _json["solution"]["response"]
    except Exception as e:
        e
    raise DirectDownloadLinkException("ERROR: Con't bypass cloudflare")


def get_captcha_token(session, params):
    recaptcha_api = "https://www.google.com/recaptcha/api2"
    res = session.get(f"{recaptcha_api}/anchor", params=params)
    anchor_html = HTML(res.text)
    if not (anchor_token := anchor_html.xpath('//input[@id="recaptcha-token"]/@value')):
        return
    params["c"] = anchor_token[0]
    params["reason"] = "q"
    res = session.post(f"{recaptcha_api}/reload", params=params)
    if token := re_findall(r'"rresp","(.*?)"', res.text):
        return token[0]


# ================================================== FILE HOSTER ===============================================
def fichier(link: str):
    """1Fichier direct link generator
    Based on https://github.com/Maujar
    """
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    gan = re_match(regex, link)
    if not gan:
        raise DirectDownloadLinkException("ERROR: The link you entered is wrong!")
    if "::" in link:
        pswd = link.split("::")[-1]
        url = link.split("::")[-2]
    else:
        pswd = None
        url = link
    cget = create_scraper().request
    try:
        if pswd is None:
            req = cget("post", url)
        else:
            pw = {"pass": pswd}
            req = cget("post", url, data=pw)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if req.status_code == 404:
        raise DirectDownloadLinkException(
            "ERROR: File not found/The link you entered is wrong!"
        )
    html = HTML(req.text)
    if dl_url := html.xpath('//a[@class="ok btn-general btn-orange"]/@href'):
        return dl_url[0]
    if not (ct_warn := html.xpath('//div[@class="ct_warn"]')):
        raise DirectDownloadLinkException(
            "ERROR: Error trying to generate Direct Link from 1fichier!"
        )
    if len(ct_warn) == 3:
        str_2 = ct_warn[-1].text
        if "you must wait" in str_2.lower():
            if numbers := [int(word) for word in str_2.split() if word.isdigit()]:
                raise DirectDownloadLinkException(
                    f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute."
                )
            raise DirectDownloadLinkException(
                "ERROR: 1fichier is on a limit. Please wait a few minutes/hour."
            )
        if "protect access" in str_2.lower():
            raise DirectDownloadLinkException(
                f"ERROR:\n{HelpString.PASSWORD_ERROR_MESSAGE.format(link)}"
            )
        raise DirectDownloadLinkException(
            "ERROR: Failed to generate Direct Link from 1fichier!"
        )
    if len(ct_warn) == 4:
        str_1 = ct_warn[-2].text
        str_3 = ct_warn[-1].text
        if "you must wait" in str_1.lower():
            if numbers := [int(word) for word in str_1.split() if word.isdigit()]:
                raise DirectDownloadLinkException(
                    f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute."
                )
            raise DirectDownloadLinkException(
                "ERROR: 1fichier is on a limit. Please wait a few minutes/hour."
            )
        if "bad password" in str_3.lower():
            raise DirectDownloadLinkException(
                "ERROR: The password you entered is wrong!"
            )
    raise DirectDownloadLinkException(
        "ERROR: Error trying to generate Direct Link from 1fichier!"
    )


def akmfiles(url):
    with create_scraper() as session:
        try:
            html = HTML(
                session.post(
                    url, data={"op": "download2", "id": url.split("/")[-1]}
                ).text
            )
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if direct_link := html.xpath("//a[contains(@class,'btn btn-dow')]/@href"):
        return direct_link[0]
    raise DirectDownloadLinkException("ERROR: Direct link not found!")


def anonbase(url: str):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if sa := html.xpath('//*[@id="download-url"]/@href'):
            return sa[0]
        raise DirectDownloadLinkException("ERROR: File not found!")


def doods(url: str):
    details = {"contents": [], "title": "", "total_size": 0, "header": ""}
    names = set()
    with create_scraper() as session:

        def _fetch_content(url: str, path="", index: int = 0):
            url = f"https://api.pake.tk/dood?url={url}"
            try:
                respon = session.get(url)
            except Exception as e:
                if path:
                    return
                raise DirectDownloadLinkException(f"ERROR: {e}.") from e

            if respon.status_code != 200:
                if path:
                    return
                raise DirectDownloadLinkException(
                    f"ERROR: Got response code: {respon.status_code}"
                )

            json_data = respon.json()

            if not json_data["success"]:
                if path:
                    return
                raise DirectDownloadLinkException("ERROR: Failed to get details!")

            if not details["title"]:
                details["title"] = path

            if isinstance(json_data["data"], dict):
                if direct_link := json_data["data"].get("direct_link"):
                    name = json_data["data"].get("title", "")
                    if name in names:
                        name = f"{index}. {name}"
                    names.add(name)
                    index += 1
                    item = {
                        "url": direct_link,
                        "filename": f"{name}.mp4",
                        "path": path,
                        "header": f"Referer: {json_data['referer']}",
                    }
                    details["contents"].append(item)
                    details["total_size"] += getSizeBytes(json_data["data"]["size"])
            else:
                path = ""
                for i, data in enumerate(json_data["data"]):
                    if not path:
                        path = data["title"]
                    _fetch_content(data["origin"], path, i)

        _fetch_content(url)

    if len(details["contents"]) == 0:
        raise DirectDownloadLinkException("ERROR: Direct link not found!")
    if len(details["contents"]) == 1:
        content = details["contents"][0]
        return (content["url"], content["filename"], content["header"])
    return details


# def doods(url: str):
#     if '/e/' in url:
#         url = url.replace('/e/', '/d/')
#     parsed_url = urlparse(url)
#     with create_scraper() as session:
#         try:
#             html = HTML(session.get(url).text)
#         except Exception as e:
#             raise DirectDownloadLinkException(f'ERROR: {e} While fetching token link.') from e
#         if not (link := html.xpath("//div[@class='download-content']//a/@href")):
#             raise DirectDownloadLinkException('ERROR: Token Link not found or maybe not allow to download! open in browser.') from e
#         link = f'{parsed_url.scheme}://{parsed_url.hostname}{link[0]}'
#         sleep(2)
#         try:
#             _res = session.get(link)
#         except Exception as e:
#             raise DirectDownloadLinkException( from e
#                 f'ERROR: {e} While fetching download link.')
#     if not (link := re_search(r"window\.open\('(\S+)'", _res.text)):
#         raise DirectDownloadLinkException("ERROR: Download link not found try again!")
#     return (link.group(1), f'Referer: {parsed_url.scheme}://{parsed_url.hostname}/')


def easyupload(url):
    if "::" in url:
        _password = url.split("::")[-1]
        url = url.split("::")[-2]
    else:
        _password = ""
    file_id = url.split("/")[-1]
    with create_scraper() as session:
        try:
            _res = session.get(url)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}") from e
        first_page_html = HTML(_res.text)
        if (
            first_page_html.xpath("//h6[contains(text(),'Password Protected')]")
            and not _password
        ):
            raise DirectDownloadLinkException(
                f"ERROR:\n{HelpString.PASSWORD_ERROR_MESSAGE.format(url)}"
            )
        if not (
            match := re_search(
                r"https://eu(?:[1-9][0-9]?|100)\.easyupload\.io/action\.php", _res.text
            )
        ):
            raise DirectDownloadLinkException(
                "ERROR: Failed to get server for EasyUpload Link"
            )
        action_url = match.group()
        session.headers.update({"referer": "https://easyupload.io/"})
        recaptcha_params = {
            "k": "6LfWajMdAAAAAGLXz_nxz2tHnuqa-abQqC97DIZ3",
            "ar": "1",
            "co": "aHR0cHM6Ly9lYXN5dXBsb2FkLmlvOjQ0Mw..",
            "hl": "en",
            "v": "0hCdE87LyjzAkFO5Ff-v7Hj1",
            "size": "invisible",
            "cb": "c3o1vbaxbmwe",
        }
        if not (captcha_token := get_captcha_token(session, recaptcha_params)):
            raise DirectDownloadLinkException("ERROR: Captcha token not found")
        try:
            data = {
                "type": "download-token",
                "url": file_id,
                "value": _password,
                "captchatoken": captcha_token,
                "method": "regular",
            }
            json_resp = session.post(url=action_url, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}") from e
    if "download_link" in json_resp:
        return json_resp["download_link"]
    if "data" in json_resp:
        raise DirectDownloadLinkException(
            f"ERROR: Failed to generate direct link due to {json_resp['data']}"
        )
    raise DirectDownloadLinkException(
        "ERROR: Failed to generate direct link from EasyUpload."
    )


def filelions_and_streamwish(url: str):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    scheme = parsed_url.scheme
    if any(
        x in hostname
        for x in [
            "vidhide.com",
            "vidhidepro.com",
            "filelions.live",
            "filelions.to",
            "filelions.site",
            "cabecabean.lol",
            "filelions.online",
        ]
    ):
        apiKey = config_dict["FILELION_API"]
        apiUrl = "https://vidhideapi.com"
    elif any(
        x in hostname
        for x in [
            "embedwish.com",
            "streamwish.com",
            "kitabmarkaz.xyz",
            "wishfast.top",
            "streamwish.to",
        ]
    ):
        apiKey = config_dict["STREAMWISH_API"]
        apiUrl = "https://api.streamwish.com"
    if not apiKey:
        raise DirectDownloadLinkException(
            f"ERROR: API is not provided get it from {scheme}://{hostname}!"
        )
    file_code = url.split("/")[-1]
    quality = ""
    if bool(file_code.endswith(("_o", "_h", "_n", "_l"))):
        spited_file_code = file_code.rsplit("_", 1)
        quality = spited_file_code[1]
        file_code = spited_file_code[0]
    url = f"{scheme}://{hostname}/{file_code}"
    with Session() as session:
        try:
            _res = session.get(
                f"{apiUrl}/api/file/direct_link",
                params={"key": apiKey, "file_code": file_code, "hls": "1"},
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if _res["status"] != 200:
        raise DirectDownloadLinkException(f"ERROR: {_res['msg']}.")
    result = _res["result"]
    if not result["versions"]:
        raise DirectDownloadLinkException("ERROR: File not found!")
    error = "\nProvide a quality to download the video\nAvailable Quality:"
    for version in result["versions"]:
        if quality == version["name"]:
            return version["url"]
        if version["name"] == "l":
            error += "\nLow"
        elif version["name"] == "n":
            error += "\nNormal"
        elif version["name"] == "o":
            error += "\nOriginal"
        elif version["name"] == "h":
            error += "\nHD"
        error += f" <code>{url}_{version['name']}</code>"
    raise DirectDownloadLinkException(f"ERROR: {error}.")


def github(url: str):
    """GitHub direct links generator"""
    try:
        re_findall(r"\bhttps?://.*github\.com.*releases\S+", url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No GitHub Releases links found!")
    with create_scraper() as session:
        _res = session.get(url, stream=True, allow_redirects=False)
        if "location" in _res.headers:
            return _res.headers["location"]
        raise DirectDownloadLinkException("ERROR: Can't extract the link!")


def gofile(url: str):
    try:
        if "::" in url:
            _password = url.split("::")[-1]
            _password = sha256(_password.encode("utf-8")).hexdigest()
            url = url.split("::")[-2]
        else:
            _password = ""
        _id = url.split("/")[-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")

    def __get_token(session):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        __url = f"https://api.gofile.io/accounts"
        try:
            __res = session.post(__url, headers=headers).json()
            if __res["status"] != "ok":
                raise DirectDownloadLinkException(f"ERROR: Failed to get token.")
            return __res["data"]["token"]
        except Exception as e:
            raise e

    def __fetch_links(session, _id, folderPath=""):
        _url = f"https://api.gofile.io/contents/{_id}?wt=4fd6sg89d7s6&cache=true"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Authorization": "Bearer" + " " + token,
        }
        if _password:
            _url += f"&password={_password}"
        try:
            _json = session.get(_url, headers=headers).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        if _json["status"] in "error-passwordRequired":
            raise DirectDownloadLinkException(
                f"ERROR:\n{HelpString.PASSWORD_ERROR_MESSAGE.format(url)}"
            )
        if _json["status"] in "error-passwordWrong":
            raise DirectDownloadLinkException("ERROR: This password is wrong !")
        if _json["status"] in "error-notFound":
            raise DirectDownloadLinkException(
                "ERROR: File not found on gofile's server"
            )
        if _json["status"] in "error-notPublic":
            raise DirectDownloadLinkException("ERROR: This folder is not public")

        data = _json["data"]

        if not details["title"]:
            details["title"] = data["name"] if data["type"] == "folder" else _id

        contents = data["children"]
        for content in contents.values():
            if content["type"] == "folder":
                if not content["public"]:
                    continue
                if not folderPath:
                    newFolderPath = ospath.join(details["title"], content["name"])
                else:
                    newFolderPath = ospath.join(folderPath, content["name"])
                __fetch_links(session, content["id"], newFolderPath)
            else:
                if not folderPath:
                    folderPath = details["title"]
                item = {
                    "path": ospath.join(folderPath),
                    "filename": content["name"],
                    "url": content["link"],
                }
                if "size" in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details["total_size"] += size
                details["contents"].append(item)

    details = {"contents": [], "title": "", "total_size": 0}
    with Session() as session:
        try:
            token = __get_token(session)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        details["header"] = f"Cookie: accountToken={token}"
        try:
            __fetch_links(session, _id)
        except Exception as e:
            raise DirectDownloadLinkException(e)

    if len(details["contents"]) == 1:
        return (details["contents"][0]["url"], details["header"])
    return details


def hxfile(url: str):
    with create_scraper() as session:
        try:
            file_code = url.split("/")[-1]
            html = HTML(
                session.post(url, data={"op": "download2", "id": file_code}).text
            )
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if direct_link := html.xpath('//a[@class="btn btn-dow"]/@href'):
        return direct_link[0]
    raise DirectDownloadLinkException("ERROR: Direct download link not found!")


def krakenfiles(url: str):
    with Session() as session:
        try:
            _res = session.get(url)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        html = HTML(_res.text)
        if post_url := html.xpath('//form[@id="dl-form"]/@action'):
            post_url = f"https:{post_url[0]}"
        else:
            raise DirectDownloadLinkException("ERROR: Unable to find post link.")
        if token := html.xpath('//input[@id="dl-token"]/@value'):
            data = {"token": token[0]}
        else:
            raise DirectDownloadLinkException("ERROR: Unable to find token for post.")
        try:
            _json = session.post(post_url, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(
                f"ERROR: {e} While send post request."
            ) from e
    if _json["status"] != "ok":
        raise DirectDownloadLinkException(
            "ERROR: Unable to find download after post request."
        )
    return _json["url"]


def linkBox(url: str):
    parsed_url = urlparse(url)
    try:
        shareToken = parsed_url.path.split("/")[-1]
    except:
        raise DirectDownloadLinkException("ERROR: Invalid URL!")

    details = {"contents": [], "title": "", "total_size": 0}

    def _singleItem(session, itemId):
        try:
            _json = session.get(
                "https://www.linkbox.to/api/file/detail", params={"itemId": itemId}
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        data = _json["data"]
        if not data:
            if "msg" in _json:
                raise DirectDownloadLinkException(f"ERROR: {_json['msg']}")
            raise DirectDownloadLinkException("ERROR: Data not found!")
        itemInfo = data["itemInfo"]
        if not itemInfo:
            raise DirectDownloadLinkException("ERROR: ItemInfo not found!")
        filename = itemInfo["name"]
        sub_type = itemInfo.get("sub_type")
        if sub_type and not filename.endswith(sub_type):
            filename += f".{sub_type}"
        if not details["title"]:
            details["title"] = filename
        item = {"path": "", "filename": filename, "url": itemInfo["url"]}
        if "size" in itemInfo:
            size = itemInfo["size"]
            if isinstance(size, str) and size.isdigit():
                size = float(size)
            details["total_size"] += size
        details["contents"].append(item)

    def _fetch_links(session, _id=0, folderPath=""):
        params = {"shareToken": shareToken, "pageSize": 1000, "pid": _id}
        try:
            _json = session.get(
                "https://www.linkbox.to/api/file/share_out_list", params=params
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        data = _json["data"]
        if not data:
            if "msg" in _json:
                raise DirectDownloadLinkException(f"ERROR: {_json['msg']}")
            raise DirectDownloadLinkException("ERROR: data not found")
        try:
            if data["shareType"] == "singleItem":
                return _singleItem(session, data["itemId"])
        except:
            pass
        if not details["title"]:
            details["title"] = data["dirName"]
        contents = data["list"]
        if not contents:
            return
        for content in contents:
            if content["type"] == "dir" and "url" not in content:
                if not folderPath:
                    newFolderPath = ospath.join(details["title"], content["name"])
                else:
                    newFolderPath = ospath.join(folderPath, content["name"])
                if not details["title"]:
                    details["title"] = content["name"]
                _fetch_links(session, content["id"], newFolderPath)
            elif "url" in content:
                if not folderPath:
                    folderPath = details["title"]
                filename = content["name"]
                if (sub_type := content.get("sub_type")) and not filename.endswith(
                    sub_type
                ):
                    filename += f".{sub_type}"
                item = {
                    "path": ospath.join(folderPath),
                    "filename": filename,
                    "url": content["url"],
                }
                if "size" in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details["total_size"] += size
                details["contents"].append(item)

    try:
        with Session() as session:
            _fetch_links(session)
    except DirectDownloadLinkException as e:
        raise e
    return details


def mdisk(url: str):
    cget = create_scraper().request
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        link = url[:-1] if url[-1] == "/" else url
        token = link.split("/")[-1]
        api = f"https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={token}"
        response = cget("get", api, headers=headers).json()
        download_url = response["download"]
        return download_url.replace(" ", "%20")
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e


def mediafire(url: str, session=None):
    if "/folder/" in url:
        return mediafireFolder(url)
    if final_link := re_findall(
        r"https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+", url
    ):
        return final_link[0]
    if session is None:
        session = Session()
        parsed_url = urlparse(url)
        url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    try:
        html = HTML(session.get(url).text)
    except Exception as e:
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if error := html.xpath('//p[@class="notranslate"]/text()'):
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {error[0]}")
    if not (final_link := html.xpath("//a[@id='downloadButton']/@href")):
        session.close()
        raise DirectDownloadLinkException(
            "ERROR: No links found in this page Try Again!"
        )
    if final_link[0].startswith("//"):
        return mediafire(f"https://{final_link[0][2:]}", session)
    session.close()
    return final_link[0]


def onedrive(link: str):
    """Onedrive direct link generator
    By https://github.com/junedkh"""
    with create_scraper() as session:
        try:
            link = session.get(link).url
            parsed_link = urlparse(link)
            link_data = parse_qs(parsed_link.query)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if not link_data:
            raise DirectDownloadLinkException("ERROR: Unable to find link_data.")
        folder_id = link_data.get("resid")
        if not folder_id:
            raise DirectDownloadLinkException("ERROR: folder id not found!")
        folder_id = folder_id[0]
        authkey = link_data.get("authkey")
        if not authkey:
            raise DirectDownloadLinkException("ERROR: authkey not found!")
        authkey = authkey[0]
        boundary = uuid4()
        headers = {"content-type": f"multipart/form-data;boundary={boundary}"}
        data = f"--{boundary}\r\nContent-Disposition: form-data;name=data\r\nPrefer: Migration=EnableRedirect;FailOnMigratedFiles\r\nX-HTTP-Method-Override: GET\r\nContent-Type: application/json\r\n\r\n--{boundary}--"
        try:
            resp = session.get(
                f"https://api.onedrive.com/v1.0/drives/{folder_id.split('!', 1)[0]}/items/{folder_id}?$select=id,@content.downloadUrl&ump=1&authKey={authkey}",
                headers=headers,
                data=data,
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if "@content.downloadUrl" not in resp:
        raise DirectDownloadLinkException("ERROR: Direct link not found!")
    return resp["@content.downloadUrl"]


def osdn(url: str):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if not (direct_link := html.xapth('//a[@class="mirror_link"]/@href')):
            raise DirectDownloadLinkException("ERROR: Direct link not found!")
        return f"https://osdn.net{direct_link[0]}"


def pcloud(url: str):
    with create_scraper() as session:
        try:
            res = session.get(url)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}") from e
    if link := re_findall(r".downloadlink.:..(https:.*)..", res.text):
        return link[0].replace(r"\/", "/")
    raise DirectDownloadLinkException("ERROR: Direct link not found!")


def qiwi(url):
    """qiwi.gg link generator
    based on https://github.com/aenulrofik"""
    with create_scraper() as session:
        file_id = url.split("/")[-1]
        try:
            res = session.get(url).text
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}") from e
        tree = HTML(res)
        if name := tree.xpath('//h1[@class="page_TextHeading__VsM7r"]/text()'):
            ext = name[0].split(".")[-1]
            return f"https://qiwi.lol/{file_id}.{ext}"
        raise DirectDownloadLinkException("ERROR: File not found!")


def pixeldrain(url: str):
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    if url.split("/")[-2] == "l":
        info_link = f"https://pixeldrain.com/api/list/{file_id}"
        dl_link = f"https://pixeldrain.com/api/list/{file_id}/zip?download"
    else:
        info_link = f"https://pixeldrain.com/api/file/{file_id}/info"
        dl_link = f"https://pixeldrain.com/api/file/{file_id}?download"
    with create_scraper() as session:
        try:
            resp = session.get(info_link).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if resp["success"]:
        return dl_link
    raise DirectDownloadLinkException(f"ERROR: Cant't download due {resp['message']}.")


def racaty(url: str):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            json_data = {"op": "download2", "id": url.split("/")[-1]}
            html = HTML(session.post(url, data=json_data).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if direct_link := html.xpath("//a[@id='uniqueExpirylink']/@href"):
        return direct_link[0]
    raise DirectDownloadLinkException("ERROR: Direct link not found!")


def rc(url: str):
    if not url.endswith("/"):
        return url
    details = {"contents": [], "title": "", "total_size": 0}
    with create_scraper() as session:

        def _fetch_content(url: str, in_loop=False):
            try:
                content = session.get(url).text
            except Exception as e:
                if in_loop:
                    return
                raise DirectDownloadLinkException(f"ERROR: {e}.") from e
            html = HTML(content)
            files = html.xpath('//tbody/tr[@class="file"]')
            path = unquote(url.strip("/").rsplit("/", 1)[-1])
            if not details["title"]:
                details["title"] = path
            if not in_loop:
                path = ""
            for file in files:
                name = file.xpath(".//@href")[0]
                link = url + name
                if not name.endswith("/"):
                    item = {"url": link, "filename": unquote(name), "path": path}
                    details["contents"].append(item)
                    details["total_size"] += int(file.xpath(".//size/text()")[0])
                else:
                    _fetch_content(link, True)

        _fetch_content(url)
    if len(details["contents"]) == 0:
        raise DirectDownloadLinkException("ERROR: Direct link not found!")
    if len(details["contents"]) == 1:
        return details["contents"][0]["url"]
    return details


def send_cm_file(url, file_id=None):
    if "::" in url:
        _password = url.split("::")[-1]
        url = url.split("::")[-2]
    else:
        _password = ""
    _passwordNeed = False
    with create_scraper() as session:
        if file_id is None:
            try:
                html = HTML(session.get(url).text)
            except Exception as e:
                raise DirectDownloadLinkException(f"ERROR: {e}.") from e
            if html.xpath("//input[@name='password']"):
                _passwordNeed = True
            if not (file_id := html.xpath("//input[@name='id']/@value")):
                raise DirectDownloadLinkException("ERROR: file_id not found!")
        try:
            data = {"op": "download2", "id": file_id}
            if _password and _passwordNeed:
                data["password"] = _password
            _res = session.post("https://send.cm/", data=data, allow_redirects=False)
            if "Location" in _res.headers:
                return (_res.headers["Location"], "Referer: https://send.cm/")
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if _passwordNeed:
            raise DirectDownloadLinkException(
                f"ERROR:\n{HelpString.PASSWORD_ERROR_MESSAGE.format(url)}"
            )
        raise DirectDownloadLinkException("ERROR: Direct link not found!")


def sendcm(url: str):
    if "/d/" in url:
        return send_cm_file(url)
    if "/s/" not in url:
        file_id = url.split("/")[-1]
        return send_cm_file(url, file_id)
    splitted_url = url.split("/")
    details = {
        "contents": [],
        "title": "",
        "total_size": 0,
        "header": "Referer: https://send.cm/",
    }
    if len(splitted_url) == 5:
        url += "/"
        splitted_url = url.split("/")
    if len(splitted_url) >= 7:
        details["title"] = splitted_url[5]
    else:
        details["title"] = splitted_url[-1]
    session = Session()

    def _collectFolders(html):
        folders = []
        folders_urls = html.xpath("//h6/a/@href")
        folders_names = html.xpath("//h6/a/text()")
        for folders_url, folders_name in zip(folders_urls, folders_names):
            folders.append(
                {
                    "folder_link": folders_url.strip(),
                    "folder_name": folders_name.strip(),
                }
            )
        return folders

    def _getFile_link(file_id):
        try:
            _res = session.post(
                "https://send.cm/",
                data={"op": "download2", "id": file_id},
                allow_redirects=False,
            )
            if "Location" in _res.headers:
                return _res.headers["Location"]
        except:
            pass

    def _getFiles(html):
        files = []
        hrefs = html.xpath('//tr[@class="selectable"]//a/@href')
        file_names = html.xpath('//tr[@class="selectable"]//a/text()')
        sizes = html.xpath('//tr[@class="selectable"]//span/text()')
        for href, file_name, size_text in zip(hrefs, file_names, sizes):
            files.append(
                {
                    "file_id": href.split("/")[-1],
                    "file_name": file_name.strip(),
                    "size": speed_string_to_bytes(size_text.strip()),
                }
            )
        return files

    def _writeContents(html_text, folderPath=""):
        folders = _collectFolders(html_text)
        for folder in folders:
            _html = HTML(cf_bypass(folder["folder_link"]))
            _writeContents(_html, ospath.join(folderPath, folder["folder_name"]))
        files = _getFiles(html_text)
        for file in files:
            if not (link := _getFile_link(file["file_id"])):
                continue
            item = {"url": link, "filename": file["filename"], "path": folderPath}
            details["total_size"] += file["size"]
            details["contents"].append(item)

    try:
        mainHtml = HTML(cf_bypass(url))
    except DirectDownloadLinkException as e:
        session.close()
        raise e
    except Exception as e:
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {e} While getting main Html.") from e
    try:
        _writeContents(mainHtml, details["title"])
    except DirectDownloadLinkException as e:
        session.close()
        raise e
    except Exception as e:
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {e} While writing Contents.") from e
    session.close()
    if len(details["contents"]) == 1:
        return (details["contents"][0]["url"], details["header"])
    return details


def shrdsk(url: str):
    with create_scraper() as session:
        try:
            _json = session.get(
                f"https://us-central1-affiliate2apk.cloudfunctions.net/get_data?shortid={url.split('/')[-1]}"
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if "download_data" not in _json:
            raise DirectDownloadLinkException("ERROR: Download data not found!")
        try:
            _res = session.get(
                f"https://shrdsk.me/download/{_json['download_data']}",
                allow_redirects=False,
            )
            if "Location" in _res.headers:
                return _res.headers["Location"]
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    raise DirectDownloadLinkException("ERROR: cannot find direct link in headers!")


def solidfiles(url: str):
    """Solidfiles direct link generator
    Based on https://github.com/Xonshiz/SolidFiles-Downloader
    By https://github.com/Jusidama18"""
    with create_scraper() as session:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36"
            }
            pageSource = session.get(url, headers=headers).text
            mainOptions = str(
                re_search(r"viewerOptions\'\,\ (.*?)\)\;", pageSource).group(1)
            )
            return jsonloads(mainOptions)["downloadUrl"]
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e


def streamhub(url: str):
    file_code = url.split("/")[-1]
    parsed_url = urlparse(url)
    url = f"{parsed_url.scheme}://{parsed_url.hostname}/d/{file_code}"
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if not (inputs := html.xpath('//form[@name="F1"]//input')):
            raise DirectDownloadLinkException("ERROR: No inputs found!")
        data = {}
        for i in inputs:
            if key := i.get("name"):
                data[key] = i.get("value")
        session.headers.update({"referer": url})
        sleep(1)
        try:
            html = HTML(session.post(url, data=data).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if directLink := html.xpath(
            '//a[@class="btn btn-primary btn-go downloadbtn"]/@href'
        ):
            return directLink[0]
        if error := html.xpath('//div[@class="alert alert-danger"]/text()[2]'):
            raise DirectDownloadLinkException(f"ERROR: {error[0]}")
        raise DirectDownloadLinkException("ERROR: direct link not found!")


def streamvid(url: str):
    file_code = url.split("/")[-1]
    parsed_url = urlparse(url)
    url = f"{parsed_url.scheme}://{parsed_url.hostname}/d/{file_code}"
    quality_defined = bool(url.endswith(("_o", "_h", "_n", "_l")))
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if quality_defined:
            data = {}
            if not (inputs := html.xpath('//form[@id="F1"]//input')):
                raise DirectDownloadLinkException("ERROR: No inputs found!")
            for i in inputs:
                if key := i.get("name"):
                    data[key] = i.get("value")
            try:
                html = HTML(session.post(url, data=data).text)
            except Exception as e:
                raise DirectDownloadLinkException(f"ERROR: {e}") from e
            if not (
                script := html.xpath(
                    '//script[contains(text(),"document.location.href")]/text()'
                )
            ):
                if error := html.xpath(
                    '//div[@class="alert alert-danger"][1]/text()[2]'
                ):
                    raise DirectDownloadLinkException(f"ERROR: {error[0]}.")
                raise DirectDownloadLinkException(
                    "ERROR: Direct link script not found!"
                )
            if directLink := re_findall(r'document\.location\.href="(.*)"', script[0]):
                return directLink[0]
            raise DirectDownloadLinkException(
                "ERROR: Direct link not found! in the script!"
            )
        if (qualities_urls := html.xpath('//div[@id="dl_versions"]/a/@href')) and (
            qualities := html.xpath('//div[@id="dl_versions"]/a/text()[2]')
        ):
            error = "\nProvide a quality to download the video\nAvailable Quality:"
            for quality_url, quality in zip(qualities_urls, qualities):
                error += f"\n{quality.strip()} <code>{quality_url}</code>"
            raise DirectDownloadLinkException(f"ERROR: {error}.")
        if error := html.xpath('//div[@class="not-found-text"]/text()'):
            raise DirectDownloadLinkException(f"ERROR: {error[0]}")
        raise DirectDownloadLinkException("ERROR: Something went wrong!")


def tmpsend(url):
    parsed_url = urlparse(url)
    if any(x in parsed_url.path for x in ["thank-you", "download"]):
        query_params = parse_qs(parsed_url.query)
        if file_id := query_params.get("d"):
            file_id = file_id[0]
    elif not (file_id := parsed_url.path.strip("/")):
        raise DirectDownloadLinkException("ERROR: Invalid URL format")
    referer_url = f"https://tmpsend.com/thank-you?d={file_id}"
    header = f"Referer: {referer_url}"
    download_link = f"https://tmpsend.com/download?d={file_id}"
    return download_link, header


def terabox(url):
    if not ospath.isfile("terabox.txt"):
        raise DirectDownloadLinkException("ERROR: terabox.txt not found!")
    try:
        jar = MozillaCookieJar("terabox.txt")
        jar.load()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    cookies = {}
    for cookie in jar:
        cookies[cookie.name] = cookie.value
    details = {"contents": [], "title": "", "total_size": 0}
    details["header"] = " ".join(f"{key}: {value}" for key, value in cookies.items())

    def _fetch_links(session, dir_="", folderPath=""):
        params = {"app_id": "250528", "jsToken": jsToken, "shorturl": shortUrl}
        if dir_:
            params["dir"] = dir_
        else:
            params["root"] = "1"
        try:
            _json = session.get(
                "https://www.1024tera.com/share/list", params=params, cookies=cookies
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if _json["errno"] not in [0, "0"]:
            if "errmsg" in _json:
                raise DirectDownloadLinkException(f"ERROR: {_json['errmsg']}.")
            raise DirectDownloadLinkException("ERROR: Something went wrong!")

        if "list" not in _json:
            return
        contents = _json["list"]
        for content in contents:
            if content["isdir"] in ["1", 1]:
                if not folderPath:
                    if not details["title"]:
                        details["title"] = content["server_filename"]
                        newFolderPath = ospath.join(details["title"])
                    else:
                        newFolderPath = ospath.join(
                            details["title"], content["server_filename"]
                        )
                else:
                    newFolderPath = ospath.join(folderPath, content["server_filename"])
                _fetch_links(session, content["path"], newFolderPath)
            else:
                if not folderPath:
                    if not details["title"]:
                        details["title"] = content["server_filename"]
                    folderPath = details["title"]
                item = {
                    "url": content["dlink"],
                    "filename": content["server_filename"],
                    "path": ospath.join(folderPath),
                }
                if "size" in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details["total_size"] += size
                details["contents"].append(item)

    with Session() as session:
        try:
            _res = session.get(url, cookies=cookies)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if jsToken := re_findall(r"window\.jsToken.*%22(.*)%22", _res.text):
            jsToken = jsToken[0]
        else:
            raise DirectDownloadLinkException("ERROR: jsToken not found!")
        shortUrl = parse_qs(urlparse(_res.url).query).get("surl")
        if not shortUrl:
            raise DirectDownloadLinkException("ERROR: Could not find surl!")
        try:
            _fetch_links(session)
        except Exception as e:
            raise DirectDownloadLinkException(e) from e
    if len(details["contents"]) == 1:
        return details["contents"][0]["url"]
    return details


def uploadbaz(url: str):
    try:
        url = url[:-1] if url[-1] == "/" else url
        token = url.split("/")[-1]
        cget = create_scraper().request
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        }
        data = {
            "op": "download2",
            "id": token,
            "rand": "",
            "referer": "",
            "method_free": "",
            "method_premium": "",
        }
        response = cget("post", url, headers=headers, data=data, allow_redirects=False)
        return response.headers["Location"]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e


def uploadee(url: str):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if link := html.xpath("//a[@id='d_l']/@href"):
        return link[0]
    raise DirectDownloadLinkException("ERROR: Direct Link not found!")


def userscloud(url: str):
    try:
        url = url[:-1] if url[-1] == "/" else url
        token = url.split("/")[-1]
        cget = create_scraper().request
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        }
        data = {
            "op": "download2",
            "id": token,
            "rand": "",
            "referer": "",
            "method_free": "",
            "method_premium": "",
        }
        response = cget("post", url, headers=headers, data=data, allow_redirects=False)
        return response.headers["Location"]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e


def uptobox(url: str):
    """Uptobox direct link generator
    based on https://github.com/jovanzers/WinTenCermin and https://github.com/sinoobie/noobie-mirror"""
    try:
        link = re_findall(r"\bhttps?://.*uptobox\.com\S+", url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Uptobox links found!")
    if link := re_findall(r"\bhttps?://.*\.uptobox\.com/dl\S+", url):
        return link[0]
    with create_scraper() as session:
        try:
            file_id = re_findall(r"\bhttps?://.*uptobox\.com/(\w+)", url)[0]
            if UPTOBOX_TOKEN := config_dict["UPTOBOX_TOKEN"]:
                file_link = f"https://uptobox.com/api/link?token={UPTOBOX_TOKEN}&file_code={file_id}"
            else:
                file_link = f"https://uptobox.com/api/link?file_code={file_id}"
            res = session.get(file_link).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
        if res["statusCode"] == 0:
            return res["data"]["dlLink"]
        if res["statusCode"] == 16:
            sleep(1)
            waiting_token = res["data"]["waitingToken"]
            sleep(res["data"]["waiting"])
        elif res["statusCode"] == 39:
            raise DirectDownloadLinkException(
                f"ERROR: Uptobox is being limited please wait {get_readable_time(res['data']['waiting'])}."
            )
        else:
            raise DirectDownloadLinkException(f"ERROR: {res['message']}.")
        try:
            res = session.get(f"{file_link}&waitingToken={waiting_token}").json()
            return res["data"]["dlLink"]
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e


def wetransfer(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            splited_url = url.split("/")
            json_data = {"security_hash": splited_url[-1], "intent": "entire_transfer"}
            res = session.post(
                f"https://wetransfer.com/api/v4/transfers/{splited_url[-2]}/download",
                json=json_data,
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}") from e
    if "direct_link" in res:
        return res["direct_link"]
    if "message" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['message']}")
    if "error" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['error']}")
    raise DirectDownloadLinkException(
        "ERROR: Error trying to generate direct link from Wetransfer."
    )


# ==============================================================================================================


# ================================================= VIDEO HOSTER ===============================================
def get_fembed_links(url):
    cget = create_scraper().request
    url = url.replace("/v/", "/f/")
    raw = cget("get", url)
    api = re_search(r"(/api/source/[^\"']+)", raw.text)
    if not api:
        raise DirectDownloadLinkException("ERROR: Link not found!")
    result = {}
    raw = cget("post", f"https://layarkacaxxi.icu{api.group(1)}").json()
    for d in raw["data"]:
        f = d["file"]
        head = cget("head", f)
        direct = head.headers.get("Location", f)
        result[f"{d['label']}/{d['type']}"] = direct
    return result


def fembed(url: str):
    dl_url = get_fembed_links(url)
    try:
        count = len(dl_url)
        lst_link = [dl_url[i] for i in dl_url]
        return lst_link[count - 1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e


def mp4upload(url: str):
    cget = create_scraper().request
    try:
        url = url[:-1] if url[-1] == "/" else url
        headers = {"referer": "https://mp4upload.com"}
        token = url.split("/")[-1]
        data = {
            "op": "download2",
            "id": token,
            "rand": "",
            "referer": "https://www.mp4upload.com/",
            "method_free": "",
            "method_premium": "",
        }
        response = cget("post", url, headers=headers, data=data, allow_redirects=False)
        bypassed_json = {
            "bypassed_url": response.headers["Location"],
            "headers ": headers,
        }
        return bypassed_json["bypassed_url"]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e


def streamtape(url: str):
    splitted_url = url.split("/")
    _id = splitted_url[4] if len(splitted_url) >= 6 else splitted_url[-1]
    try:
        with Session() as session:
            html = HTML(session.get(url).text)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e
    if not (script := html.xpath("//script[contains(text(),'ideoooolink')]/text()")):
        raise DirectDownloadLinkException("ERROR: requeries script not found!")
    if not (link := re_findall(r"(&expires\S+)'", script[0])):
        raise DirectDownloadLinkException("ERROR: Download link not found!")
    return f"https://streamtape.com/get_video?id={_id}{link[-1]}"


# ==============================================================================================================


# ================================================= GDRIVE SHARER ==============================================
def sharerpw(url: str, forced_login=False):
    SHARERPW_XSRF_TOKEN = config_dict["SHARERPW_XSRF_TOKEN"]
    SHARERPW_LARAVEL_SESSION = config_dict["SHARERPW_LARAVEL_SESSION"]
    if not SHARERPW_XSRF_TOKEN or not SHARERPW_LARAVEL_SESSION:
        raise DirectDownloadLinkException("ERROR: Sharer Token/Session not provided!")
    try:
        client = create_scraper(allow_brotli=False)
        client.cookies.update(
            {
                "XSRF-TOKEN": SHARERPW_XSRF_TOKEN,
                "laravel_session": SHARERPW_LARAVEL_SESSION,
            }
        )
        res = client.get(url)
        token = re_findall(r"_token\s=\s'(.*?)'", res.text, DOTALL)[0]
        ddl_btn = HTML(res.content).xpath("//button[@id='btndirect']")
        headers = {
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
        }
        data = {"_token": token}
        if not forced_login:
            data["nl"] = 1
        try:
            res = client.post(f"{url}/dl", headers=headers, data=data).json()
            return res["url"]
        except:
            if len(ddl_btn) and not forced_login:
                return sharerpw(url, forced_login=True)
            raise DirectDownloadLinkException("ERROR: Not found any ddl!")
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e


def gdtot(url: str):
    CRYPT_GDTOT = config_dict["CRYPT_GDTOT"]
    if not CRYPT_GDTOT:
        LOGGER.info("ERROR: CRYPT_GDTOT cookie not provided")
        return gdtot_plus(url)
    match = re_findall(r"https?://(.+)\.gdtot\.(.+)\/\S+\/\S+", url)[0]
    session = create_scraper()
    session.cookies.update({"crypt": CRYPT_GDTOT})
    session.request("get", url)
    res = session.request(
        "get", f"https://{match[0]}.gdtot.{match[1]}/dld?id={url.split('/')[-1]}"
    )
    matches = re_findall("gd=(.*?)&", res.text)
    try:
        decoded_id = b64decode(str(matches[0])).decode("utf-8")
        return f"https://drive.google.com/open?id={decoded_id}"
    except:
        return gdtot_plus(url)


def filepress(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            raw = urlparse(url)
            json_data = {"id": raw.path.split("/")[-1], "method": "publicDownlaod"}
            api = f"{raw.scheme}://{raw.hostname}/api/file/downlaod/"
            res2 = session.post(
                api,
                headers={"Referer": f"{raw.scheme}://{raw.hostname}"},
                json=json_data,
            ).json()
            json_data2 = {"id": res2["data"], "method": "publicUserDownlaod"}
            api2 = "https://new2.filepress.store/api/file/downlaod2/"
            res = session.post(
                api2,
                headers={"Referer": f"{raw.scheme}://{raw.hostname}"},
                json=json_data2,
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}.") from e
    if "data" not in res:
        raise DirectDownloadLinkException(f"ERROR: {res['statusText']}.")
    return f"https://drive.google.com/uc?id={res['data']}&export=download"


def gdtot_plus(url):
    cget = create_scraper().request
    try:
        res = cget("GET", f"https://gdtot.pro/file/{url.split('/')[-1]}")
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e
    token_url = HTML(res.text).xpath(
        "//a[contains(@class,'inline-flex items-center justify-center')]/@href"
    )
    if not token_url:
        try:
            url = cget("GET", url).url
            p_url = urlparse(url)
            res = cget(
                "GET", f"{p_url.scheme}://{p_url.hostname}/ddl/{url.split('/')[-1]}"
            )
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e}") from e
        if (
            drive_link := re_findall(r"myDl\('(.*?)'\)", res.text)
        ) and "drive.google.com" in drive_link[0]:
            return drive_link[0]
        raise DirectDownloadLinkException(
            "ERROR: Drive Link not found, Try in your broswer!"
        )
    token_url = token_url[0]
    try:
        token_page = cget("GET", token_url)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e} with {token_url}") from e
    match = re_findall(r'\("(.*?)"\)', token_page.text)
    if not match:
        raise DirectDownloadLinkException("ERROR: Cannot bypass this link!")
    match = match[0]
    raw = urlparse(token_url)
    final_url = f"{raw.scheme}://{raw.hostname}{match}"
    return sharer_scraper(final_url)


def sharer_scraper(url):
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        raw = urlparse(url)
        header = {
            "useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10"
        }
        res = cget("GET", url, headers=header)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e
    key = re_findall(r'"key",\s+"(.*?)"', res.text)
    if not key:
        raise DirectDownloadLinkException("ERROR: Key not found!")
    key = key[0]
    if not HTML(res.text).xpath("//button[@id='drc']"):
        raise DirectDownloadLinkException(
            "ERROR: This link don't have direct download button."
        )
    boundary = uuid4()
    headers = {
        "Content-Type": f"multipart/form-data; boundary=----WebKitFormBoundary{boundary}",
        "x-token": raw.hostname,
        "useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10",
    }
    data = (
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\ndirect\r\n'
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n'
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action_token"\r\n\r\n\r\n'
        f"------WebKitFormBoundary{boundary}--\r\n"
    )
    try:
        res = cget("POST", url, cookies=res.cookies, headers=headers, data=data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e
    if "url" not in res:
        raise DirectDownloadLinkException(
            "ERROR: Drive Link not found, Try in your broswer!"
        )
    if "drive.google.com" in res["url"]:
        return res["url"]
    try:
        res = cget("GET", res["url"])
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}") from e
    if (
        drive_link := HTML(res.text).xpath("//a[contains(@class,'btn')]/@href")
    ) and "drive.google.com" in drive_link[0]:
        return drive_link[0]
    raise DirectDownloadLinkException(
        "ERROR: Drive Link not found, Try in your broswer!"
    )


def mediafireFolder(url: str):
    try:
        raw = url.split("/", 4)[-1]
        folderkey = raw.split("/", 1)[0]
        folderkey = folderkey.split(",")
    except:
        raise DirectDownloadLinkException("ERROR: Could not parse ")
    if len(folderkey) == 1:
        folderkey = folderkey[0]
    details = {"contents": [], "title": "", "total_size": 0, "header": ""}

    session = req_session()
    adapter = HTTPAdapter(
        max_retries=Retry(total=10, read=10, connect=10, backoff_factor=0.3)
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session = create_scraper(
        browser={"browser": "firefox", "platform": "windows", "mobile": False},
        delay=10,
        sess=session,
    )
    folder_infos = []

    def _get_info(folderkey):
        try:
            if isinstance(folderkey, list):
                folderkey = ",".join(folderkey)
            _json = session.post(
                "https://www.mediafire.com/api/1.5/folder/get_info.php",
                data={
                    "recursive": "yes",
                    "folder_key": folderkey,
                    "response_format": "json",
                },
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e} While getting info") from e
        _res = _json["response"]
        if "folder_infos" in _res:
            folder_infos.extend(_res["folder_infos"])
        elif "folder_info" in _res:
            folder_infos.append(_res["folder_info"])
        elif "message" in _res:
            raise DirectDownloadLinkException(f"ERROR: {_res['message']}")
        else:
            raise DirectDownloadLinkException("ERROR: something went wrong!")

    try:
        _get_info(folderkey)
    except Exception as e:
        raise DirectDownloadLinkException(e) from e

    details["title"] = folder_infos[0]["name"]

    def _scraper(url):
        try:
            html = HTML(session.get(url).text)
        except:
            return
        if final_link := html.xpath("//a[@id='downloadButton']/@href"):
            return final_link[0]

    def _get_content(folderKey, folderPath="", content_type="folders"):
        try:
            params = {
                "content_type": content_type,
                "folder_key": folderKey,
                "response_format": "json",
            }
            _json = session.get(
                "https://www.mediafire.com/api/1.5/folder/get_content.php",
                params=params,
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(
                f"ERROR: {e} While getting content"
            ) from e
        _res = _json["response"]
        if "message" in _res:
            raise DirectDownloadLinkException(f"ERROR: {_res['message']}")
        _folder_content = _res["folder_content"]
        if content_type == "folders":
            folders = _folder_content["folders"]
            for folder in folders:
                if folderPath:
                    newFolderPath = ospath.join(folderPath, folder["name"])
                else:
                    newFolderPath = ospath.join(folder["name"])
                _get_content(folder["folderkey"], newFolderPath)
            _get_content(folderKey, folderPath, "files")
        else:
            files = _folder_content["files"]
            for file in files:
                item = {}
                if not (_url := _scraper(file["links"]["normal_download"])):
                    continue
                item["filename"] = file["filename"]
                if not folderPath:
                    folderPath = details["title"]
                item["path"] = ospath.join(folderPath)
                item["url"] = _url
                if "size" in file:
                    size = file["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details["total_size"] += size
                details["contents"].append(item)

    try:
        for folder in folder_infos:
            _get_content(folder["folderkey"], folder["name"])
    except Exception as e:
        raise DirectDownloadLinkException(e) from e
    finally:
        session.close()
    if len(details["contents"]) == 1:
        return (details["contents"][0]["url"], details["header"])
    return details


# ==============================================================================================================
