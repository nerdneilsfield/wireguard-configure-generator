"""
Configuration file loaders for WireGuard mesh generator
"""

from typing import List, Dict, Any
from .utils import load_config
from .logger import get_logger


def load_nodes(file_path: str) -> List[Dict[str, Any]]:
    """
    Load nodes configuration from file.
    
    Args:
        file_path: Path to nodes configuration file
        
    Returns:
        List of node configurations
    """
    logger = get_logger()
    logger.info(f"加载节点配置文件: {file_path}")
    
    try:
        config = load_config(file_path)
        nodes = config.get('nodes', [])
        
        if not nodes:
            logger.warning("节点配置文件中没有找到节点定义")
            return []
        
        logger.info(f"成功加载 {len(nodes)} 个节点配置")
        
        # Validate basic node structure
        for i, node in enumerate(nodes):
            if 'name' not in node:
                logger.error(f"节点 {i} 缺少必需的 'name' 字段")
                raise ValueError(f"Node {i} missing required 'name' field")
            
            if 'role' not in node:
                logger.warning(f"节点 {node['name']} 缺少 'role' 字段，默认设为 'client'")
                node['role'] = 'client'
        
        return nodes
        
    except Exception as e:
        logger.error(f"加载节点配置失败: {e}")
        raise


def load_topology(file_path: str) -> List[Dict[str, Any]]:
    """
    Load topology configuration from file.
    
    Args:
        file_path: Path to topology configuration file
        
    Returns:
        List of peer connections
    """
    logger = get_logger()
    logger.info(f"加载拓扑配置文件: {file_path}")
    
    try:
        config = load_config(file_path)
        peers = config.get('peers', [])
        
        if not peers:
            logger.warning("拓扑配置文件中没有找到对等连接定义")
            return []
        
        logger.info(f"成功加载 {len(peers)} 个对等连接配置")
        
        # Validate basic peer structure
        for i, peer in enumerate(peers):
            required_fields = ['from', 'to']
            for field in required_fields:
                if field not in peer:
                    logger.error(f"对等连接 {i} 缺少必需的 '{field}' 字段")
                    raise ValueError(f"Peer {i} missing required '{field}' field")
        
        return peers
        
    except Exception as e:
        logger.error(f"加载拓扑配置失败: {e}")
        raise


def validate_configuration(nodes: List[Dict[str, Any]], peers: List[Dict[str, Any]]) -> bool:
    """
    Validate that the configuration is consistent.
    
    Args:
        nodes: List of node configurations
        peers: List of peer connections
        
    Returns:
        True if configuration is valid
    """
    logger = get_logger()
    logger.info("验证配置文件一致性")
    
    # Get all node names
    node_names = {node['name'] for node in nodes}
    
    # Check that all peer references exist
    for i, peer in enumerate(peers):
        from_node = peer['from']
        to_node = peer['to']
        
        if from_node not in node_names:
            logger.error(f"对等连接 {i} 引用了不存在的节点: {from_node}")
            return False
        
        if to_node not in node_names:
            logger.error(f"对等连接 {i} 引用了不存在的节点: {to_node}")
            return False
    
    logger.info("配置文件结构验证通过")
    return True
