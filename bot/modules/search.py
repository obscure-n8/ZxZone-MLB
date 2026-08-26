import os
import json
import asyncio
import aiohttp
from typing import List, Dict, Optional
from bot.config import Config

class TorrentSearch:
    def __init__(self):
        self.api_link = Config.SEARCH_API_LINK
        self.plugins = []
        self.search_cache = {}
        self.cache_timeout = 300  # 5 minutes
        
    async def search_torrents(
        self,
        query: str,
        limit: int = 10,
        category: str = "all"
    ) -> List[Dict]:
        """Search torrents from multiple sources"""
        results = []
        
        # Check cache
        cache_key = f"{query}_{limit}_{category}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
            
        # Search from API
        if self.api_link:
            api_results = await self.search_api(query, limit)
            results.extend(api_results)
            
        # Search from plugins
        plugin_results = await self.search_plugins(query, limit)
        results.extend(plugin_results)
        
        # Remove duplicates
        unique_results = self.remove_duplicates(results)
        
        # Limit results
        unique_results = unique_results[:limit]
        
        # Cache results
        self.search_cache[cache_key] = unique_results
        
        return unique_results
        
    async def search_api(self, query: str, limit: int) -> List[Dict]:
        """Search using API"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': query,
                    'limit': limit
                }
                async with session.get(self.api_link, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.parse_api_results(data)
        except:
            pass
        return []
        
    async def search_plugins(self, query: str, limit: int) -> List[Dict]:
        """Search using qBittorrent plugins"""
        results = []
        
        # This would integrate with qBittorrent search
        # For now, return empty
        return results
        
    def parse_api_results(self, data: Dict) -> List[Dict]:
        """Parse API results"""
        results = []
        
        if 'data' in data:
            for item in data['data']:
                result = {
                    'name': item.get('name', ''),
                    'size': item.get('size', ''),
                    'seeders': item.get('seeders', 0),
                    'leechers': item.get('leechers', 0),
                    'magnet': item.get('magnet', ''),
                    'category': item.get('category', ''),
                    'uploaded': item.get('uploaded', '')
                }
                results.append(result)
                
        return results
        
    def remove_duplicates(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate results"""
        seen = set()
        unique = []
        
        for result in results:
            key = result.get('magnet', result.get('name', ''))
            if key not in seen:
                seen.add(key)
                unique.append(result)
                
        return unique
        
    async def get_torrent_info(self, magnet_link: str) -> Dict:
        """Get torrent information"""
        try:
            import libtorrent as lt
            session = lt.session()
            params = lt.parse_magnet_uri(magnet_link)
            handle = session.add_torrent(params)
            
            # Wait for metadata
            timeout = 30
            start_time = asyncio.get_event_loop().time()
            
            while not handle.has_metadata():
                if asyncio.get_event_loop().time() - start_time > timeout:
                    break
                await asyncio.sleep(1)
                
            if handle.has_metadata():
                torrent_info = handle.get_torrent_info()
                return {
                    'name': torrent_info.name(),
                    'size': torrent_info.total_size(),
                    'files': torrent_info.num_files(),
                    'private': torrent_info.priv()
                }
                
        except:
            pass
            
        return {}
        
    async def search_suggestions(self, query: str) -> List[str]:
        """Get search suggestions"""
        suggestions = []
        
        # This would integrate with autocomplete API
        # For now, return common suggestions
        common_suffixes = ['1080p', '720p', '2160p', 'x264', 'x265', 'HEVC']
        for suffix in common_suffixes:
            suggestions.append(f"{query} {suffix}")
            
        return suggestions

# Create instance
torrent_search = TorrentSearch()
