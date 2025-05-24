# builder.py
from typing import List, Dict, Any
from wg_mesh_gen.loader import load_nodes, load_topology
from wg_mesh_gen.storage import init_keystore, load_key, save_key
from wg_mesh_gen.crypto import gen_keypair

def build_peer_configs(nodes_path: str,
                       topology_path: str,
                       db_url: str = 'sqlite:///wg_keys.db') -> Dict[str, List[Dict[str, Any]]]:
    """
    Construct peer configurations mapping each node to its list of peers.
    Uses 'endpoint' field in topology to choose the correct endpoint by name.
    """
    # Load raw configs
    nodes = load_nodes(nodes_path)
    peers = load_topology(topology_path)
    session = init_keystore(db_url)

    # Build lookup for nodes and keys
    node_map = {n['name']: n for n in nodes}
    key_map = {}
    for name in node_map:
        kp = load_key(session, name)
        if not kp:
            # Auto-generate keypair if missing
            private, public, psk = gen_keypair()
            save_key(session, name, private, public, psk)
            kp = load_key(session, name)
            print(f"Auto-generated keys for {name}")
        key_map[name] = kp

    # Prepare container
    peer_configs: Dict[str, List[Dict[str, Any]]] = {n: [] for n in node_map}

    # Iterate topology
    for rel in peers:
        src = rel['from']
        dst = rel['to']
        ep_name = rel['endpoint']
        allowed_ips = rel['allowed_ips']

        # Find dst endpoint entry by name
        dst_node = node_map[dst]
        ep_entry = next((e for e in dst_node['endpoints'] if e['name']==ep_name), None)
        if not ep_entry:
            raise ValueError(f"Endpoint '{ep_name}' not found for node '{dst}'")

        peer_configs[src].append({
            'peer_name': dst,
            'endpoint_name': ep_name,
            'public_key': key_map[dst].public_key,
            'psk': key_map[dst].psk,
            'endpoint': ep_entry['endpoint'],
            'allowed_ips': allowed_ips,
            'keepalive': rel.get('keepalive', 25)
        })

    return peer_configs
