from __future__ import annotations
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, makedirs, listdir
from aioshutil import move
import json
from asyncio import create_subprocess_exec, sleep, gather, Event, wrap_future
from asyncio.subprocess import PIPE
from natsort import natsorted
from os import path as ospath, walk, replace as os_replace
from time import time
import re

from bot import task_dict, task_dict_lock, queue_dict_lock, non_queued_dl, LOGGER, user_data
from bot.core.config_manager import Config, BinConfig
config_dict = Config.get_all()
for _k, _v in {'DISABLE_MULTI_VIDTOOLS': [], 'COMPRESS_BANNER': '', 'HARDSUB_FONT_NAME': '', 'HARDSUB_FONT_SIZE': 24, 'LIB264_PRESET': 'veryfast', 'LIB265_PRESET': 'veryfast', 'VIDTOOLS_FAST_MODE': True}.items():
    config_dict.setdefault(_k, _v)
FFMPEG_NAME = BinConfig.FFMPEG_NAME
VID_MODE = {
    'vid_vid':'Video + Video','vid_vid_audio':'Video + Audio','vid_sub':'Video + Subtitle',
    'subsync':'SubSync','compress':'Compress','convert':'Convert','watermark':'Watermark',
    'remove_ads_names':'Remove Ads & Names','extract':'Extract','trim':'Trim','audio_swap':'Audio Swap',
    'audio_track':'Audio Track','audio_export':'Audio Export → M4A','audio_split':'Audio Split (Language Variants)',
    'subtitle_translate':'Translate Existing Subtitles',
    'audio_to_subtitle':'Audio → Translated Subtitles (Whisper)',
    'video_audio_sync':'Audio Sync','audio_channel':'Audio Channel',
    'subtitle_swap':'Subtitle Swap / Order','subtitle_rename':'Subtitle Rename',
    'rmstream':'Remove Stream','binary_split':'Media Split → Binary','multivt':'MULTI VT','rename':'Rename',
    'vid_vid_audio_swap':'Video + Video → Audio Swap',
    'vid_vid_rmstream':'Video + Video → Remove Stream',
    'vid_vid_audio_sync':'Video + Video → Audio Sync',
    'audio_rename':'Audio Track Rename'
}
from bot.helper.ext_utils.bot_utils import sync_to_async, cmd_exec, new_task
from bot.helper.ext_utils.files_utils import get_path_size, clean_target
from bot.helper.ext_utils.links_utils import get_url_name
from bot.helper.ext_utils.media_utils import get_document_type, get_media_info, FFProgress
from bot.helper.ext_utils.task_manager import check_running_tasks
from bot.helper.listeners import task_listener as task
from bot.helper.mirror_leech_utils.status_utils.ffmpeg_status import FFmpegStatus as FFMpegStatus
from bot.helper.mirror_leech_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import send_status_message as sendStatusMessage, update_status_message
from bot.helper.video_utils.extra_selector import ExtraSelect


async def get_metavideo(video_file):
    stdout, stderr, rcode = await cmd_exec([
        'ffprobe', '-hide_banner', '-print_format', 'json', '-show_format',
        '-show_streams', video_file
    ])
    if rcode != 0:
        LOGGER.error(stderr)
        return {}, {}
    metadata = json.loads(stdout)
    return metadata.get('streams', {}), metadata.get('format', {})


# ---- METADATA HELPER ----
async def add_metadata_flag(cmd: list):
    if '-map_metadata' not in cmd:
        cmd.insert(-1, '-map_metadata')
        cmd.insert(-1, '0')
    return cmd


async def estimate_audio_content_offset(reference_file: str, target_file: str, max_seconds: int = 300):
    """Estimate A/V audio offset from coarse speech/energy patterns.

    This is intentionally dependency-free. It compares low-rate mono RMS envelopes
    from the original video audio and the external/dubbed audio. It works well when
    both tracks contain the same program/dialogue with a mostly constant offset.
    If confidence is low, callers should fall back to timestamp synchronization.
    Returns offset in seconds: positive means target audio starts earlier and must
    be delayed; negative means target starts later and must be advanced.
    """
    async def envelope(file):
        proc = await create_subprocess_exec(
            FFMPEG_NAME, '-hide_banner', '-loglevel', 'error', '-nostdin',
            '-i', file, '-t', str(max_seconds), '-vn', '-ac', '1', '-ar', '4000',
            '-f', 's16le', 'pipe:1', stdout=PIPE, stderr=PIPE)
        raw, err = await proc.communicate()
        if proc.returncode != 0 or not raw:
            return []
        import struct
        samples = struct.unpack('<%dh' % (len(raw) // 2), raw[:len(raw) - (len(raw) % 2)])
        step = 2000  # 0.5 second at 4000 Hz
        env = []
        for i in range(0, len(samples) - step + 1, step):
            chunk = samples[i:i + step]
            energy = sum(x * x for x in chunk) / len(chunk)
            env.append(energy ** 0.5)
        if not env:
            return []
        mean = sum(env) / len(env)
        env = [max(0.0, x - mean) for x in env]
        scale = max(env) or 1.0
        return [x / scale for x in env]

    ref, target = await gather(envelope(reference_file), envelope(target_file))
    if len(ref) < 20 or len(target) < 20:
        return None, 0.0

    # Search +/- 30 seconds in 0.5 second steps.
    max_shift = min(60, min(len(ref), len(target)) // 4)
    best_shift, best_score, second_score = 0, -1.0, -1.0
    for shift in range(-max_shift, max_shift + 1):
        r0 = max(0, shift)
        t0 = max(0, -shift)
        n = min(len(ref) - r0, len(target) - t0)
        if n < 20:
            continue
        a = ref[r0:r0 + n]
        b = target[t0:t0 + n]
        ma = sum(a) / n
        mb = sum(b) / n
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        da = sum((x - ma) ** 2 for x in a)
        db = sum((y - mb) ** 2 for y in b)
        score = num / ((da * db) ** 0.5 or 1.0)
        if score > best_score:
            second_score = best_score
            best_score = score
            best_shift = shift
        elif score > second_score:
            second_score = score

    # Require useful correlation and separation from the runner-up.
    confidence = max(0.0, best_score)
    if best_score < 0.28 or best_score - max(second_score, -1.0) < 0.015:
        return None, confidence

    # shift > 0 means reference is later in the aligned comparison, so target
    # begins earlier and needs to be delayed by shift * 0.5 seconds.
    return best_shift * 0.5, confidence


class VidEcxecutor(FFProgress):

    def __init__(self,
                 listener: task.TaskListener,
                 path: str,
                 gid: str,
                 metadata=False):
        self.data = None
        self.event = Event()
        self.listener = listener
        self.path = path
        self.name = ''
        self.outfile = ''
        self.size = 0
        self._metadata = metadata
        self._up_path = path
        self._gid = gid
        self._start_time = time()
        self._files = []
        self._qual = {
            '1080p': '1920',
            '720p': '1280',
            '540p': '960',
            '480p': '854',
            '360p': '640'
        }
        super().__init__()
        self.is_cancel = False

    async def _queue(self, update=False):
        if self._metadata:
            add_to_queue, event = await check_running_tasks(self.listener.mid)
            if add_to_queue:
                LOGGER.info('Added to Queue/Download: %s', self.name)
                async with task_dict_lock:
                    task_dict[self.listener.mid] = QueueStatus(
                        self.listener, self.size, self._gid, 'dl')
                await self.listener.on_download_start()
                if update:
                    await sendStatusMessage(self.listener.message)
                await event.wait()
                async with task_dict_lock:
                    if self.listener.mid not in task_dict:
                        self.is_cancel = True
                        return
            async with queue_dict_lock:
                non_queued_dl.add(self.listener.mid)

    async def execute(self):
        self._is_dir = await aiopath.isdir(self.path)
        self.mode, self.name, kwargs = self.listener.vidMode
        self.data = dict(kwargs or {})
        if not self._metadata and self.mode in config_dict[
                'DISABLE_MULTI_VIDTOOLS']:
            if path := await self._get_video():
                self.path = path
            else:
                return self._up_path
        if self._metadata:
            if not self.name:
                self.name = get_url_name(self.path)
            if not self.name.upper().endswith(('MP4', 'MKV')):
                self.name += '.mkv'
            try:
                self.size = int(self._metadata[1]['size'])
            except Exception as e:
                LOGGER.error(e)
                await self.listener.on_download_error(
                    'Invalid data, check the link!')
                return

        try:
            match self.mode:
                case 'vid_vid':
                    return await self._merge_vids()
                case 'vid_vid_audio_swap':
                    merged = await self._merge_vids()
                    if not merged or self.is_cancel:
                        return self._up_path
                    self.path = merged
                    self.is_vid_vid_audio_swap = True
                    self.mode = "audio_swap"
                    return await self._vid_audio_swap()

                case 'vid_vid_rmstream':
                    merged = await self._merge_vids()
                    if not merged or self.is_cancel:
                        return self._up_path
                    self.path = merged
                    self.is_vid_vid_rmstream = True
                    self.mode = "rmstream"
                    return await self._rm_stream()

                case 'vid_vid_audio_sync':
                    merged = await self._merge_vids()
                    if not merged or self.is_cancel:
                        return self._up_path
                    self.path = merged
                    self.mode = "video_audio_sync"
                    return await self._video_audio_sync()

                case 'remove_ads_names':
                    # Remove Ads & Names is fully configured by SelectMode.
                    # Do not send it through ExtraSelect before the main job.
                    self.data = dict(kwargs or {})
                    if self.data.get('cuts'):
                        result = await self._remove_ad_clips(**self.data)
                    else:
                        result = await self._remove_ads_names()
                    if self.is_cancel or not self.data.get('audio_track'):
                        return result
                    return await self._audio_track_postprocess(result)
                case 'vid_aud' | 'vid_vid_audio':
                    return await self._merge_auds()
                case 'audio_export':
                    return await self._audio_export()
                case 'audio_split':
                    return await self._audio_split()
                case 'subtitle_translate':
                    return await self._audio_to_translated_subtitles(audio_only=False)
                case 'audio_to_subtitle':
                    return await self._audio_to_translated_subtitles(audio_only=True)
                case 'audio_track':
                    video_path = await self._get_video()
                    if not video_path:
                        return self._up_path
                    # Audio Track only edits stream metadata in-place. The menu
                    # label/name (sometimes "🎬 .mkv") must never replace the
                    # real media filename used for upload/status.
                    self.name = ospath.basename(video_path)
                    self.path = video_path
                    result = await self._audio_track_postprocess(video_path)
                    self.outfile = result or video_path
                    self._up_path = result or video_path
                    return self._up_path
                case 'rename':
                    return await self._rename_output()
                case 'vid_sub':
                    return await self._merge_subs(**kwargs)
                case 'trim':
                    return await self._vid_trimmer(**kwargs)
                case 'watermark':
                    return await self._vid_marker(**kwargs)
                case 'compress':
                    return await self._vid_compress(**kwargs)
                case 'subsync':
                    return await self._subsync(**kwargs)
                case 'rmstream':
                    return await self._rm_stream()
                case 'audio_swap':
                    return await self._vid_audio_swap()
                case 'subtitle_swap':
                    return await self._vid_subtitle_swap()
                case 'subtitle_rename':
                    return await self._subtitle_rename()
                case 'audio_channel':
                    return await self._audio_channel()
                case 'audio_rename':
                    return await self._audio_rename()
                case 'video_audio_sync':
                    return await self._video_audio_sync()
                case 'extract':
                    return await self._vid_extract()
                case 'binary_split':
                    self.data = dict(kwargs or {})
                    return await self._binary_split()
                case _:
                    return await self._vid_convert()
        except Exception as e:
            LOGGER.error(e, exc_info=True)
        return self._up_path

    @new_task
    async def _start_handler(self, *args):
        await sleep(0.5)
        await ExtraSelect(self).get_buttons(*args)

    async def _send_status(self, status='wait'):
        async with task_dict_lock:
            task_dict[self.listener.mid] = FFMpegStatus(
                self.listener, self, self._gid, status)
        if self._metadata and status == 'wait':
            await sendStatusMessage(self.listener.message)

    async def _get_files(self):
        file_list = []
        if self._metadata:
            file_list.append(self.path)
        elif await aiopath.isfile(self.path):
            if (await get_document_type(self.path))[0]:
                file_list.append(self.path)
        else:
            for dirpath, _, files in await sync_to_async(walk, self.path):
                for file in natsorted(files):
                    file = ospath.join(dirpath, file)
                    if (await get_document_type(file))[0]:
                        file_list.append(file)
        return file_list

    async def _get_video(self):
        if not self._is_dir and (await get_document_type(self.path))[0]:
            return self.path
        for dirpath, _, files in await sync_to_async(walk, self.path):
            for file in natsorted(files):
                file = ospath.join(dirpath, file)
                if (await get_document_type(file))[0]:
                    return file

    async def _rename_output(self):
        """Rename the selected output without invoking the conversion fallback."""
        requested = ospath.basename((self.name or '').strip())
        if not requested or requested in ('.', '..'):
            LOGGER.warning('Video Tools rename skipped: empty or invalid name')
            return self._up_path
        target_path = self.path
        if self._is_dir:
            target_path = await self._get_video()
            if not target_path:
                LOGGER.warning('Video Tools rename skipped: no video file found')
                return self._up_path
        base_dir, old_name = ospath.split(target_path)
        old_ext = ospath.splitext(old_name)[1]
        if not ospath.splitext(requested)[1] and old_ext:
            requested += old_ext
        new_path = ospath.join(base_dir, requested)
        if ospath.abspath(new_path) == ospath.abspath(target_path):
            return self._up_path
        if await aiopath.exists(new_path):
            stem, ext = ospath.splitext(requested)
            suffix = 2
            while await aiopath.exists(new_path):
                requested_candidate = f'{stem} ({suffix}){ext}'
                new_path = ospath.join(base_dir, requested_candidate)
                suffix += 1
            LOGGER.info('Rename target already existed; using available name: %s', new_path)
        try:
            await sync_to_async(os_replace, target_path, new_path)
        except Exception:
            LOGGER.error('Video Tools rename failed', exc_info=True)
            return self._up_path
        if self._is_dir:
            return self._up_path
        self.outfile = new_path
        self._up_path = new_path
        return new_path

    async def _final_path(self, outfile=''):
        if self._metadata:
            if outfile:
                self._up_path = outfile
            elif self.outfile:
                self._up_path = self.outfile
            return self._up_path

        # Prefer the concrete output created by FFmpeg. Scanning the entire
        # download directory used to return the old source path (often already
        # deleted by _run_cmd) whenever an unrelated subtitle/image was present.
        if self.outfile and await aiopath.isfile(self.outfile):
            if self._is_dir or self.mode in ('extract', 'binary_split'):
                self._up_path = ospath.dirname(self.outfile)
            else:
                self._up_path = self.outfile
            return self._up_path

        scan_dir = self._up_path if self._is_dir else ospath.split(self._up_path)[0]
        for dirpath, _, files in await sync_to_async(walk, scan_dir):
            for file in files:
                if file.endswith(tuple(self.listener.excluded_extensions)):
                    await clean_target(ospath.join(dirpath, file))

        all_files = []
        for dirpath, _, files in await sync_to_async(walk, scan_dir):
            all_files.extend((dirpath, file) for file in files)
        if len(all_files) == 1:
            self._up_path = ospath.join(*all_files[0])
        return self._up_path

    async def _name_base_dir(self,
                             path,
                             info: str = None,
                             multi: bool = False):
        """Choose a natural output filename without adding tool-name suffixes.

        Keep an explicitly configured/requested output name. Otherwise retain
        the source basename and extension, and write generated files into a
        dedicated VT_Output directory so FFmpeg never reads and writes the
        same path. `info` remains accepted for compatibility with callers but
        is deliberately not appended to the filename.
        """
        is_file = await aiopath.isfile(path)
        base_dir, file_name = ospath.split(path)
        if not self.name or multi:
            self.name = file_name or 'output.mkv'
        if not ospath.splitext(self.name)[1]:
            ext = ospath.splitext(file_name)[1] or '.mkv'
            self.name += ext
        # Preserve a valid media extension; don't silently rename user choices.
        if ospath.splitext(self.name)[1].lower() not in {
                '.mkv', '.mp4', '.webm', '.mov', '.m4v', '.avi', '.ts',
                '.m2ts', '.mts', '.flv', '.wmv', '.mpg', '.mpeg', '.3gp',
                '.ogv', '.vob', '.mxf', '.f4v', '.divx', '.asf'}:
            # Only fall back when the source/output extension is not a known
            # media container. Keep the original basename and supported ext.
            stem = ospath.splitext(self.name)[0]
            self.name = f'{stem}.mkv'
        output_root = base_dir if is_file else path
        output_dir = ospath.join(output_root, 'VT_Output')
        await makedirs(output_dir, exist_ok=True)
        return output_dir

    async def _run_cmd(self, cmd, status='prog'):
        await self._send_status(status)
        self.listener.subproc = await create_subprocess_exec(*cmd, stderr=PIPE)
        _, code = await gather(self.progress(status),
                               self.listener.subproc.wait())

        if code == 0:
            if not self.listener.seed:
                await gather(*[clean_target(file) for file in self._files])

            self._files.clear()
            return True

        if self.listener.subproc == 'cancelled' or code == -9:
            self.is_cancel = True
        else:
            LOGGER.error('%s. Failed to %s: %s',
                         (await
                          self.listener.subproc.stderr.read()).decode().strip(),
                         VID_MODE[self.mode], self.outfile)
            self._files.clear()

    @staticmethod
    def _time_seconds(value):
        h, m, sec = map(int, value.split(':'))
        return h * 3600 + m * 60 + sec

    async def _remove_ad_clips(self, cuts=None, preset=None, presets=None, areas=None, **_):
        """Remove user-selected ad intervals from the timeline.

        Each interval is treated as [start, end). The remaining portions are
        concatenated back together while re-encoding video/audio so timestamps
        stay continuous. Multiple audio tracks are handled independently.
        """
        file_list = await self._get_files()
        if not file_list:
            return self._up_path

        for file in file_list:
            streams, fmt = await get_metavideo(file)
            try:
                duration = float(fmt.get('duration', 0))
            except (TypeError, ValueError):
                duration = 0
            if duration <= 0:
                LOGGER.error('Unable to determine duration for ad removal: %s', file)
                return self._up_path

            raw_cuts = []
            for start, end in (cuts or []):
                try:
                    a = 0.0 if start == '00:00:00' else max(0.0, min(self._time_seconds(start), duration))
                    b = duration if end == '00:00:00' else max(0.0, min(self._time_seconds(end), duration))
                except (TypeError, ValueError):
                    continue
                if b > a:
                    raw_cuts.append((a, b))
            if not raw_cuts:
                return self._up_path

            raw_cuts.sort()
            merged = []
            for a, b in raw_cuts:
                if merged and a <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], b))
                else:
                    merged.append((a, b))

            keep = []
            cursor = 0.0
            for a, b in merged:
                if a > cursor:
                    keep.append((cursor, a))
                cursor = max(cursor, b)
            if cursor < duration:
                keep.append((cursor, duration))
            if not keep:
                LOGGER.error('Ad removal would remove the complete video: %s', file)
                return self._up_path

            video_streams = [x for x in streams if x.get('codec_type') == 'video']
            audio_streams = [x for x in streams if x.get('codec_type') == 'audio']
            if not video_streams:
                return self._up_path

            width = int(video_streams[0].get('width') or 0)
            height = int(video_streams[0].get('height') or 0)
            overlay_filters = []
            selected_presets = list(presets or [])
            if preset and preset not in selected_presets:
                selected_presets.append(preset)
            if 'top_bottom' in selected_presets:
                selected_presets.extend(x for x in ('top', 'bottom') if x not in selected_presets)
            if width > 2 and height > 2:
                banner_h = max(1, int(height * 0.20))
                if 'top' in selected_presets:
                    overlay_filters.append((1, 1, width - 2, max(1, banner_h - 2)))
                if 'bottom' in selected_presets:
                    overlay_filters.append((1, max(1, height - banner_h + 1),
                                            width - 2, max(1, banner_h - 2)))
                # Custom areas are additive; they must not be discarded when
                # Top/Bottom is selected at the same time.  Older selector
                # payloads may omit ``areas`` entirely.
                for x, y, w, h in (areas or []):
                    x = max(1, min(int(x), width - 2))
                    y = max(1, min(int(y), height - 2))
                    w = max(1, min(int(w), width - x - 1))
                    h = max(1, min(int(h), height - y - 1))
                    overlay_filters.append((x, y, w, h))

            base_dir = self.listener.dir if self._metadata else ospath.dirname(file)
            await makedirs(base_dir, exist_ok=True)
            self.path = file
            if not self.name:
                base_name = ospath.basename(file).rsplit('.', 1)[0]
                self.name = f'{base_name}_Clean.mkv'
            elif not self.name.upper().endswith(('MP4', 'MKV')):
                self.name += '.mkv'
            self.outfile = ospath.join(base_dir, self.name)
            # Never ask FFmpeg to read and write the same file.  The previous
            # path collision caused Remove Ads & Names to fail and the bot
            # then uploaded the untouched source.
            final_outfile = self.outfile
            temp_outfile = f'{final_outfile}.rmads.tmp.mkv'
            self.outfile = temp_outfile
            self.size = await get_path_size(file)
            self._files.append(file)

            parts = []
            for i, (a, b) in enumerate(keep):
                vf = f'trim=start={a}:end={b},setpts=PTS-STARTPTS'
                if overlay_filters:
                    vf += ',' + ','.join(
                        f'delogo=x={x}:y={y}:w={w}:h={h}:show=0'
                        for x, y, w, h in overlay_filters
                    )
                parts.append(f'[0:v:0]{vf}[v{i}]')
            parts.append(''.join(f'[v{i}]' for i in range(len(keep))) +
                         f'concat=n={len(keep)}:v=1:a=0[vout]')

            audio_labels = []
            for ai, _stream in enumerate(audio_streams):
                labels = []
                for i, (a, b) in enumerate(keep):
                    label = f'a{ai}_{i}'
                    labels.append(f'[{label}]')
                    parts.append(f'[0:a:{ai}]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[{label}]')
                out = f'aout{ai}'
                parts.append(''.join(labels) + f'concat=n={len(keep)}:v=0:a=1[{out}]')
                audio_labels.append(out)

            filter_complex = ';'.join(parts)
            cmd = [
                FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y', '-i', file,
                '-filter_complex', filter_complex, '-map', '[vout]'
            ]
            for label in audio_labels:
                cmd.extend(('-map', f'[{label}]'))
            # Keep the final file close to the source size. The previous
            # fixed video bitrate could be much larger than the source when
            # ffprobe reported a container/stream bitrate that included peaks.
            # Budget the original total bitrate across video and copied audio.
            source_total_br = max(1, int((self.size * 8) / max(duration, 1)))
            # The audio streams above are filtered with atrim/concat, so they
            # cannot be stream-copied. Re-encode them at a bounded bitrate;
            # otherwise FFmpeg fails and the untouched source gets uploaded.
            source_audio_brs = [
                int(float(s.get('bit_rate') or 0)) for s in audio_streams
            ]
            audio_out_brs = [min(max(br, 64_000), 192_000) if br else 128_000
                             for br in source_audio_brs]
            output_duration = sum(b - a for a, b in keep)
            # Dynamic size budget: source size + 50 MiB. Reserve space for the
            # re-encoded audio and container overhead before choosing video
            # bitrate. This keeps the output from exploding in size.
            size_budget = max(self.size, 1) + (50 * 1024 * 1024) - (4 * 1024 * 1024)
            audio_budget_br = sum(audio_out_brs)
            video_budget_bits = max(180_000, int(size_budget * 8 - audio_budget_br * output_duration))
            src_br = max(180_000, int(video_budget_bits / max(output_duration, 1)))
            cmd.extend((
                '-map_metadata', '0', '-c:v', 'libx264', '-preset', 'veryfast',
                '-crf', '18', '-b:v', str(src_br), '-maxrate', str(src_br),
                '-bufsize', str(src_br), '-pix_fmt', 'yuv420p'
            ))
            for ai, abr in enumerate(audio_out_brs):
                cmd.extend((f'-c:a:{ai}', 'aac', f'-b:a:{ai}', str(abr)))
            cmd.append(self.outfile)
            ok = await self._run_cmd(cmd)
            if self.is_cancel or not ok:
                return self._up_path
            try:
                os_replace(temp_outfile, final_outfile)
            except Exception as e:
                LOGGER.error('Failed to finalize Remove Ads & Names output: %s', e, exc_info=True)
                return self._up_path
            self.outfile = final_outfile

        return await self._final_path()

    async def _remove_ads_names(self):
        """Remove burned-in ads/names from selected video areas.

        FFmpeg's delogo filter reconstructs the selected rectangular area from
        surrounding pixels. Presets are useful for common top/bottom banners;
        custom areas allow multiple fixed overlays.
        """
        file_list = await self._get_files()
        multi = len(file_list) > 1
        if not file_list:
            return self._up_path

        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, 'Clean', multi),
                get_metavideo(main_video),
                get_path_size(main_video)
            )

        # Remove Ads & Names has no stream-selection step. The selected
        # presets/areas are already stored in self.data by SelectMode.
        # Starting ExtraSelect here would wait for a callback that does not
        # exist, causing the task to remain at Waiting... until timeout.
        await self._queue()
        if self.is_cancel:
            return
        if not isinstance(self.data, dict):
            return self._up_path

        presets = list(self.data.get('presets') or [])
        preset = self.data.get('preset')
        if not presets and preset:
            presets = [preset]
        areas = self.data.get('areas') or []

        for file in file_list:
            # Presets need the actual frame size because delogo does not expose
            # iw/ih expressions for its width/height options.
            file_streams = streams
            if not self._metadata:
                file_streams, _ = await get_metavideo(file)
            video_stream = next(
                (s for s in file_streams if s.get('codec_type') == 'video'),
                {}
            )
            width = int(video_stream.get('width') or 0)
            height = int(video_stream.get('height') or 0)
            if width <= 0 or height <= 0:
                LOGGER.error('Unable to determine video dimensions for %s', file)
                continue

            banner_h = max(1, int(height * 0.20))
            selected_areas = []
            # Multiple presets may be selected together. Top + Bottom is kept
            # as a convenience preset, and custom areas can be added too.
            # Accept both the current expanded representation
            # (['top', 'bottom']) and the legacy ['top_bottom'] value.
            if 'top_bottom' in presets:
                presets = [p for p in presets if p != 'top_bottom'] + ['top', 'bottom']
            for selected in presets:
                if selected == 'top':
                    selected_areas.append((1, 1, max(1, width - 2), max(1, banner_h - 2)))
                elif selected == 'bottom':
                    selected_areas.append((1, max(1, height - banner_h + 1),
                                          max(1, width - 2), max(1, banner_h - 2)))
            # delogo requires the rectangle to stay inside the frame.
            # Custom areas can coexist with any preset selection.
            for x, y, w, h in areas:
                x = max(1, min(x, width - 2))
                y = max(1, min(y, height - 2))
                w = max(1, min(w, width - x - 1))
                h = max(1, min(h, height - y - 1))
                selected_areas.append((x, y, w, h))

            filters = [
                f'delogo=x={x}:y={y}:w={w}:h={h}:show=0'
                for x, y, w, h in selected_areas
            ]
            if not filters:
                continue

            vf = ','.join(filters)

            self.path = file
            if not self._metadata:
                _, self.size = await gather(
                    self._name_base_dir(self.path, 'Clean', multi),
                    get_path_size(self.path)
                )

            final_outfile = ospath.join(base_dir, self.name)
            # Use a temporary output because input and final name can be the
            # same path when processing downloaded files in-place.
            temp_outfile = f'{final_outfile}.rmads.tmp.mkv'
            self.outfile = temp_outfile
            self._files.append(self.path)

            src_duration = float(video_stream.get('duration') or 0)
            if src_duration <= 0:
                _, src_fmt = await get_metavideo(self.path)
                src_duration = float(src_fmt.get('duration') or 1)
            audio_br = sum(
                int(float(s.get('bit_rate') or 0))
                for s in file_streams if s.get('codec_type') == 'audio'
            )
            # Allow source size + 50 MiB, with 4 MiB reserved for container
            # overhead. This scales automatically for 500 MB, 700 MB, 1 GB,
            # etc., instead of imposing one fixed cap.
            size_budget = max(self.size, 1) + (50 * 1024 * 1024) - (4 * 1024 * 1024)
            video_budget_bits = max(180_000, int(size_budget * 8 - audio_br * src_duration))
            src_br = max(180_000, int(video_budget_bits / max(src_duration, 1)))
            cmd = [
                FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y',
                '-i', self.path,
                '-map', '0:v:0?',
                '-map', '0:a:?',
                '-map', '0:s:?',
                '-vf', vf,
                # Keep good visual quality while enforcing the dynamic
                # source+50 MiB bitrate budget.
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '18',
                '-b:v', str(src_br),
                '-maxrate', str(src_br),
                '-bufsize', str(src_br),
                '-pix_fmt', 'yuv420p',
                '-c:a', 'copy',
                '-c:s', 'copy',
                '-map_metadata', '0',
                self.outfile
            ]
            ok = await self._run_cmd(cmd)
            if self.is_cancel or not ok:
                return self._up_path
            try:
                os_replace(temp_outfile, final_outfile)
            except Exception as e:
                LOGGER.error('Failed to finalize Remove Ads & Names output: %s', e, exc_info=True)
                return self._up_path
            self.outfile = final_outfile

        return await self._final_path()

    async def _vid_convert(self):
        file_list = await self._get_files()
        multi = len(file_list) > 1
        if not file_list:
            return self._up_path

        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, 'Convert',
                                    len(file_list) > 1),
                get_metavideo(main_video), get_path_size(main_video))
        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())
        await self._queue()
        if self.is_cancel:
            return
        if not self.data:
            return self._up_path
        self.outfile = self._up_path
        for file in file_list:
            self.path = file
            if not self._metadata:
                _, self.size = await gather(
                    self._name_base_dir(self.path, f'Convert-{self.data}',
                                        multi), get_path_size(self.path))
            self.outfile = ospath.join(base_dir, self.name)
            self._files.append(self.path)
            cmd = [
                FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y', '-i',
                self.path, '-map', '0:v:0', '-vf',
                f'scale={self._qual[self.data]}:-2', '-map', '0:a:?', '-map',
                '0:s:?', '-c:a', 'copy', '-c:s', 'copy', self.outfile
            ]
            await self._run_cmd(cmd)
            if self.is_cancel:
                return

        return await self._final_path()

    async def _binary_split(self):
        """Split a video into byte-identical binary parts named .mkv.001, .002, etc."""
        file_list = await self._get_files()
        if not file_list:
            return self._up_path

        source = file_list[0]
        base_dir = self.listener.dir
        await makedirs(base_dir, exist_ok=True)
        requested_size = int((self.data or {}).get('split_size', 1024 ** 3))
        # Guard against accidental unusably-small or excessively large values.
        part_size = max(50 * 1024 ** 2, min(requested_size, 20 * 1024 ** 3))

        # Ensure the split source is an MKV container. Stream-copy remuxing does
        # not re-encode audio/video; already-MKV inputs are split byte-for-byte.
        is_local = await aiopath.isfile(source)
        source_is_mkv = is_local and source.lower().endswith('.mkv')
        temp_source = None
        if not source_is_mkv:
            stem = ospath.splitext(ospath.basename(self.name or source))[0] or 'video'
            temp_source = ospath.join(base_dir, f'{stem}_binary_source.mkv')
            cmd = [FFMPEG_NAME, '-hide_banner', '-loglevel', 'error', '-y',
                   '-i', source, '-map', '0', '-c', 'copy', '-map_metadata', '0',
                   temp_source]
            stdout, stderr, code = await cmd_exec(cmd)
            if code != 0 or not await aiopath.isfile(temp_source):
                LOGGER.error('Binary split remux failed: %s', stderr)
                return self._up_path
            source = temp_source

        stem = ospath.splitext(ospath.basename(self.name or source))[0] or 'video'
        output_dir = ospath.join(base_dir, f'{stem}_binary_parts')
        await makedirs(output_dir, exist_ok=True)
        total_size = await get_path_size(source)
        self.size = total_size
        await self._send_status('direct')
        part_count = (total_size + part_size - 1) // part_size
        try:
            async with aiopen(source, 'rb') as src:
                for index in range(1, part_count + 1):
                    part_path = ospath.join(output_dir, f'{stem}.mkv.{index:03d}')
                    remaining = part_size
                    async with aiopen(part_path, 'wb') as dst:
                        while remaining > 0:
                            chunk = await src.read(min(8 * 1024 * 1024, remaining))
                            if not chunk:
                                break
                            await dst.write(chunk)
                            remaining -= len(chunk)
                    self._processed_bytes = min(total_size, index * part_size)
                    self._percentage = f'{round(self._processed_bytes / max(total_size, 1) * 100, 2)}%'
                    if self.is_cancel:
                        return self._up_path
        finally:
            if temp_source and await aiopath.exists(temp_source):
                await clean_target(temp_source)
        return output_dir

    async def _vid_extract(self):
        """Extract selected video/audio/subtitle streams into separate files."""
        file_list = await self._get_files()
        if not file_list:
            return self._up_path

        multi = len(file_list) > 1
        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, None, multi),
                get_metavideo(main_video),
                get_path_size(main_video)
            )

        # Show the stream/format selector before starting FFmpeg.
        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())
        await self._queue()
        if self.is_cancel or not isinstance(self.data, dict):
            return self._up_path

        selected = self.data.get('key')
        if selected is None:
            return self._up_path
        if not isinstance(selected, list):
            selected = [selected]
        if len(selected) == 1 and isinstance(selected[0], str):
            # "video audio subtitle" / "audio" / "subtitle" selections.
            groups = selected[0].split()
            if all(g in ('video', 'audio', 'subtitle') for g in groups):
                selected = [s.get('index') for s in streams
                            if s.get('codec_type') in groups]
        selected = {int(x) for x in selected if str(x).isdigit()}
        if not selected:
            return self._up_path

        ext = self.data.get('extension') or [None, None, 'mkv']
        while len(ext) < 3:
            ext.append(None)
        ext_audio = ext[0] or 'aac'
        ext_sub = ext[1] or 'srt'
        ext_video = ext[2] or 'mkv'

        for source in file_list:
            self.path = source
            if not self._metadata:
                _, self.size = await gather(
                    self._name_base_dir(source, None, multi),
                    get_path_size(source)
                )

            source_stem = ospath.splitext(ospath.basename(source))[0]
            source_dir = base_dir
            source_streams = streams
            # Refresh metadata for directory/multi-file mode so indexes match
            # the actual source file.
            if not self._metadata:
                source_streams, _ = await get_metavideo(source)

            for stream in source_streams:
                idx = stream.get('index')
                if idx not in selected:
                    continue

                ctype = stream.get('codec_type')
                if ctype == 'video':
                    out_ext = ext_video
                elif ctype == 'audio':
                    out_ext = ext_audio
                elif ctype == 'subtitle':
                    out_ext = ext_sub
                else:
                    continue

                lang = (stream.get('tags') or {}).get('language') or str(idx)
                safe_lang = re.sub(r'[^A-Za-z0-9._-]+', '_', str(lang))
                outfile = ospath.join(
                    source_dir,
                    f'{source_stem}_{ctype}_{safe_lang}.{out_ext}'
                )
                self.outfile = outfile

                # Build a single-stream extraction command. FFmpeg copies
                # compatible streams and only converts when the selected
                # container/format requires it.
                cmd = [
                    FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y',
                    '-i', source, '-map', f'0:{idx}'
                ]
                if ctype == 'video':
                    cmd += ['-c:v', 'copy']
                elif ctype == 'audio':
                    codec_map = {
                        'aac': 'aac', 'ac3': 'ac3', 'eac3': 'eac3',
                        'm4a': 'aac', 'mka': 'copy', 'wav': 'pcm_s16le'
                    }
                    cmd += ['-c:a', codec_map.get(out_ext, 'copy')]
                else:
                    if out_ext == 'srt':
                        cmd += ['-c:s', 'srt']
                    elif out_ext == 'ass':
                        cmd += ['-c:s', 'ass']
                    else:
                        cmd += ['-c:s', 'copy']

                cmd.append(outfile)
                ok = await self._run_cmd(cmd)
                if self.is_cancel:
                    return self._up_path
                if not ok:
                    return self._up_path

                # Keep the last extracted file as the executor result. The
                # upload layer can then process the resulting directory.
                self.outfile = outfile

        return await self._final_path()

    async def _rm_stream(self):
        file_list = await self._get_files()
        multi = len(file_list) > 1
        if not file_list:
            return self._up_path

        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, 'Remove', multi),
                get_metavideo(main_video), get_path_size(main_video))
        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())
        await self._queue()
        if self.is_cancel:
            return
        if not self.data:
            return self._up_path

        self.outfile = self._up_path
        for file in file_list:
            self.path = file
            if not self._metadata:
                _, self.size = await gather(
                    self._name_base_dir(self.path, 'Remove', multi),
                    get_path_size(self.path))
            key = self.data.get('key')
            if isinstance(key, list):
                key = key[0] if key else ''
            self.outfile = ospath.join(base_dir, self.name)
            self._files.append(self.path)
            cmd = [
                FFMPEG_NAME, '-hide_banner', '-y', '-ignore_unknown', '-i',
                self.path
            ]
            if key == 'audio':
                cmd.extend(('-map', '0', '-map', '-0:a'))
            elif key == 'subtitle':
                cmd.extend(('-map', '0', '-map', '-0:s'))
            else:
                for x in self.data['stream']:
                    if x not in self.data['sdata']:
                        cmd.extend(('-map', f'0:{x}'))
            cmd.extend(('-c', 'copy', self.outfile))
            await self._run_cmd(cmd)
            if self.is_cancel:
                return

        return await self._final_path()

    async def _vid_audio_swap(self):
        file_list = await self._get_files()
        multi = len(file_list) > 1
        if not file_list:
            return self._up_path

        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, 'AudioSwap', multi),
                get_metavideo(main_video), get_path_size(main_video))

        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())

        await self._queue()
        if self.is_cancel:
            return
        if not self.data:
            return self._up_path

        idx_list = self.data.get('key')

        if isinstance(idx_list, int):
            idx_list = [idx_list]

        if not idx_list:
            return self._up_path

        for file in file_list:
            self.path = file

            if not self._metadata:
                _, self.size = await gather(
                    self._name_base_dir(self.path, 'AudioSwap', multi),
                    get_path_size(self.path))

            self.outfile = ospath.join(base_dir, self.name)
            self._files.append(self.path)

            all_audios = [
                s["index"] for s in streams if s.get("codec_type") == "audio"
            ]
            final_order = idx_list + [
                x for x in all_audios if x not in idx_list
            ]

            cmd = [
                FFMPEG_NAME, "-hide_banner", "-ignore_unknown", "-y", "-i",
                self.path, "-map", "0:v"
            ]

            for idx in final_order:
                cmd += ["-map", f"0:{idx}"]

            cmd += ["-map", "0:s?"]
            cmd += ["-map_metadata", "0"]

            combined_mode = getattr(self, "is_vid_vid_audio_swap", False)

            for out_i, idx in enumerate(final_order):
                base_title = "TEAM MOVIES"
                lang = "AUDIO"

                for s in streams:
                    if s.get("index") == idx:
                        tags = s.get("tags", {})
                        base_title = tags.get("title") or tags.get(
                            "handler_name") or "TEAM MOVIES"
                        lang = tags.get("language") or tags.get(
                            "LANGUAGE") or f"AUDIO {idx}"
                        break

                lang_code = (lang or "").lower()[:3]
                lang_map = {
                    "tel": "Telugu",
                    "tam": "Tamil",
                    "hin": "Hindi",
                    "mal": "Malayalam",
                    "kan": "Kannada",
                    "eng": "English",
                }
                lang_name = lang_map.get(lang_code, lang)

                from bot import user_data
                user_dict = user_data.get(self.listener.message.from_user.id, {})
                metadata_title = user_dict.get("metadata") or base_title or "TEAM MOVIES"

                cmd += [
                    f"-metadata:s:a:{out_i}", f"title={metadata_title}",
                    f"-metadata:s:a:{out_i}", f"language={lang_name}"
                ]

            for i in range(len(final_order)):
                cmd += [f"-disposition:a:{i}", "0"]

            cmd += ["-disposition:a:0", "default"]

            cmd += ["-c", "copy", self.outfile]

            await self._run_cmd(cmd)
            if self.is_cancel:
                return

        return await self._final_path()

    
    


    async def _vid_subtitle_swap(self):
        """Reorder embedded subtitle streams while copying video/audio unchanged."""
        file_list = await self._get_files()
        if not file_list:
            return self._up_path
        main_video = file_list[0]
        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, 'SubtitleSwap', len(file_list) > 1),
                get_metavideo(main_video), get_path_size(main_video))
        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())
        await self._queue()
        if self.is_cancel:
            return self._up_path
        selected = self.data.get('key') if isinstance(self.data, dict) else None
        if not isinstance(selected, list) or not selected:
            return self._up_path
        subtitles = [s['index'] for s in streams if s.get('codec_type') == 'subtitle']
        order = [idx for idx in selected if idx in subtitles]
        order += [idx for idx in subtitles if idx not in order]
        if not order:
            return self._up_path
        audio = [s['index'] for s in streams if s.get('codec_type') == 'audio']
        video = [s['index'] for s in streams if s.get('codec_type') == 'video']
        mapped = set(video + audio + order)
        other = [s['index'] for s in streams if s.get('index') not in mapped]
        for file in file_list:
            self.path = file
            if not self._metadata:
                await self._name_base_dir(file, 'SubtitleSwap', len(file_list) > 1)
            self.outfile = ospath.join(base_dir, self.name)
            cmd = [FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y', '-i', file]
            for idx in video + audio + order + other:
                cmd += ['-map', f'0:{idx}']
            cmd += ['-map_metadata', '0', '-c', 'copy']
            for i in range(len(order)):
                cmd += [f'-disposition:s:{i}', '0']
            cmd += ['-disposition:s:0', 'default', self.outfile]
            ok = await self._run_cmd(cmd)
            if self.is_cancel:
                return self._up_path
            if not ok:
                return self._up_path
        return await self._final_path()

    async def _subtitle_rename(self):
        """Rename/language-tag selected subtitle streams without re-encoding."""
        file_list = await self._get_files()
        if not file_list:
            return self._up_path
        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, 'SubtitleRename', len(file_list) > 1),
                get_metavideo(main_video), get_path_size(main_video))
        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())
        await self._queue()
        if self.is_cancel:
            return self._up_path
        rename_map = self.data.get('rename', {}) if isinstance(self.data, dict) else {}
        if not rename_map:
            return self._up_path
        sub_streams = [s for s in streams if s.get('codec_type') == 'subtitle']
        for file in file_list:
            self.path = file
            if not self._metadata:
                await self._name_base_dir(file, 'SubtitleRename', len(file_list) > 1)
            self.outfile = ospath.join(base_dir, self.name)
            cmd = [FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y', '-i', file, '-map', '0', '-map_metadata', '0']
            for i, stream in enumerate(sub_streams):
                name = rename_map.get(str(stream.get('index')))
                if name:
                    clean_name = name.strip()
                    lang_aliases = {
                        'english': 'eng', 'telugu': 'tel', 'tamil': 'tam',
                        'hindi': 'hin', 'malayalam': 'mal', 'kannada': 'kan',
                        'japanese': 'jpn', 'korean': 'kor', 'chinese': 'zho',
                        'mandarin': 'zho', 'spanish': 'spa', 'french': 'fra',
                        'german': 'deu', 'italian': 'ita', 'portuguese': 'por',
                        'russian': 'rus', 'arabic': 'ara', 'indonesian': 'ind',
                        'thai': 'tha', 'vietnamese': 'vie', 'bengali': 'ben',
                        'marathi': 'mar', 'urdu': 'urd',
                    }
                    lang = lang_aliases.get(clean_name.lower())
                    cmd += [f'-metadata:s:s:{i}', f'title={clean_name}']
                    if lang:
                        cmd += [f'-metadata:s:s:{i}', f'language={lang}']
            cmd += ['-c', 'copy', self.outfile]
            ok = await self._run_cmd(cmd)
            if self.is_cancel:
                return self._up_path
            if not ok:
                return self._up_path
        return await self._final_path()

    async def _video_audio_sync(self):
        """Automatically synchronize embedded video/audio timestamps."""
        file_list = await self._get_files()
        multi = len(file_list) > 1
        if not file_list:
            return self._up_path

        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, 'AudioSync', multi),
                get_metavideo(main_video),
                get_path_size(main_video)
            )

        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())

        await self._queue()
        if self.is_cancel:
            return

        if not self.data:
            return self._up_path

        for file in file_list:
            self.path = file
            if not self._metadata:
                _, self.size = await gather(
                    self._name_base_dir(self.path, 'AudioSync', multi),
                    get_path_size(self.path)
                )

            try:
                streams, fmt = await get_metavideo(self.path)
                video_stream = next(
                    (x for x in streams if x.get('codec_type') == 'video'), {}
                )
                audio_stream = next(
                    (x for x in streams if x.get('codec_type') == 'audio'), {}
                )
                video_start = float(
                    video_stream.get('start_time')
                    or fmt.get('start_time')
                    or 0.0
                )
                audio_start = float(
                    audio_stream.get('start_time')
                    or fmt.get('start_time')
                    or 0.0
                )
                delay_ms = round((video_start - audio_start) * 1000)
            except Exception as e:
                LOGGER.warning('Automatic audio sync probe failed: %s', e)
                delay_ms = 0

            self.outfile = ospath.join(base_dir, self.name)

            if delay_ms == 0:
                cmd = [
                    FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y',
                    '-i', self.path,
                    '-map', '0', '-map_metadata', '0',
                    '-c', 'copy', self.outfile
                ]
            elif delay_ms > 0:
                # Audio starts earlier than video: delay only the audio.
                cmd = [
                    FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y',
                    '-i', self.path,
                    '-map', '0:v:0?', '-map', '0:a:?', '-map', '0:s:?',
                    '-af', f'adelay={delay_ms}:all=1',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
                    '-ac', '2', '-ar', '48000', '-c:s', 'copy',
                    self.outfile
                ]
            else:
                # Audio starts later than video: trim the leading audio time.
                trim_sec = abs(delay_ms) / 1000
                cmd = [
                    FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y',
                    '-i', self.path,
                    '-map', '0:v:0?', '-map', '0:a:?', '-map', '0:s:?',
                    '-af', f'atrim=start={trim_sec:.3f},asetpts=PTS-STARTPTS',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
                    '-ac', '2', '-ar', '48000', '-c:s', 'copy',
                    self.outfile
                ]

            await self._run_cmd(cmd)
            if self.is_cancel:
                return

        return await self._final_path()

    async def _audio_export(self):
        """Export the first audio stream from a video as a portable AAC/M4A file."""
        video_path = await self._get_video()
        if not video_path:
            LOGGER.warning('Audio Export skipped: no supported media file found')
            return self._up_path

        base_dir = await self._name_base_dir(video_path, 'Audio Export', False)
        stem = ospath.splitext(ospath.basename(video_path))[0]
        output = ospath.join(base_dir, f'{stem}.m4a')
        suffix = 2
        while await aiopath.exists(output):
            output = ospath.join(base_dir, f'{stem} ({suffix}).m4a')
            suffix += 1

        self.path = video_path
        self.size = await get_path_size(video_path)
        self.name = ospath.basename(output)
        self.outfile = output
        # Per-user Audio Export bitrate; strict allowlist protects FFmpeg args.
        owner = getattr(getattr(self.listener, 'message', None), 'from_user', None)
        user_id = getattr(owner, 'id', None)
        bitrate = user_data.get(user_id, {}).get('VT_AUDIO_BITRATE', '192k') if user_id else '192k'
        if bitrate not in {'128k', '160k', '192k', '256k', '320k'}:
            bitrate = '192k'
        cmd = [
            FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y', '-i',
            video_path, '-map', '0:a:0', '-vn', '-sn', '-dn',
            '-c:a', 'aac', '-b:a', bitrate, '-map_metadata', '0', output
        ]
        success = await self._run_cmd(cmd)
        if success and await aiopath.isfile(output):
            self._up_path = output
            return output
        return self._up_path


    async def _audio_split(self):
        """Split every supported video in a file or folder task.

        Folder/archive tasks produce one result ZIP containing all successful
        language variants. Missing languages and non-video files are skipped.
        """
        import os
        from zipfile import ZipFile, ZIP_DEFLATED

        if not self._is_dir:
            return await self._audio_split_single()

        original_path, original_name, original_up_path = self.path, self.name, self._up_path
        original_outfile, original_size = self.outfile, self.size
        video_files = []
        for dirpath, _, files in await sync_to_async(walk, original_path):
            for filename in natsorted(files):
                candidate = ospath.join(dirpath, filename)
                try:
                    if (await aiopath.isfile(candidate)) and (await get_document_type(candidate))[0]:
                        video_files.append(candidate)
                except Exception:
                    LOGGER.debug("Audio Split: skipped unreadable folder entry %s", candidate, exc_info=True)

        if not video_files:
            LOGGER.warning("Audio Split: folder contains no supported video files: %s", original_path)
            return original_up_path

        folder_base = ospath.basename(ospath.normpath(original_path)) or "Audio_Split"
        archive = ospath.join(self.listener.dir, f"{folder_base}_audio_split_results.zip")
        try:
            if await aiopath.exists(archive):
                os.remove(archive)
        except Exception:
            pass

        successful = 0
        try:
            with ZipFile(archive, "w", ZIP_DEFLATED) as combined:
                for candidate in video_files:
                    relative = ospath.relpath(candidate, original_path)
                    self.path = candidate
                    self._is_dir = False
                    self._up_path = candidate
                    self.outfile = ""
                    self.name = ospath.basename(candidate)
                    result = await self._audio_split_single()
                    if not result or not await aiopath.isfile(str(result)) or not str(result).lower().endswith(".zip"):
                        LOGGER.warning("Audio Split: no variants created for %s; continuing", relative)
                        continue
                    try:
                        with ZipFile(str(result), "r") as variants:
                            prefix = ospath.splitext(relative)[0].replace(ospath.sep, "/")
                            for member in variants.namelist():
                                if member.endswith("/"):
                                    continue
                                combined.writestr(f"{prefix}/{member}", variants.read(member))
                                successful += 1
                    except Exception:
                        LOGGER.warning("Audio Split: could not collect variants for %s", relative, exc_info=True)
            if successful == 0 or not await aiopath.isfile(archive) or await get_path_size(archive) <= 0:
                try:
                    if await aiopath.exists(archive):
                        os.remove(archive)
                except Exception:
                    pass
                return original_up_path
            self.name = ospath.basename(archive)
            self.outfile = archive
            self._up_path = archive
            self.size = await get_path_size(archive)
            LOGGER.info("Audio Split: packaged %d variant file(s) from %d video(s)", successful, len(video_files))
            return archive
        finally:
            self.path, self._is_dir = original_path, True
            # Keep the result path when a combined archive was successfully created.
            if not (self._up_path and str(self._up_path).endswith("_audio_split_results.zip")):
                self.name, self.outfile, self.size, self._up_path = original_name, original_outfile, original_size, original_up_path

    async def _audio_split_single(self):
        """Split one video into language-specific video+audio variants."""
        import os
        import unicodedata
        from zipfile import ZipFile, ZIP_DEFLATED

        video_path = await self._get_video()
        if not video_path or not await aiopath.isfile(video_path):
            LOGGER.warning("Audio Split: input video is missing")
            return self._up_path

        owner = getattr(getattr(self.listener, "message", None), "from_user", None)
        user_id = getattr(owner, "id", None)
        user_settings = user_data.get(user_id, {}) if user_id else {}
        raw_langs = ((self.data or {}).get("languages")
                     or user_settings.get("AUDIO_SPLIT_LANGUAGES") or "te,ta,hi")

        # Accept ISO codes, common ISO-639-2 codes, and full English language names.
        language_aliases = {
            "telugu": "te", "tel": "te", "te": "te",
            "tamil": "ta", "tam": "ta", "ta": "ta",
            "hindi": "hi", "hin": "hi", "hi": "hi",
            "kannada": "kn", "kan": "kn", "kn": "kn",
            "malayalam": "ml", "mal": "ml", "ml": "ml",
            "bengali": "bn", "bangla": "bn", "ben": "bn", "bn": "bn",
            "marathi": "mr", "mar": "mr", "mr": "mr",
            "gujarati": "gu", "guj": "gu", "gu": "gu",
            "punjabi": "pa", "panjabi": "pa", "pan": "pa", "pa": "pa",
            "urdu": "ur", "urd": "ur", "ur": "ur",
            "odia": "or", "oriya": "or", "ori": "or", "or": "or",
            "assamese": "as", "asm": "as", "as": "as",
            "sanskrit": "sa", "san": "sa", "sa": "sa",
            "nepali": "ne", "nep": "ne", "ne": "ne",
            "sindhi": "sd", "snd": "sd", "sd": "sd",
            "english": "en", "eng": "en", "en": "en",
            "spanish": "es", "spa": "es", "es": "es",
            "french": "fr", "fra": "fr", "fre": "fr", "fr": "fr",
            "german": "de", "deu": "de", "ger": "de", "de": "de",
            "italian": "it", "ita": "it", "it": "it",
            "portuguese": "pt", "por": "pt", "pt": "pt",
            "russian": "ru", "rus": "ru", "ru": "ru",
            "japanese": "ja", "jpn": "ja", "ja": "ja",
            "korean": "ko", "kor": "ko", "ko": "ko",
            "chinese": "zh", "zho": "zh", "chi": "zh", "zh": "zh",
        }
        def normalize_language(value):
            value = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
            value = value.replace("_", "-")
            # Tags can be e.g. en-US, Telugu (India), or 'telugu audio'.
            first = value.split("(", 1)[0].strip()
            first = re.sub(r"\s+(audio|dub|dubbed|track)$", "", first).strip()
            if first in language_aliases:
                return language_aliases[first]
            if "-" in first and first.split("-", 1)[0] in language_aliases:
                return language_aliases[first.split("-", 1)[0]]
            # Allow a full language name embedded in a stream title.
            for name, code in sorted(language_aliases.items(), key=lambda item: len(item[0]), reverse=True):
                if len(name) > 2 and re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", value):
                    return code
            return ""

        if isinstance(raw_langs, (list, tuple, set)):
            raw_values = list(raw_langs)
        else:
            raw_values = re.split(r"[,;\n]+", str(raw_langs))
        languages = list(dict.fromkeys(code for item in raw_values if (code := normalize_language(item))))
        if not languages:
            LOGGER.warning("Audio Split: no valid languages in setting %r", raw_langs)
            return self._up_path

        streams, _ = await get_metavideo(video_path)
        if not isinstance(streams, list):
            LOGGER.warning("Audio Split: ffprobe returned an invalid stream list")
            return self._up_path
        audio_streams = []
        for stream in streams:
            if not isinstance(stream, dict) or stream.get("codec_type") != "audio":
                continue
            tags = stream.get("tags") or {}
            candidates = [tags.get("language"), tags.get("LANGUAGE"), tags.get("title"),
                          tags.get("handler_name"), stream.get("language")]
            code = next((normalized for value in candidates
                         if (normalized := normalize_language(value))), "")
            audio_streams.append((int(stream.get("index", -1)), code, candidates))
        if not audio_streams:
            LOGGER.warning("Audio Split: input contains no audio streams")
            return self._up_path

        base = ospath.splitext(ospath.basename(video_path))[0]
        add_suffix = bool(user_settings.get("AUDIO_SPLIT_LANGUAGE_SUFFIX", False))
        # Use readable language names in suffixes (e.g. _Telugu, _Tamil), not
        # internal ISO codes. Apply this to every successfully generated variant.
        language_suffix_names = {
            "te": "Telugu", "ta": "Tamil", "hi": "Hindi", "kn": "Kannada",
            "ml": "Malayalam", "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati",
            "pa": "Punjabi", "ur": "Urdu", "or": "Odia", "as": "Assamese",
            "sa": "Sanskrit", "ne": "Nepali", "sd": "Sindhi", "en": "English",
            "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
            "pt": "Portuguese", "ru": "Russian", "ja": "Japanese", "ko": "Korean",
            "zh": "Chinese",
        }
        out_dir = ospath.join(self.listener.dir, f"{base}_audio_split")
        await makedirs(out_dir, exist_ok=True)
        made = []
        missing_languages = []
        # Some releases have multiple audio tracks but omit language tags entirely.
        # Preserve explicitly tagged matches first, then map remaining requested languages
        # to unlabelled tracks in their original order. Never re-use a stream for two variants.
        used_stream_indexes = set()
        unlabelled_indexes = [idx for idx, code, _ in audio_streams if idx >= 0 and not code]
        fallback_by_language = {}
        pending_languages = [lang for lang in languages if not any(code == lang and idx >= 0 for idx, code, _ in audio_streams)]
        for lang, idx in zip(pending_languages, unlabelled_indexes):
            fallback_by_language[lang] = idx

        for lang in languages:
            # A requested language is optional: absence must never abort the other variants.
            match = next(((idx, candidates) for idx, code, candidates in audio_streams
                          if code == lang and idx >= 0 and idx not in used_stream_indexes), None)
            if match is not None:
                stream_index, _ = match
            elif lang in fallback_by_language:
                stream_index = fallback_by_language[lang]
                LOGGER.warning(
                    "Audio Split: stream %s has no language tag; assigning it to configured language '%s' by track order",
                    stream_index, lang,
                )
            else:
                missing_languages.append(lang)
                LOGGER.info(
                    "Audio Split: configured language '%s' was not found in audio metadata; skipping it",
                    lang,
                )
                continue
            if stream_index in used_stream_indexes:
                missing_languages.append(lang)
                continue
            used_stream_indexes.add(stream_index)
            # Unique paths avoid stale files and overwrite bugs on retries.
            suffix_text = language_suffix_names.get(lang, lang.upper())
            output_name = f"{base}_{suffix_text}.mkv" if add_suffix else f"{base}.mkv"
            lang_dir = ospath.join(out_dir, lang)
            await makedirs(lang_dir, exist_ok=True)
            output = ospath.join(lang_dir, output_name)
            cmd = [FFMPEG_NAME, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                   "-i", video_path, "-map", "0:v:0?", "-map", f"0:{stream_index}",
                   "-map_metadata", "0", "-c", "copy", "-sn", "-dn", output]
            _, stderr, code = await cmd_exec(cmd)
            if code == 0 and await aiopath.isfile(output) and await get_path_size(output) > 0:
                made.append((lang, output))
            else:
                LOGGER.warning("Audio Split: ffmpeg failed for %s (exit=%s): %s", lang, code, stderr)
                try:
                    if await aiopath.exists(output):
                        os.remove(output)
                except Exception:
                    pass

        if not made:
            found = ", ".join(sorted({code or "unlabelled" for _, code, _ in audio_streams}))
            LOGGER.warning("Audio Split produced no variants. Requested=%s; detected=%s", languages, found)
            return self._up_path

        archive = ospath.join(self.listener.dir, f"{base}_audio_split.zip")
        try:
            if await aiopath.exists(archive):
                os.remove(archive)
        except Exception:
            pass
        with ZipFile(archive, "w", ZIP_DEFLATED) as zf:
            for lang, file in made:
                arcname = ospath.basename(file) if add_suffix else ospath.join(lang, ospath.basename(file))
                zf.write(file, arcname=arcname)
        if not await aiopath.isfile(archive) or await get_path_size(archive) <= 0:
            LOGGER.error("Audio Split: output archive was not created correctly")
            return self._up_path
        self.name = ospath.basename(archive)
        self.outfile = archive
        self._up_path = archive
        self.size = await get_path_size(archive)
        LOGGER.info("Audio Split complete: created %d variant(s) for %s", len(made), ",".join(lang for lang, _ in made))
        if missing_languages:
            LOGGER.info(
                "Audio Split skipped unavailable configured language(s): %s",
                ",".join(missing_languages),
            )
        return archive

    async def _audio_to_translated_subtitles(self, audio_only=False):
        """Translate embedded subtitles, or independently transcribe audio to translated SRT."""
        video_path = await self._get_video()
        if not video_path:
            LOGGER.warning('Audio-to-subtitles skipped: no supported media file found')
            return self._up_path

        import os
        target_language = (self.data.get('subtitle_language') or os.environ.get('VT_SUBTITLE_LANGUAGE') or config_dict.get('VT_SUBTITLE_LANGUAGE') or 'en').strip().lower()
        # Keep the target language configurable without exposing arbitrary command arguments.
        if not re.fullmatch(r'[a-z]{2,3}(?:-[a-z]{2,4})?', target_language):
            target_language = 'en'
        base_dir = await self._name_base_dir(video_path, 'Translated Subtitles', False)
        stem = ospath.splitext(ospath.basename(video_path))[0]
        output = ospath.join(base_dir, f'{stem}.{target_language}.srt')
        suffix = 2
        while await aiopath.exists(output):
            output = ospath.join(base_dir, f'{stem}.{target_language} ({suffix}).srt')
            suffix += 1

        def _transcribe_translate(source, destination, target, audio_only=False):
            # Keep subtitle-only mode independent of Whisper; audio mode requires it.
            import subprocess
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source='auto', target=target)

            def stamp(seconds):
                millis = max(0, int(seconds * 1000))
                hours, millis = divmod(millis, 3_600_000)
                minutes, millis = divmod(millis, 60_000)
                secs, millis = divmod(millis, 1000)
                return f'{hours:02}:{minutes:02}:{secs:02},{millis:03}'

            # Subtitle mode only reads existing embedded subtitles; audio mode ignores them.
            extracted = destination + '.source.srt'
            subtitle_rows = []
            if not audio_only:
                probe = subprocess.run(
                    ['ffprobe', '-v', 'error', '-select_streams', 's', '-show_entries',
                     'stream=index,codec_name', '-of', 'csv=p=0', source],
                    capture_output=True, text=True, timeout=60, check=False)
                subtitle_rows = [row.strip() for row in probe.stdout.splitlines() if row.strip()]
            cues = []
            if subtitle_rows:
                result = subprocess.run(
                    [FFMPEG_NAME, '-hide_banner', '-loglevel', 'error', '-y', '-i', source,
                     '-map', '0:s:0', '-c:s', 'srt', extracted],
                    capture_output=True, text=True, timeout=180, check=False)
                if result.returncode == 0 and ospath.isfile(extracted):
                    with open(extracted, encoding='utf-8-sig', errors='replace') as handle:
                        raw = handle.read().strip()
                    for block in re.split(r'\r?\n\s*\r?\n', raw):
                        lines = block.splitlines()
                        if len(lines) >= 3 and '-->' in lines[1]:
                            cues.append((lines[1].strip(), '\n'.join(lines[2:]).strip()))
            if cues:
                with open(destination, 'w', encoding='utf-8') as handle:
                    for idx, (timing, text) in enumerate(cues, 1):
                        translated = translator.translate(text[:4500]) if target not in {'auto', 'und'} else text
                        handle.write(f'{idx}\n{timing}\n{translated.strip()}\n\n')
                try:
                    os.remove(extracted)
                except OSError:
                    pass
                return len(cues)
            try:
                os.remove(extracted)
            except OSError:
                pass

            # Existing-subtitles mode must never silently switch to audio transcription.
            if not audio_only:
                raise RuntimeError('No usable embedded text subtitle stream was found. Choose Audio → Translated Subtitles (Whisper) to create subtitles from speech.')

            # Audio mode always transcribes speech with Whisper, regardless of embedded subtitles.
            from faster_whisper import WhisperModel
            model_size = (os.environ.get('VT_WHISPER_MODEL') or config_dict.get('VT_WHISPER_MODEL') or 'base').strip().lower()
            if model_size not in {'tiny', 'base', 'small', 'medium', 'large-v3'}:
                model_size = 'base'
            model = WhisperModel(model_size, device='cpu', compute_type='int8')
            segments, _ = model.transcribe(source, beam_size=5, vad_filter=True)
            count = 0
            with open(destination, 'w', encoding='utf-8') as handle:
                for segment in segments:
                    text = (segment.text or '').strip()
                    if not text:
                        continue
                    translated = translator.translate(text[:4500]) if target not in {'auto', 'und'} else text
                    count += 1
                    handle.write(f'{count}\n{stamp(segment.start)} --> {stamp(segment.end)}\n{translated.strip()}\n\n')
            if not count:
                raise RuntimeError('No speech was detected in the selected audio track.')
            return count

        try:
            count = await sync_to_async(_transcribe_translate, video_path, output, target_language, audio_only)
        except ImportError as exc:
            LOGGER.error('Subtitle translation dependencies are missing: %s', exc)
            await sendStatusMessage(self.listener.message)
            return self._up_path
        except Exception as exc:
            LOGGER.error('Subtitle processing failed: %s', exc, exc_info=True)
            try:
                await sendMessage(str(exc), self.listener.message)
            except Exception:
                pass
            return self._up_path

        self.path = output
        self.name = ospath.basename(output)
        self.outfile = output
        self.size = await get_path_size(output)
        self._up_path = output
        LOGGER.info('Created %s translated subtitle cues: %s', count, output)
        return output

    async def _audio_track_postprocess(self, source):
        """Run the same Audio Track rename flow used by standalone Audio Track."""
        if not source or not await aiopath.isfile(source):
            return source

        streams, _ = await get_metavideo(source)
        audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
        if not audio_streams:
            return source

        # Reuse the standalone Audio Track selector semantics: selecting a
        # track and supplying a new name changes its language metadata, while
        # Done without a rename leaves the processed video unchanged.
        self.path = source
        self.executor_streams = streams
        self.data = {'rename': {}}
        extra = ExtraSelect(self)
        future = extra._event_handler()
        await gather(extra.audio_rename_select(streams), wrap_future(future))
        if self.is_cancel:
            return source

        rename_map = self.data.get('rename', {})
        if not rename_map:
            self.outfile = source
            return source

        source_dir, source_name = ospath.split(source)
        # Keep the actual source basename; UI mode labels are not filenames.
        self.name = source_name
        source_stem, source_ext = ospath.splitext(source_name)
        temp = ospath.join(source_dir, f'{source_stem}.audio-track.tmp{source_ext or ".mkv"}')
        cmd = [
            FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y',
            '-i', source, '-map', '0', '-map_metadata', '0'
        ]

        for i, stream in enumerate(audio_streams):
            idx = str(stream.get('index'))
            new_name = rename_map.get(idx)
            if new_name:
                # Match standalone Audio Track: use the supplied track name
                # as the language metadata instead of only changing title.
                lang_code = new_name.strip().lower()[:3]
                if lang_code:
                    cmd.extend((f'-metadata:s:a:{i}', f'language={lang_code}'))

        cmd.extend(('-c', 'copy', temp))
        ok = await self._run_cmd(cmd)
        if self.is_cancel or not ok:
            try:
                if await aiopath.isfile(temp):
                    await aiopath.remove(temp)
            except Exception:
                pass
            return source

        try:
            os_replace(temp, source)
        except Exception as e:
            LOGGER.error('Audio Track metadata replace failed: %s', e, exc_info=True)
            return source

        self.outfile = source
        return source

    async def _audio_channel(self):
        """Change selected audio tracks to 1.0/2.0/5.1/7.1 layouts."""
        file_list = await self._get_files()
        if not file_list:
            return self._up_path

        multi = len(file_list) > 1
        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, None, multi),
                get_metavideo(main_video),
                get_path_size(main_video)
            )

        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())
        await self._queue()
        if self.is_cancel or not isinstance(self.data, dict):
            return self._up_path

        channel_map = self.data.get('channel') or {}
        if not channel_map:
            return self._up_path

        for file in file_list:
            self.path = file
            if not self._metadata:
                _, self.size = await gather(
                    self._name_base_dir(self.path, None, multi),
                    get_path_size(self.path)
                )
            final_outfile = ospath.join(base_dir, self.name)
            # FFmpeg cannot write to the same file it is reading. Use a
            # temporary file and replace the original only after success.
            stem, ext = ospath.splitext(self.name)
            temp_outfile = ospath.join(base_dir, f'{stem}.__audio_channel_tmp{ext or ".mkv"}')
            self.outfile = temp_outfile
            self._files.append(self.path)

            # Use the actual source metadata for every file. This keeps stream
            # indexes correct when processing multiple files.
            current_streams = streams
            if not self._metadata:
                try:
                    current_streams, _ = await get_metavideo(self.path)
                except Exception:
                    current_streams = streams

            cmd = [
                FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y', '-i', self.path,
                '-map', '0', '-map_metadata', '0'
            ]

            # Re-encode only the audio tracks whose channel layout was changed.
            # Video, subtitles and unchanged audio tracks remain untouched.
            audio_out = 0
            for stream in current_streams:
                if not isinstance(stream, dict) or stream.get('codec_type') != 'audio':
                    continue
                idx = str(stream.get('index'))
                if idx in channel_map:
                    channels = str(channel_map[idx])
                    layout = {'1': 'mono', '2': 'stereo', '6': '5.1', '8': '7.1'}.get(channels, channels)
                    cmd += [
                        f'-c:a:{audio_out}', 'aac',
                        f'-ac:a:{audio_out}', channels,
                        f'-channel_layout:a:{audio_out}', layout
                    ]
                else:
                    cmd += [f'-c:a:{audio_out}', 'copy']
                audio_out += 1

            cmd += ['-c:v', 'copy', '-c:s', 'copy', temp_outfile]
            ok = await self._run_cmd(cmd)
            if self.is_cancel:
                return
            if not ok:
                return self._up_path

            try:
                os_replace(temp_outfile, final_outfile)
            except Exception as e:
                LOGGER.error('Audio Channel replace failed: %s', e, exc_info=True)
                return self._up_path

            self.outfile = final_outfile

        return await self._final_path()

    async def _audio_rename(self):
        file_list = await self._get_files()
        if not file_list:
            return self._up_path

        multi = len(file_list) > 1
        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, 'Rename', multi),
                get_metavideo(main_video),
                get_path_size(main_video)
            )

        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())
        await self._queue()

        if self.is_cancel:
            return

        if not isinstance(self.data, dict):
            return self._up_path

        rename_map = self.data.get("rename", {})

        for file in file_list:
            self.path = file
            if not self._metadata:
                await self._name_base_dir(self.path, 'Rename', multi)
            self.outfile = ospath.join(base_dir, self.name)
            self._files.append(self.path)

            cmd = [
                FFMPEG_NAME,
                "-hide_banner",
                "-ignore_unknown",
                "-y",
                "-i", self.path,
                "-map", "0",
                "-map_metadata", "0"
            ]

            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

            for i, s in enumerate(audio_streams):
                idx = str(s.get("index"))
                new_name = rename_map.get(idx)

                if new_name:
                    tags = s.get("tags", {})
                    old_title = tags.get("title") or tags.get("handler_name") or "TEAM MOVIES"

                    lang_code = new_name.lower()[:3]

                    cmd += [
                        f"-metadata:s:a:{i}", f"language={lang_code}"
                    ]

            cmd += ["-c", "copy", self.outfile]

            await self._run_cmd(cmd)
            if self.is_cancel:
                return

        return await self._final_path()


    async def _vid_trimmer(self, start_time, end_time):
        await self._queue(True)
        if self.is_cancel:
            return
        self.outfile = self._up_path
        for file in (file_list := await self._get_files()):
            self.path = file
            if self._metadata:
                base_dir = self.listener.dir
                await makedirs(base_dir, exist_ok=True)
            else:
                base_dir, self.size = await gather(
                    self._name_base_dir(self.path, 'Trim',
                                        len(file_list) > 1),
                    get_path_size(self.path))
            self.outfile = ospath.join(base_dir, self.name)
            self._files.append(self.path)
            cmd = [
                FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-i',
                self.path, '-ss', start_time, '-to', end_time, '-map',
                '0:v:0?', '-map', '0:a:?', '-map', '0:s:?', '-c:v', 'copy',
                '-c:a', 'copy', '-c:s', 'copy', self.outfile, '-y'
            ]
            await self._run_cmd(cmd)
            if self.is_cancel:
                return

        return await self._final_path()

    async def _subsync(self, type: str = 'sync_manual'):
        if not self._is_dir:
            return self._up_path
        self.size = await get_path_size(self.path)
        list_files = natsorted(await listdir(self.path))
        if len(list_files) <= 1:
            return self._up_path
        sub_files, ref_files = [], []
        if type == 'sync_manual':
            index = 1
            self.data = {'list': {}, 'final': {}}
            for file in list_files:
                if (await get_document_type(ospath.join(self.path, file)
                                            ))[0] or file.endswith(
                                                ('.srt', '.ass')):
                    self.data['list'].update({index: file})
                    index += 1
            if not self.data['list']:
                return self._up_path
            await self._start_handler()
            await gather(self._send_status(), self.event.wait())

            if self.is_cancel:
                return
            if not self.data or not self.data['final']:
                return self._up_path
            for key in self.data['final'].values():
                sub_files.append(ospath.join(self.path, key['file']))
                ref_files.append(ospath.join(self.path, key['ref']))
        else:
            for file in list_files:
                file_ = ospath.join(self.path, file)
                is_video, is_audio, _ = await get_document_type(file_)
                if is_video or is_audio:
                    ref_files.append(file_)
                elif file_.lower().endswith(('.srt', '.ass')):
                    sub_files.append(file_)

            if not sub_files:
                return self._up_path

            if not ref_files and len(sub_files) > 1:
                # Use the first subtitle as a reference for the remaining
                # subtitle files without mutating the list being iterated.
                ref_files = [sub_files[0]]
                sub_files = sub_files[1:]

            if not ref_files or not sub_files:
                return self._up_path

        for sub_file, ref_file in zip(sub_files, ref_files):
            self._files.extend((sub_file, ref_file))
            self.size = await get_path_size(ref_file)
            self.name = ospath.basename(sub_file)
            name, ext = ospath.splitext(sub_file)
            cmd = [
                'alass', '--allow-negative-timestamps', ref_file, sub_file,
                f'{name}_SYNC.{ext}'
            ]
            await self._run_cmd(cmd, 'direct')
            if self.is_cancel:
                return

        return await self._final_path(self._up_path)

    async def _vid_compress(self, quality=None):
        file_list = await self._get_files()
        multi = len(file_list) > 1
        if not file_list:
            return self._up_path

        if self._metadata:
            base_dir = self.listener.dir
            await makedirs(base_dir, exist_ok=True)
            streams = self._metadata[0]
        else:
            main_video = file_list[0]
            base_dir, (streams, _), self.size = await gather(
                self._name_base_dir(main_video, 'Compress', multi),
                get_metavideo(main_video), get_path_size(main_video))
        await self._start_handler(streams)
        await gather(self._send_status(), self.event.wait())
        await self._queue()
        if self.is_cancel:
            return
        if not isinstance(self.data, dict):
            return self._up_path

        self.outfile = self._up_path
        for file in file_list:
            self.path = file
            if not self._metadata:
                _, self.size = await gather(
                    self._name_base_dir(self.path, 'Compress', multi),
                    get_path_size(self.path))
            self.outfile = ospath.join(base_dir, self.name)
            self._files.append(self.path)
            cmd = [
                FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y', '-i',
                self.path, '-preset', config_dict['LIB265_PRESET'], '-c:v',
                'libx265', '-pix_fmt', 'yuv420p10le', '-crf', '24',
                '-profile:v', 'main10', '-map', f'0:{self.data["video"]}',
                '-map', '0:s:?', '-c:s', 'copy'
            ]
            if banner := config_dict['COMPRESS_BANNER']:
                sub_file = ospath.join(base_dir, 'subtitle.srt')
                self._files.append(sub_file)
                quality = f',scale={self._qual[quality]}:-2' if quality else ''
                async with aiopen(sub_file, 'w') as f:
                    await f.write(f'1\n00:00:03,000 --> 00:00:08,00\n{banner}')
                cmd.extend((
                    '-vf',
                    f"subtitles='{sub_file}'{quality},unsharp,eq=contrast=1.07",
                    '-metadata', f'title={banner}', '-metadata:s:v',
                    f'title={banner}', '-x265-params', 'no-info=1', '-bsf:v',
                    'filter_units=remove_types=6'))
            elif quality:
                cmd.extend(('-vf', f'scale={self._qual[quality]}:-2'))

            cmd.extend(('-c:a', 'aac', '-b:a', '160k', '-map',
                        f'0:{self.data["audio"]}?',
                        self.outfile) if self.data else [self.outfile])
            await self._run_cmd(cmd)
            if self.is_cancel:
                return

        return await self._final_path()

    async def _vid_marker(self, **kwargs):
        await self._queue(True)
        if self.is_cancel:
            return
        wmpath = ospath.join('watermark', f'{self.listener.mid}.png')
        for file in (file_list := await self._get_files()):
            self.path = file
            self._files.append(self.path)
            if self._metadata:
                base_dir, fsize = self.listener.dir, self.size
                await makedirs(base_dir, exist_ok=True)
            else:
                await self._name_base_dir(self.path, 'Marker',
                                          len(file_list) > 1)
                base_dir, fsize = await gather(
                    self._name_base_dir(self.path, 'Marker',
                                        len(file_list) > 1),
                    get_path_size(self.path))
            self.size = fsize + await get_path_size(wmpath)
            self.outfile = ospath.join(base_dir, self.name)
            wmsize, wmposition, popupwm = kwargs.get('wmsize'), kwargs.get(
                'wmposition'), kwargs.get('popupwm') or ''
            if popupwm:
                duration = (await get_media_info(self.path))[0]
                popupwm = f':enable=lt(mod(t\\,{duration}/{popupwm})\\,20)'

            hardusb, subfile = kwargs.get('hardsub') or '', kwargs.get(
                'subfile', '')
            if hardusb and await aiopath.exists(subfile):
                fontname = kwargs.get('fontname', '').replace(
                    '_', ' ') or config_dict['HARDSUB_FONT_NAME']
                fontsize = f',FontSize={fontsize}' if (
                    fontsize := kwargs.get('fontsize')
                    or config_dict['HARDSUB_FONT_SIZE']) else ''
                fontcolour = f',PrimaryColour=&H{kwargs["fontcolour"]}' if kwargs.get(
                    'fontcolour') else ''
                boldstyle = ',Bold=1' if kwargs.get('boldstyle') else ''
                hardusb = f",subtitles='{subfile}':force_style='FontName={fontname},Shadow=1.5{fontsize}{fontcolour}{boldstyle}',unsharp,eq=contrast=1.07"

            quality = f',scale={self._qual[kwargs["quality"]]}:-2' if kwargs.get(
                'quality') else ''
            cmd = [
                FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y', '-i',
                self.path, '-i', wmpath, '-filter_complex',
                f"[1][0]scale2ref=w='iw*{wmsize}/100':h='ow/mdar'[wm][vid];[vid][wm]overlay={wmposition}{popupwm}{quality}{hardusb}"
            ]
            if config_dict['VIDTOOLS_FAST_MODE']:
                cmd.extend(('-c:v', 'libx264', '-preset',
                            config_dict['LIB264_PRESET'], '-crf', '25'))
            cmd.extend(('-map', '0:a:?', '-map', '0:s:?', '-c:a', 'copy',
                        '-c:s', 'copy', self.outfile))
            await self._run_cmd(cmd)
            if self.is_cancel:
                return
        await gather(clean_target(wmpath), clean_target(subfile))

        return await self._final_path()

    async def _merge_vids(self):
        """Merge videos using the selected Normal or existing Advanced planner mode."""
        merge_mode = (self.data or {}).get('merge_mode', 'normal')
        if merge_mode == 'advanced':
            # Reuse the bot's existing -ht Advanced Merge Planner instead of
            # maintaining a second planner implementation in Video Tools.
            if not await aiopath.isdir(self.path):
                LOGGER.warning('Advanced Video + Video merge expects an extracted folder: %s', self.path)
                return self._up_path
            # `proceed_merge` normally receives a downloaded task path, where
            # `listener.is_file` describes the original download. Here we pass
            # an extracted folder, so temporarily force folder scanning.
            old_is_file = getattr(self.listener, 'is_file', False)
            try:
                self.listener.is_file = False
                result = await self.listener.proceed_merge(
                    self.path, self._gid, custom_name='Merged'
                )
            finally:
                self.listener.is_file = old_is_file
            if result and await aiopath.isfile(str(result)):
                self._up_path = str(result)
                return self._up_path
            return self._up_path

        """Normal mode uses the existing fast concat/fallback implementation below."""
        if not await aiopath.isdir(self.path):
            # Video + Video is a folder operation. A single video/archive is
            # not silently treated as a directory or merged with itself.
            LOGGER.warning('Video + Video expects an extracted folder containing at least two videos: %s', self.path)
            return self._up_path

        video_paths = []
        for dirpath, _, files in await sync_to_async(walk, self.path):
            for filename in natsorted(files):
                video_file = ospath.join(dirpath, filename)
                if filename == 'input.txt' or filename.endswith(('.merge.tmp.mkv', '.part')):
                    continue
                # Avoid re-merging the destination from a previous operation.
                if self.name and ospath.abspath(video_file) == ospath.abspath(ospath.join(self.path, self.name)):
                    continue
                if (await get_document_type(video_file))[0]:
                    video_paths.append(video_file)

        video_paths = natsorted(video_paths)
        if len(video_paths) < 2:
            LOGGER.warning('Video + Video requires at least two video files; leaving input unchanged')
            return self._up_path

        await self._name_base_dir(self.path)
        # Keep output at the task root, even when source videos are nested in
        # one or more folders produced by an unzip/extract task.
        self.outfile = ospath.join(self.path, self.name)
        if self.outfile in video_paths:
            LOGGER.error('Video + Video output collides with an input file: %s', self.outfile)
            return self._up_path

        self.size = sum([await get_path_size(item) for item in video_paths])
        self._files = list(video_paths)
        input_file = ospath.join(self.path, 'input.txt')

        def concat_quote(value):
            # FFmpeg concat-demuxer quoting: escape backslashes and quotes.
            return value.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')

        async with aiopen(input_file, 'w') as f:
            await f.write('\n'.join("file '{}'".format(concat_quote(item)) for item in video_paths))

        await update_status_message(self.listener.message.chat.id)
        cmd = [FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-f', 'concat',
               '-safe', '0', '-i', input_file, '-map', '0', '-c', 'copy',
               '-y', self.outfile]
        ok = await self._run_cmd(cmd, 'direct')
        if not ok and not self.is_cancel:
            # The first attempt failed; _run_cmd clears its cleanup list on
            # failure. Retry for common mixed-resolution/codec inputs.
            self._files = list(video_paths)
            cmd = [FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-f', 'concat',
                   '-safe', '0', '-i', input_file, '-map', '0:v:0?', '-map', '0:a?',
                   '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                   '-c:a', 'aac', '-b:a', '192k', '-y', self.outfile]
            ok = await self._run_cmd(cmd, 'direct')

        await clean_target(input_file)
        if self.is_cancel:
            return self._up_path
        if ok and await aiopath.isfile(self.outfile):
            self._up_path = self.outfile
            return self.outfile
        return self._up_path

    async def _merge_auds(self):
        """Merge video + external audio with automatic timestamp synchronization."""
        main_video = False
        audio_files = []

        for dirpath, _, files in await sync_to_async(walk, self.path):
            for file in natsorted(files):
                file = ospath.join(dirpath, file)
                is_video, is_audio, _ = await get_document_type(file)
                if is_video:
                    if main_video:
                        continue
                    main_video = file
                elif is_audio:
                    self.size += await get_path_size(file)
                    audio_files.append(file)

        if not main_video or not audio_files:
            return self._up_path

        # Exactly two logical inputs are required here: the main movie/video
        # and the external audio file(s). The movie stays input #0 and every
        # external audio becomes input #1, #2, ... so the merge is deterministic.
        self._files = [main_video, *audio_files]
        LOGGER.info('Video + Audio merge: video=%s external_audio=%s',
                    ospath.basename(main_video),
                    ', '.join(ospath.basename(x) for x in audio_files))

        # _up_path can be the task/output directory (for example: .../sample).
        # FFmpeg needs an actual output filename with a muxer extension.
        output_name = self.name or ospath.basename(main_video)
        if not ospath.splitext(output_name)[1]:
            output_name = f"{output_name}.mkv"
        elif ospath.splitext(output_name)[1].lower() not in {'.mkv', '.mp4', '.webm', '.mov'}:
            output_name = f"{ospath.splitext(output_name)[0]}.mkv"
        self.outfile = ospath.join(self.path, output_name)

        _, size = await gather(
            self._name_base_dir(self.path),
            get_path_size(main_video)
        )
        self.size += size
        await update_status_message(self.listener.message.chat.id)

        # First try content-based synchronization against the video's original
        # audio. This catches constant lip/dialogue timing mismatches even when
        # container timestamps are both zero. If confidence is low, fall back to
        # stream/container timestamps.
        try:
            video_streams, video_fmt = await get_metavideo(main_video)
            ref_audio = next((s for s in video_streams if s.get('codec_type') == 'audio'), None)
        except Exception:
            video_streams, video_fmt, ref_audio = [], {}, None

        # Build one FFmpeg command: input 0 is always the movie/video,
        # following inputs are the NEW external audio tracks.
        cmd = [FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y', '-i', main_video]

        for audio in audio_files:
            offset = None
            confidence = 0.0
            if ref_audio:
                try:
                    offset, confidence = await estimate_audio_content_offset(main_video, audio)
                    if offset is not None:
                        LOGGER.info('Content audio sync: %s offset=%.2fs confidence=%.2f',
                                    ospath.basename(audio), offset, confidence)
                except Exception as e:
                    LOGGER.warning('Content audio sync failed for %s: %s', audio, e)

            if offset is None:
                try:
                    audio_streams, audio_fmt = await get_metavideo(audio)
                    video_start = float(
                        next((x.get('start_time') for x in video_streams
                              if x.get('codec_type') == 'video' and x.get('start_time') is not None),
                             video_fmt.get('start_time') or 0.0)
                    )
                    audio_start = float(
                        next((x.get('start_time') for x in audio_streams
                              if x.get('codec_type') == 'audio' and x.get('start_time') is not None),
                             audio_fmt.get('start_time') or 0.0)
                    )
                    offset = video_start - audio_start
                except Exception:
                    offset = 0.0

            if abs(offset) >= 0.02:
                cmd.extend(('-itsoffset', f'{offset:.3f}'))
            cmd.extend(('-i', audio))

        # Both files are muxed into ONE MKV. Keep the video bit-for-bit
        # untouched so sync/audio processing never causes a large video
        # re-encode. Re-encode audio only and cap it at 192 kbps so large
        # AC3/DTS tracks do not unnecessarily inflate the output size.
        cmd.extend(('-map', '0:v:0?', '-map', '0:s:?', '-map', '0:a:?'))
        for j in range(1, len(audio_files) + 1):
            cmd.extend(('-map', f'{j}:a:?'))

        cmd.extend((
            '-map_metadata', '0',
            '-c:v', 'copy',
            '-c:a', 'aac', '-b:a', '192k',
            '-c:s', 'copy',
            self.outfile,
        ))

        await self._run_cmd(cmd, 'direct')
        if self.is_cancel:
            return

        # Video + Audio is a merge operation. Do NOT call _final_path() here:
        # _final_path() scans the source directory and removes media files,
        # which can remove/replace the newly-created output or leave multiple
        # candidates for upload. Return the exact output path and clean only
        # the original input files after FFmpeg succeeds.
        if await aiopath.isfile(self.outfile):
            for source in self._files:
                if source != self.outfile and await aiopath.exists(source):
                    await clean_target(source)
            self._up_path = self.outfile
            return self._up_path

        return self._up_path

    async def _merge_subs(self, **kwargs):
        main_video = False
        subtitle_files = []
        for dirpath, _, files in await sync_to_async(walk, self.path):
            for file in natsorted(files):
                file = ospath.join(dirpath, file)
                is_video, is_sub = (await
                                    get_document_type(file))[0], file.endswith(
                                        ('.ass', '.srt', '.vtt'))
                if is_video:
                    if main_video:
                        continue
                    main_video = file
                if is_sub:
                    self.size += await get_path_size(file)
                    subtitle_files.append(file)

        if not main_video or not subtitle_files:
            LOGGER.warning('Video + Subtitle requires a video and at least one subtitle file; leaving input unchanged')
            return self._up_path
        self._files = subtitle_files
        self._files.insert(0, main_video)
        self.outfile = self._up_path
        if len(self._files) > 1:
            base_dir, size = await gather(self._name_base_dir(main_video),
                                          get_path_size(main_video))
            self.size += size
            cmd = [FFMPEG_NAME, '-hide_banner', '-ignore_unknown', '-y']
            # Keep the original media filename while writing into VT_Output;
            # never read and overwrite the same source file.
            self.outfile, status = ospath.join(base_dir, self.name), 'direct'
            if kwargs.get('hardsub'):
                self.path, status = self._files[0], 'prog'
                cmd.extend(('-i', self.path, '-vf'))
                fontname = kwargs.get('fontname', '').replace(
                    '_', ' ') or config_dict['HARDSUB_FONT_NAME']
                fontsize = f',FontSize={fontsize}' if (
                    fontsize := kwargs.get('fontsize')
                    or config_dict['HARDSUB_FONT_SIZE']) else ''
                fontcolour = f',PrimaryColour=&H{kwargs["fontcolour"]}' if kwargs.get(
                    'fontcolour') else ''
                boldstyle = ',Bold=1' if kwargs.get('boldstyle') else ''
                quality = f',scale={self._qual[kwargs["quality"]]}:-2' if kwargs.get(
                    'quality') else ''

                cmd.append(
                    f"subtitles='{self._files[1]}':force_style='FontName={fontname},Shadow=1.5{fontsize}{fontcolour}{boldstyle}'{quality},unsharp,eq=contrast=1.07"
                )

                if config_dict['VIDTOOLS_FAST_MODE']:
                    cmd.extend(('-preset', config_dict['LIB264_PRESET'],
                                '-c:v', 'libx264', '-crf', '24'))
                    extra = ['-map', '0:a:?', '-c:a', 'copy']
                else:
                    cmd.extend(
                        ('-preset', config_dict['LIB265_PRESET'], '-c:v',
                         'libx265', '-pix_fmt', 'yuv420p10le', '-crf', '24',
                         '-profile:v', 'main10', '-x265-params', 'no-info=1',
                         '-bsf:v', 'filter_units=remove_types=6'))
                    extra = ['-c:a', 'aac', '-b:a', '160k', '-map', '0:1']
                cmd.extend(['-map', '0:v:0?', '-map', '-0:s'] + extra +
                           [self.outfile])
            else:
                for i in self._files:
                    cmd.extend(('-i', i))
                cmd.extend(
                    ('-map', '0:v:0?', '-map', '0:a:?', '-map', '0:s:?'))
                for j in range(1, (len(self._files))):
                    cmd.extend(('-map', f'{j}:s'))
                cmd.extend(('-c:v', 'copy', '-c:a', 'copy', '-c:s', 'srt',
                            self.outfile))
            await self._run_cmd(cmd, status)
            if self.is_cancel:
                return

        return await self._final_path()
