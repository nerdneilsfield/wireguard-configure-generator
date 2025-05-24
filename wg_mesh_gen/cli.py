import os
import sys
import click
from wg_mesh_gen.loader import load_nodes, load_topology
from wg_mesh_gen.utils import ensure_dir, load_json
from wg_mesh_gen.render import render_all
from wg_mesh_gen.storage import init_keystore, save_key, load_key
from wg_mesh_gen.crypto import gen_private_key, gen_public_key, gen_psk
from wg_mesh_gen.visualizer import visualize
from wg_mesh_gen.smart_builder import build_smart_peer_configs, generate_route_script


@click.group()
@click.option('--nodes-file', '-n', default=None,
              help='Path to nodes.json configuration file')
@click.option('--topo-file', '-t', default=None,
              help='Path to topology.json configuration file')
@click.option('--template-dir', '-T', default=None,
              help='Jinja2 templates directory (default: project templates)')
@click.option('--output-dir', '-o', default='out', help='Output directory for generated files')
@click.option('--db', '-d', default='wg_keys.db', help='SQLite DB file name or URL')
@click.pass_context
def cli(ctx, nodes_file, topo_file, template_dir, output_dir, db):
    """
    WireGuard 配置生成器 CLI
    """
    # Determine project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Default config dir is project/config
    config_dir = os.path.join(project_root, 'config')
    # Default templates dir
    default_template = os.path.join(os.path.dirname(__file__), 'templates')

    # Build db_url
    if db.startswith('sqlite://') or db.startswith('postgresql://'):
        db_url = db
    else:
        # treat as filename under project root
        db_path = os.path.abspath(db)
        db_url = f'sqlite:///{db_path}'

    # Resolve nodes and topo files
    nodes_path = nodes_file or os.path.join(config_dir, 'nodes.json')
    topo_path = topo_file or os.path.join(config_dir, 'topology.json')
    tmpl_dir = template_dir or default_template

    # Store in context
    ctx.ensure_object(dict)
    ctx.obj.update({
        'nodes_path': nodes_path,
        'topo_path': topo_path,
        'template_dir': tmpl_dir,
        'output_dir': output_dir,
        'db_url': db_url
    })


@cli.command('valid')
@click.pass_context
def validate(ctx):
    """
    校验 JSON 配置文件的基本结构
    """
    try:
        nodes = load_json(ctx.obj['nodes_path'])
        peers = load_json(ctx.obj['topo_path'])
        if 'nodes' not in nodes:
            raise click.ClickException("Missing 'nodes' in nodes.json")
        if 'peers' not in peers:
            raise click.ClickException("Missing 'peers' in topology.json")
        click.echo(click.style('Configuration validation passed.', fg='green'))
    except Exception as e:
        click.echo(click.style(f'Validation error: {e}', fg='red'))
        sys.exit(1)


@cli.command('gen')
@click.option('--nodes-file', '-n', default=None, help='Override nodes file path')
@click.option('--topo-file', '-t', default=None, help='Override topology file path')
@click.option('--output-dir', '-o', default=None, help='Override output directory')
@click.pass_context
def generate(ctx, nodes_file, topo_file, output_dir):
    """
    根据配置生成 WireGuard 配置文件和启动脚本
    """
    # Use override files if provided, otherwise use context
    nodes_path = nodes_file or ctx.obj['nodes_path']
    topo_path = topo_file or ctx.obj['topo_path']
    output_path = output_dir or ctx.obj['output_dir']

    ensure_dir(output_path)
    render_all(
        nodes_path=nodes_path,
        topology_path=topo_path,
        template_dir=ctx.obj['template_dir'],
        output_dir=output_path,
        db_url=ctx.obj['db_url']
    )


@cli.command('update')
@click.option('--force', '-f', is_flag=True, default=False, help='Force regenerate keys even if they exist')
@click.option('--nodes-file', '-n', default=None, help='Override nodes file path')
@click.pass_context
def update_keys(ctx, force, nodes_file):
     """
     为节点生成或更新 WireGuard 密钥对
     """
     nodes_path = nodes_file or ctx.obj['nodes_path']
     nodes = load_nodes(nodes_path)
     session = init_keystore(ctx.obj['db_url'])
     for node in nodes:
         name = node['name']
         kp = load_key(session, name)
         if kp and not force:
             click.echo(f"KeyPair exists for {name}, skipping.")
             continue
         if kp and force:
             click.echo(f"Force regenerating KeyPair for {name}.")
         private_key = gen_private_key()
         public_key = gen_public_key(private_key)
         psk = gen_psk()
         save_key(session, name, private_key, public_key, psk)
         click.echo(click.style(f'Generated keys for {name}', fg='green'))


@cli.command('smart-gen')
@click.option('--nodes-file', '-n', default=None, help='Override nodes file path')
@click.option('--topo-file', '-t', default=None, help='Override topology file path')
@click.option('--output-dir', '-o', default=None, help='Override output directory')
@click.option('--enable-multipath/--disable-multipath', default=True, help='Enable multipath routing')
@click.pass_context
def smart_generate(ctx, nodes_file, topo_file, output_dir, enable_multipath):
    """
    智能生成 WireGuard 配置，支持多路径和路由优化
    """
    from jinja2 import Environment, FileSystemLoader
    from tqdm import tqdm

    # Use override files if provided, otherwise use context
    nodes_path = nodes_file or ctx.obj['nodes_path']
    topo_path = topo_file or ctx.obj['topo_path']
    output_path = output_dir or ctx.obj['output_dir']

    ensure_dir(output_path)

    # Load nodes and build smart peer configs
    nodes = load_nodes(nodes_path)
    peer_configs = build_smart_peer_configs(nodes_path, topo_path, ctx.obj['db_url'], enable_multipath)

    # Setup Jinja2 environment
    env = Environment(loader=FileSystemLoader(ctx.obj['template_dir']), trim_blocks=True, lstrip_blocks=True)
    iface_t = env.get_template('interface.conf.j2')
    script_t = env.get_template('wg-quick.sh.j2')

    session = init_keystore(ctx.obj['db_url'])

    for node in tqdm(nodes, desc='Generating smart configs'):
        name = node['name']

        # Get or generate keypair
        kp = load_key(session, name)
        if not kp:
            private_key = gen_private_key()
            public_key = gen_public_key(private_key)
            psk = gen_psk()
            save_key(session, name, private_key, public_key, psk)
            kp = load_key(session, name)

        # Render .conf
        conf = iface_t.render(node=node, key={'private_key': kp.private_key}, peers=peer_configs.get(name, []))
        with open(os.path.join(output_path, f"{name}.conf"), 'w') as f:
            f.write(conf)

        # Render .sh
        script = script_t.render(node=node, out_dir=output_path)
        sh_path = os.path.join(output_path, f"{name}.sh")
        with open(sh_path, 'w') as f:
            f.write(script)
        os.chmod(sh_path, 0o755)

        # Generate route optimization script
        if enable_multipath:
            route_script = generate_route_script(name, peer_configs.get(name, []))
            route_path = os.path.join(output_path, f"{name}_route_optimizer.sh")
            with open(route_path, 'w') as f:
                f.write(route_script)
            os.chmod(route_path, 0o755)

    click.echo(click.style('Smart configs generated with route optimization!', fg='green'))


@cli.command('vis')
@click.option('--layout', '-l', default='spring', help='Graph layout: spring, shell, circular, kamada_kawai')
@click.option('--output-image', '-i', default=None, help='Output file path (default: output_dir/topology.png)')
@click.option('--nodes-file', '-n', default=None, help='Override nodes file path')
@click.option('--topo-file', '-t', default=None, help='Override topology file path')
@click.pass_context
def visualize_cmd(ctx, layout, output_image, nodes_file, topo_file):
    """
    绘制并输出网络拓扑可视化图
    """
    # Use override files if provided, otherwise use context
    nodes_path = nodes_file or ctx.obj['nodes_path']
    topo_path = topo_file or ctx.obj['topo_path']

    # Set default output image if not provided
    if output_image is None:
        output_image = os.path.join(ctx.obj['output_dir'], 'topology.png')

    output_dir = os.path.dirname(output_image)
    ensure_dir(output_dir)

    visualize(nodes_path=nodes_path,
              topology_path=topo_path,
              output_path=output_image,
              layout=layout)
    click.echo(click.style(f'Topology image saved to {output_image}', fg='green'))


if __name__ == '__main__':
    cli()
