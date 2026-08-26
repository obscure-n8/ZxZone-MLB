import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from bot.database.users import users_db

class PremiumSystem:
    def __init__(self):
        self.plans = {
            'weekly': {
                'name': 'Weekly',
                'duration': 7 * 24 * 3600,
                'price': 49,
                'features': ['unlimited_tasks', 'priority_queue', 'no_ads']
            },
            'monthly': {
                'name': 'Monthly',
                'duration': 30 * 24 * 3600,
                'price': 149,
                'features': ['unlimited_tasks', 'priority_queue', 'no_ads', 'speed_boost']
            },
            'yearly': {
                'name': 'Yearly',
                'duration': 365 * 24 * 3600,
                'price': 999,
                'features': ['unlimited_tasks', 'priority_queue', 'no_ads', 'speed_boost', 'vip_support']
            }
        }
        
    async def activate_premium(
        self,
        user_id: int,
        plan: str = 'monthly'
    ) -> bool:
        """Activate premium for user"""
        if plan not in self.plans:
            return False
            
        plan_info = self.plans[plan]
        expiry = time.time() + plan_info['duration']
        
        await users_db.update_user(user_id, {
            'is_premium': True,
            'premium_plan': plan,
            'premium_expiry': expiry,
            'premium_features': plan_info['features']
        })
        
        return True
        
    async def deactivate_premium(self, user_id: int) -> bool:
        """Deactivate premium for user"""
        await users_db.update_user(user_id, {
            'is_premium': False,
            'premium_plan': None,
            'premium_expiry': None,
            'premium_features': []
        })
        return True
        
    async def check_premium(self, user_id: int) -> bool:
        """Check if user has active premium"""
        user = await users_db.get_user(user_id)
        if not user:
            return False
            
        if not user.get('is_premium', False):
            return False
            
        # Check expiry
        expiry = user.get('premium_expiry', 0)
        if expiry < time.time():
            await self.deactivate_premium(user_id)
            return False
            
        return True
        
    async def get_premium_info(self, user_id: int) -> Dict:
        """Get premium information for user"""
        user = await users_db.get_user(user_id)
        if not user:
            return {}
            
        return {
            'is_premium': user.get('is_premium', False),
            'plan': user.get('premium_plan'),
            'expiry': user.get('premium_expiry'),
            'features': user.get('premium_features', []),
            'days_left': max(0, (user.get('premium_expiry', 0) - time.time()) // (24 * 3600))
        }
        
    async def get_plans(self) -> Dict:
        """Get available premium plans"""
        return self.plans
        
    async def has_feature(self, user_id: int, feature: str) -> bool:
        """Check if user has specific premium feature"""
        user = await users_db.get_user(user_id)
        if not user:
            return False
            
        features = user.get('premium_features', [])
        return feature in features
        
    async def get_premium_users(self) -> List[Dict]:
        """Get all premium users"""
        users = await users_db.get_all_users()
        premium_users = []
        
        for user in users:
            if user.get('is_premium', False):
                premium_users.append({
                    'user_id': user['user_id'],
                    'first_name': user.get('first_name', ''),
                    'plan': user.get('premium_plan'),
                    'expiry': user.get('premium_expiry')
                })
                
        return premium_users
        
    async def extend_premium(self, user_id: int, days: int) -> bool:
        """Extend premium duration"""
        user = await users_db.get_user(user_id)
        if not user:
            return False
            
        current_expiry = user.get('premium_expiry', time.time())
        new_expiry = current_expiry + (days * 24 * 3600)
        
        await users_db.update_user(user_id, {
            'premium_expiry': new_expiry
        })
        
        return True
        
    async def apply_premium_benefits(self, user_id: int) -> Dict:
        """Apply premium benefits to user"""
        benefits = {}
        
        if await self.check_premium(user_id):
            if await self.has_feature(user_id, 'unlimited_tasks'):
                benefits['max_tasks'] = 0  # Unlimited
            else:
                benefits['max_tasks'] = 3
                
            if await self.has_feature(user_id, 'priority_queue'):
                benefits['priority'] = True
                
            if await self.has_feature(user_id, 'speed_boost'):
                benefits['speed_limit'] = 0  # Unlimited speed
                
        return benefits

# Create instance
premium_system = PremiumSystem()
