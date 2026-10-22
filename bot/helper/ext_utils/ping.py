from aiohttp import ClientSession, ClientTimeout
from asyncio import sleep

from bot import config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import new_task


@new_task
async def ping_server(repeat: bool):
    if repeat:
        return
    attemp = 1
    while True:
        try:
            if not (url := config_dict["PING_URL"]):
                raise ValueError(
                    f"PING_URL not provided! Retrying in 10 seconds ({attemp}/5)."
                )
            async with (
                ClientSession(timeout=ClientTimeout(total=10)) as session,
                session.get(url, ssl=False) as res,
            ):
                if (respon := res.status) != 200:
                    raise ValueError(
                        f"ERROR, got respons {respon}. Retrying in 10 seconds ({attemp}/5)."
                    )
            await sleep(600)
        except Exception as e:
            LOGGER.error(e)
            await sleep(10)
            if attemp < 5:
                attemp += 1
                continue
            break
