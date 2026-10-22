from time import time

from bot import LOGGER
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    MirrorStatus,
    get_readable_time,
)


class QueueStatus:
    def __init__(self, listener, size, gid, status):
        self._size = size
        self._gid = gid
        self._status = status
        self._elapsed = time()
        self.listener = listener

    @staticmethod
    def engine():
        return "QSystem"

    def elapsed(self):
        return get_readable_time(time() - self._elapsed)

    def gid(self):
        return self._gid

    def name(self):
        return self.listener.name

    def size(self):
        return get_readable_file_size(self._size)

    def status(self):
        return (
            MirrorStatus.STATUS_QUEUEDL
            if self._status == "dl"
            else MirrorStatus.STATUS_QUEUEUP
        )

    @staticmethod
    def processed_bytes():
        return 0

    @staticmethod
    def progress():
        return "0%"

    @staticmethod
    def speed():
        return "0B/s"

    @staticmethod
    def eta():
        return "~"

    def task(self):
        return self

    async def cancel_task(self):
        LOGGER.info("Cancelling Queue%s: %s", self._status, self.name())
        if self._status == "dl":
            await self.listener.onDownloadError(
                "Task have been removed from queue/download!"
            )
        else:
            await self.listener.onUploadError(
                "Task have been removed from queue/upload!"
            )
