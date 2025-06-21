"""
WireGuard configuration builder
"""

from typing import List, Dict, Any, Optional
from .validator import validate_and_load_config
from .crypto import generate_keypair, generate_preshared_key
from .simple_storage import SimpleKeyStorage
from .logger import get_logger
from .utils import mask_sensitive_info


def build_peer_configs(nodes_file: str,
                      topology_file: str,
                      output_dir: str = "out",
                      auto_generate_keys: bool = True,
                      db_path: str = "wg_keys.json") -> Dict[str, Any]:
    """
    Build WireGuard peer configurations.

    Args:
        nodes_file: Path to nodes configuration file
        topology_file: Path to topology configuration file
        output_dir: Output directory for configuration files
        auto_generate_keys: Whether to auto-generate missing keys
        db_path: Path to key storage database

    Returns:
        Dictionary containing build results
    """
    logger = get_logger()
    logger.info("开始构建WireGuard配置")

    # Load and validate configurations in one step
    nodes, peers = validate_and_load_config(nodes_file, topology_file)

    # Initialize key storage
    key_storage = SimpleKeyStorage(db_path)
    try:
        # Generate or load keys for all nodes
        for node in nodes:
            node_name = node['name']

            # Check if keys already exist
            existing_keys = key_storage.get_keypair(node_name)

            if existing_keys:
                logger.debug(f"使用已存在的密钥对: {node_name}")
                private_key, public_key = existing_keys
                node['private_key'] = private_key
                node['public_key'] = public_key
            elif auto_generate_keys:
                logger.info(f"为节点 {node_name} 生成新密钥对")
                private_key, public_key = generate_keypair()

                # Store keys
                key_storage.store_keypair(node_name, private_key, public_key)

                node['private_key'] = private_key
                node['public_key'] = public_key

                logger.debug(f"节点 {node_name} 密钥生成完成")
                logger.debug(f"  公钥: {mask_sensitive_info(public_key)}")
            else:
                logger.error(f"节点 {node_name} 缺少密钥且未启用自动生成")
                raise ValueError(f"Node {node_name} missing keys and auto-generation disabled")

        # Build peer configurations
        configs = {}

        for node in nodes:
            node_name = node['name']
            config = _build_node_config(node, nodes, peers)
            configs[node_name] = config

            logger.debug(f"节点 {node_name} 配置构建完成")

        logger.info(f"成功构建 {len(configs)} 个节点配置")

        return {
            'configs': configs,
            'nodes': nodes,
            'peers': peers,
            'output_dir': output_dir
        }
    finally:
        key_storage.close()


def _build_node_config(node: Dict[str, Any],
                      all_nodes: List[Dict[str, Any]],
                      peers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build configuration for a single node.

    Args:
        node: Node configuration
        all_nodes: All node configurations
        peers: All peer connections

    Returns:
        Node configuration with peer information
    """
    node_name = node['name']

    # Create node lookup
    node_lookup = {n['name']: n for n in all_nodes}

    # Find all peers for this node
    node_peers = []

    for peer in peers:
        if peer['from'] == node_name:
            # This node connects to peer['to']
            target_node = node_lookup[peer['to']]
            peer_config = {
                'name': target_node['name'],
                'public_key': target_node['public_key'],
                'endpoint': peer.get('endpoint'),
                'allowed_ips': peer.get('allowed_ips', []),
                'persistent_keepalive': peer.get('persistent_keepalive')
            }
            node_peers.append(peer_config)

        elif peer['to'] == node_name:
            # peer['from'] connects to this node
            source_node = node_lookup[peer['from']]
            peer_config = {
                'name': source_node['name'],
                'public_key': source_node['public_key'],
                'endpoint': None,  # Incoming connection
                'allowed_ips': peer.get('allowed_ips', []),
                'persistent_keepalive': peer.get('persistent_keepalive')
            }
            node_peers.append(peer_config)

    # Build final configuration
    config = {
        'interface': {
            'private_key': node['private_key'],
            'address': node.get('wireguard_ip'),
            'listen_port': node.get('listen_port'),
            'dns': node.get('dns'),
            'mtu': node.get('mtu')
        },
        'peers': node_peers
    }

    return config
