import os
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
from wg_mesh_gen.loader import load_nodes, load_topology
from wg_mesh_gen.utils import ensure_dir


def visualize(nodes_path: str,
              topology_path: str,
              output_path: str = 'out/topology.png',
              layout: str = 'spring') -> None:
    """
    Visualize WireGuard topology with endpoint labels.
    """
    nodes = load_nodes(nodes_path)
    peers = load_topology(topology_path)

    # Use undirected graph for better visualization
    G = nx.Graph()

    # Add nodes with roles
    for n in nodes:
        G.add_node(n['name'], role=n.get('role','client'))

    # Group connections by endpoint type and create consolidated edges
    connections = defaultdict(set)

    for pr in peers:
        src, dst, ep = pr['from'], pr['to'], pr['endpoint']
        # Create undirected connection key (sorted to avoid duplicates)
        edge_key = tuple(sorted([src, dst]))
        connections[edge_key].add(ep)

    # Add edges with consolidated endpoint labels
    for (node1, node2), endpoints in connections.items():
        # Join multiple endpoint types with comma
        label = ', '.join(sorted(endpoints))
        G.add_edge(node1, node2, label=label)

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
        pos = nx.kamada_kawai_layout(G)
    else:
        pos = nx.spring_layout(G, seed=42)

    # Color mapping
    colors = {'client': 'lightblue', 'relay': 'lightcoral', 'server': 'lightgreen'}
    node_colors = [colors.get(G.nodes[n]['role'], 'lightgray') for n in G]

    # Create figure with larger size for better readability
    plt.figure(figsize=(12, 8))

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1200, alpha=0.9)

    # Draw node labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')

    # Draw edges
    nx.draw_networkx_edges(G, pos, alpha=0.6, width=2)

    # Draw edge labels with better positioning
    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8, alpha=0.8)

    plt.title('WireGuard Network Topology', fontsize=16, fontweight='bold')

    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightblue',
                   markersize=10, label='Client'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightcoral',
                   markersize=10, label='Relay'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgreen',
                   markersize=10, label='Server')
    ]
    plt.legend(handles=legend_elements, loc='upper right')

    plt.axis('off')
    plt.tight_layout()

    ensure_dir(os.path.dirname(output_path))
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

