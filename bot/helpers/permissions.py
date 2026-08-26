from typing import Optional, List
from bot.config import Config
from bot.database.users import users_db

class PermissionSystem:
    """Advanced permission management system"""
    
    def __init__(self):
        self.permission_levels = {
            'owner': 5,      # Full access
            'sudo': 4,       # Almost full access
            'admin': 3,      # Admin access
            'premium': 2,    # Premium user
            'user': 1,       # Normal user
            'banned': 0      # Banned user
        }
        
        self.permissions = {
            'bsettings': ['owner', 'sudo'],
            'admin_panel': ['owner', 'sudo'],
            'aria2_settings': ['owner', 'sudo'],
            'qbit_settings': ['owner', 'sudo'],
            'user_management': ['owner', 'sudo', 'admin'],
            'broadcast': ['owner', 'sudo'],
            'backup': ['owner', 'sudo'],
            'logs': ['owner', 'sudo'],
            'update': ['owner', 'sudo'],
            'premium_give': ['owner', 'sudo'],
            'ban_user': ['owner', 'sudo', 'admin'],
            'mute_user': ['owner', 'sudo', 'admin'],
            'view_stats': ['owner', 'sudo', 'admin'],
            'delete_files': ['owner', 'sudo', 'admin'],
            'change_settings': ['owner', 'sudo'],
            'manage_sudo': ['owner'],
            'manage_admins': ['owner', 'sudo'],
        }
        
    async def get_user_level(self, user_id: int) -> str:
        """Get user permission level"""
        # Check owner
        if user_id == Config.OWNER_ID:
            return 'owner'
            
        # Check sudo
        if user_id in Config.SUDO_USERS:
            return 'sudo'
            
        # Check database
        user = await users_db.get_user(user_id)
        if not user:
            return 'user'
            
        if user.get('is_banned', False):
            return 'banned'
            
        if user.get('is_admin', False):
            return 'admin'
            
        if user.get('is_premium', False):
            return 'premium'
            
        return 'user'
        
    async def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has specific permission"""
        user_level = await self.get_user_level(user_id)
        
        if user_level == 'banned':
            return False
            
        allowed_levels = self.permissions.get(permission, [])
        
        if user_level == 'owner':
            return True  # Owner has all permissions
            
        if user_level == 'sudo' and permission != 'manage_sudo':
            return True  # Sudo has almost all permissions
            
        return user_level in allowed_levels
        
    async def is_owner(self, user_id: int) -> bool:
        """Check if user is owner"""
        return user_id == Config.OWNER_ID
        
    async def is_sudo(self, user_id: int) -> bool:
        """Check if user is sudo"""
        return user_id in Config.SUDO_USERS
        
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        level = await self.get_user_level(user_id)
        return level in ['owner', 'sudo', 'admin']
        
    async def can_manage_sudo(self, user_id: int) -> bool:
        """Check if user can manage sudo users"""
        return await self.is_owner(user_id)
        
    async def get_permission_info(self, user_id: int) -> dict:
        """Get user permission information"""
        level = await self.get_user_level(user_id)
        
        return {
            'user_id': user_id,
            'level': level,
            'level_number': self.permission_levels.get(level, 0),
            'is_owner': level == 'owner',
            'is_sudo': level == 'sudo',
            'is_admin': level in ['owner', 'sudo', 'admin'],
            'is_premium': level == 'premium',
            'is_banned': level == 'banned',
            'permissions': self.get_user_permissions(level)
        }
        
    def get_user_permissions(self, level: str) -> List[str]:
        """Get permissions for user level"""
        user_permissions = []
        
        for permission, allowed_levels in self.permissions.items():
            if level == 'owner':
                user_permissions.append(permission)
            elif level == 'sudo' and permission != 'manage_sudo':
                user_permissions.append(permission)
            elif level in allowed_levels:
                user_permissions.append(permission)
                
        return user_permissions

# Create instance
permission_system = PermissionSystem()
