from math import ceil
from asyncio import sleep

from bot import bot_loop
from bot.helper.telegram_helper.button_build import ButtonMaker


content_dict = {}


class TeleContent:
    def __init__(self, message, key=None, max_page=8, direct=True):
        self.key = key
        self.task = None
        self._message = message
        self._max = max_page
        self._start = 0
        self._direct = direct
        self._content = {}
        self._cap = ""
        self._count = 0
        self._page_no = 1
        self._pages = ceil(len(self._content) / self._max)
        if self._direct:
            content_dict[message.id] = self

    @property
    def reply(self):
        return self._message.reply_to_message

    @property
    def pages(self):
        return self._pages

    def _clenup(self):
        content_dict.pop(self._message.id, None)

    async def _auto_clean(self):
        if len(self._content) <= self._max or not self._direct:
            self.task = None
            self._clenup()
            return
        await sleep(300)
        self._clenup()

    def cancel(self):
        if self.task:
            self._clenup()
            self.task.cancel()

    def set_data(self, content, cap):
        if len(content) < 100:
            content = [x[1:] for x in content]
        self._content = content
        self._cap = cap
        self._count = 0
        self._page_no = 1
        self._pages = ceil(len(self._content) / self._max)
        self.task = bot_loop.create_task(self._auto_clean())

    def _prepare_data(self, data, fdata):
        match data:
            case "nex":
                if self._page_no == self._pages:
                    self._count = 0
                    self._page_no = 1
                else:
                    self._count += self._max
                    self._page_no += 1
            case "pre":
                if self._page_no == 1:
                    self._count = self._max * (self._pages - 1)
                    self._page_no = self._pages
                else:
                    self._count -= self._max
                    self._page_no -= 1
            case "foot":
                if fdata in (self._start, self._count):
                    return f"Already in page {self._page_no}!"
                self._start = fdata
                self._count = self._start
                if self._start / self._max == 0:
                    self._page_no = 1
                else:
                    self._page_no = int(self._start / self._max) + 1

        if self._page_no > self._pages and self._pages != 0:
            self._count -= self._max
            self._page_no -= 1

    async def get_content(self, pattern, data=None, fdata=None, extra_buttons=None):
        if pre := self._prepare_data(data, fdata):
            return pre, None
        buttons = ButtonMaker()
        if not self._content:
            return "", None
        text, mid, user_id = "", self._message.id, self._message.from_user.id
        task = len(self._content)
        for index, r_data in enumerate(self._content[self._count :], start=1):
            text += r_data
            if index == self._max:
                break
        if task > self._max:
            buttons.button_data("<<", f"{pattern} {user_id} pre {mid}")
            buttons.button_data(
                f"{self._page_no}/{self._pages}", f"{pattern} {user_id} page {mid}"
            )
            buttons.button_data(">>", f"{pattern} {user_id} nex {mid}")
        buttons.button_data("Close", f"{pattern} {user_id} close {mid}")
        if extra_buttons:
            for key, value in extra_buttons:
                buttons.button_data(key, f"{pattern} {value}", "header")
        if self._pages >= 5:
            for x in range(0, task, self._max):
                buttons.button_data(
                    int(x / self._max) + 1,
                    f"{pattern} {user_id} foot {mid} {x}",
                    position="footer",
                )
        text += f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n{self._cap}"
        return text, buttons.build_menu(3)
