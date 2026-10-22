from aiofiles import open as aiopen
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler, EditedMessageHandler
from pyrogram.types import Message

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import cmd_exec, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendFile, sendMessage


@new_task
async def shell(_, message: Message):
    cmd = message.text.split(maxsplit=1)
    if len(cmd) == 1:
        await sendMessage("No command given to execute!", message)
        return
    cmd = cmd[1].strip()
    stdout, stderr, _ = await cmd_exec(cmd, shell=True)
    text = ""
    if len(stdout) != 0:
        text += f"<b>Stdout</b>\n<code>{stdout}</code>\n"
        LOGGER.info("Shell - %s - %s", cmd, stdout)
    if len(stderr) != 0:
        text += f"<b>Stderr</b>\n<code>{stderr}</code>\n"
        LOGGER.error("Shell - %s - %s", cmd, stderr)
    if len(text) > 4000:
        async with aiopen("shell_output.txt", "w") as f:
            await f.write(text)
        await sendFile(
            message, "shell_output.txt", "shell_output", config_dict["IMAGE_TXT"]
        )
    elif len(text) != 0:
        await sendMessage(text, message)
    else:
        await sendMessage("No output.", message)


bot.add_handler(
    MessageHandler(
        shell, filters=command(BotCommands.ShellCommand) & CustomFilters.owner
    )
)
bot.add_handler(
    EditedMessageHandler(
        shell, filters=command(BotCommands.ShellCommand) & CustomFilters.owner
    )
)
