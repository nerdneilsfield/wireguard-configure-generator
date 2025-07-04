"""
Command Line Interface for WireGuard Mesh Generator
"""

import click
import os
import sys
from pathlib import Path
from .logger import setup_logging, get_logger

# Debug: Uncomment to see what's happening
# print(f"DEBUG: cli.py loaded with sys.argv = {sys.argv}", file=sys.stderr)
from .loader import load_nodes, load_topology, validate_configuration
from .builder import build_peer_configs
from .render import ConfigRenderer
from .visualizer import visualize
from .simple_storage import SimpleKeyStorage
from .crypto import generate_keypair, generate_preshared_key


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--log-file', help='日志文件路径')
@click.option('--nodes-file', '-n', default='examples/nodes.yaml',
              help='节点配置文件路径')
@click.option('--topo-file', '-t', default='examples/topology.yaml',
              help='拓扑配置文件路径')
@click.option('--output-dir', '-o', default='out',
              help='输出目录')
@click.pass_context
def cli(ctx, verbose, log_file, nodes_file, topo_file, output_dir):
    """WireGuard Mesh Configuration Generator

    生成WireGuard网状网络配置的工具
    """
    # Setup logging
    setup_logging(verbose=verbose, log_file=log_file)

    # Store common options in context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['nodes_file'] = nodes_file
    ctx.obj['topo_file'] = topo_file
    ctx.obj['output_dir'] = output_dir


@cli.command()
@click.option('--auto-keys/--no-auto-keys', default=True,
              help='自动生成缺失的密钥')
@click.option('--db-path', default='wg_keys.db',
              help='密钥数据库路径')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--log-file', help='日志文件路径')
@click.option('--nodes-file', '-n', help='节点配置文件路径')
@click.option('--topo-file', '-t', help='拓扑配置文件路径')
@click.option('--output-dir', '-o', help='输出目录')
@click.option('--group-config', '-g', help='组网络配置文件路径')
@click.pass_context
def gen(ctx, auto_keys, db_path, verbose, log_file, nodes_file, topo_file, output_dir, group_config):
    """生成WireGuard配置文件"""
    # 使用子命令参数或回退到主命令参数
    verbose = verbose or ctx.obj.get('verbose', False)
    nodes_file = nodes_file or ctx.obj['nodes_file']
    topo_file = topo_file or ctx.obj['topo_file']
    output_dir = output_dir or ctx.obj['output_dir']

    # 设置日志
    if verbose or log_file:
        setup_logging(verbose=verbose, log_file=log_file)

    logger = get_logger()

    try:
        # Check if using group configuration
        if group_config:
            logger.info("使用组网络配置模式")
            logger.info(f"组配置文件: {group_config}")
            logger.info(f"输出目录: {output_dir}")
            
            if not os.path.exists(group_config):
                logger.error(f"组配置文件不存在: {group_config}")
                raise click.ClickException(f"Group config file not found: {group_config}")
            
            # Use group network builder
            from .group_network_builder import GroupNetworkBuilder
            
            builder = GroupNetworkBuilder(group_config)
            nodes, peers = builder.build()
            
            # Create temporary data structures
            nodes_data = {'nodes': nodes}
            topology_data = {'peers': peers}
            
            # Use existing builder with generated data
            from .builder import build_from_data
            build_result = build_from_data(
                nodes_data=nodes_data,
                topology_data=topology_data,
                output_dir=output_dir,
                auto_generate_keys=auto_keys,
                db_path=db_path
            )
        else:
            # Traditional mode
            logger.info("开始生成WireGuard配置")
            logger.info(f"节点文件: {nodes_file}")
            logger.info(f"拓扑文件: {topo_file}")
            logger.info(f"输出目录: {output_dir}")

            # Check if input files exist
            if not os.path.exists(nodes_file):
                logger.error(f"节点配置文件不存在: {nodes_file}")
                raise click.ClickException(f"Nodes file not found: {nodes_file}")

            if not os.path.exists(topo_file):
                logger.error(f"拓扑配置文件不存在: {topo_file}")
                raise click.ClickException(f"Topology file not found: {topo_file}")

            # Build configurations
            build_result = build_peer_configs(
                nodes_file=nodes_file,
                topology_file=topo_file,
                output_dir=output_dir,
                auto_generate_keys=auto_keys,
                db_path=db_path
            )

        # Render configurations
        renderer = ConfigRenderer()
        renderer.render_all(build_result)

        logger.info("WireGuard配置生成完成")
        click.echo(f"配置文件已生成到: {output_dir}")

    except Exception as e:
        logger.error(f"生成配置失败: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.option('--layout', '-l', default='auto',
              type=click.Choice(['auto', 'spring', 'circular', 'shell', 'hierarchical', 'kamada_kawai']),
              help='网络布局算法')
@click.option('--output', help='输出文件路径')
@click.option('--show-edge-labels/--no-edge-labels', default=None,
              help='是否显示边标签（默认自动决定）')
@click.option('--high-dpi/--low-dpi', default=True,
              help='是否使用高DPI输出')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--log-file', help='日志文件路径')
@click.option('--nodes-file', '-n', help='节点配置文件路径')
@click.option('--topo-file', '-t', help='拓扑配置文件路径')
@click.option('--output-dir', '-o', help='输出目录')
@click.option('--group-config', '-g', help='组网络配置文件路径')
@click.pass_context
def vis(ctx, layout, output, show_edge_labels, high_dpi, verbose, log_file, nodes_file, topo_file, output_dir, group_config):
    """生成网络拓扑可视化图"""
    # 使用子命令参数或回退到主命令参数
    verbose = verbose or ctx.obj.get('verbose', False)
    output_dir = output_dir or ctx.obj['output_dir']
    
    # Only get nodes_file/topo_file from context if not using group_config
    if not group_config:
        nodes_file = nodes_file or ctx.obj.get('nodes_file')
        topo_file = topo_file or ctx.obj.get('topo_file')

    # 设置日志
    if verbose or log_file:
        setup_logging(verbose=verbose, log_file=log_file)

    logger = get_logger()

    # 确定输出路径
    if output:
        output_path = output
    else:
        output_path = os.path.join(output_dir, 'topology.png')

    logger.info("开始生成网络拓扑可视化")
    logger.info(f"布局算法: {layout}")

    try:
        # Check if using group configuration
        if group_config:
            logger.info("使用组网络配置模式")
            
            if not os.path.exists(group_config):
                logger.error(f"组配置文件不存在: {group_config}")
                raise click.ClickException(f"Group config file not found: {group_config}")
            
            # Convert group config to nodes and topology
            from .group_network_builder import GroupNetworkBuilder
            import tempfile
            import json
            
            builder = GroupNetworkBuilder(group_config)
            nodes, peers = builder.build()
            
            # Create temporary files for visualization
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as nodes_tmp:
                json.dump({'nodes': nodes}, nodes_tmp)
                temp_nodes_file = nodes_tmp.name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as topo_tmp:
                json.dump({'peers': peers}, topo_tmp)
                temp_topo_file = topo_tmp.name
            
            # Use temporary files for visualization
            nodes_file = temp_nodes_file
            topo_file = temp_topo_file
        else:
            # Traditional mode - check if input files exist
            if not os.path.exists(nodes_file):
                logger.error(f"节点配置文件不存在: {nodes_file}")
                raise click.ClickException(f"Nodes file not found: {nodes_file}")

            if not os.path.exists(topo_file):
                logger.error(f"拓扑配置文件不存在: {topo_file}")
                raise click.ClickException(f"Topology file not found: {topo_file}")

        # Generate visualization
        from .visualizer import visualize as viz_func
        viz_func(
            nodes_path=nodes_file,
            topology_path=topo_file,
            output_path=output_path,
            layout=layout,
            show_edge_labels=show_edge_labels,
            high_dpi=high_dpi
        )

        logger.info("网络拓扑可视化生成完成")
        click.echo(f"拓扑图已保存到: {output_path}")
        
        # Clean up temporary files if using group config
        if group_config:
            try:
                os.unlink(temp_nodes_file)
                os.unlink(temp_topo_file)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"生成可视化失败: {e}")
        # Clean up temporary files on error
        if group_config and 'temp_nodes_file' in locals():
            try:
                os.unlink(temp_nodes_file)
                os.unlink(temp_topo_file)
            except Exception:
                pass
        raise click.ClickException(str(e))


@cli.command()
@click.option('--nodes-file', '-n', help='节点配置文件路径')
@click.option('--topo-file', '-t', help='拓扑配置文件路径')
@click.option('--group-config', '-g', help='组网络配置文件路径')
@click.option('--test-routes', is_flag=True, help='测试所有路由路径')
@click.option('--test-connectivity', is_flag=True, help='测试节点连通性')
@click.option('--duration', '-d', default=10, help='模拟持续时间（秒）')
@click.option('--failure-node', help='模拟指定节点故障')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.pass_context
def simulate(ctx, nodes_file, topo_file, group_config, test_routes, test_connectivity, duration, failure_node, verbose):
    """模拟网络连接和路由情况"""
    from .simulator import run_simulation
    
    # 设置日志
    verbose = verbose or ctx.obj.get('verbose', False)
    if verbose:
        setup_logging(verbose=True)
    
    logger = get_logger()
    
    # Get nodes/topo files from context if not provided
    if not group_config:
        nodes_file = nodes_file or ctx.obj.get('nodes_file')
        topo_file = topo_file or ctx.obj.get('topo_file')
    
    try:
        # Run the simulation
        results = run_simulation(
            nodes_file=nodes_file,
            topo_file=topo_file,
            group_config=group_config,
            test_routes=test_routes,
            test_connectivity=test_connectivity,
            duration=duration,
            failure_node=failure_node
        )
        
        # Results are already logged by the simulator
        # Just return success
        
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        raise click.ClickException(str(e))
    except ValueError as e:
        logger.error(f"参数错误: {e}")
        raise click.ClickException(str(e))
    except Exception as e:
        logger.error(f"模拟失败: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.argument('nodes_file')
@click.argument('topology_file')
@click.option('--output', '-o', default='out/topology.png', help='输出文件路径')
@click.option('--layout', '-l', default='auto',
              type=click.Choice(['auto', 'spring', 'circular', 'shell', 'hierarchical', 'kamada_kawai']),
              help='网络布局算法')
@click.option('--show-edge-labels/--no-edge-labels', default=None,
              help='是否显示边标签（默认自动决定）')
@click.option('--high-dpi/--low-dpi', default=True,
              help='是否使用高DPI输出')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
def visualize(nodes_file, topology_file, output, layout, show_edge_labels, high_dpi, verbose):
    """生成网络拓扑可视化图
    
    NODES_FILE: 节点配置文件路径
    TOPOLOGY_FILE: 拓扑配置文件路径
    """
    if verbose:
        setup_logging(verbose=True)

    logger = get_logger()

    logger.info("开始生成网络拓扑可视化")
    logger.info(f"节点文件: {nodes_file}")
    logger.info(f"拓扑文件: {topology_file}")
    logger.info(f"布局算法: {layout}")

    try:
        # Check if input files exist
        if not os.path.exists(nodes_file):
            logger.error(f"节点配置文件不存在: {nodes_file}")
            raise click.ClickException(f"Nodes file not found: {nodes_file}")

        if not os.path.exists(topology_file):
            logger.error(f"拓扑配置文件不存在: {topology_file}")
            raise click.ClickException(f"Topology file not found: {topology_file}")

        # Generate visualization
        from .visualizer import visualize as viz_func
        viz_func(
            nodes_path=nodes_file,
            topology_path=topology_file,
            output_path=output,
            layout=layout,
            show_edge_labels=show_edge_labels,
            high_dpi=high_dpi
        )

        logger.info("网络拓扑可视化生成完成")
        click.echo(f"拓扑图已保存到: {output}")

    except Exception as e:
        logger.error(f"生成可视化失败: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--log-file', help='日志文件路径')
@click.option('--nodes-file', '-n', help='节点配置文件路径')
@click.option('--topo-file', '-t', help='拓扑配置文件路径')
@click.pass_context
def valid(ctx, verbose, log_file, nodes_file, topo_file):
    """验证配置文件"""
    # 使用子命令参数或回退到主命令参数
    verbose = verbose or ctx.obj.get('verbose', False)
    nodes_file = nodes_file or ctx.obj['nodes_file']
    topo_file = topo_file or ctx.obj['topo_file']

    # 设置日志
    if verbose or log_file:
        setup_logging(verbose=verbose, log_file=log_file)

    logger = get_logger()

    logger.info("开始验证配置文件")

    try:
        # Check if input files exist
        if not os.path.exists(nodes_file):
            logger.error(f"节点配置文件不存在: {nodes_file}")
            raise click.ClickException(f"Nodes file not found: {nodes_file}")

        if not os.path.exists(topo_file):
            logger.error(f"拓扑配置文件不存在: {topo_file}")
            raise click.ClickException(f"Topology file not found: {topo_file}")

        # Load and validate configurations
        nodes = load_nodes(nodes_file)
        peers = load_topology(topo_file)

        if validate_configuration(nodes, peers):
            logger.info("配置文件验证通过")
            click.echo("Configuration validation passed.")
        else:
            logger.error("配置文件验证失败")
            raise click.ClickException("Configuration validation failed.")

    except Exception as e:
        logger.error(f"验证配置失败: {e}")
        raise click.ClickException(str(e))


@cli.command('convert-group')
@click.option('--group-config', '-g', required=True, help='组网络配置文件路径')
@click.option('--output-nodes', '-n', default='nodes_generated.yaml', help='输出节点配置文件')
@click.option('--output-topology', '-t', default='topology_generated.yaml', help='输出拓扑配置文件')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
def convert_group(group_config, output_nodes, output_topology, verbose):
    """将组配置转换为传统配置格式"""
    if verbose:
        setup_logging(verbose=True)
    
    logger = get_logger()
    logger.info("开始转换组配置")
    
    try:
        if not os.path.exists(group_config):
            raise click.ClickException(f"Group config file not found: {group_config}")
        
        from .group_network_builder import GroupNetworkBuilder
        import yaml
        
        # Build configurations
        builder = GroupNetworkBuilder(group_config)
        nodes, peers = builder.build()
        
        # Save nodes configuration
        nodes_data = {'nodes': nodes}
        with open(output_nodes, 'w', encoding='utf-8') as f:
            yaml.dump(nodes_data, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"节点配置已保存到: {output_nodes}")
        
        # Save topology configuration
        topology_data = {'peers': peers}
        with open(output_topology, 'w', encoding='utf-8') as f:
            yaml.dump(topology_data, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"拓扑配置已保存到: {output_topology}")
        
        click.echo(f"转换完成:")
        click.echo(f"  节点配置: {output_nodes}")
        click.echo(f"  拓扑配置: {output_topology}")
        
    except Exception as e:
        logger.error(f"转换失败: {e}")
        raise click.ClickException(str(e))


@cli.group()
def keys():
    """密钥管理命令"""
    pass


@keys.command()
@click.argument('node_name')
@click.option('--db-path', default='wg_keys.json', help='密钥存储文件路径')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--log-file', help='日志文件路径')
def generate(node_name, db_path, verbose, log_file):
    """为指定节点生成密钥对"""
    # 设置日志
    if verbose or log_file:
        setup_logging(verbose=verbose, log_file=log_file)

    logger = get_logger()
    logger.info(f"为节点 {node_name} 生成密钥对")

    try:
        # Generate keys
        private_key, public_key = generate_keypair()
        psk = generate_preshared_key()

        # Store keys
        key_storage = SimpleKeyStorage(db_path)
        key_storage.store_keypair(node_name, private_key, public_key)

        logger.info(f"密钥对生成完成: {node_name}")
        click.echo(f"Keys generated for node: {node_name}")
        click.echo(f"Public key: {public_key}")

    except Exception as e:
        logger.error(f"生成密钥失败: {e}")
        raise click.ClickException(str(e))


@keys.command()
@click.option('--db-path', default='wg_keys.json', help='密钥存储文件路径')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--log-file', help='日志文件路径')
def list(db_path, verbose, log_file):
    """列出所有存储的密钥"""
    # 设置日志
    if verbose or log_file:
        setup_logging(verbose=verbose, log_file=log_file)

    logger = get_logger()

    try:
        key_storage = SimpleKeyStorage(db_path)
        stored_keys = key_storage.list_keys()

        if stored_keys:
            click.echo("Stored keys:")
            for key_info in stored_keys:
                click.echo(f"  - {key_info['node_name']} (Public: {key_info['public_key'][:8]}...)")
        else:
            click.echo("No keys stored.")

    except Exception as e:
        logger.error(f"列出密钥失败: {e}")
        raise click.ClickException(str(e))


@keys.command()
@click.argument('node_name')
@click.option('--db-path', default='wg_keys.json', help='密钥存储文件路径')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--log-file', help='日志文件路径')
def show(node_name, db_path, verbose, log_file):
    """显示指定节点的密钥信息"""
    # 设置日志
    if verbose or log_file:
        setup_logging(verbose=verbose, log_file=log_file)

    logger = get_logger()

    try:
        key_storage = SimpleKeyStorage(db_path)
        keys = key_storage.get_keypair(node_name)

        if keys:
            from .string_utils import mask_sensitive_info
            private_key, public_key = keys
            click.echo(f"Keys for node: {node_name}")
            click.echo(f"Public key: {public_key}")
            click.echo(f"Private key: {mask_sensitive_info(private_key)}")
        else:
            click.echo(f"No keys found for node: {node_name}")

    except Exception as e:
        logger.error(f"显示密钥失败: {e}")
        raise click.ClickException(str(e))


@keys.command()
@click.argument('node_name')
@click.option('--db-path', default='wg_keys.json', help='密钥存储文件路径')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--log-file', help='日志文件路径')
@click.confirmation_option(prompt='Are you sure you want to delete this key?')
def delete(node_name, db_path, verbose, log_file):
    """删除指定节点的密钥"""
    # 设置日志
    if verbose or log_file:
        setup_logging(verbose=verbose, log_file=log_file)

    logger = get_logger()

    try:
        key_storage = SimpleKeyStorage(db_path)
        success = key_storage.delete_keypair(node_name)

        if success:
            logger.info(f"密钥已删除: {node_name}")
            click.echo(f"Keys deleted for node: {node_name}")
        else:
            click.echo(f"No keys found for node: {node_name}")

    except Exception as e:
        logger.error(f"删除密钥失败: {e}")
        raise click.ClickException(str(e))


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main()
