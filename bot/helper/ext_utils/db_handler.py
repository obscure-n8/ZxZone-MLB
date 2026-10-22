from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, makedirs
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from bot import (
    user_data,
    rss_dict,
    bot_id,
    config_dict,
    aria2_options,
    qbit_options,
    bot_loop,
    DATABASE_URL,
    LOGGER,
)


class DbManager:
    def __init__(self):
        self._err = False
        self._db = None
        self._conn = None
        self._connect()

    def _connect(self):
        try:
            self._conn = AsyncIOMotorClient(DATABASE_URL)
            self._db = self._conn.mltb
        except PyMongoError as e:
            LOGGER.error("Error in DB connection: %s", e)
            self._err = True

    async def db_load(self):
        if self._err:
            return
        # Save bot settings
        await self._db.settings.config.update_one(
            {"_id": bot_id}, {"$set": config_dict}, upsert=True
        )
        # Save Aria2c options
        if await self._db.settings.aria2c.find_one({"_id": bot_id}) is None:
            await self._db.settings.aria2c.update_one(
                {"_id": bot_id}, {"$set": aria2_options}, upsert=True
            )
        # Save qbittorrent options
        if await self._db.settings.qbittorrent.find_one({"_id": bot_id}) is None:
            await self._db.settings.qbittorrent.update_one(
                {"_id": bot_id}, {"$set": qbit_options}, upsert=True
            )
        # User Data
        if await self._db.users[bot_id].find_one():
            rows = self._db.users[bot_id].find({})
            # return a dict ==> {_id, is_sudo, is_auth, as_doc, thumb, yt_opt, media_group, equal_splits, split_size, rclone}
            async for row in rows:
                uid = row["_id"]
                del row["_id"]
                thumb_path = f"thumbnails/{uid}.jpg"
                rclone_path = f"rclone/{uid}.conf"
                token_path = f"tokens/{uid}.pickle"
                if row.get("thumb"):
                    await makedirs("thumbnails", exist_ok=True)
                    async with aiopen(thumb_path, "wb+") as f:
                        await f.write(row["thumb"])
                    row["thumb"] = thumb_path
                if row.get("rclone_config"):
                    await makedirs("rclone", exist_ok=True)
                    async with aiopen(rclone_path, "wb+") as f:
                        await f.write(row["rclone_config"])
                    row["rclone_config"] = rclone_path
                if row.get("token_pickle"):
                    await makedirs("tokens", exist_ok=True)
                    async with aiopen(token_path, "wb+") as f:
                        await f.write(row["token_pickle"])
                    row["token_pickle"] = token_path
                user_data[uid] = row
            LOGGER.info("Users data has been imported from Database.")
        # Rss Data
        if await self._db.rss[bot_id].find_one():
            # return a dict ==> {_id, title: {link, last_feed, last_name, inf, exf, command, paused}
            rows = self._db.rss[bot_id].find({})
            async for row in rows:
                user_id = row["_id"]
                del row["_id"]
                rss_dict[user_id] = row
            LOGGER.info("Rss data has been imported from Database.")

    async def update_deploy_config(self):
        if self._err:
            return
        current_config = dict(dotenv_values("config.env"))
        await self._db.settings.deployConfig.replace_one(
            {"_id": bot_id}, current_config, upsert=True
        )

    async def update_config(self, dict_):
        if self._err:
            return
        await self._db.settings.config.update_one(
            {"_id": bot_id}, {"$set": dict_}, upsert=True
        )

    async def update_aria2(self, key, value):
        if self._err:
            return
        await self._db.settings.aria2c.update_one(
            {"_id": bot_id}, {"$set": {key: value}}, upsert=True
        )

    async def update_qbittorrent(self, key, value):
        if self._err:
            return
        await self._db.settings.qbittorrent.update_one(
            {"_id": bot_id}, {"$set": {key: value}}, upsert=True
        )

    async def update_private_file(self, path):
        if self._err:
            return
        original_path = path
        if await aiopath.exists(original_path):
            async with aiopen(original_path, "rb+") as pf:
                pf_bin = await pf.read()
        else:
            # MongoDB should receive bytes for stored files, not a text sentinel.
            pf_bin = b""
        db_path = original_path.replace(".", "__")
        await self._db.settings.files.update_one(
            {"_id": bot_id}, {"$set": {db_path: pf_bin}}, upsert=True
        )
        if original_path == "config.env":
            await self.update_deploy_config()

    async def update_user_data(self, user_id):
        if self._err:
            return
        data = dict(user_data.get(user_id, {}))
        data.pop("thumb", None)
        data.pop("rclone_config", None)
        data.pop("token_pickle", None)
        await self._db.users[bot_id].replace_one({"_id": user_id}, data, upsert=True)

    async def update_user_doc(self, user_id, key, path=""):
        if self._err:
            return
        if path:
            async with aiopen(path, "rb+") as doc:
                doc_bin = await doc.read()
        else:
            doc_bin = ""
        await self._db.users[bot_id].update_one(
            {"_id": user_id}, {"$set": {key: doc_bin}}, upsert=True
        )

    async def rss_update_all(self):
        if self._err:
            return
        for user_id in list(rss_dict.keys()):
            await self._db.rss[bot_id].replace_one(
                {"_id": user_id}, rss_dict[user_id], upsert=True
            )

    async def rss_update(self, user_id):
        if self._err:
            return
        await self._db.rss[bot_id].replace_one(
            {"_id": user_id}, rss_dict[user_id], upsert=True
        )

    async def rss_delete(self, user_id):
        if self._err:
            return
        await self._db.rss[bot_id].delete_one({"_id": user_id})

    async def add_incomplete_task(self, cid, link, tag):
        if self._err:
            return
        await self._db.tasks[bot_id].insert_one({"_id": link, "cid": cid, "tag": tag})

    async def rm_complete_task(self, link):
        if self._err:
            return
        await self._db.tasks[bot_id].delete_one({"_id": link})

    async def get_incomplete_tasks(self):
        notifier_dict = {}
        if self._err:
            return notifier_dict
        if await self._db.tasks[bot_id].find_one():
            # return a dict ==> {_id, cid, tag}
            rows = self._db.tasks[bot_id].find({})
            async for row in rows:
                if row["cid"] in list(notifier_dict):
                    if row["tag"] in list(notifier_dict[row["cid"]]):
                        notifier_dict[row["cid"]][row["tag"]].append(row["_id"])
                    else:
                        notifier_dict[row["cid"]][row["tag"]] = [row["_id"]]
                else:
                    notifier_dict[row["cid"]] = {row["tag"]: [row["_id"]]}
        await self._db.tasks[bot_id].drop()
        return notifier_dict  # return a dict ==> {cid: {tag: [_id, _id, ...]}}

    async def delete_user(self, user_id):
        if not self._err and user_data.pop(user_id, None):
            await self._db.users[bot_id].delete_one({"_id": user_id})

    async def trunc_table(self, name):
        if self._err:
            return
        await self._db[name][bot_id].drop()


if DATABASE_URL:
    try:
        bot_loop.run_until_complete(DbManager().db_load())
    except Exception as e:
        LOGGER.warning(e)
