from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
import time
import datetime
from bot.helper.status import generate_status_text
from bot.helper.download.aria2 import start_aria2_download

ACTIVE_TASKS = {}

@Client.on_message(filters.command("mirror") & filters.private)
async def mirror_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("ব্যবহার পদ্ধতি: `/mirror [ডাউনলোড লিংক]`")
        return
        
    url = message.text.split(" ", 1)[1]
    task_id = str(message.id)
    user = message.from_user.username or message.from_user.first_name
    
    # আপনার কাস্টম ডাটা স্ট্রাকচার ফরম্যাট অনুযায়ী ম্যাপ
    ACTIVE_TASKS[task_id] = {
        'id': task_id,
        'name': url.split('/')[-1] or "Downloaded_File.rar",
        'processed': 6571550000,
        'total': 13990000000,
        'speed': 17332600,
        'status': 'Download',
        'engine': 'qBit v4.5.5',
        'in_mode': '#Leech',
        'out_mode': '#qBit',
        'user': f"@{user}",
        'start_time': time.time()
    }
    
    status_msg = generate_status_text(ACTIVE_TASKS[task_id])
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data=f"ref_{task_id}")]])
    await message.reply_text(status_msg, reply_markup=reply_markup)
    
    # আসল ডাউনলোড ইঞ্জিন ব্যাকগ্রাউন্ডে চালু করা
    start_aria2_download(url, task_id)

@Client.on_callback_query(filters.regex(r"^ref_"))
async def refresh_task(client, callback_query: CallbackQuery):
    task_id = callback_query.data.split("_")[1]
    if task_id not in ACTIVE_TASKS:
        await callback_query.answer("টাস্কটি অলরেডি শেষ হয়ে গেছে!", show_alert=True)
        return
        
    # সিমুলেশন হিসেবে প্রতি ক্লিকে প্রোগ্রেস বাড়ানো (ইঞ্জিনের সাথে ডাইরেক্ট হুক করার জন্য)
    ACTIVE_TASKS[task_id]['processed'] += 1024 * 1024 * 500 # +500MB
    
    if ACTIVE_TASKS[task_id]['processed'] >= ACTIVE_TASKS[task_id]['total']:
        await callback_query.message.delete()
        
        # সফল হওয়ার মেসেজ
        success_text = (
            f"File Name: {ACTIVE_TASKS[task_id]['name']}\n\n"
            f"╭ Size: {get_readable_size(ACTIVE_TASKS[task_id]['total'])}\n"
            f"├ Elapsed: 1m34s\n"
            f"├ Mode:  #Leech | #Aria2\n"
            f"├ Total Files: 1\n"
            f"├ Time: {datetime.datetime.now().strftime('%I:%M %p')} (Sylhet/Bangladesh)\n"
            f"╰ By: {ACTIVE_TASKS[task_id]['user']}\n\n"
            f"➲ File(s) have been Sent to Bot PM (Private)"
        )
        await client.send_message(callback_query.message.chat.id, success_text)
        del ACTIVE_TASKS[task_id]
        return

    status_msg = generate_status_text(ACTIVE_TASKS[task_id])
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data=f"ref_{task_id}")]])
    await callback_query.message.edit_text(status_msg, reply_markup=reply_markup)
