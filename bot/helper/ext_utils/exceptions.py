class DirectDownloadLinkException(Exception):
    """Not method found for extracting direct download link from the http link"""


class NotSupportedExtractionArchive(Exception):
    """The archive format use is trying to extract is not supported"""


class RssShutdownException(Exception):
    """This exception should be raised when shutdown is called to stop the montior"""


class TgLinkException(Exception):
    """No Access granted for this chat"""


class InvalidHash(Exception):
    message = "Invalid hash!"


class FIleNotFound(Exception):
    message = "File not found!"
