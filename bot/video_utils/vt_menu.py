"""Interactive pre-download video-tools menu for the -vt flag."""
from asyncio import Event, wait_for
from functools import partial
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import send_message, delete_message

VT_MODES = [
    ("vid_vid", "Video + Video"), ("vid_vid_audio", "Video + Audio"),
    ("vid_sub", "Video + Subtitle"), ("subsync", "SubSync"),
    ("compress", "Compress"), ("convert", "Convert"),
    ("watermark", "Watermark"), ("remove_ads_names", "Remove Ads & Names"),
    ("extract", "Extract"), ("trim", "Trim"),
    ("audio_swap", "Audio Swap"), ("audio_track", "Audio Track"),
    ("audio_export", "Audio Export → M4A"), ("audio_split", "Audio Split (Language Variants)"),
    ("subtitle_translate", "Translate Existing Subtitles"),
    ("audio_to_subtitle", "Audio → Translated Subtitles (Whisper)"),
    ("video_audio_sync", "Audio Sync"), ("audio_channel", "Audio Channel"),
    ("subtitle_swap", "Subtitle Swap / Order"), ("subtitle_rename", "Subtitle Rename"),
    ("rmstream", "Remove Stream"), ("binary_split", "Media Split → Binary"),
    ("multivt", "MULTI VT"), ("rename", "Rename"),
]

async def choose_vt_mode(client, message, user_id, timeout=900):
    """Show the requested menu before download and return selected mode or None."""
    event = Event()
    state = {"mode": None, "done": False, "cancel": False, "reply": None}

    def build():
        buttons = ButtonMaker()
        for key, label in VT_MODES:
            mark = "✅ " if state["mode"] == key else ""
            buttons.data_button(mark + label, f"vtmenu select {key}")
        buttons.data_button("Cancel", "vtmenu cancel", "footer")
        buttons.data_button("Done", "vtmenu done", "footer")
        return buttons.build_menu(2)

    async def callback(_, query):
        data = (query.data or "").split()
        if len(data) < 2:
            await query.answer()
            return
        action = data[1]
        if action == "select" and len(data) >= 3:
            state["mode"] = data[2]
            await state["reply"].edit_text("<b>Video Tools</b>\n\nSelected: <b>{}</b>\nChoose an operation, then press Done.".format(
                dict((k, v) for k, v in VT_MODES).get(state["mode"], state["mode"])
            ), reply_markup=build())
            await query.answer("Selected")
        elif action == "done":
            if not state["mode"]:
                await query.answer("Choose an operation first", show_alert=True)
                return
            state["done"] = True
            event.set()
            await query.answer("Confirmed")
        elif action == "cancel":
            state["cancel"] = True
            event.set()
            await query.answer("Cancelled")
    handler = client.add_handler(
        CallbackQueryHandler(callback, filters=regex(r"^vtmenu") & user(user_id)),
        group=-9,
    )
    try:
        state["reply"] = await send_message(message,
            "<b>Video Tools</b>\n\nChoose an operation before downloading, then press Done.",
            build(), block=False)
        try:
            await wait_for(event.wait(), timeout=timeout)
        except TimeoutError:
            state["cancel"] = True
        return None if state["cancel"] else state["mode"]
    finally:
        client.remove_handler(*handler)
        if state.get("reply"):
            try:
                await delete_message(state["reply"])
            except Exception:
                pass
