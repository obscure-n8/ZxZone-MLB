from time import time

from bot.helper.ext_utils.status_utils import (
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
)


class GofileUploadStatus:
    def __init__(self, listener, obj, size, gid):
        self._obj = obj
        self._size = size
        self._gid = gid
        self._elapsed = time()
        self.listener = listener

    @staticmethod
    def engine():
        return "GoFile"

    @staticmethod
    def status():
        return MirrorStatus.STATUS_UPLOADINGTOGO

    def elapsed(self):
        return get_readable_time(time() - self._elapsed)

    def processed_bytes(self):
        return get_readable_file_size(self._obj.uploaded_bytes)

    def size(self):
        return get_readable_file_size(self._size)

    def name(self):
        return self.listener.name

    def progress_raw(self):
        try:
            return self._obj.uploaded_bytes / self._size * 100
        except:
            return 0

    def progress(self):
        return f"{round(self.progress_raw(), 2)}%"

    def speed(self):
        return f"{get_readable_file_size(self._obj.speed)}/s"

    def eta(self):
        try:
            return get_readable_time(
                (self._size - self._obj.uploaded_bytes) / self._obj.speed
            )
        except:
            return "~"

    def gid(self):
        return self._gid

    def task(self):
        return self._obj
