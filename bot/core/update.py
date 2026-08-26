import os
import sys
import git
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from bot.config import Config

class UpdateSystem:
    """Advanced update management system"""
    
    def __init__(self):
        self.repo_path = Path(__file__).parent.parent.parent
        self.backup_dir = self.repo_path / "data" / "backups" / "updates"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    async def check_for_updates(self) -> dict:
        """Check for available updates"""
        try:
            repo = git.Repo(self.repo_path)
            
            # Fetch updates
            repo.git.fetch('upstream', Config.UPSTREAM_BRANCH)
            
            # Get current and latest commits
            current_commit = repo.head.commit
            latest_commit = repo.refs[f'upstream/{Config.UPSTREAM_BRANCH}'].commit
            
            # Check if updates available
            if current_commit != latest_commit:
                # Get commit difference
                commits = list(repo.iter_commits(
                    f'{current_commit}..{latest_commit}'
                ))
                
                return {
                    'update_available': True,
                    'current_commit': str(current_commit)[:7],
                    'latest_commit': str(latest_commit)[:7],
                    'commits': len(commits),
                    'changes': [
                        {
                            'hash': str(c)[:7],
                            'message': c.message.strip(),
                            'author': str(c.author),
                            'date': datetime.fromtimestamp(c.committed_date)
                        }
                        for c in commits[:10]
                    ]
                }
            else:
                return {
                    'update_available': False,
                    'current_commit': str(current_commit)[:7],
                    'latest_commit': str(latest_commit)[:7]
                }
                
        except Exception as e:
            return {'error': str(e)}
            
    async def create_backup(self) -> str:
        """Create backup before update"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{timestamp}"
            
            # Copy important files
            shutil.copytree(self.repo_path / "bot", backup_path / "bot")
            shutil.copytree(self.repo_path / "config", backup_path / "config")
            
            # Copy .env
            env_file = self.repo_path / ".env"
            if env_file.exists():
                shutil.copy2(env_file, backup_path)
                
            return str(backup_path)
            
        except Exception as e:
            return str(e)
            
    async def apply_update(self) -> dict:
        """Apply update"""
        try:
            # Create backup first
            backup_path = await self.create_backup()
            
            repo = git.Repo(self.repo_path)
            
            # Pull updates
            repo.git.pull('upstream', Config.UPSTREAM_BRANCH)
            
            # Install new dependencies
            process = await asyncio.create_subprocess_shell(
                "pip install -r requirements.txt --quiet",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            
            return {
                'success': True,
                'backup_path': backup_path,
                'message': 'Update applied successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    async def rollback(self, backup_path: str) -> bool:
        """Rollback to previous version"""
        try:
            # Restore backup
            if os.path.exists(backup_path):
                shutil.rmtree(self.repo_path / "bot")
                shutil.copytree(backup_path / "bot", self.repo_path / "bot")
                
                shutil.rmtree(self.repo_path / "config")
                shutil.copytree(backup_path / "config", self.repo_path / "config")
                
                return True
        except:
            pass
        return False
        
    async def get_update_history(self) -> list:
        """Get update history"""
        history = []
        
        if self.backup_dir.exists():
            for backup in self.backup_dir.iterdir():
                if backup.is_dir():
                    history.append({
                        'name': backup.name,
                        'created': datetime.fromtimestamp(backup.stat().st_mtime),
                        'size': sum(f.stat().st_size for f in backup.rglob('*'))
                    })
                    
        return sorted(history, key=lambda x: x['created'], reverse=True)
        
    async def cleanup_old_backups(self, keep_last: int = 5):
        """Clean up old backups"""
        history = await self.get_update_history()
        
        for backup in history[keep_last:]:
            backup_path = self.backup_dir / backup['name']
            if backup_path.exists():
                shutil.rmtree(backup_path)

# Create instance
update_system = UpdateSystem()
