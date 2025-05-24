from tqdm import tqdm
import os
from typing import Tuple
from jinja2 import Environment, FileSystemLoader
from wg_mesh_gen.storage import init_keystore, save_key, load_key
from wg_mesh_gen.loader import load_nodes
from wg_mesh_gen.builder import build_peer_configs
from wg_mesh_gen.crypto import gen_keypair


def generate_keypair(name: str, session) -> Tuple[str, str, str]:
    """
    生成 WireGuard 密钥对并保存到 keystore 与文件。
    """
    privkey, pubkey, psk = gen_keypair()

    # 保存到数据库
    save_key(session, name, privkey, pubkey, psk)

    # 写入本地文件以备参考



def render_all(nodes_path: str,
               topology_path: str,
               output_dir: str,
               template_dir: str = os.path.join(os.path.dirname(__file__), 'templates'),
               db_url: str = 'sqlite:///wg_keys.db') -> None:
    """
    Generate and render all WireGuard configs and scripts.
    """
    nodes = load_nodes(nodes_path)
    peer_configs = build_peer_configs(nodes_path, topology_path, db_url)

    env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
    iface_t = env.get_template('interface.conf.j2')
    script_t = env.get_template('wg-quick.sh.j2')

    os.makedirs(output_dir, exist_ok=True)
    session = init_keystore(db_url)

    for node in tqdm(nodes, desc='Render configs'):
        name = node['name']
        # keypair auto-generated if missing
        kp = load_key(session, name)
        if not kp:
            private, public, psk = gen_keypair()
            save_key(session, name, private, public, psk)
            kp = load_key(session, name)

        # Render .conf
        conf = iface_t.render(node=node, key={'private_key': kp.private_key}, peers=peer_configs.get(name, []))
        with open(os.path.join(output_dir, f"{name}.conf"), 'w') as f:
            f.write(conf)

        # Render .sh
        script = script_t.render(node=node, out_dir=output_dir)
        sh_path = os.path.join(output_dir, f"{name}.sh")
        with open(sh_path, 'w') as f:
            f.write(script)
        os.chmod(sh_path, 0o755)

    print("All configs generated.")
