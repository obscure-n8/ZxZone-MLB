import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.premium import premium_system
from bot.database.users import users_db

@Client.on_message(filters.command("premium") & filters.private)
async def premium_command(client: Client, message: Message):
    """Handle /premium command"""
    user = message.from_user
    
    # Get premium info
    premium_info = await premium_system.get_premium_info(user.id)
    
    if premium_info.get('is_premium', False):
        # Show premium status
        days_left = premium_info.get('days_left', 0)
        plan = premium_info.get('plan', 'Unknown')
        
        premium_text = f"""
💎 **Premium Status**

✅ **Active Premium**

📊 **Plan:** {plan}
⏰ **Days Left:** {days_left} days

🎁 **Your Benefits:**
"""
        
        for feature in premium_info.get('features', []):
            premium_text += f"• {feature}\n"
            
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ]
        ])
        
    else:
        # Show premium plans
        premium_text = """
💎 **Premium Plans**

🚀 **Upgrade to Premium for:**

• Unlimited Tasks
• Priority Queue
• No Ads
• Speed Boost
• VIP Support

📊 **Available Plans:**
"""
        
        plans = await premium_system.get_plans()
        keyboard_buttons = []
        
        for plan_id, plan_info in plans.items():
            premium_text += f"\n**{plan_info['name']}**: ₹{plan_info['price']}"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"💎 {plan_info['name']} - ₹{plan_info['price']}",
                    callback_data=f"premium_{plan_id}"
                )
            ])
            
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    await message.reply_text(
        premium_text,
        reply_markup=keyboard,
        parse_mode="markdown"
    )

@Client.on_callback_query(filters.regex("^premium_"))
async def premium_callback(client: Client, callback_query):
    """Handle premium plan selection"""
    plan = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    # Get plan info
    plans = await premium_system.get_plans()
    plan_info = plans.get(plan)
    
    if not plan_info:
        await callback_query.answer("Invalid plan!")
        return
    
    # Show payment instructions
    payment_text = f"""
💎 **Premium Plan:** {plan_info['name']}

💰 **Price:** ₹{plan_info['price']}

📝 **How to Upgrade:**

1. Send payment to UPI: `zonexus@upi`
2. Send screenshot to admin
3. You'll get premium within 5 minutes

**Contact:** @ZonexusSupport

✅ After payment, use /redeem to activate
"""
    
    await callback_query.message.edit_text(
        payment_text,
        parse_mode="markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="premium_back")]
        ])
    )
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^premium_back$"))
async def premium_back_callback(client: Client, callback_query):
    """Back to premium menu"""
    await premium_command(client, callback_query.message)
    await callback_query.answer()

@Client.on_message(filters.command("redeem") & filters.private)
async def redeem_command(client: Client, message: Message):
    """Handle /redeem command for premium code"""
    user = message.from_user
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /redeem <code>")
        return
    
    code = message.command[1]
    
    # This would validate code from database
    # For now, show info
    await message.reply_text(
        f"🔑 **Redeem Code:** {code}\n\n"
        f"⏳ Validating...\n\n"
        f"Contact @ZonexusSupport for valid codes."
    )

@Client.on_message(filters.command("givepremium") & filters.private)
async def give_premium_command(client: Client, message: Message):
    """Give premium to user (admin only)"""
    user = message.from_user
    
    # Check if admin
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 3:
        await message.reply_text(
            "📝 **Usage:** /givepremium <user_id> <plan>\n\n"
            "Plans: weekly, monthly, yearly",
            parse_mode="markdown"
        )
        return
    
    target_user_id = int(message.command[1])
    plan = message.command[2].lower()
    
    # Activate premium
    if await premium_system.activate_premium(target_user_id, plan):
        await message.reply_text(
            f"✅ **Premium activated!**\n\n"
            f"👤 User: {target_user_id}\n"
            f"💎 Plan: {plan}",
            parse_mode="markdown"
        )
    else:
        await message.reply_text("❌ **Invalid plan!**")
