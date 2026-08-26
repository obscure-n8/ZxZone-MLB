import motor.motor_asyncio
from bot.config import Config

class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(Config.DATABASE_URL)
        self.db = self.client["zxzone_mlb"]
        self.users = self.db["users"]
        self.tasks = self.db["tasks"]
        self.settings = self.db["settings"]
        self.thumbnails = self.db["thumbnails"]
        
    async def ping(self):
        """Check database connection"""
        try:
            await self.client.admin.command('ping')
            return True
        except:
            return False
            
    async def close(self):
        """Close database connection"""
        self.client.close()

# Create global database instance
db = Database()
