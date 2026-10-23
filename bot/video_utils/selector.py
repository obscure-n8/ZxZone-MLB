from __future__ import annotations
from aiofiles.os import path as aiopath, makedirs
from ast import literal_eval
from asyncio import Event, wait_for, gather
from functools import partial
from html import escape
from os import path as ospath
from PIL import Image
from pyrogram.filters import regex, user, text, photo, document
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from re import match as re_match
from time import time

from bot.core.config_manager import Config
config_dict = Config.get_all()
for _k, _v in {'DISABLE_VIDTOOLS': [], 'HARDSUB_FONT_NAME': '', 'HARDSUB_FONT_SIZE': 24}.items():
    config_dict.setdefault(_k, _v)
PRIVILEGED_ONLY_VT_MODES = {'compress', 'convert', 'watermark', 'subsync', 'video_audio_sync'}

# Broad GoogleTranslator language-code support, with Indian languages first.
VT_SUBTITLE_LANGUAGES = [
    ('te', 'Telugu'), ('ta', 'Tamil'), ('hi', 'Hindi'), ('kn', 'Kannada'),
    ('ml', 'Malayalam'), ('bn', 'Bengali'), ('mr', 'Marathi'), ('gu', 'Gujarati'),
    ('pa', 'Punjabi'), ('ur', 'Urdu'), ('or', 'Odia'), ('as', 'Assamese'),
    ('sa', 'Sanskrit'), ('ne', 'Nepali'), ('sd', 'Sindhi'), ('ks', 'Kashmiri'),
    ('kok', 'Konkani'), ('mai', 'Maithili'), ('doi', 'Dogri'), ('mni', 'Manipuri'),
    ('sat', 'Santali'), ('en', 'English'), ('es', 'Spanish'), ('fr', 'French'),
    ('de', 'German'), ('it', 'Italian'), ('pt', 'Portuguese'), ('ru', 'Russian'),
    ('uk', 'Ukrainian'), ('ar', 'Arabic'), ('fa', 'Persian'), ('tr', 'Turkish'),
    ('zh-CN', 'Chinese (Simplified)'), ('zh-TW', 'Chinese (Traditional)'),
    ('ja', 'Japanese'), ('ko', 'Korean'), ('id', 'Indonesian'), ('ms', 'Malay'),
    ('th', 'Thai'), ('vi', 'Vietnamese'), ('fil', 'Filipino'), ('sw', 'Swahili'),
    ('nl', 'Dutch'), ('pl', 'Polish'), ('sv', 'Swedish'), ('da', 'Danish'),
    ('fi', 'Finnish'), ('el', 'Greek'), ('he', 'Hebrew'), ('ro', 'Romanian'),
    ('hu', 'Hungarian'), ('cs', 'Czech'), ('sk', 'Slovak'), ('bg', 'Bulgarian'),
    ('hr', 'Croatian'), ('sr', 'Serbian'), ('sq', 'Albanian'), ('af', 'Afrikaans'),
]

VID_MODE = {
    'vid_vid':'Video + Video','vid_vid_audio':'Video + Audio','vid_sub':'Video + Subtitle',
    'subsync':'SubSync','compress':'Compress','convert':'Convert','watermark':'Watermark',
    'remove_ads_names':'Remove Ads & Names','extract':'Extract','trim':'Trim','audio_swap':'Audio Swap',
    'audio_track':'Audio Track','audio_export':'Audio Export → M4A','audio_split':'Audio Split (Language Variants)','subtitle_translate':'Translate Existing Subtitles','audio_to_subtitle':'Audio → Translated Subtitles (Whisper)','video_audio_sync':'Audio Sync','audio_channel':'Audio Channel',
    'subtitle_swap':'Subtitle Swap / Order','subtitle_rename':'Subtitle Rename',
    'rmstream':'Remove Stream','binary_split':'Media Split → Binary','multivt':'MULTI VT','rename':'Rename'
}
from bot.helper.ext_utils.bot_utils import new_task, new_thread, sync_to_async
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.links_utils import is_media
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.listeners import task_listener as task
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import send_message, edit_message, delete_message
async def sendMessage(text, message, buttons=None):
    return await send_message(message, text, buttons)
async def editMessage(text, message, buttons=None):
    return await edit_message(message, text, buttons)
async def deleteMessage(message):
    return await delete_message(message)


class SelectMode():
    def __init__(self, listener: task.TaskListener, isLink=False, multi_vt=False):
        self._isLink = isLink
        self._time = time()
        self._reply = None
        self.listener = listener
        self.is_rename = False
        self.mode = ''
        self.extra_data = {}
        self.multi_vt = bool(multi_vt)
        self.multi_modes = []
        self.newname = ''
        self.event = Event()
        self.message_event = Event()
        self.is_cancelled = False

    @new_thread
    async def _event_handler(self):
        pfunc = partial(cb_vidtools, obj=self)
        handler = self.listener.client.add_handler(CallbackQueryHandler(pfunc, filters=regex('^vidtool') & user(self.listener.user_id)), group=-1)
        try:
            await wait_for(self.event.wait(), timeout=900)
        except:
            self.mode = 'Task has been cancelled, time out!'
            self.is_cancelled = True
            self.event.set()
        finally:
            self.listener.client.remove_handler(*handler)

    @new_thread
    async def message_event_handler(self, mode=''):
        pfunc = partial(message_handler, obj=self, is_sub=mode == 'subfile')
        handler = self.listener.client.add_handler(MessageHandler(pfunc, user(self.listener.user_id)), group=1)
        try:
            await wait_for(self.message_event.wait(), timeout=900)
        except:
            self.message_event.set()
        finally:
            self.listener.client.remove_handler(*handler)
            self.message_event.clear()

    async def _send_message(self, text: str, buttons):
        if not self._reply:
            self._reply = await sendMessage(text, self.listener.message, buttons)
        else:
            await editMessage(text, self._reply, buttons)

    def _captions(self, mode: str = None):
        msg = '<b>🎬 VIDEO TOOLS STUDIO</b>\n<blockquote>Fine-tune your media with a clear, guided workflow.</blockquote>'
        if vidmode := VID_MODE.get(self.mode):
            msg += f'\nMode: <b>{vidmode}</b>'
        if self.newname:
            msg += f'\nName: <code>{escape(self.newname)}</code>'
        if self.mode in ('subtitle_translate', 'audio_to_subtitle'):
            language = next((name for code, name in VT_SUBTITLE_LANGUAGES if code.lower() == self.extra_data.get('subtitle_language', 'en').lower()), self.extra_data.get('subtitle_language', 'English'))
            msg += f'\nTarget Language: <b>{escape(language)}</b>'
        if self.mode == 'trim' and self.extra_data:
            msg += f'\nTrim Duration: <b>{self.extra_data.get("start_time", "")} – {self.extra_data.get("end_time", "")}</b>'
        if self.mode in ('vid_sub', 'watermark'):
            hardsub = self.extra_data.get('hardsub')
            msg += f"\nHardsub Mode: <b>{'Enable' if hardsub else 'Disable'}</b>"
            if hardsub:
                msg += f"\nBold Style: <b>{'Enable' if self.extra_data.get('boldstyle') else 'Disable'}</b>"
                if fontname := self.extra_data.get('fontname') or config_dict['HARDSUB_FONT_NAME']:
                    msg += f'\nFont Name: <b>{fontname.replace("_", " ")}</b>'
                if fontsize := self.extra_data.get('fontsize') or config_dict['HARDSUB_FONT_SIZE']:
                    msg += f'\nFont Size: <b>{fontsize}</b>'
                if fontcolour := self.extra_data.get('fontcolour'):
                    msg += f'\nFont Colour: <b>{fontcolour}</b>'
        if quality := self.extra_data.get('quality'):
            msg += f'\nQuality: <b>{quality}</b>'
        if self.mode == 'watermark' and (wmsize := self.extra_data.get('wmsize')):
            msg += f'\nWM Size: <b>{wmsize}</b>'
            if wmsize and (wmposition := self.extra_data.get('wmposition')):
                pos_dict = {'5:5': 'Top Left',
                            'main_w-overlay_w-5:5': 'Top Right',
                            '5:main_h-overlay_h': 'Bottom Left',
                            'w-overlay_w-5:main_h-overlay_h-5': 'Bottom Right'}
                msg += f'\nWM Position: <b>{pos_dict[wmposition]}</b>'
            if popupwm := self.extra_data.get('popupwm'):
                msg += f'\nDisplay: <b>{popupwm}x/20s</b>'
        if self.mode == 'subsync' and (typee := self.extra_data.get('type')):
            msg += f'\nSync Mode: <b>{typee.removeprefix("sync_").title()}</b>'
        match mode:
            case 'rename':
                msg += '\n\n<i>Send the new filename (extension optional).</i>'
            case 'watermark':
                msg += '\n\n<i>Send valid image to set as watermark...</i>'
            case 'subfile':
                msg += '\n\n<i>Send valid subtitle (.ass or .srt) for hardsub...</i>'
            case 'wmsize':
                msg += '\n\n<i>Choose watermark size</i>'
            case 'fontsize':
                msg += ('\n\n<i>Choose font size</i>\n'
                        '<b>Recommended:</b>\n'
                        '1080p: <b>21-26 </b>\n'
                        '720p: <b>16-21</b>\n'
                        '480p: <b>11-16</b>')
            case 'trim':
                msg += '\n\n<i>Send valid trim duration <b>hh:mm:ss hh:mm:ss</b></i>'
            case 'audio_delay':
                msg += '\n\n<i>Send audio delay in milliseconds. Example: <b>-5300</b> or <b>5300</b></i>'
            case 'remove_ads_names':
                if self.extra_data.get('awaiting_remove_area'):
                    msg += ('\n\n<i>Send area as <b>x:y:w:h</b>.</i>'
                            '\nFor multiple areas use <b>;</b>. Example: <b>0:0:1920:180;0:900:1920:180</b>')
                if self.extra_data.get('awaiting_remove_cut'):
                    cut_type = self.extra_data.get('cut_type')
                    if cut_type == 'start':
                        msg += ('\n\n<i>Send start-ad end time as <b>hh:mm:ss</b>.</i>'
                                '\nExample: <b>00:02:30</b>')
                    elif cut_type == 'end':
                        msg += ('\n\n<i>Send end-ad start time as <b>hh:mm:ss</b>.</i>'
                                '\nExample: <b>02:25:10</b>')
                    else:
                        msg += ('\n\n<i>Send ad time as <b>hh:mm:ss-hh:mm:ss</b>.</i>'
                                '\nExample: <b>01:18:20-01:20:45</b>')
                elif self.extra_data.get('cuts'):
                    cuts = ', '.join(f"{a}-{b}" for a, b in self.extra_data['cuts'])
                    msg += f'\nCuts: <b>{cuts}</b>'
        msg += f'\n\n<blockquote>⏳ <b>Session time left:</b> {get_readable_time(max(0, 900 - (time()-self._time)))}\nTap <b>Done</b> when your settings are ready.</blockquote>'
        return msg

    async def list_buttons(self, mode: str=''):
        buttons, bnum = ButtonMaker(), 2
        if not mode:
            vid_modes = VID_MODE
            vid_modes = dict(list(VID_MODE.items())[4:]) if self._isLink else VID_MODE
            # Compression, conversion and watermarking are resource-intensive and
            # must only be available to the bot owner or configured sudo users.
            # Hide them in the UI and enforce the same policy in cb_vidtools.
            if not await CustomFilters.sudo('', self.listener.message):
                vid_modes = {key: value for key, value in vid_modes.items()
                             if key not in PRIVILEGED_ONLY_VT_MODES}
            for key, value in vid_modes.items():
                buttons.data_button(f"{'✅ ' if self.mode == key else ''}{value}", f'vidtool {key}')
            if self.mode == 'binary_split':
                split_size = self.extra_data.get('split_size', 1024 ** 3)
                for size, label in [(500 * 1024**2, '500 MB'), (1024**3, '1 GB'), (2 * 1024**3, '2 GB'), (4 * 1024**3, '4 GB')]:
                    buttons.data_button(f"{'✅ ' if split_size == size else ''}{label}", f'vidtool binary_size {size}', 'header')
            buttons.data_button(f"{'✅ ' if self.multi_vt else ''}🧩 Multi-step", 'vidtool multivt', 'header')
            buttons.data_button(f'{"✅ " if self.newname else ""}Rename', 'vidtool rename', 'header')
            buttons.data_button('✖ Cancel', 'vidtool cancel', 'footer')
            # Rename is a complete selectable operation even though it does not
            # use self.mode. Keep DONE visible after the user enters the name so
            # the operation only starts when the user explicitly presses DONE.
            if self.mode or self.newname:
                buttons.data_button('✅ Done', 'vidtool done', 'footer')
            if self.mode in ('vid_sub', 'watermark') and await CustomFilters.sudo('', self.listener.message):
                hardsub = self.extra_data.get('hardsub')
                buttons.data_button(f"{'✅ ' if hardsub else ''}Hardsub", 'vidtool hardsub', 'header')
                if hardsub:
                    if self.mode == 'watermark':
                        buttons.data_button(f"{'✅ ' if await aiopath.exists(self.extra_data.get('subfile', '')) else ''}Sub File", 'vidtool subfile', 'header')
                    buttons.data_button('Font Style', 'vidtool fontstyle', 'header')

            if self.mode in ('compress', 'watermark') or self.extra_data.get('hardsub'):
                buttons.data_button('Quality', 'vidtool quality', 'header')
            if self.mode == 'watermark':
                buttons.data_button('Popup', 'vidtool popupwm', 'header')
            if self.mode == 'subsync':
                delay = self.extra_data.get('audio_delay')
                buttons.data_button(
                    f"{'✅ ' if delay is not None else ''}Custom Delay"
                    + (f" ({delay} ms)" if delay is not None else ''),
                    'vidtool audio_delay', 'header'
                )
        else:
            def _buttons_style(name=True, size=True, colour=True, position='header', cb='fontstyle'):
                if name:
                    buttons.data_button('Font Name', 'vidtool fontstyle fontname', position)
                if size:
                    buttons.data_button('Font Size', 'vidtool fontstyle fontsize', position)
                if colour:
                    buttons.data_button('Font Colour', 'vidtool fontstyle fontcolour', position)
                buttons.data_button('<<', f'vidtool {cb}', 'footer')
                buttons.data_button('✅ Done', 'vidtool done', 'footer')

            match mode:
                case 'subtitle_languages':
                    page = int(self.extra_data.get('subtitle_language_page', 0))
                    per_page = 20
                    languages = VT_SUBTITLE_LANGUAGES[page * per_page:(page + 1) * per_page]
                    selected = self.extra_data.get('subtitle_language', 'en').lower()
                    for code, name in languages:
                        buttons.data_button(f"{'✅ ' if code.lower() == selected else ''}{name}", f'vidtool subtitle_lang {code}')
                    if page > 0:
                        buttons.data_button('◀ Previous', f'vidtool subtitle_page {page - 1}', 'footer')
                    if (page + 1) * per_page < len(VT_SUBTITLE_LANGUAGES):
                        buttons.data_button('Next ▶', f'vidtool subtitle_page {page + 1}', 'footer')
                    buttons.data_button('Back', 'vidtool back', 'footer')
                    buttons.data_button('✅ Done', 'vidtool done', 'footer')
                case 'merge_mode':
                    merge_mode = self.extra_data.get('merge_mode', 'normal')
                    buttons.data_button(f"{'✅ ' if merge_mode == 'normal' else ''}Normal Mode", 'vidtool merge_mode normal')
                    buttons.data_button(f"{'✅ ' if merge_mode == 'advanced' else ''}Advanced Mode", 'vidtool merge_mode advanced')
                    buttons.data_button('<<', 'vidtool back', 'footer')
                    buttons.data_button('✅ Done', 'vidtool done', 'footer')
                case 'remove_ads_names':
                    presets = self.extra_data.get('presets') or ([self.extra_data.get('preset')] if self.extra_data.get('preset') else [])
                    buttons.data_button(f"{'✅ ' if 'top' in presets else ''}Top Banner", 'vidtool rmads top')
                    buttons.data_button(f"{'✅ ' if 'bottom' in presets else ''}Bottom Banner", 'vidtool rmads bottom')
                    buttons.data_button(f"{'✅ ' if 'top' in presets and 'bottom' in presets else ''}Top + Bottom", 'vidtool rmads top_bottom')
                    buttons.data_button(f"{'✅ ' if self.extra_data.get('areas') else ''}Custom Area", 'vidtool rmads custom')
                    buttons.data_button(f"{'✅ ' if self.extra_data.get('start_ad') else ''}Start Ad", 'vidtool rmads start')
                    buttons.data_button(f"{'✅ ' if self.extra_data.get('interval_ad') else ''}Interval Ad", 'vidtool rmads interval')
                    buttons.data_button(f"{'✅ ' if self.extra_data.get('end_ad') else ''}End Ad", 'vidtool rmads end')
                    buttons.data_button(f"{'✅ ' if self.extra_data.get('custom_cut') else ''}Custom Cut", 'vidtool rmads cut')
                    if self.extra_data.get('areas'):
                        buttons.data_button('Clear Areas', 'vidtool rmads clear', 'header')
                    if self.extra_data.get('cuts'):
                        buttons.data_button('Clear Cuts', 'vidtool rmads clearcuts', 'header')
                    buttons.data_button('<<', 'vidtool back', 'footer')
                    buttons.data_button('✅ Done', 'vidtool done', 'footer')
                case 'subsync':
                    buttons.data_button('Manual', 'vidtool sync_manual')
                    buttons.data_button('Auto', 'vidtool sync_auto')
                case 'audio_delay':
                    buttons.data_button('<<', 'vidtool back', 'footer')
                    buttons.data_button('✅ Done', 'vidtool done', 'footer')
                case 'quality':
                    bnum = 3
                    [buttons.data_button(f"{'✅ ' if self.extra_data.get('quality') == key else ''}{key}", f'vidtool quality {key}') for key in ['1080p', '720p', '540p', '480p', '360p']]
                    buttons.data_button('<<', 'vidtool back', 'footer')
                    buttons.data_button('✅ Done', 'vidtool done', 'footer')
                case 'popupwm':
                    bnum, popupwm = 5, self.extra_data.get('popupwm', 0)
                    if popupwm:
                        buttons.data_button('Reset', 'vidtool popupwm 0', 'header')
                    [buttons.data_button(f"{'✅ ' if popupwm == key else ''}{key}", f'vidtool popupwm {key}') for key in range(2, 21, 2)]
                    buttons.data_button('<<', 'vidtool back', 'footer')
                    buttons.data_button('✅ Done', 'vidtool done', 'footer')
                case 'wmsize':
                    bnum = 3
                    [buttons.data_button(str(btn), f'vidtool wmsize {btn}') for btn in [5, 10, 15, 20, 25, 30]]
                case 'fontstyle':
                    bnum = 3
                    _buttons_style(position=None, cb='back')
                    buttons.data_button(f"{'✅ ' if self.extra_data.get('boldstyle') else ''}Bold Style", f"vidtool fontstyle boldstyle {self.extra_data.get('boldstyle', False)}", 'header')
                case 'fontname':
                    _buttons_style(name=False)
                    [buttons.data_button(f"{'✅ ' if btn == self.extra_data.get('fontname') else ''}{btn.replace('_', ' ')}", f'vidtool fontstyle fontname {btn}')
                     for btn in ['Arial', 'Impact', 'Verdana', 'Consolas', 'DejaVu_Sans', 'Comic_Sans_MS', 'Simple_Day_Mistu']]
                case 'fontsize':
                    bnum = 5
                    _buttons_style(size=False)
                    [buttons.data_button(f"{'✅ ' if str(btn) == self.extra_data.get('fontsize') else ''}{btn}", f'vidtool fontstyle fontsize {btn}') for btn in range(11, 31)]
                case 'fontcolour':
                    bnum = 3
                    _buttons_style(colour=False)
                    colours = [('Red', '0000ff'), ('Green', '00ff00'), ('Blue', 'ff0000'), ('Yellow', '00ffff'), ('Orange', '0054ff'), ('Purple', '005aff'),
                               ('Soft Red', 'd470ff'), ('Soft Green', '80ff80'), ('Soft Blue', 'ffb84d'), ('Soft Yellow', '80ffff')]
                    [buttons.data_button(f"{'✅ ' if hexcolour == self.extra_data.get('fontcolour') else ''}{btn}", f'vidtool fontstyle fontcolour {hexcolour}') for btn, hexcolour in colours]
                case 'wmposition':
                    buttons.data_button('Top Left', 'vidtool wmposition 5:5')
                    buttons.data_button('Top Right', 'vidtool wmposition main_w-overlay_w-5:5')
                    buttons.data_button('Bottom Left', 'vidtool wmposition 5:main_h-overlay_h')
                    buttons.data_button('Bottom Right', 'vidtool wmposition w-overlay_w-5:main_h-overlay_h-5')
                case _:
                    buttons.data_button('<<', 'vidtool back', 'footer')

        caption = self._captions(mode)
        if mode == 'subtitle_languages':
            caption = (
                '<b>Choose Target Language</b>\n\n'
                + ('Translate existing embedded subtitles into your chosen language.\n' if self.mode == 'subtitle_translate' else 'Transcribe the audio with Whisper, then translate the generated subtitles.\n')
                + 'Indian languages include Telugu, Tamil, Hindi, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, Urdu, Odia, Assamese and more.\n'
                + 'Other international languages are available on the next pages.\n\n'
                + 'The source language is detected automatically.'
            )
        if mode == 'merge_mode':
            caption = (
                '<b>Video + Video — Merge Mode</b>\n\n'
                'Choose the existing merge workflow used by the <code>-ht</code> menu.\n'
                '• <b>Normal Mode:</b> merge automatically\n'
                '• <b>Advanced Mode:</b> open the merge planner to reorder files and rename output'
            )
        if not mode and not self.mode:
            caption = (
                "<b>Merge Tools</b>\n\n"
                "<b>1.</b> Video + Video\n"
                "<b>Audio Tools</b>\n\n"
                "<b>1.</b> Video + Audio\n"
                "<b>2.</b> Audio Swap\n"
                "<b>3.</b> Audio Track\n"
                "<b>4.</b> Audio Sync\n"
                "<b>5.</b> Audio Channel\n"
                "<b>6.</b> Remove Stream\n"
                "<b>7.</b> Remove Ads & Names\n\n"
                "<b>Select a mode:</b>"
            )
        await self._send_message(caption, buttons.build_menu(bnum, 3))

    async def get_buttons(self):
        future = self._event_handler()
        await gather(self.list_buttons(), future)
        if self.is_cancelled:
            if self._reply:
                await deleteMessage(self._reply)
            return
        if self._reply:
            await deleteMessage(self._reply)
        return [self.mode, self.newname, self.extra_data]


async def message_handler(_, message: Message, obj: SelectMode, is_sub=False):
    data = None
    if obj.is_rename and message.text:
        requested = (message.text or '').strip().replace('\\', '/')
        requested = requested.rsplit('/', 1)[-1].replace('\x00', '').strip()
        if not requested or requested in ('.', '..'):
            await sendMessage('Invalid filename. Send a name such as <code>Episode 01.mkv</code>.', message)
            return
        if len(requested.encode('utf-8')) > 240:
            await sendMessage('Filename is too long. Please use 240 UTF-8 bytes or fewer.', message)
            return
        obj.newname = requested
        obj.is_rename = False
        try:
            await message.delete()
        except Exception:
            pass
        # The shared handler tail refreshes the menu and removes this message.
    elif obj.mode == 'watermark' and (media := is_media(message)):
        if is_sub:
            if message.document and not media.file_name.lower().endswith(('.ass', '.srt')):
                await sendMessage('Only .ass or .srt allowed!', message)
                return
            obj.extra_data['subfile'] = await message.download(ospath.join('watermark', media.file_id))
        else:
            if message.document and 'image' not in getattr(media, 'mime_type', 'None'):
                await sendMessage('Only image document allowed!', message)
                return
            fpath = await message.download(ospath.join('watermark', media.file_id))
            await sync_to_async(Image.open(fpath).convert('RGBA').save, ospath.join('watermark', f'{obj.listener.mid}.png'), 'PNG')
            await clean_target(fpath)
            data = 'wmsize'
    elif obj.mode == 'trim' and message.text:
        if match := re_match(r'(\d{2}:\d{2}:\d{2})\s(\d{2}:\d{2}:\d{2})', message.text.strip()):
            obj.extra_data.update({'start_time': match.group(1), 'end_time': match.group(2)})
        else:
            await sendMessage('Invalid trim duration format!', message)
            return
    elif obj.mode == 'subsync' and obj.extra_data.get('awaiting_audio_delay') and message.text:
        value = message.text.strip()
        if re_match(r'^[-+]?\d+$', value):
            obj.extra_data['audio_delay'] = int(value)
            obj.extra_data.pop('awaiting_audio_delay', None)
        else:
            await sendMessage('Invalid delay! Send milliseconds like -5300 or 5300.', message)
            return
    elif obj.mode == 'remove_ads_names' and obj.extra_data.get('awaiting_remove_area') and message.text:
        value = message.text.strip()
        areas = []
        try:
            for part in value.split(';'):
                nums = part.strip().split(':')
                if len(nums) != 4:
                    raise ValueError
                x, y, w, h = [int(n) for n in nums]
                if min(x, y, w, h) < 0 or w <= 0 or h <= 0:
                    raise ValueError
                areas.append((x, y, w, h))
            if not areas or len(areas) > 20:
                raise ValueError
        except (TypeError, ValueError):
            await sendMessage('Invalid area. Use x:y:w:h, or multiple areas separated by ;', message)
            return
        obj.extra_data['areas'] = areas
        obj.extra_data.pop('awaiting_remove_area', None)
    elif obj.mode == 'remove_ads_names' and obj.extra_data.get('awaiting_remove_cut') and message.text:
        value = message.text.strip()
        cut_type = obj.extra_data.get('cut_type')
        if cut_type in ('start', 'end'):
            # Start/End Ad accept either a single boundary time or a full range.
            # This lets End Ad use e.g. 02:17:53-02:18:12 directly.
            range_match = re_match(
                r'^\s*(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})\s*$',
                value
            )
            single_match = re_match(r'^\s*(\d{2}:\d{2}:\d{2})\s*$', value)

            def _valid_time(t):
                h, m, sec = map(int, t.split(':'))
                return m <= 59 and sec <= 59

            if range_match:
                start, end = range_match.group(1), range_match.group(2)
                if not (_valid_time(start) and _valid_time(end)):
                    await sendMessage('Invalid time. Use hh:mm:ss or hh:mm:ss-hh:mm:ss', message)
                    return
                if cut_type == 'start' and start != '00:00:00':
                    # Start Ad is defined from the beginning; when a range is supplied,
                    # use its end as the start-ad end boundary.
                    start, end = '00:00:00', end
                elif cut_type == 'end':
                    # End Ad can now use the exact supplied range.
                    pass
            elif single_match:
                value = single_match.group(1)
                if not _valid_time(value):
                    await sendMessage('Invalid time. Use hh:mm:ss or hh:mm:ss-hh:mm:ss', message)
                    return
                if cut_type == 'start':
                    start, end = '00:00:00', value
                else:
                    start, end = value, '00:00:00'
            else:
                await sendMessage('Invalid time. Use hh:mm:ss or hh:mm:ss-hh:mm:ss', message)
                return
        else:
            # Accept one or many ranges, e.g.
            # 00:00:00-00:00:29,02:17:53 - 02:18:12
            ranges = [part.strip() for part in value.split(',') if part.strip()]
            if not ranges or len(ranges) > 20:
                await sendMessage('Invalid time. Use hh:mm:ss-hh:mm:ss, multiple ranges separated by commas.', message)
                return
            parsed_ranges = []
            def _secs(t):
                h, m, sec = map(int, t.split(':'))
                if m > 59 or sec > 59:
                    raise ValueError
                return h * 3600 + m * 60 + sec
            try:
                for item in ranges:
                    parts = re_match(r'^\s*(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})\s*$', item)
                    if not parts:
                        raise ValueError
                    start_i, end_i = parts.group(1), parts.group(2)
                    if _secs(end_i) <= _secs(start_i):
                        raise ValueError
                    parsed_ranges.append((start_i, end_i))
            except ValueError:
                await sendMessage('Invalid time. Use hh:mm:ss-hh:mm:ss, multiple ranges separated by commas.', message)
                return
            start, end = parsed_ranges[0]
        cuts = obj.extra_data.setdefault('cuts', [])
        if cut_type == 'start':
            cuts = [c for c in cuts if c[0] != '00:00:00']
            cuts.insert(0, (start, end))
        elif cut_type == 'end':
            cuts = [c for c in cuts if c[1] != '00:00:00']
            cuts.append((start, end))
        else:
            # Custom Cut can contain multiple comma-separated ranges.
            if 'parsed_ranges' in locals():
                cuts.extend(parsed_ranges)
            else:
                cuts.append((start, end))
            obj.extra_data['custom_cut'] = True
        if cut_type == 'start':
            obj.extra_data['start_ad'] = True
        elif cut_type == 'interval':
            obj.extra_data['interval_ad'] = True
        elif cut_type == 'end':
            obj.extra_data['end_ad'] = True
        obj.extra_data['cuts'] = cuts[:20]
        obj.extra_data.pop('awaiting_remove_cut', None)
        obj.extra_data.pop('cut_type', None)
    obj.message_event.set()
    # After Remove Ads & Names text input, stay inside its submenu.
    # Returning to the root video-tools menu here makes the next
    # Remove Ads & Names click appear to do nothing because the mode
    # is already selected.
    if obj.mode == 'remove_ads_names' and data is None:
        data = 'remove_ads_names'
    await gather(obj.list_buttons(data), deleteMessage(message))


@new_task
async def cb_vidtools(_, query: CallbackQuery, obj: SelectMode):
    data = (query.data or '').split()
    if len(data) < 2:
        await query.answer()
        return
    if data[1] in ('start', 'done') and not obj.mode and not obj.newname:
        await query.answer('Select a video tool first!', show_alert=True)
        return
    # Defense in depth: even a stale or manually crafted callback cannot start
    # privileged video operations for ordinary users.
    is_privileged = await CustomFilters.sudo('', obj.listener.message)
    if data[1] in PRIVILEGED_ONLY_VT_MODES and not is_privileged:
        await query.answer(
            f'{VID_MODE.get(data[1], data[1])} is available only to the bot owner or sudo users.',
            show_alert=True,
        )
        return
    if obj.mode in PRIVILEGED_ONLY_VT_MODES and not is_privileged:
        obj.mode = ''
        obj.extra_data.clear()
        await query.answer('This video operation is restricted to the bot owner or sudo users.', show_alert=True)
        await obj.list_buttons()
        return
    if data[1] in config_dict.get('DISABLE_VIDTOOLS', []):
        await query.answer(f'{VID_MODE[data[1]]} has been disabled!', True)
        return
    await query.answer()
    if data[1] == obj.mode and data[1] != 'remove_ads_names':
        return
    match data[1]:
        case 'multivt':
            obj.multi_vt = not obj.multi_vt
            if obj.multi_vt:
                obj.mode = ''
                obj.extra_data.clear()
            await obj.list_buttons()
        case 'start':
            obj.extra_data['_multi_vt'] = obj.multi_vt
            obj.message_event.set()
            obj.event.set()
        case 'done':
            # Rename has no self.mode; newname itself is the selected operation.
            # In MULTI VT mode, every completed single operation returns the
            # current MULTI VT state to the caller. This is required even for
            # Rename and submenu-based tools whose button is "Done" rather
            # than "Start".
            obj.extra_data['_multi_vt'] = bool(obj.multi_vt)
            obj.message_event.set()
            obj.event.set()
        case 'subtitle_lang':
            if len(data) > 2:
                selected = data[2]
                if any(code.lower() == selected.lower() for code, _ in VT_SUBTITLE_LANGUAGES):
                    obj.extra_data['subtitle_language'] = selected
            await obj.list_buttons('subtitle_languages')
        case 'subtitle_page':
            if len(data) > 2 and data[2].isdigit():
                obj.extra_data['subtitle_language_page'] = max(0, min(int(data[2]), (len(VT_SUBTITLE_LANGUAGES) - 1) // 20))
            await obj.list_buttons('subtitle_languages')
        case 'merge_mode':
            if len(data) > 2 and data[2] in ('normal', 'advanced'):
                obj.extra_data['merge_mode'] = data[2]
            await obj.list_buttons('merge_mode')
        case 'back':
            if obj.message_event:
                obj.message_event.set()
            if data[1] == 'back' and obj.mode == 'vid_vid':
                obj.mode = ''
                obj.extra_data.clear()
            await obj.list_buttons('remove_ads_names' if obj.mode == 'remove_ads_names' else '')
        case 'cancel':
            obj.mode = 'Task has been cancelled!'
            obj.is_cancelled = True
            obj.message_event.set()
            obj.event.set()
        case 'binary_size':
            obj.extra_data['split_size'] = int(data[2])
            await obj.list_buttons()
        case 'quality' | 'popupwm' as value:
            if len(data) == 3:
                obj.extra_data[value] = data[2] if value == 'quality' else int(data[2])
            await obj.list_buttons(value)
        case 'hardsub':
            hmode = not bool(obj.extra_data.get('hardsub'))
            if not hmode and obj.mode == 'vid_sub':
                obj.extra_data.clear()
            obj.extra_data['hardsub'] = hmode
            await obj.list_buttons()
        case 'subfile':
            future = obj.message_event_handler('subfile')
            await gather(obj.list_buttons('subfile'), future)
        case 'fontstyle':
            mode = 'fontstyle'
            if len(data) > 2:
                mode = data[2]
                is_bold = mode == 'boldstyle'
                if len(data) == 4:
                    if not is_bold and obj.extra_data.get(mode) == data[3]:
                        return
                    obj.extra_data[mode] = not literal_eval(data[3]) if is_bold else data[3]
                if is_bold:
                    mode = 'fontstyle'
            await obj.list_buttons(mode)
        case 'sync_manual' | 'sync_auto' as value:
            obj.extra_data['type'] = value
            await obj.list_buttons()
        case 'wmsize' | 'wmposition' as value:
            obj.extra_data[value] = data[2]
            await obj.list_buttons('wmposition' if value == 'wmsize' else None)
        case 'rmads':
            action = data[2] if len(data) > 2 else ''
            if action == 'custom':
                obj.extra_data['awaiting_remove_area'] = True
                obj.extra_data.pop('preset', None)
                future = obj.message_event_handler('remove_ads_names')
                await future
                await obj.list_buttons('remove_ads_names')
                return
            if action in ('start', 'interval', 'end', 'cut'):
                obj.extra_data['awaiting_remove_cut'] = True
                obj.extra_data['cut_type'] = action
                future = obj.message_event_handler('remove_ads_names')
                await future
                await obj.list_buttons('remove_ads_names')
                return
            if action == 'clear':
                obj.extra_data.pop('areas', None)
                obj.extra_data.pop('preset', None)
            elif action == 'clearcuts':
                obj.extra_data.pop('cuts', None)
            elif action == 'audio_track':
                obj.extra_data['audio_track'] = not bool(obj.extra_data.get('audio_track'))
            elif action in ('top', 'bottom', 'top_bottom'):
                presets = obj.extra_data.setdefault('presets', [])
                if action == 'top_bottom':
                    # Treat Top + Bottom as a convenience toggle for both
                    # individual selections, so it can coexist with Custom
                    # Area and other options without creating a duplicate
                    # pseudo-preset.
                    if 'top' in presets and 'bottom' in presets:
                        presets.remove('top')
                        presets.remove('bottom')
                    else:
                        if 'top' not in presets:
                            presets.append('top')
                        if 'bottom' not in presets:
                            presets.append('bottom')
                else:
                    if action in presets:
                        presets.remove(action)
                    else:
                        presets.append(action)
                # Keep legacy single-preset key in sync for older executor paths.
                obj.extra_data['preset'] = presets[0] if len(presets) == 1 else None
            await obj.list_buttons('remove_ads_names')
        case value:
            if value == 'rename':
                obj.mode = 'rename'
                obj.is_rename = True
                obj.extra_data.clear()
            else:
                obj.mode = value
                obj.extra_data.clear()
            if value in ('subtitle_translate', 'audio_to_subtitle'):
                obj.extra_data['subtitle_language'] = 'en'
                obj.extra_data['subtitle_language_page'] = 0
                await obj.list_buttons('subtitle_languages')
                return
            if value == 'vid_vid':
                obj.extra_data['merge_mode'] = 'normal'
                await obj.list_buttons('merge_mode')
                return
            if value in ['watermark', 'rename', 'trim']:
                future = obj.message_event_handler(value)
                await gather(obj.list_buttons(value), future)
                return
            if value == 'remove_ads_names':
                await obj.list_buttons('remove_ads_names')
                return
            await obj.list_buttons('subsync' if value == 'subsync' else '')
