"""
Simple key storage implementation using JSON file
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import fcntl
from .logger import get_logger


class SimpleKeyStorage:
    """Simple JSON-based key storage"""
    
    def __init__(self, storage_path: str = "wg_keys.json"):
        """
        Initialize simple key storage.
        
        Args:
            storage_path: Path to JSON storage file
        """
        self.logger = get_logger()
        self.storage_path = Path(storage_path)
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self):
        """Ensure storage file exists"""
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_data({})
            self.logger.info(f"创建密钥存储文件: {self.storage_path}")
    
    def _load_data(self) -> Dict[str, Dict[str, str]]:
        """Load data from JSON file with file locking"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(f"无法读取存储文件: {e}，返回空数据")
            return {}
        except UnicodeDecodeError as e:
            self.logger.error(f"存储文件损坏: {e}")
            # Try to backup the corrupted file and create a new one
            backup_path = self.storage_path.with_suffix('.corrupted')
            try:
                self.storage_path.rename(backup_path)
                self.logger.warning(f"已将损坏文件备份至: {backup_path}")
            except Exception:
                pass
            # Return empty data and let the system recreate the file
            return {}
    
    def _save_data(self, data: Dict[str, Dict[str, str]]):
        """Save data to JSON file with file locking"""
        try:
            # Write to temporary file first
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                # Acquire exclusive lock for writing
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Atomic rename
            temp_path.replace(self.storage_path)
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")
            raise
    
    def store_keypair(self, node_name: str, private_key: str, public_key: str) -> bool:
        """
        Store a keypair for a node.
        
        Args:
            node_name: Name of the node
            private_key: Private key
            public_key: Public key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = self._load_data()
            data[node_name] = {
                'private_key': private_key,
                'public_key': public_key,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            self._save_data(data)
            self.logger.info(f"存储节点密钥对: {node_name}")
            return True
        except Exception as e:
            self.logger.error(f"存储密钥对失败: {e}")
            return False
    
    def get_keypair(self, node_name: str) -> Optional[Tuple[str, str]]:
        """
        Get keypair for a node.
        
        Args:
            node_name: Name of the node
            
        Returns:
            Tuple of (private_key, public_key) or None if not found
        """
        try:
            data = self._load_data()
            if node_name in data:
                node_data = data[node_name]
                return (node_data['private_key'], node_data['public_key'])
            return None
        except Exception as e:
            self.logger.error(f"获取密钥对失败: {e}")
            return None
    
    def list_keys(self) -> List[Dict[str, str]]:
        """
        List all stored keys.
        
        Returns:
            List of dictionaries containing key information
        """
        try:
            data = self._load_data()
            result = []
            for node_name, node_data in data.items():
                result.append({
                    'node_name': node_name,
                    'public_key': node_data['public_key'],
                    'created_at': node_data.get('created_at', 'Unknown'),
                    'updated_at': node_data.get('updated_at', node_data.get('created_at', 'Unknown'))
                })
            return result
        except Exception as e:
            self.logger.error(f"列出密钥失败: {e}")
            return []
    
    def delete_keypair(self, node_name: str) -> bool:
        """
        Delete keypair for a node.
        
        Args:
            node_name: Name of the node
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = self._load_data()
            if node_name in data:
                del data[node_name]
                self._save_data(data)
                self.logger.info(f"删除节点密钥对: {node_name}")
                return True
            else:
                self.logger.warning(f"节点不存在: {node_name}")
                return False
        except Exception as e:
            self.logger.error(f"删除密钥对失败: {e}")
            return False
    
    def has_keypair(self, node_name: str) -> bool:
        """
        Check if a node has a stored keypair.
        
        Args:
            node_name: Name of the node
            
        Returns:
            True if keypair exists, False otherwise
        """
        try:
            data = self._load_data()
            return node_name in data
        except Exception:
            return False
    
    def close(self):
        """Close storage (no-op for JSON storage)"""
        pass