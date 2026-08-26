import os
import asyncio
from typing import Dict, List, Optional
from pyrogram import Client
from bot.config import Config

class MultiBotManager:
    """Manage multiple bot instances"""
    
    def __init__(self):
        self.bots = {}
        self.bot_configs = {}
        self.active_bots = 0
        
    async def add_bot(
        self,
        bot_token: str,
        api_id: int,
        api_hash: str,
        bot_name: str = ""
    ) -> bool:
        """Add new bot instance"""
        try:
            # Generate bot ID
            bot_id = f"bot_{len(self.bots) + 1}"
            
            # Create bot client
            bot = Client(
                bot_id,
                api_id=api_id,
                api_hash=api_hash,
                bot_token=bot_token
            )
            
            # Store bot info
            self.bot_configs[bot_id] = {
                'token': bot_token,
                'api_id': api_id,
                'api_hash': api_hash,
                'name': bot_name
            }
            
            self.bots[bot_id] = bot
            self.active_bots += 1
            
            return True
            
        except Exception as e:
            return False
            
    async def start_bot(self, bot_id: str) -> bool:
        """Start specific bot"""
        if bot_id in self.bots:
            await self.bots[bot_id].start()
            return True
        return False
        
    async def stop_bot(self, bot_id: str) -> bool:
        """Stop specific bot"""
        if bot_id in self.bots:
            await self.bots[bot_id].stop()
            return True
        return False
        
    async def start_all_bots(self):
        """Start all bots"""
        for bot_id, bot in self.bots.items():
            await bot.start()
            
    async def stop_all_bots(self):
        """Stop all bots"""
        for bot_id, bot in self.bots.items():
            await bot.stop()
            
    async def remove_bot(self, bot_id: str) -> bool:
        """Remove bot instance"""
        if bot_id in self.bots:
            await self.stop_bot(bot_id)
            del self.bots[bot_id]
            del self.bot_configs[bot_id]
            self.active_bots -= 1
            return True
        return False
        
    async def get_bot(self, bot_id: str) -> Optional[Client]:
        """Get bot instance"""
        return self.bots.get(bot_id)
        
    async def get_all_bots(self) -> Dict:
        """Get all bot instances"""
        return self.bots
        
    async def get_bot_info(self, bot_id: str) -> Dict:
        """Get bot information"""
        bot = self.bots.get(bot_id)
        if bot:
            me = await bot.get_me()
            return {
                'id': bot_id,
                'username': me.username,
                'name': me.first_name,
                'active': True
            }
        return {}
        
    async def get_status(self) -> Dict:
        """Get multi-bot system status"""
        return {
            'total_bots': len(self.bots),
            'active_bots': self.active_bots,
            'max_bots': 10,
            'bots': [
                await self.get_bot_info(bot_id) 
                for bot_id in self.bots
            ]
        }
        
    async def broadcast_to_all(self, message: str) -> Dict:
        """Broadcast message to all bots"""
        results = {'sent': 0, 'failed': 0}
        
        for bot_id, bot in self.bots.items():
            try:
                me = await bot.get_me()
                # Send to bot's admin
                await bot.send_message(Config.OWNER_ID, message)
                results['sent'] += 1
            except:
                results['failed'] += 1
                
        return results

# Create instance
multi_bot = MultiBotManager()
