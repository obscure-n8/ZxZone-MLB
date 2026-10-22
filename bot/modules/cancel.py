from pyrogram import Client, filters

@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_command(client, message):
    # আপনার কাস্টম স্টপ বা এরর মেসেজ ট্রিগার লজিক
    user = message.from_user.username or message.from_user.first_name
    error_text = (
        f"Your Download has been stopped\n\n"
        f"╭ Task By: @{user}\n"
        f"├ In Mode:  #Leech | #Aria2\n"
        f"╰ Reason: The response status is not successful. status=400"
    )
    await message.reply_text(error_text)
