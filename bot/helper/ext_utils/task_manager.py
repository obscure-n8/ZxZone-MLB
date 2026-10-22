from aiofiles.os import path as aiopath
from asyncio import Event, sleep
from os import path as ospath

from bot import (
    config_dict,
    queued_dl,
    queued_up,
    non_queued_up,
    non_queued_dl,
    queue_dict_lock,
    LOGGER,
)
from bot.helper.ext_utils.bot_utils import (
    sync_to_async,
    presuf_remname_name,
    is_premium_user,
)
from bot.helper.ext_utils.files_utils import get_base_name, check_storage_threshold
from bot.helper.ext_utils.links_utils import is_gdrive_id, is_mega_link
from bot.helper.mirror_utils.gdrive_utlis.search import gdSearch


async def stop_duplicate_check(listener):
    if (
        isinstance(listener.upDest, int)
        or listener.isLeech
        or listener.select
        or listener.sameDir
        or not is_gdrive_id(listener.upDest)
        or not listener.stopDuplicate
    ):
        return None, ""
    name = listener.name
    LOGGER.info("Checking File/Folder if already in Drive: %s", name)
    if listener.compress:
        name = f"{name}.zip"
    elif listener.extract:
        try:
            name = get_base_name(name)
        except:
            name = None
    if name:
        if not listener.isRename and await aiopath.isfile(
            ospath.join(listener.dir, name)
        ):
            name = presuf_remname_name(listener.user_dict, name)
        count, file = await sync_to_async(
            gdSearch(stopDup=True, noMulti=listener.isClone).drive_list,
            name,
            listener.upDest,
            listener.user_id,
        )
        if count:
            return file, name
    LOGGER.info("Checking duplicate is passed...")
    return None, ""


async def check_limits_size(listener, size, playlist=False, play_count=False):
    msgerr = None
    max_pyt, megadl, torddl, zuzdl, leechdl, storage = (
        config_dict["MAX_YTPLAYLIST"],
        config_dict["MEGA_LIMIT"],
        config_dict["TORRENT_DIRECT_LIMIT"],
        config_dict["ZIP_UNZIP_LIMIT"],
        config_dict["LEECH_LIMIT"],
        config_dict["STORAGE_THRESHOLD"],
    )
    if config_dict["PREMIUM_MODE"] and not is_premium_user(listener.user_id):
        mdl = torddl = zuzdl = leechdl = config_dict["NONPREMIUM_LIMIT"]
        # An unset MEGA_LIMIT is represented by an empty string.  Do not pass
        # it to min(), which crashes every premium-mode non-premium request.
        megadl = min(megadl, mdl) if megadl else mdl
        max_pyt = 10

    arch = any([listener.compress, listener.isLeech, listener.extract])
    if torddl and not arch and size >= torddl * 1024**3:
        msgerr = f"Torrent/direct limit is {torddl}GB"
    elif (
        zuzdl and any([listener.compress, listener.extract]) and size >= zuzdl * 1024**3
    ):
        msgerr = f"Zip/Unzip limit is {zuzdl}GB"
    elif leechdl and listener.isLeech and size >= leechdl * 1024**3:
        msgerr = f"Leech limit is {leechdl}GB"
    if is_mega_link(listener.link) and megadl and size >= megadl * 1024**3:
        msgerr = f"Mega limit is {megadl}GB"
    if max_pyt and playlist and (play_count > max_pyt):
        msgerr = f"Only {max_pyt} playlist allowed. Current playlist is {play_count}."
    if storage and not await check_storage_threshold(size, arch):
        msgerr = f"Need {storage}GB free storage"
    return msgerr


async def check_running_tasks(mid: int, state="dl"):
    all_limit = config_dict["QUEUE_ALL"]
    state_limit = (
        config_dict["QUEUE_DOWNLOAD"] if state == "dl" else config_dict["QUEUE_UPLOAD"]
    )
    event = None
    is_over_limit = False
    if all_limit or state_limit:
        async with queue_dict_lock:
            if state == "up" and mid in non_queued_dl:
                non_queued_dl.remove(mid)
            dl_count, up_count = len(non_queued_dl), len(non_queued_up)
            state_count = dl_count if state == "dl" else up_count
            is_over_limit = bool(
                (all_limit and dl_count + up_count >= all_limit)
                or (state_limit and state_count >= state_limit)
            )
            if is_over_limit:
                event = Event()
                if state == "dl":
                    queued_dl[mid] = event
                else:
                    queued_up[mid] = event

    return is_over_limit, event


async def start_dl_from_queued(mid: int):
    async with queue_dict_lock:
        event = queued_dl.pop(mid, None)
    if event:
        event.set()
        await sleep(0.7)


async def start_up_from_queued(mid: int):
    async with queue_dict_lock:
        event = queued_up.pop(mid, None)
    if event:
        event.set()
        await sleep(0.7)


async def start_task_from_queued(task_type, limit, non_queued, queued):
    """Wake queued tasks until the state-specific limit is filled.

    The old implementation acquired ``queue_dict_lock`` and then called
    helpers that acquired it again when ``QUEUE_ALL`` was enabled.  An
    ``asyncio.Lock`` is not re-entrant, so the queue deadlocked as soon as a
    queued task existed.  Pop the events while holding the lock, then wake
    them after releasing it.
    """
    async with queue_dict_lock:
        count = len(non_queued)
        if not queued:
            return
        if limit == float("inf"):
            available = len(queued)
        else:
            available = max(0, int(limit - count))
        events = [queued.pop(mid) for mid in list(queued)[:available]]

    for event in events:
        event.set()
    if events:
        await sleep(0.7)


async def start_from_queued():
    all_limit, dl_limit, up_limit = (
        config_dict["QUEUE_ALL"],
        config_dict["QUEUE_DOWNLOAD"],
        config_dict["QUEUE_UPLOAD"],
    )

    if all_limit:
        # Reserve slots for both queues in one critical section.  Do not call
        # start_task_from_queued here: it also takes queue_dict_lock.
        async with queue_dict_lock:
            slots = max(0, all_limit - len(non_queued_dl) - len(non_queued_up))
            up_slots = min(
                slots,
                max(0, up_limit - len(non_queued_up)) if up_limit else slots,
            )
            up_events = [queued_up.pop(mid) for mid in list(queued_up)[:up_slots]]
            slots -= len(up_events)
            dl_slots = min(
                slots,
                max(0, dl_limit - len(non_queued_dl)) if dl_limit else slots,
            )
            dl_events = [queued_dl.pop(mid) for mid in list(queued_dl)[:dl_slots]]

        for event in up_events + dl_events:
            event.set()
        if up_events or dl_events:
            await sleep(0.7)
        return

    await start_task_from_queued(
        "up", up_limit or float("inf"), non_queued_up, queued_up
    )
    await start_task_from_queued(
        "dl", dl_limit or float("inf"), non_queued_dl, queued_dl
    )
