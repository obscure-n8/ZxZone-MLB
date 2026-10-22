from aiofiles import open as aiopen
from contextlib import redirect_stdout
from io import StringIO
from os import path as ospath, getcwd, chdir
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from textwrap import indent
from traceback import format_exc

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    auto_delete_message,
    sendFile,
)

namespaces = {}


def namespace_of(message: Message):
    if message.chat.id not in namespaces:
        namespaces[message.chat.id] = {
            "__builtins__": globals()["__builtins__"],
            "bot": bot,
            "message": message,
            "user": message.from_user or message.sender_chat,
            "chat": message.chat,
        }
    return namespaces[message.chat.id]


def log_input(message: Message):
    LOGGER.info(
        "IN: %s (user=%s, chat=%s)",
        message.text,
        message.from_user.id if message.from_user else message.sender_chat.id,
        message.chat.id,
    )


async def send(msg, message):
    if len(str(msg)) > 2000:
        async with aiopen("output.txt", "w", encoding="utf-8") as f:
            await f.write(msg)
        await sendFile(message, "output.txt", "Eval output", config_dict["IMAGE_TXT"])
    else:
        LOGGER.info("OUT: '%s'", msg)
        await sendMessage(f"<code>{msg}</code>", message)


@new_task
async def aioexecute(_, message: Message):
    if len(message.text.split()) == 1:
        await sendMessage("No command given to execute!", message)
        return
    await send(await do("aexec", message), message)


@new_task
async def execute(_, message: Message):
    if len(message.text.split()) == 1:
        await sendMessage("No command given to execute!", message)
        return
    await send(await do("exec", message), message)


def cleanup_code(code):
    if code.startswith("```") and code.endswith("```"):
        return "\n".join(code.split("\n")[1:-1])
    return code.strip("` \n")


async def do(func, message: Message):
    log_input(message)
    content = message.text.split(maxsplit=1)[-1]
    body = cleanup_code(content)
    env = namespace_of(message)
    chdir(getcwd())
    async with aiopen(ospath.join(getcwd(), "bot", "modules", "temp.txt"), "w") as temp:
        await temp.write(body)
    stdout = StringIO()

    try:
        if func == "exec":
            exec(f"def func():\n{indent(body, '  ')}", env)
        else:
            exec(f"async def func():\n{indent(body, '  ')}", env)
    except Exception as e:
        return f"{e.__class__.__name__}: {e}"

    rfunc = env["func"]

    try:
        with redirect_stdout(stdout):
            func_return = (
                await sync_to_async(rfunc) if func == "exec" else await rfunc()
            )
    except:
        value = stdout.getvalue()
        return f"{value}{format_exc()}"
    else:
        value = stdout.getvalue()
        result = None
        if func_return is None:
            if value:
                result = f"{value}"
            else:
                try:
                    result = f"{repr(await sync_to_async(eval, body, env))}"
                except:
                    pass
        else:
            result = f"{value}{func_return}"
        if result:
            return result


async def clear(_, message: Message):
    log_input(message)
    namespaces.pop(message.chat.id, None)
    await send("Locals Cleared.", message)


@new_task
async def exechelp(_, message: Message):
    text = f"""
<b>Executor</b>
<b>╭ </b>{BotCommands.AExecCommand} <i>Exec async functions</i>
<b>┊ </b>{BotCommands.ExecCommand} <i>Exec sync functions</i>
<b>╰ </b>{BotCommands.ClearLocalsCommand} <i>Cleared locals</i>
"""
    msg = await sendMessage(text, message)
    await auto_delete_message(message, msg)


bot.add_handler(
    MessageHandler(
        exechelp, filters=command(BotCommands.ExecHelpCommand) & CustomFilters.owner
    )
)
bot.add_handler(
    MessageHandler(
        aioexecute, filters=command(BotCommands.AExecCommand) & CustomFilters.owner
    )
)
bot.add_handler(
    MessageHandler(
        execute, filters=command(BotCommands.ExecCommand) & CustomFilters.owner
    )
)
bot.add_handler(
    MessageHandler(
        clear, filters=command(BotCommands.ClearLocalsCommand) & CustomFilters.owner
    )
)
