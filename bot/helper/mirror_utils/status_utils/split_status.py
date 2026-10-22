from time import time

from bot import subprocess_lock, LOGGER
from bot.helper.ext_utils.bot_utils import async_to_sync
from bot.helper.ext_utils.files_utils import get_path_size
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    MirrorStatus,
    get_readable_time,
)


class SplitStatus:
    def __init__(self, listener, size, gid):
        self._size = size
        self._gid = gid
        self._start_time = time()
        self.listener = listener
        self.state = ""

    def engine(self):
        return "p7zip" if self.state == "archive" else "FFmpeg"

    def elapsed(self):
        return get_readable_time(time() - self._start_time)

    def gid(self):
        return self._gid

    def speed_raw(self):
        return self.processed_raw() / (time() - self._start_time)

    def progress_raw(self):
        try:
            return self.processed_raw() / self._size * 100
        except:
            return 0

    def progress(self):
        return f"{round(self.progress_raw(), 2)}%"

    def speed(self):
        return f"{get_readable_file_size(self.speed_raw())}/s"

    def name(self):
        return self.listener.name

    def size(self):
        return get_readable_file_size(self._size)

    def eta(self):
        try:
            return get_readable_time(
                (self._size - self.processed_raw()) / self.speed_raw()
            )
        except:
            return "~"

    @staticmethod
    def status():
        return MirrorStatus.STATUS_SPLITTING

    def processed_bytes(self):
        return get_readable_file_size(self.processed_raw())

    def processed_raw(self):
        return self.listener.total_size + (
            async_to_sync(get_path_size, self.listener.dir) - self._size
        )

    def task(self):
        return self

    async def cancel_task(self):
        LOGGER.info("Cancelling Split: %s", self.name())
        async with subprocess_lock:
            if self.listener.suproc and self.listener.suproc.returncode is None:
                self.listener.suproc.kill()
            else:
                self.listener.suproc = "cancelled"
        await self.listener.onUploadError("Splitting stopped by user!")
