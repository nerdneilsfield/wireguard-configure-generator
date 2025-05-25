import os
import networkx as nx
import matplotlib.pyplot as plt
import warnings
import math
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


def calculate_layout_params(num_nodes: int, num_edges: int):
    """
    根据网络规模计算布局参数
    
    Args:
        num_nodes: 节点数量
        num_edges: 边数量
        
    Returns:
        包含各种布局参数的字典
    """
    # 基础参数
    base_figure_size = 12
    base_node_size = 1000
    base_font_size = 10
    base_edge_font_size = 8
    
    # 根据节点数量调整参数
    if num_nodes <= 10:
        # 小型网络
        scale_factor = 1.0
        layout_k = 1
        iterations = 50
    elif num_nodes <= 30:
        # 中型网络
        scale_factor = 1.2
        layout_k = 2
        iterations = 100
    elif num_nodes <= 70:
        # 大型网络
        scale_factor = 1.5
        layout_k = 3
        iterations = 150
    else:
        # 超大型网络
        scale_factor = 2.0
        layout_k = 4
        iterations = 200
    
    # 计算画布大小 - 根据节点数量动态调整
    figure_width = base_figure_size * scale_factor
    figure_height = base_figure_size * scale_factor * 0.8
    
    # 节点大小 - 节点越多，单个节点越小
    node_size = max(200, base_node_size / math.sqrt(num_nodes / 10))
    
    # 字体大小 - 根据节点数量和画布大小调整
    font_size = max(6, base_font_size - math.log10(max(1, num_nodes / 10)))
    edge_font_size = max(4, base_edge_font_size - math.log10(max(1, num_nodes / 10)))
    
    # 边的透明度和宽度
    edge_alpha = max(0.3, 0.8 - (num_edges / 500))
    edge_width = max(0.5, 2 - (num_edges / 200))
    
    return {
        'figure_size': (figure_width, figure_height),
        'node_size': node_size,
        'font_size': font_size,
        'edge_font_size': edge_font_size,
        'edge_alpha': edge_alpha,
        'edge_width': edge_width,
        'layout_k': layout_k,
        'iterations': iterations,
        'scale_factor': scale_factor
    }


def choose_best_layout(G, num_nodes: int, layout_preference: str = 'auto'):
    """
    根据网络规模选择最佳布局算法
    
    Args:
        G: NetworkX图对象
        num_nodes: 节点数量
        layout_preference: 布局偏好
        
    Returns:
        节点位置字典
    """
    logger = get_logger()
    
    if layout_preference != 'auto':
        # 用户指定了布局
        return get_layout(G, layout_preference, num_nodes)
    
    # 自动选择布局
    if num_nodes <= 15:
        # 小型网络：使用circular或shell布局，更清晰
        logger.info("使用circular布局（小型网络）")
        return nx.circular_layout(G)
    elif num_nodes <= 50:
        # 中型网络：使用spring布局
        logger.info("使用spring布局（中型网络）")
        return nx.spring_layout(G, seed=42, k=2, iterations=100)
    else:
        # 大型网络：使用分层布局或force-directed布局
        logger.info("使用分层spring布局（大型网络）")
        # 尝试按角色分组
        try:
            return create_hierarchical_layout(G)
        except:
            # 回退到标准spring布局
            return nx.spring_layout(G, seed=42, k=3, iterations=150)


def create_hierarchical_layout(G):
    """
    创建分层布局，将不同角色的节点分层显示
    """
    # 按角色分组节点
    relay_nodes = [n for n in G.nodes() if G.nodes[n]['role'] == 'relay']
    gateway_nodes = [n for n in G.nodes() if G.nodes[n]['role'] == 'gateway']
    client_nodes = [n for n in G.nodes() if G.nodes[n]['role'] == 'client']
    
    pos = {}
    
    # 中继节点放在中心
    if relay_nodes:
        relay_pos = nx.circular_layout(relay_nodes, scale=0.5)
        for node, position in relay_pos.items():
            pos[node] = position
    
    # 网关节点放在中间层
    if gateway_nodes:
        gateway_pos = nx.circular_layout(gateway_nodes, scale=1.5)
        for node, position in gateway_pos.items():
            pos[node] = position
    
    # 客户端节点放在外层
    if client_nodes:
        client_pos = nx.circular_layout(client_nodes, scale=2.5)
        for node, position in client_pos.items():
            pos[node] = position
    
    # 如果某些角色没有节点，使用spring布局填充
    remaining_nodes = set(G.nodes()) - set(pos.keys())
    if remaining_nodes:
        remaining_pos = nx.spring_layout(G.subgraph(remaining_nodes), seed=42)
        pos.update(remaining_pos)
    
    return pos


def get_layout(G, layout: str, num_nodes: int):
    """
    获取指定的布局
    """
    logger = get_logger()
    params = calculate_layout_params(num_nodes, G.number_of_edges())
    
    if layout == 'spring':
        return nx.spring_layout(G, seed=42, k=params['layout_k'], iterations=params['iterations'])
    elif layout == 'circular':
        return nx.circular_layout(G)
    elif layout == 'shell':
        # Group nodes by role for shell layout
        client_nodes = [n for n in G.nodes() if G.nodes[n]['role'] == 'client']
        relay_nodes = [n for n in G.nodes() if G.nodes[n]['role'] == 'relay']
        gateway_nodes = [n for n in G.nodes() if G.nodes[n]['role'] == 'gateway']
        
        shells = []
        if relay_nodes:
            shells.append(relay_nodes)
        if gateway_nodes:
            shells.append(gateway_nodes)
        if client_nodes:
            shells.append(client_nodes)
        
        if not shells:
            shells = [list(G.nodes())]
            
        return nx.shell_layout(G, nlist=shells)
    elif layout == 'kamada_kawai':
        try:
            return nx.kamada_kawai_layout(G)
        except ImportError:
            logger.warning("scipy not available, using spring layout instead of kamada_kawai")
            return nx.spring_layout(G, seed=42, k=params['layout_k'], iterations=params['iterations'])
    elif layout == 'hierarchical':
        return create_hierarchical_layout(G)
    else:
        return nx.spring_layout(G, seed=42)


def simplify_edge_labels(peers, max_labels_per_edge: int = 3):
    """
    简化边标签，避免标签过多导致图形混乱
    """
    edge_labels = {}
    endpoint_counts = defaultdict(int)
    
    for peer in peers:
        edge = (peer['from'], peer['to'])
        if edge not in edge_labels:
            edge_labels[edge] = []
        
        endpoint = peer.get('endpoint', '')
        if endpoint:
            endpoint_counts[endpoint] += 1
            if len(edge_labels[edge]) < max_labels_per_edge:
                edge_labels[edge].append(endpoint)
            elif len(edge_labels[edge]) == max_labels_per_edge:
                edge_labels[edge].append('...')
    
    return edge_labels, endpoint_counts


def visualize(nodes_path: str,
              topology_path: str,
              output_path: str = 'out/topology.png',
              layout: str = 'auto',
              show_edge_labels: bool = None,
              high_dpi: bool = True) -> None:
    """
    Visualize WireGuard topology with adaptive scaling based on network size.
    
    Args:
        nodes_path: 节点配置文件路径
        topology_path: 拓扑配置文件路径
        output_path: 输出图片路径
        layout: 布局算法 ('auto', 'spring', 'circular', 'shell', 'hierarchical', 'kamada_kawai')
        show_edge_labels: 是否显示边标签（None表示自动决定）
        high_dpi: 是否使用高DPI输出
    """
    logger = get_logger()
    nodes = load_nodes(nodes_path)
    peers = load_topology(topology_path)
    
    num_nodes = len(nodes)
    num_edges = len(peers)
    
    logger.info(f"开始可视化网络: {num_nodes} 个节点, {num_edges} 条连接")
    
    # 计算布局参数
    params = calculate_layout_params(num_nodes, num_edges)
    logger.info(f"自动调整参数: 画布大小={params['figure_size']}, 节点大小={params['node_size']:.0f}, 字体大小={params['font_size']:.1f}")
    
    # 自动决定是否显示边标签
    if show_edge_labels is None:
        show_edge_labels = num_edges <= 100  # 连接数超过100时不显示边标签
    
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
        
        # Create figure with adaptive size
        plt.figure(figsize=params['figure_size'])
        
        # Choose layout
        pos = choose_best_layout(G, num_nodes, layout)
        
        # Color nodes by role with better color scheme
        node_colors = []
        for node in G.nodes():
            role = G.nodes[node]['role']
            if role == 'relay':
                node_colors.append('#FF6B6B')  # 更鲜艳的红色
            elif role == 'gateway':
                node_colors.append('#4ECDC4')  # 青色
            elif role == 'client':
                node_colors.append('#45B7D1')  # 蓝色
            else:
                node_colors.append('#96CEB4')  # 绿色
        
        # Draw the graph with adaptive parameters
        nx.draw_networkx_nodes(G, pos, 
                              node_color=node_colors,
                              node_size=params['node_size'], 
                              alpha=0.8,
                              edgecolors='black',
                              linewidths=0.5)
        
        nx.draw_networkx_edges(G, pos, 
                              alpha=params['edge_alpha'], 
                              width=params['edge_width'],
                              edge_color='gray')
        
        # 节点标签 - 对于大型网络使用简化标签
        if num_nodes <= 50:
            # 小中型网络显示完整名称
            clean_labels = {clean_name: display_mapping[clean_name] for clean_name in G.nodes()}
        else:
            # 大型网络显示简化名称
            clean_labels = {clean_name: clean_name for clean_name in G.nodes()}
        
        nx.draw_networkx_labels(G, pos, 
                               labels=clean_labels, 
                               font_size=params['font_size'], 
                               font_weight='bold')
        
        # Add endpoint information as edge labels (仅在适当时显示)
        if show_edge_labels:
            edge_labels, endpoint_counts = simplify_edge_labels(peers, max_labels_per_edge=2)
            
            # 转换边标签的键为清理后的名称
            formatted_edge_labels = {}
            for (from_node, to_node), endpoints in edge_labels.items():
                edge_key = (name_mapping[from_node], name_mapping[to_node])
                if endpoints:
                    formatted_edge_labels[edge_key] = '\n'.join(endpoints)
            
            if formatted_edge_labels:
                nx.draw_networkx_edge_labels(G, pos, formatted_edge_labels,
                                            font_size=params['edge_font_size'], 
                                            alpha=0.7)
        
        # Add title and legend
        plt.title('WireGuard Mesh Network Topology', 
                 fontsize=max(14, params['font_size'] + 4), 
                 fontweight='bold', 
                 pad=20)
        
        # Create legend with role information
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#45B7D1',
                      markersize=10, label='Client Node'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#4ECDC4',
                      markersize=10, label='Gateway Node'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#FF6B6B',
                      markersize=10, label='Relay Node')
        ]
        plt.legend(handles=legend_elements, loc='upper right', fontsize=params['font_size'])
        
        # 调整布局以避免标签被截断
        plt.tight_layout()
        
        # Ensure output directory exists
        ensure_dir(os.path.dirname(output_path))
        
        # Save the plot with adaptive DPI
        dpi = 300 if high_dpi else 150
        if num_nodes > 100:
            dpi = 200  # 超大网络使用中等DPI以控制文件大小
        
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
    
    logger.info(f"网络拓扑图已保存到: {output_path}")
    
    # Print statistics (使用原始节点信息)
    logger.info(f"网络统计:")
    logger.info(f"  节点数量: {len(nodes)}")
    logger.info(f"  连接数量: {len(peers)}")
    
    relay_count = len([n for n in nodes if n.get('role') == 'relay'])
    gateway_count = len([n for n in nodes if n.get('role') == 'gateway'])
    client_count = len([n for n in nodes if n.get('role') == 'client'])
    
    logger.info(f"  中继节点: {relay_count}")
    logger.info(f"  网关节点: {gateway_count}")
    logger.info(f"  客户端节点: {client_count}")
    
    if show_edge_labels and num_edges <= 100:
        edge_labels, endpoint_counts = simplify_edge_labels(peers)
        if endpoint_counts:
            logger.info(f"  端点使用统计:")
            for endpoint, count in sorted(endpoint_counts.items()):
                logger.info(f"    {endpoint}: {count} 次")
    
    # 如果有非ASCII节点名称，记录映射信息
    non_ascii_nodes = [node['name'] for node in nodes if not node['name'].isascii()]
    if non_ascii_nodes:
        logger.info(f"  注意: {len(non_ascii_nodes)} 个节点名称包含非ASCII字符，在图中显示为简化名称")
    
    # 给出优化建议
    if num_nodes > 50:
        logger.info(f"  建议: 网络规模较大，可以考虑使用 'hierarchical' 布局获得更好的可读性")
    if num_edges > 200:
        logger.info(f"  建议: 连接数量较多，已自动隐藏边标签以提高可读性")
