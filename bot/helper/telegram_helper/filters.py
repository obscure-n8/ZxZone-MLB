from pyrogram.filters import create

from bot import config_dict, user_data, OWNER_ID


class CustomFilters:
    @staticmethod
    async def owner_filter(_, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        return uid == OWNER_ID

    owner = create(owner_filter)

    @staticmethod
    async def authorized_user(_, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        chat_id = message.chat.id
        user_dict = user_data.get(uid, {})
        return bool(
            uid == OWNER_ID
            or (
                user_dict.get("is_auth")
                or user_dict.get("is_sudo")
                or (config_dict["PREMIUM_MODE"] and user_dict.get("is_premium"))
            )
            or user_data.get(chat_id, {}).get("is_auth")
        )

    authorized = create(authorized_user)

    @staticmethod
    async def sudo_user(_, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        return bool(uid == OWNER_ID or user_data.get(uid, {}).get("is_sudo"))

    sudo = create(sudo_user)
