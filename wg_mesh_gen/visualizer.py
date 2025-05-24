import os
import networkx as nx
import matplotlib.pyplot as plt
import warnings
from collections import defaultdict
from wg_mesh_gen.loader import load_nodes, load_topology
from wg_mesh_gen.utils import ensure_dir
from wg_mesh_gen.logger import get_logger


def sanitize_node_name(name: str) -> str:
    """
    清理节点名称，将非ASCII字符替换为安全字符

    Args:
        name: 原始节点名称

    Returns:
        清理后的节点名称
    """
    # 如果名称只包含ASCII字符，直接返回
    if name.isascii():
        return name

    # 对于包含非ASCII字符的名称，使用简化版本
    # 保留字母数字和常见符号，其他字符用下划线替换
    sanitized = ""
    for char in name:
        if char.isascii() and (char.isalnum() or char in '-_'):
            sanitized += char
        else:
            sanitized += "_"

    # 如果完全被替换了，使用原名称的hash
    if sanitized.replace('_', '') == '':
        sanitized = f"node_{hash(name) % 10000}"

    return sanitized


def visualize(nodes_path: str,
              topology_path: str,
              output_path: str = 'out/topology.png',
              layout: str = 'spring') -> None:
    """
    Visualize WireGuard topology with endpoint labels.
    """
    logger = get_logger()
    nodes = load_nodes(nodes_path)
    peers = load_topology(topology_path)

    # 抑制matplotlib字体警告
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

        # Create graph
        G = nx.Graph()

        # 创建节点名称映射（原名称 -> 清理后的名称）
        name_mapping = {}
        display_mapping = {}  # 清理后的名称 -> 原名称（用于显示）

        # Add nodes with attributes
        for node in nodes:
            original_name = node['name']
            clean_name = sanitize_node_name(original_name)
            name_mapping[original_name] = clean_name
            display_mapping[clean_name] = original_name

            G.add_node(clean_name,
                      role=node.get('role', 'client'),
                      ip=node.get('wireguard_ip', ''),
                      original_name=original_name)

        # Add edges (使用清理后的名称)
        for peer in peers:
            from_clean = name_mapping[peer['from']]
            to_clean = name_mapping[peer['to']]
            G.add_edge(from_clean, to_clean)

        # Create figure
        plt.figure(figsize=(12, 8))

        # Choose layout
        if layout == 'spring':
            pos = nx.spring_layout(G, seed=42, k=3, iterations=50)
        elif layout == 'circular':
            pos = nx.circular_layout(G)
        elif layout == 'shell':
            # Group nodes by role for shell layout
            client_nodes = [n for n in G.nodes() if G.nodes[n]['role'] == 'client']
            relay_nodes = [n for n in G.nodes() if G.nodes[n]['role'] == 'relay']
            shells = [client_nodes, relay_nodes] if relay_nodes else [client_nodes]
            pos = nx.shell_layout(G, nlist=shells)
        elif layout == 'kamada_kawai':
            try:
                pos = nx.kamada_kawai_layout(G)
            except ImportError:
                # scipy not available, fallback to spring layout
                logger.warning("scipy not available, using spring layout instead of kamada_kawai")
                pos = nx.spring_layout(G, seed=42, k=3, iterations=50)
        else:
            pos = nx.spring_layout(G, seed=42)

        # Color nodes by role
        node_colors = []
        for node in G.nodes():
            role = G.nodes[node]['role']
            if role == 'relay':
                node_colors.append('lightcoral')
            elif role == 'client':
                node_colors.append('lightblue')
            else:
                node_colors.append('lightgray')

        # Draw the graph
        nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                              node_size=1000, alpha=0.8)
        nx.draw_networkx_edges(G, pos, alpha=0.6, width=2)

        # 使用清理后的名称作为标签，但在日志中记录原名称
        clean_labels = {clean_name: clean_name for clean_name in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=clean_labels, font_size=10, font_weight='bold')

        # Add endpoint information as edge labels
        edge_labels = {}
        endpoint_counts = defaultdict(int)

        for peer in peers:
            # 使用清理后的名称作为边的键
            edge = (name_mapping[peer['from']], name_mapping[peer['to']])
            if edge not in edge_labels:
                edge_labels[edge] = []

            endpoint = peer.get('endpoint', '')
            if endpoint:
                endpoint_counts[endpoint] += 1
                edge_labels[edge].append(endpoint)

        # Draw edge labels
        formatted_edge_labels = {}
        for edge, endpoints in edge_labels.items():
            if endpoints:
                formatted_edge_labels[edge] = '\n'.join(endpoints)

        nx.draw_networkx_edge_labels(G, pos, formatted_edge_labels,
                                    font_size=8, alpha=0.7)

        # Add title and legend
        plt.title('WireGuard Mesh Network Topology', fontsize=16, fontweight='bold')

        # Create legend
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightblue',
                      markersize=10, label='Client Node'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightcoral',
                      markersize=10, label='Relay Node')
        ]
        plt.legend(handles=legend_elements, loc='upper right')

        # Ensure output directory exists
        ensure_dir(os.path.dirname(output_path))

        # Save the plot
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    logger.info(f"网络拓扑图已保存到: {output_path}")

    # Print statistics (使用原始节点信息)
    logger.info(f"网络统计:")
    logger.info(f"  节点数量: {len(nodes)}")
    logger.info(f"  连接数量: {len(peers)}")

    relay_count = len([n for n in nodes if n.get('role') == 'relay'])
    client_count = len([n for n in nodes if n.get('role') == 'client'])

    logger.info(f"  中继节点: {relay_count}")
    logger.info(f"  客户端节点: {client_count}")

    if endpoint_counts:
        logger.info(f"  端点使用统计:")
        for endpoint, count in sorted(endpoint_counts.items()):
            logger.info(f"    {endpoint}: {count} 次")

    # 如果有非ASCII节点名称，记录映射信息
    non_ascii_nodes = [node['name'] for node in nodes if not node['name'].isascii()]
    if non_ascii_nodes:
        logger.info(f"  注意: {len(non_ascii_nodes)} 个节点名称包含非ASCII字符，在图中显示为简化名称")
