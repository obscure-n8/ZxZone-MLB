from __future__ import annotations
import re
from ast import literal_eval
from asyncio import Event, wait_for, wrap_future, gather
from functools import partial
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery
from time import time

VID_MODE = {
    'vid_vid':'Video + Video','vid_vid_audio':'Video + Audio','vid_sub':'Video + Subtitle',
    'subsync':'SubSync','compress':'Compress','convert':'Convert','watermark':'Watermark',
    'remove_ads_names':'Remove Ads & Names','extract':'Extract','trim':'Trim','audio_swap':'Audio Swap',
    'audio_track':'Audio Track','audio_export':'Audio Export → M4A','audio_split':'Audio Split (Language Variants)','subtitle_translate':'Translate Existing Subtitles','audio_to_subtitle':'Audio → Translated Subtitles (Whisper)','video_audio_sync':'Audio Sync','audio_channel':'Audio Channel',
    'subtitle_swap':'Subtitle Swap / Order','subtitle_rename':'Subtitle Rename',
    'rmstream':'Remove Stream','binary_split':'Media Split → Binary','multivt':'MULTI VT','rename':'Rename'
}
from bot.helper.ext_utils.bot_utils import new_thread
from bot.helper.ext_utils.status_utils import get_readable_file_size, get_readable_time
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import send_message, edit_message, delete_message
async def sendMessage(text, message, buttons=None):
    return await send_message(message, text, buttons)
async def editMessage(text, message, buttons=None):
    return await edit_message(message, text, buttons)
async def deleteMessage(message):
    return await delete_message(message)
from bot.helper.video_utils import executor as exc
from pyrogram.handlers import MessageHandler
from pyrogram.filters import text


class ExtraSelect:
    def __init__(self, executor: exc.VidEcxecutor):
        self._listener = executor.listener
        self._time = time()
        self._reply = None
        self.executor = executor
        self.event = Event()
        self.is_cancel = False
        self.extension: list[str] = [None, None, 'mkv']
        self.status = ''

    @new_thread
    async def _event_handler(self):
        pfunc = partial(cb_extra, obj=self)
        handler = self._listener.client.add_handler(
            CallbackQueryHandler(pfunc, filters=regex('^extra') & user(self._listener.user_id)),
            group=-1
        )

        msg_handler = self._listener.client.add_handler(
            MessageHandler(partial(extra_message_handler, obj=self), filters=text & user(self._listener.user_id)),
            group=-2
        )

        try:
            await wait_for(self.event.wait(), timeout=900)
        except:
            self.event.set()
        finally:
            self._listener.client.remove_handler(*handler)
            self._listener.client.remove_handler(*msg_handler)


    async def update_message(self, text: str, buttons):
        if not self._reply:
            self._reply = await sendMessage(text, self._listener.message, buttons)
        else:
            await editMessage(text, self._reply, buttons)

    def streams_select(self, streams: dict=None):
        buttons = ButtonMaker()
        if not self.executor.data:
            self.executor.data.setdefault('stream', {})
            self.executor.data['sdata'] = []
            for stream in streams:
                indexmap, codec_name, codec_type, lang = stream.get('index'), stream.get('codec_name'), stream.get('codec_type'), stream.get('tags', {}).get('language')
                if not lang:
                    lang = str(indexmap)
                if codec_type not in ['video', 'audio', 'subtitle']:
                    continue
                if codec_type == 'audio':
                    self.executor.data['is_audio'] = True
                elif codec_type == 'subtitle':
                    self.executor.data['is_sub'] = True
                self.executor.data['stream'][indexmap] = {'info': f'{codec_type.title()} ~ {lang.upper()}',
                                                          'name': codec_name,
                                                          'map': indexmap,
                                                          'type': codec_type,
                                                          'lang': lang}
        mode, ddict = self.executor.mode, self.executor.data
        if not ddict.get('stream'):
            return ('No supported audio, subtitle, or video streams were found.', buttons.build_menu(1))
        text = ''
        for key, value in ddict['stream'].items():
            if mode == 'extract':
                buttons.data_button(value['info'], f'extra {mode} {key}')
                audext, subext, vidext = self.extension
                text = (f'<b>STREAM EXTRACT SETTINGS ~ {self._listener.tag}</b>\n'
                        f'<code>{self.executor.name}</code>\n'
                        f"<b>┌ </b>File Size: <b>{get_readable_file_size(self.executor.size)}</b>\n"
                        f'<b>├ </b>Video Format: <b>{vidext.upper()}</b>\n'
                        f'<b>├ </b>Audio Format: <b>{audext.upper()}</b>\n'
                        f'<b>├ </b>Subtitle Format: <b>{subext.upper()}</b>\n'
                        f"<b>└ </b>Alternative Mode: <b>{'✅ Enable' if ddict.get('alt_mode') else 'Disable'}</b>\n\n"
                        'Select an available stream below to extract.')
            else:
                if value['type'] != 'video':
                    buttons.data_button(value['info'], f'extra {mode} {key}')
                text = (f'<b>STREAM REMOVE SETTINGS ~ {self._listener.tag}</b>\n'
                        f'<code>{self.executor.name}</code>\n'
                        f'File Size: <b>{get_readable_file_size(self.executor.size)}</b>\n')
                if sdata := ddict.get('sdata'):
                    text += '\nThe following streams will be removed:\n'
                    for i, sindex in enumerate(sdata, start=1):
                        text += f"{i}. {ddict['stream'][sindex]['info']}\n".replace('✅ ', '')
                text += '\nSelect an available stream below!'
        if mode == 'extract':
            buttons.data_button('✅ ALT Mode' if ddict.get('alt_mode') else 'ALT Mode', f"extra {mode} alt {ddict.get('alt_mode', False)}", 'footer')
        if ddict.get('is_sub'):
            buttons.data_button('All Subs', f'extra {mode} subtitle')
        if ddict.get('is_audio'):
            buttons.data_button('All Audio', f'extra {mode} audio')
        buttons.data_button('Cancel', 'extra cancel', 'footer')
        if mode == 'extract':
            for ext in self.extension:
                buttons.data_button(ext.upper(), f'extra {mode} extension {ext}', 'header')
            buttons.data_button('Extract All', f'extra {mode} video audio subtitle')
        else:
            buttons.data_button('Reset', f'extra {mode} reset', 'header')
            buttons.data_button('Reverse', f'extra {mode} reverse', 'header')
            buttons.data_button('Continue', f'extra {mode} continue', 'footer')
        text += f'\n\n<i>Time Out: {get_readable_time(900 - (time()-self._time))}</i>'
        return text, buttons.build_menu(2)

    async def compress_select(self, streams: dict):
        self.executor.data = {}
        buttons = ButtonMaker()
        for stream in streams:
            indexmap, codec_type, lang = stream.get('index'), stream.get('codec_type'), stream.get('tags', {}).get('language')
            if not lang:
                lang = str(indexmap)
            if codec_type == 'video' and indexmap == 0:
                self.executor.data['video'] = indexmap
            if codec_type == 'video' and 'video' not in self.executor.data:
                self.executor.data['video'] = indexmap
            if codec_type == 'audio':
                buttons.data_button(f'Audio ~ {lang.upper()}', f'extra compress {indexmap}')
        buttons.data_button('Continue', 'extra compress 0')
        buttons.data_button('Cancel', 'extra cancel')
        await self.update_message(f'{self._listener.tag}, Select available audio or press <b>Continue (no audio)</b>.\n<code>{self.executor.name}</code>', buttons.build_menu(2))

    async def rmstream_select(self, streams: dict):
        self.executor.data = {}
        await self.update_message(*self.streams_select(streams))

    async def convert_select(self, streams: dict):
        buttons = ButtonMaker()
        hvid = '1080p'
        resolution = {'1080p': 'Convert 1080p',
                      '720p': 'Convert 720p',
                      '540p': 'Convert 540p',
                      '480p': 'Convert 480p',
                      '360p': 'Convert 360p'}
        for stream in streams:
            if stream['codec_type'] == 'video':
                vid_height = f'{stream["height"]}p'
                if vid_height in resolution:
                    hvid = vid_height
                break
        keys = list(resolution)
        for key in keys[keys.index(hvid)+1:]:
            buttons.data_button(resolution[key], f'extra convert {key}')
        buttons.data_button('Cancel', 'extra cancel', 'footer')
        await self.update_message(f'{self._listener.tag}, Select an available resolution to convert.\n<code>{self.executor.name}</code>', buttons.build_menu(2))

    async def subsync_select(self):
        buttons = ButtonMaker()
        text = ''
        index = 1
        if not self.status:
            for possition, file in self.executor.data['list'].items():
                if file.endswith(('srt', '.ass')):
                    ref_file = self.executor.data['final'].get(possition, {}).get('ref', '')
                    text += f'{index}. {file} {"✅ " if ref_file else ""}\n'
                    but_txt = f'✅ {index}' if ref_file else index
                    buttons.data_button(but_txt, f'extra subsync {possition}')
                    index += 1
            buttons.data_button('Cancel', 'extra cancel', 'footer')
            if self.executor.data['final']:
                buttons.data_button('Continue', 'extra subsync continue', 'footer')
        else:
            file: dict = self.executor.data['list'][self.status]
            text = (f'Current: <b>{file}</b>\n'
                    f'References: <b>{ref}</b>\n' if (ref := self.executor.data['final'].get(self.status, {}).get('ref')) else ''
                    '\nSelect Available References Below!\n')
            self.executor.data['final'][self.status] = {'file': file}
            selected_refs = {
                item.get('ref') for key, item in self.executor.data['final'].items()
                if key != self.status and isinstance(item, dict) and item.get('ref')
            }
            for possition, file in self.executor.data['list'].items():
                if possition != self.status and file not in selected_refs:
                    text += f'{index}. {file}\n'
                    buttons.data_button(index, f'extra subsync select {possition}')
                    index += 1
        await self.update_message(text, buttons.build_menu(5))

    async def extract_select(self, streams: dict):
        self.executor.data = {}
        ext = [None, None, 'mkv']
        for stream in streams:
            codec_name, codec_type = stream.get('codec_name'), stream.get('codec_type')
            if codec_type == 'audio' and not ext[0]:
                # The codec is codec_name, not codec_type (which is always
                # "audio" here). Pick a compatible default output extension.
                match codec_name:
                    case 'mp3':
                        ext[0] = 'mp3'
                    case 'aac' | 'ac3' | 'eac3' as value:
                        ext[0] = value
                    case 'flac':
                        ext[0] = 'flac'
                    case 'alac':
                        ext[0] = 'm4a'
                    case 'pcm_s16le' | 'pcm_s24le' | 'pcm_s32le':
                        ext[0] = 'wav'
                    case _:
                        ext[0] = 'aac'
            elif codec_type == 'subtitle' and not ext[1]:
                ext[1] = 'srt' if codec_name == 'subrip' else 'ass'
        if not ext[0]:
            ext[0] = 'aac'
        if not ext[1]:
            ext[1] = 'srt'
        self.extension = ext
        await self.update_message(*self.streams_select(streams))

    
    async def audio_swap_select(self, streams: dict):
        self.executor.executor_streams = streams

        if not self.executor.data:
            self.executor.data = {'key': []}

        selected = self.executor.data.get('key', [])

        selected_streams = [s for s in streams if s.get('index') in selected]
        unselected_streams = [s for s in streams if s.get('index') not in selected]

        selected_streams = sorted(
            selected_streams,
            key=lambda x: selected.index(x.get('index'))
        )

        streams = selected_streams + unselected_streams

        buttons = ButtonMaker()

        text = f'<b>AUDIO SWAP SETTINGS ~ {self._listener.tag}</b>\n'
        text += f'<code>{self.executor.name}</code>\n'
        text += f'File Size: <b>{get_readable_file_size(self.executor.size)}</b>\n\n'

        if selected:
            text += '<b>Audio Swap Order:</b>\n'
            for i, idx in enumerate(selected, start=1):
                for s in streams:
                    if s.get('index') == idx:
                        lang = s.get('tags', {}).get('language', str(idx))
                        text += f'{i}. {lang.upper()}\n'
                        break
            text += '\n'

        text += 'Select available stream below!\n'
        text += f'\n\n<i>Time Out: {get_readable_time(900 - (time()-self._time))}</i>'

        for stream in streams:
            if stream.get('codec_type') == 'audio':
                indexmap = stream.get('index')
                lang = stream.get('tags', {}).get('language', str(indexmap))

                prefix = "✅ " if indexmap in selected else ""
                buttons.data_button(f'{prefix}Audio ~ {lang.upper()}', f'extra audio_swap {indexmap}')

        if any(s.get('codec_type') == 'subtitle' for s in streams):
            buttons.data_button('All Subs', 'extra audio_swap subtitle')

        buttons.data_button('All Audio', 'extra audio_swap audio')
        buttons.data_button('Cancel', 'extra cancel', 'footer')
        buttons.data_button('Continue', 'extra audio_swap done', 'footer')

        await self.update_message(text, buttons.build_menu(2))

    async def subtitle_swap_select(self, streams: dict):
        """Choose subtitle order; the first selected subtitle becomes default."""
        self.executor.executor_streams = streams
        if not self.executor.data:
            self.executor.data = {'key': []}
        selected = self.executor.data.get('key', [])
        subs = [s for s in streams if s.get('codec_type') == 'subtitle']
        ordered = sorted(subs, key=lambda x: selected.index(x.get('index')) if x.get('index') in selected else len(selected) + subs.index(x))
        buttons = ButtonMaker()
        text = (f'<b>SUBTITLE SWAP / ORDER ~ {self._listener.tag}</b>\n'
                f'<code>{self.executor.name}</code>\n\n'
                'Select subtitle tracks in the order you want. The first selected track becomes the default.\n')
        if selected:
            text += '\n<b>Selected order:</b>\n'
            for pos, idx in enumerate(selected, 1):
                stream = next((x for x in subs if x.get('index') == idx), None)
                if stream:
                    tags = stream.get('tags', {})
                    text += f"{pos}. {(tags.get('language') or tags.get('title') or f'Subtitle {idx}').upper()}\n"
        for stream in ordered:
            idx = stream.get('index')
            tags = stream.get('tags', {})
            label = tags.get('language') or tags.get('title') or f'Subtitle {idx}'
            buttons.data_button(f"{'✅ ' if idx in selected else ''}💬 {label}", f'extra subtitle_swap {idx}')
        buttons.data_button('Clear Selection', 'extra subtitle_swap clear', 'header')
        buttons.data_button('Cancel', 'extra cancel', 'footer')
        buttons.data_button('Continue', 'extra subtitle_swap done', 'footer')
        await self.update_message(text, buttons.build_menu(2))

    async def subtitle_rename_select(self, streams: dict):
        self.executor.executor_streams = streams
        if not self.executor.data:
            self.executor.data = {'rename': {}}
        rename_map = self.executor.data.get('rename', {})
        buttons = ButtonMaker()
        text = f'<b>SUBTITLE TRACK NAMES ~ {self._listener.tag}</b>\n<code>{self.executor.name}</code>\n\n'
        subs = [s for s in streams if s.get('codec_type') == 'subtitle']
        for stream in subs:
            idx = stream.get('index')
            tags = stream.get('tags', {})
            label = rename_map.get(str(idx)) or tags.get('language') or tags.get('title') or f'Subtitle {idx}'
            buttons.data_button(f'✏ {label}', f'extra subtitle_rename {idx}')
            text += f'• {label}\n'
        text += '\nSend a new name/language when prompted. Existing subtitles remain unchanged unless renamed.'
        buttons.data_button('Cancel', 'extra cancel', 'footer')
        buttons.data_button('Done', 'extra subtitle_rename done', 'footer')
        await self.update_message(text, buttons.build_menu(2))

    async def audio_channel_select(self, streams: dict):
        """Select an audio track and target channel layout."""
        self.executor.executor_streams = streams
        self.executor.data = self.executor.data or {}
        self.executor.data.setdefault('channel', {})
        buttons = ButtonMaker()
        text = (f'<b>AUDIO CHANNEL SETTINGS ~ {self._listener.tag}</b>\n'
                f'<code>{self.executor.name}</code>\n\n'
                'Select an audio track to change its channel layout.\n')

        audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
        for i, stream in enumerate(audio_streams):
            idx = stream.get('index')
            tags = stream.get('tags', {})
            lang = tags.get('language') or f'AUDIO {idx}'
            title = tags.get('title') or tags.get('handler_name') or ''
            current = stream.get('channels') or '?'
            layout = stream.get('channel_layout') or f'{current}ch'
            selected = self.executor.data['channel'].get(str(idx))
            label = f'{"✅ " if selected else ""}Audio ~ {lang.upper()} ({layout})'
            if title:
                label += f' - {title}'
            buttons.data_button(label, f'extra audio_channel {idx}')

        buttons.data_button('Continue', 'extra audio_channel done', 'footer')
        buttons.data_button('Cancel', 'extra cancel', 'footer')
        await self.update_message(text, buttons.build_menu(1))

    async def audio_channel_options(self, idx: int):
        self.executor.data = self.executor.data or {'channel': {}}
        self.executor.data.setdefault('channel', {})
        current = self.executor.data['channel'].get(str(idx))
        buttons = ButtonMaker()
        for label, value in [('1.0', '1'), ('2.0', '2'), ('5.1', '6'), ('7.1', '8')]:
            buttons.data_button(f'{"✅ " if current == value else ""}{label}', f'extra audio_channel_set {idx} {value}')
        buttons.data_button('<< Back', 'extra audio_channel back', 'footer')
        await self.update_message(
            f'<b>Select Channel Layout</b>\nTrack: <b>{idx}</b>\n\n'
            'Choose the target audio channel layout.',
            buttons.build_menu(2)
        )

    async def audio_rename_select(self, streams: dict):
        self.executor.executor_streams = streams

        if not self.executor.data:
            self.executor.data = {"rename": {}}

        rename_map = self.executor.data.get("rename", {})

        buttons = ButtonMaker()

        text = f'<b>AUDIO TRACK NAMES ~ {self._listener.tag}</b>\n'
        text += f'<code>{self.executor.name}</code>\n\n'

        for stream in streams:
            if stream.get("codec_type") == "audio":
                idx = stream.get("index")
                tags = stream.get("tags", {})
                lang = tags.get("language") or tags.get("LANGUAGE") or str(idx)

                name = lang.upper()

                if str(idx) in rename_map:
                    name = f'✏ {rename_map[str(idx)]}'

                text += f'• {name}\n'
                buttons.data_button(name, f'extra audio_rename {idx}')

        text += f'\n<i>Time Out: {get_readable_time(900 - (time()-self._time))}</i>'

        buttons.data_button('Cancel', 'extra cancel', 'footer')
        buttons.data_button('Done', 'extra audio_rename done', 'footer')

        await self.update_message(text, buttons.build_menu(2))









    async def video_audio_sync_select(self, streams=None):
        if not self.executor.data:
            self.executor.data = {}
        buttons = ButtonMaker()
        msg = (
            f'<b>VIDEO AUDIO SYNC</b>\n'
            f'<code>{self.executor.name}</code>\n\n'
            'Automatic timestamp-based audio synchronization is enabled.\n'
            'Press Start to detect and correct the audio offset automatically.\n\n'
            f'<i>Time Out: {get_readable_time(900 - (time()-self._time))}</i>'
        )
        buttons.data_button('▶ Start Automatic Sync', 'extra video_audio_sync start')
        buttons.data_button('❌ Cancel', 'extra cancel', 'footer')
        await self.update_message(msg, buttons.build_menu(2))

    async def get_buttons(self, *args):
        future = self._event_handler()
        if extra_mode := getattr(self, f'{self.executor.mode}_select', None):
            await extra_mode(*args)
        await wrap_future(future)
        self.executor.event.set()
        await deleteMessage(self._reply)
        if self.is_cancel:
            self._listener.suproc = 'cancelled'
            await self._listener.onUploadError(f'{VID_MODE[self.executor.mode]} stopped by user!')


async def cb_extra(_, query: CallbackQuery, obj: ExtraSelect):
    data = (query.data or '').split()
    if len(data) < 2:
        await query.answer()
        return
    match data[1]:
        case 'cancel':
            await query.answer()
            obj.is_cancel = obj.executor.is_cancel = True
            obj.executor.data = None
            obj.event.set()
        case 'subsync':
            if data[2].isdigit():
                obj.status = int(data[2])
            elif data[2] == 'select':
                obj.executor.data['final'][obj.status]['ref'] = obj.executor.data['list'][int(data[3])]
                obj.status = ''
            elif data[2] == 'continue':
                await query.answer()
                obj.event.set()
                return
            await gather(query.answer(), obj.subsync_select())
        case 'compress':
            await query.answer()
            obj.executor.data['audio'] = int(data[2])
            obj.event.set()
        case 'convert':
            await query.answer()
            obj.executor.data = data[2]
            obj.event.set()
        case 'rmstream':
            ddict: dict = obj.executor.data
            match data[2]:
                case 'reset':
                    if sdata := ddict['sdata']:
                        await query.answer()
                        for mapindex in sdata:
                            info = ddict['stream'][mapindex]['info']
                            ddict['stream'][mapindex]['info'] = info.replace('✅ ', '')
                        sdata.clear()
                        await obj.update_message(*obj.streams_select())
                    else:
                        await query.answer('No streams are selected to reset.', True)
                case 'continue':
                    if ddict['sdata']:
                        await query.answer()
                        obj.event.set()
                    else:
                        await query.answer('Select at least one stream.', True)
                case 'audio' | 'subtitle' as value:
                    await query.answer()
                    obj.executor.data['key'] = value
                    obj.event.set()
                case 'reverse':
                    if ddict['sdata']:
                        await query.answer()
                        new_sdata = [x for x in ddict['stream'] if x not in ddict['sdata'] and x != 0]
                        for key, value in ddict['stream'].items():
                            info = value['info']
                            ddict['stream'][key]['info'] = f'✅ {info}' if key in new_sdata else info.replace('✅ ', '')
                        ddict['sdata'] = new_sdata
                        await obj.update_message(*obj.streams_select())
                    else:
                        await query.answer('No streams are selected to reverse.', True)
                case value:
                    await query.answer()
                    mapindex = int(value)
                    info = ddict['stream'][mapindex]['info']
                    if mapindex in ddict['sdata']:
                        ddict['sdata'].remove(mapindex)
                        ddict['stream'][mapindex]['info'] = info.replace('✅ ', '')
                    else:
                        ddict['sdata'].append(mapindex)
                        ddict['stream'][mapindex]['info'] = f'✅ {info}'
                    await obj.update_message(*obj.streams_select())
        
        case 'audio_swap':
            if len(data) < 3:
                await query.answer()
                return
            if data[2] == 'done' and (not obj.executor.data or not obj.executor.data.get('key')):
                await query.answer('Select at least one audio!', show_alert=True)
                return
            await query.answer()

            if data[2] == 'subtitle':
                obj.executor.data['key'] = 'subtitle'
                obj.event.set()
                return

            if data[2] == 'audio':
                obj.executor.data['key'] = 'audio'
                obj.event.set()
                return

            if data[2] == 'done':
                obj.event.set()
                return

            idx = int(data[2])

            if not obj.executor.data:
                obj.executor.data = {'key': []}

            if idx in obj.executor.data['key']:
                obj.executor.data['key'].remove(idx)
            else:
                obj.executor.data['key'].append(idx)

            await obj.audio_swap_select(obj.executor.executor_streams)


        case 'subtitle_swap':
            if len(data) < 3:
                await query.answer()
                return
            value = data[2]
            if value == 'done':
                if not obj.executor.data or not obj.executor.data.get('key'):
                    await query.answer('Select at least one subtitle track!', show_alert=True)
                    return
                await query.answer('Subtitle order saved')
                obj.event.set()
                return
            await query.answer()
            if value == 'clear':
                obj.executor.data = {'key': []}
            else:
                try:
                    idx = int(value)
                except ValueError:
                    return
                selected = obj.executor.data.setdefault('key', [])
                if idx in selected:
                    selected.remove(idx)
                else:
                    selected.append(idx)
            await obj.subtitle_swap_select(obj.executor.executor_streams)

        case 'subtitle_rename':
            if len(data) < 3:
                await query.answer()
                return
            if data[2] == 'done':
                if not obj.executor.data.get('rename'):
                    await query.answer('Rename at least one subtitle track!', show_alert=True)
                    return
                await query.answer('Subtitle names saved')
                obj.event.set()
                return
            try:
                idx = int(data[2])
            except (TypeError, ValueError):
                await query.answer()
                return
            await query.answer()
            if not obj.executor.data:
                obj.executor.data = {'rename': {}}
            obj.executor.data['waiting'] = idx
            msg = await sendMessage(f'Send name/language for subtitle track {idx}', obj._listener.message)
            obj.executor.data['prompt_msg'] = msg.id

        case 'audio_channel':
            if len(data) < 3:
                await query.answer()
                return
            if data[2] == 'done' and (not obj.executor.data or not obj.executor.data.get('channel')):
                await query.answer('Select at least one audio track!', show_alert=True)
                return
            await query.answer()
            if data[2] == 'done':
                obj.event.set()
                return
            if data[2] == 'back':
                await obj.audio_channel_select(obj.executor.executor_streams)
                return
            try:
                idx = int(data[2])
            except ValueError:
                return
            await obj.audio_channel_options(idx)

        case 'audio_channel_set':
            await query.answer()
            if len(data) < 4:
                return
            try:
                idx = int(data[2])
            except ValueError:
                return
            obj.executor.data = obj.executor.data or {'channel': {}}
            obj.executor.data.setdefault('channel', {})
            obj.executor.data['channel'][str(idx)] = data[3]
            await obj.audio_channel_select(obj.executor.executor_streams)

        case 'audio_rename':
            if len(data) < 3:
                await query.answer()
                return

            if data[2] == 'done':
                if not obj.executor.data.get("rename"):
                    await query.answer("Rename at least one track!", show_alert=True)
                    return

                await query.answer()
                obj.executor.rename = obj.executor.data["rename"]

                obj.event.set()
                return

            try:
                idx = int(data[2])
            except (TypeError, ValueError):
                await query.answer()
                return

            await query.answer()
            if not obj.executor.data:
                obj.executor.data = {"rename": {}}

            obj.executor.data["waiting"] = idx

            msg = await sendMessage(
                f"Send name for Track {idx}",
                obj._listener.message
            )
            obj.executor.data["prompt_msg"] = msg.id



        case 'video_audio_sync':
            await query.answer()
            obj.executor.data = obj.executor.data or {}
            if data[2] == 'start':
                obj.executor.data['mode'] = 'automatic'
                obj.event.set()
                return

        case 'extract':
            value = data[2]
            await query.answer()
            if value in ('extension', 'alt'):
                ext_dict = {'ass': [1, 'srt'],
                            'srt': [1, 'ass'],
                            'aac': [0, 'ac3'],
                            'ac3': [0, 'eac3'],
                            'eac3': [0, 'm4a'],
                            'm4a': [0, 'mka'],
                            'mka': [0, 'wav'],
                            'wav': [0, 'aac'],
                            'mp4': [2, 'mkv'],
                            'mkv': [2, 'mp4']}
                if data[3] in ext_dict:
                    index, ext = ext_dict[data[3]]
                    obj.extension[index] = ext
                if value == 'alt':
                    obj.executor.data['alt_mode'] = not literal_eval(data[3])
                await obj.update_message(*obj.streams_select())
            else:
                obj.executor.data.update({'key': int(value) if value.isdigit() else data[2:],
                                          'extension': obj.extension})
                obj.event.set()


async def extra_message_handler(_, message, obj: ExtraSelect):
    data = obj.executor.data or {}

    # Custom audio delay has priority over all other text input.
    if data.get('waiting_audio_delay') is True:
        value = (message.text or '').strip()

        if not re.fullmatch(r'[+-]?\d+', value):
            await sendMessage(
                'Invalid delay. Enter only milliseconds, e.g. -5300 or +5300.',
                message
            )
            return

        obj.executor.data['delay'] = int(value)
        obj.executor.data['waiting_audio_delay'] = False

        try:
            await message.delete()
        except:
            pass
        if obj.executor.data.get('delay_prompt_msg'):
            try:
                await message._client.delete_messages(
                    chat_id=message.chat.id,
                    message_ids=obj.executor.data['delay_prompt_msg']
                )
            except:
                pass
            obj.executor.data.pop('delay_prompt_msg', None)

        obj.event.set()
        return

    await rename_message_handler(_, message, obj)


async def rename_message_handler(_, message, obj: ExtraSelect):
    if not obj.executor.data or "waiting" not in obj.executor.data:
        return

    idx = obj.executor.data["waiting"]
    name = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    if not name:
        return

    obj.executor.data.setdefault("rename", {})
    obj.executor.data["rename"][str(idx)] = name

    if obj.executor.data.get("prompt_msg"):
        try:
            await message._client.delete_messages(
                chat_id=message.chat.id,
                message_ids=obj.executor.data["prompt_msg"]
            )
        except:
            pass

    obj.executor.data.pop("prompt_msg", None)
    obj.executor.data.pop("waiting", None)

    if obj.executor.mode == 'subtitle_rename':
        await obj.subtitle_rename_select(obj.executor.executor_streams)
    else:
        await obj.audio_rename_select(obj.executor.executor_streams)
