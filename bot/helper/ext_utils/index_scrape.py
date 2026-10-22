from aiohttp import ClientSession
from base64 import b64decode, b64encode
from json import loads as jsonloads
from urllib.parse import quote

from bot import LOGGER


next_page = False
next_page_token = ""


async def func(payload_input, url: str, username: str, password: str):
    global next_page, next_page_token
    if not url.endswith("/"):
        url += "/"
    try:
        user_pass = f"{username}:{password}"
        headers = {"authorization": f"Basic {b64encode(user_pass.encode()).decode()}"}
    except:
        return "Username/password combination is wrong or invalid link!"
    try:
        async with (
            ClientSession() as session,
            session.post(url, data=payload_input, headers=headers, ssl=False) as r,
        ):
            if r.status == 401:
                return "Username/password combination is wrong or invalid link!"
            try:
                json_data = b64decode((await r.read())[::-1][24:-20]).decode("utf-8")
                decrypted_response = jsonloads(json_data)
            except:
                return "Something went wrong or invalid link! Check index link/username/password and try again."
    except:
        return "Something wrong or invalid link!"
    page_token = decrypted_response.get("nextPageToken")
    if page_token is None:
        next_page = False
    else:
        next_page = True
        next_page_token = page_token
    result = []
    try:
        if list(decrypted_response.get("data").keys())[0] == "error":
            raise ValueError("Gor error respons!")
        file_length = len(decrypted_response["data"]["files"])
        for i, _ in enumerate(range(file_length)):
            files_type = decrypted_response["data"]["files"][i]["mimeType"]
            files_name = decrypted_response["data"]["files"][i]["name"]
            if files_type != "application/vnd.google-apps.folder":
                direct_download_link = url + quote(files_name)
                result.append(direct_download_link)
    except Exception as e:
        LOGGER.error(e.__class__.__name__)
    return result


async def index_scrapper(url, username, password):
    x = 0
    payload = {"page_token": next_page_token, "page_index": x}
    res = await func(payload, url, username, password)
    results = []
    if "wrong" not in res:
        results.extend(res)
    while next_page is True:
        payload = {"page_token": next_page_token, "page_index": x}
        res = await func(payload, url, username, password)
        if "wrong" not in res:
            results.extend(res)
        x += 1
    return res if "wrong" in res else results
