"""
Group Network Builder - 组网络配置构建器

This module provides a high-level abstraction for defining complex WireGuard network topologies
using groups and simplified connection rules.
"""

import ipaddress
import re
from typing import Dict, List, Any, Tuple, Optional, Set
from collections import defaultdict
import yaml

from .logger import get_logger


class GroupNetworkBuilder:
    """将组网络配置转换为传统的节点和拓扑配置"""
    
    def __init__(self, config_path: str):
        """
        初始化组网络构建器
        
        Args:
            config_path: 组网络配置文件路径
        """
        self.logger = get_logger()
        self.config_path = config_path
        self.config = self._load_config()
        self.generated_nodes = []
        self.generated_peers = []
        self._node_map = {}  # node_name -> node_config mapping
        self._group_subnets = {}  # group_name -> subnet
        self._node_groups = {}  # node_name -> group_name mapping
        self._routing_table = defaultdict(set)  # node -> reachable subnets
        
    def _load_config(self) -> Dict[str, Any]:
        """加载并验证组网络配置"""
        self.logger.info(f"加载组网络配置: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Validate schema if needed
        try:
            from .data_utils import validate_schema
            validate_schema(config, 'group_network_schema.json')
        except Exception as e:
            self.logger.warning(f"Schema validation skipped: {e}")
        
        return config['network_topology']
    
    def build(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        构建节点和对等连接配置
        
        Returns:
            (nodes, peers) 元组
        """
        self.logger.info("开始构建组网络配置")
        
        # 1. 生成所有节点
        self._generate_nodes()
        
        # 2. 生成组内连接
        self._generate_intra_group_connections()
        
        # 3. 生成组间连接
        self._generate_inter_group_connections()
        
        # 4. 优化和验证
        self._validate_and_optimize()
        
        self.logger.info(f"生成完成: {len(self.generated_nodes)} 个节点, "
                        f"{len(self.generated_peers)} 个对等连接")
        
        return self.generated_nodes, self.generated_peers
    
    def _generate_nodes(self):
        """生成所有节点配置"""
        for group_name, group_config in self.config['groups'].items():
            self.logger.debug(f"处理组 {group_name}")
            
            # 提取组子网
            subnet = None
            for node_name, node_config in group_config['nodes'].items():
                ip_with_prefix = node_config['ip']
                ip = ipaddress.ip_interface(ip_with_prefix)
                if subnet is None:
                    subnet = ip.network
                self._group_subnets[group_name] = str(subnet)
                
                # 记录节点所属组
                self._node_groups[node_name] = group_name
                
                # 构建节点配置
                node = {
                    'name': node_name,
                    'wireguard_ip': ip_with_prefix,
                    'role': 'relay' if group_config.get('topology') == 'single' else 'client',
                    'group': group_name  # 添加组信息
                }
                
                # 检查是否为中继节点
                is_relay = node_config.get('is_relay', False) or group_config.get('role') == 'relay'
                if is_relay:
                    node['role'] = 'relay'
                    node['enable_ip_forward'] = True
                
                # 处理端点
                endpoints = node_config.get('endpoints', {})
                if isinstance(endpoints, dict):
                    # 多端点配置
                    endpoint_list = []
                    for ep_name, ep_value in endpoints.items():
                        endpoint_list.append(ep_value)
                    node['endpoints'] = endpoint_list
                    node['endpoint_names'] = endpoints  # 保存端点名称映射
                elif isinstance(endpoints, str):
                    # 单端点配置
                    node['endpoints'] = [endpoints]
                
                # 提取监听端口
                if node.get('endpoints'):
                    first_endpoint = node['endpoints'][0]
                    if ':' in first_endpoint:
                        try:
                            port = int(first_endpoint.split(':')[-1])
                            node['listen_port'] = port
                        except ValueError:
                            pass
                
                # PostUp/PostDown 脚本
                if node_config.get('post_up'):
                    node['post_up'] = node_config['post_up']
                if node_config.get('post_down'):
                    node['post_down'] = node_config['post_down']
                
                self.generated_nodes.append(node)
                self._node_map[node_name] = node
    
    def _generate_intra_group_connections(self):
        """生成组内连接"""
        for group_name, group_config in self.config['groups'].items():
            topology = group_config.get('topology', 'mesh')
            nodes = list(group_config['nodes'].keys())
            
            if topology == 'mesh':
                endpoint_selector = group_config.get('mesh_endpoint', 'default')
                self._generate_mesh_topology(nodes, group_name, endpoint_selector)
            elif topology == 'star':
                hub_node = group_config.get('hub_node')
                if not hub_node:
                    raise ValueError(f"Star topology for group {group_name} requires hub_node")
                self._generate_star_topology(nodes, hub_node, group_name)
            elif topology == 'chain':
                self._generate_chain_topology(nodes, group_name)
            elif topology == 'single':
                # 单节点组，无需内部连接
                pass
            else:
                raise ValueError(f"Unknown topology type: {topology}")
    
    def _generate_mesh_topology(self, nodes: List[str], group_name: str, 
                               endpoint_selector: str = 'default'):
        """
        生成mesh拓扑连接
        
        Args:
            nodes: 节点列表
            group_name: 组名
            endpoint_selector: 端点选择器
        """
        self.logger.debug(f"生成 {group_name} 的 mesh 拓扑，使用端点: {endpoint_selector}")
        
        for i, node_a in enumerate(nodes):
            for node_b in nodes[i+1:]:
                # A -> B
                self._add_peer_connection(
                    from_node=node_a,
                    to_node=node_b,
                    allowed_ips=[self._get_node_ip(node_b)],
                    endpoint_selector=endpoint_selector
                )
                
                # B -> A
                self._add_peer_connection(
                    from_node=node_b,
                    to_node=node_a,
                    allowed_ips=[self._get_node_ip(node_a)],
                    endpoint_selector=endpoint_selector
                )
    
    def _generate_star_topology(self, nodes: List[str], hub_node: str, group_name: str):
        """生成星型拓扑连接"""
        self.logger.debug(f"生成 {group_name} 的 star 拓扑，中心节点: {hub_node}")
        
        for node in nodes:
            if node != hub_node:
                # Spoke -> Hub
                self._add_peer_connection(
                    from_node=node,
                    to_node=hub_node,
                    allowed_ips=[self._get_node_ip(hub_node)]
                )
                
                # Hub -> Spoke
                self._add_peer_connection(
                    from_node=hub_node,
                    to_node=node,
                    allowed_ips=[self._get_node_ip(node)]
                )
    
    def _generate_chain_topology(self, nodes: List[str], group_name: str):
        """生成链式拓扑连接"""
        self.logger.debug(f"生成 {group_name} 的 chain 拓扑")
        
        for i in range(len(nodes) - 1):
            # Current -> Next
            self._add_peer_connection(
                from_node=nodes[i],
                to_node=nodes[i + 1],
                allowed_ips=[self._get_node_ip(nodes[i + 1])]
            )
            
            # Next -> Current
            self._add_peer_connection(
                from_node=nodes[i + 1],
                to_node=nodes[i],
                allowed_ips=[self._get_node_ip(nodes[i])]
            )
    
    def _generate_inter_group_connections(self):
        """生成组间连接"""
        for conn in self.config.get('connections', []):
            conn_type = conn['type']
            
            if conn_type == 'outbound_only':
                self._generate_outbound_connections(conn)
            elif conn_type == 'bidirectional':
                self._generate_bidirectional_connections(conn)
            elif conn_type == 'gateway':
                self._generate_gateway_connections(conn)
            elif conn_type == 'selective':
                self._generate_selective_connections(conn)
            elif conn_type == 'full_mesh':
                self._generate_full_mesh_connections(conn)
            else:
                raise ValueError(f"Unknown connection type: {conn_type}")
    
    def _generate_outbound_connections(self, conn: Dict[str, Any]):
        """生成单向出站连接"""
        from_groups = conn['from'] if isinstance(conn['from'], list) else [conn['from']]
        to_group = conn['to']
        
        for from_group in from_groups:
            from_nodes = self._get_group_nodes(from_group)
            to_nodes = self._get_group_nodes(to_group)
            
            endpoint_selector = conn.get('endpoint_selector', 'default')
            allowed_ips = self._resolve_allowed_ips(conn['routing']['allowed_ips'])
            
            # 每个from节点连接所有to节点
            for from_node in from_nodes:
                for to_node in to_nodes:
                    self._add_peer_connection(
                        from_node=from_node,
                        to_node=to_node,
                        allowed_ips=allowed_ips,
                        endpoint_selector=endpoint_selector
                    )
    
    def _generate_bidirectional_connections(self, conn: Dict[str, Any]):
        """生成双向连接"""
        # 解析节点
        from_spec = conn['from']
        to_spec = conn['to']
        
        from_node = self._parse_node_spec(from_spec)
        to_node = self._parse_node_spec(to_spec)
        
        # 处理端点映射
        endpoint_mapping = conn.get('endpoint_mapping', {})
        
        # 处理路由
        routing = conn.get('routing', {})
        from_allowed_ips = self._resolve_allowed_ips(
            routing.get(f'{from_node}_allowed_ips', [])
        )
        to_allowed_ips = self._resolve_allowed_ips(
            routing.get(f'{to_node}_allowed_ips', [])
        )
        
        # 特殊标志
        special_flags = conn.get('special_flags', {})
        persistent_keepalive = special_flags.get('persistent_keepalive')
        
        # From -> To
        self._add_peer_connection(
            from_node=from_node,
            to_node=to_node,
            allowed_ips=from_allowed_ips,
            endpoint_spec=endpoint_mapping.get(f'{from_node}_to_{to_node}'),
            persistent_keepalive=persistent_keepalive
        )
        
        # To -> From
        self._add_peer_connection(
            from_node=to_node,
            to_node=from_node,
            allowed_ips=to_allowed_ips,
            endpoint_spec=endpoint_mapping.get(f'{to_node}_to_{from_node}'),
            persistent_keepalive=persistent_keepalive
        )
    
    def _generate_gateway_connections(self, conn: Dict[str, Any]):
        """生成网关模式连接"""
        from_group = conn['from']
        to_group = conn['to']
        
        from_nodes = self._get_group_nodes(from_group)
        gateway_nodes = conn['gateway_nodes']['to']
        
        endpoint_selector = conn.get('endpoint_selector', 'default')
        allowed_ips = self._resolve_allowed_ips(conn['routing']['allowed_ips'])
        
        # 所有from节点连接到网关节点
        for from_node in from_nodes:
            for gateway_node in gateway_nodes:
                self._add_peer_connection(
                    from_node=from_node,
                    to_node=gateway_node,
                    allowed_ips=allowed_ips,
                    endpoint_selector=endpoint_selector
                )
    
    def _generate_selective_connections(self, conn: Dict[str, Any]):
        """生成选择性连接"""
        from_group = conn['from']
        to_spec = conn['to']
        nodes = conn.get('nodes', [])
        
        to_node = self._parse_node_spec(to_spec)
        endpoint_selector = conn.get('endpoint_selector')
        allowed_ips = self._resolve_allowed_ips(conn['routing']['allowed_ips'])
        
        # 只有指定的节点连接
        for node in nodes:
            self._add_peer_connection(
                from_node=node,
                to_node=to_node,
                allowed_ips=allowed_ips,
                endpoint_spec=endpoint_selector
            )
    
    def _generate_full_mesh_connections(self, conn: Dict[str, Any]):
        """生成组间全连接"""
        from_group = conn['from']
        to_group = conn['to']
        
        from_nodes = self._get_group_nodes(from_group)
        to_nodes = self._get_group_nodes(to_group)
        
        endpoint_selector = conn.get('endpoint_selector', 'default')
        allowed_ips = self._resolve_allowed_ips(conn['routing']['allowed_ips'])
        
        # 两组之间的所有节点互连
        for from_node in from_nodes:
            for to_node in to_nodes:
                # From -> To
                self._add_peer_connection(
                    from_node=from_node,
                    to_node=to_node,
                    allowed_ips=allowed_ips,
                    endpoint_selector=endpoint_selector
                )
                
                # To -> From (如果需要双向)
                if not conn.get('one_way', False):
                    # 反向连接可能需要不同的端点选择器
                    reverse_endpoint_selector = conn.get('reverse_endpoint_selector', endpoint_selector)
                    reverse_allowed_ips = allowed_ips  # TODO: 可能需要不同的allowed_ips
                    
                    self._add_peer_connection(
                        from_node=to_node,
                        to_node=from_node,
                        allowed_ips=reverse_allowed_ips,
                        endpoint_selector=reverse_endpoint_selector
                    )
    
    def _add_peer_connection(self, from_node: str, to_node: str, 
                           allowed_ips: List[str],
                           endpoint_selector: Optional[str] = None,
                           endpoint_spec: Optional[str] = None,
                           persistent_keepalive: Optional[int] = None):
        """添加对等连接"""
        # 获取目标节点的端点
        endpoint = self._get_node_endpoint(to_node, endpoint_selector or endpoint_spec)
        
        peer = {
            'from': from_node,
            'to': to_node,
            'allowed_ips': allowed_ips
        }
        
        if endpoint:
            peer['endpoint'] = endpoint
            
        if persistent_keepalive:
            peer['persistent_keepalive'] = persistent_keepalive
        
        self.generated_peers.append(peer)
        self.logger.debug(f"添加连接: {from_node} -> {to_node}, "
                         f"allowed_ips: {allowed_ips}, endpoint: {endpoint}")
    
    def _get_node_endpoint(self, node_name: str, selector: Optional[str] = None) -> Optional[str]:
        """获取节点的端点"""
        node = self._node_map.get(node_name)
        if not node:
            return None
        
        if not selector or selector == 'default':
            # 返回第一个端点
            return node.get('endpoints', [None])[0]
        
        # 处理特殊选择器格式，如 "H.special"
        if '.' in selector:
            target_node, endpoint_name = selector.split('.', 1)
            if target_node == node_name:
                endpoint_names = node.get('endpoint_names', {})
                return endpoint_names.get(endpoint_name)
        else:
            # 直接使用选择器名称
            endpoint_names = node.get('endpoint_names', {})
            return endpoint_names.get(selector)
        
        return None
    
    def _resolve_allowed_ips(self, allowed_specs: List[str]) -> List[str]:
        """解析allowed_ips规范"""
        resolved = []
        
        # 如果还没有构建节点，先扫描组以获取子网信息
        if not self._group_subnets:
            self._scan_group_subnets()
        
        for spec in allowed_specs:
            if '.' in spec and not self._is_ip_address(spec):
                # 处理组引用，如 "office.subnet" 或 "china_relay.nodes"
                parts = spec.split('.')
                if len(parts) == 2:
                    group_name, attr = parts
                    if attr == 'subnet':
                        subnet = self._group_subnets.get(group_name)
                        if subnet:
                            resolved.append(subnet)
                    elif attr == 'nodes':
                        nodes = self._get_group_nodes(group_name)
                        for node in nodes:
                            # 如果节点还没有映射，从配置中获取IP
                            if node not in self._node_map:
                                node_ip = self._get_node_ip_from_config(group_name, node)
                                if node_ip:
                                    resolved.append(f"{node_ip}/32")
                            else:
                                resolved.append(self._get_node_ip(node))
                elif len(parts) == 3:
                    # 如 "china_relay.G.ip"
                    group_name, node_name, attr = parts
                    if attr == 'ip':
                        resolved.append(self._get_node_ip(node_name))
            else:
                # 直接使用的组名或IP地址
                if self._is_ip_address(spec):
                    resolved.append(spec)
                else:
                    # 尝试作为组名解析
                    subnet = self._group_subnets.get(spec)
                    if subnet:
                        resolved.append(subnet)
                    else:
                        # 可能是简写，如 "overseas" -> "overseas.subnet"
                        subnet = self._group_subnets.get(spec.replace('.subnet', ''))
                        if subnet:
                            resolved.append(subnet)
        
        return resolved
    
    def _scan_group_subnets(self):
        """扫描所有组以获取子网信息"""
        for group_name, group_config in self.config['groups'].items():
            for node_name, node_config in group_config['nodes'].items():
                ip_with_prefix = node_config['ip']
                ip = ipaddress.ip_interface(ip_with_prefix)
                self._group_subnets[group_name] = str(ip.network)
                break  # 只需要第一个节点的子网
    
    def _get_node_ip_from_config(self, group_name: str, node_name: str) -> Optional[str]:
        """从配置中获取节点IP"""
        group_config = self.config['groups'].get(group_name, {})
        node_config = group_config.get('nodes', {}).get(node_name, {})
        if node_config and 'ip' in node_config:
            ip_interface = ipaddress.ip_interface(node_config['ip'])
            return str(ip_interface.ip)
        return None
    
    def _is_ip_address(self, value: str) -> bool:
        """检查是否为IP地址或CIDR"""
        try:
            ipaddress.ip_interface(value)
            return True
        except ValueError:
            try:
                ipaddress.ip_network(value)
                return True
            except ValueError:
                return False
    
    def _get_group_nodes(self, group_name: str) -> List[str]:
        """获取组内的所有节点"""
        group_config = self.config['groups'].get(group_name, {})
        return list(group_config.get('nodes', {}).keys())
    
    def _parse_node_spec(self, spec: str) -> str:
        """解析节点规范，如 'china_relay.G' -> 'G'"""
        if '.' in spec:
            parts = spec.split('.')
            return parts[-1]
        return spec
    
    def _get_node_ip(self, node_name: str) -> str:
        """获取节点的IP地址（/32格式）"""
        node = self._node_map.get(node_name)
        if node:
            ip_interface = ipaddress.ip_interface(node['wireguard_ip'])
            return f"{ip_interface.ip}/32"
        return ""
    
    def _validate_and_optimize(self):
        """验证和优化生成的配置"""
        # 检查重复的对等连接
        seen_connections = set()
        unique_peers = []
        
        for peer in self.generated_peers:
            conn_key = (peer['from'], peer['to'])
            if conn_key not in seen_connections:
                seen_connections.add(conn_key)
                unique_peers.append(peer)
            else:
                self.logger.warning(f"发现重复连接: {peer['from']} -> {peer['to']}")
        
        self.generated_peers = unique_peers
        
        # 检查AllowedIPs冲突
        self._check_allowed_ips_conflicts()
        
        # 分析路由路径
        self._analyze_routing_paths()
        
        # 为中继节点生成路由脚本
        self._generate_relay_routing_scripts()
        
        # 警告过大的AllowedIPs
        for peer in self.generated_peers:
            for ip in peer.get('allowed_ips', []):
                if ip == '0.0.0.0/0':
                    self.logger.warning(
                        f"连接 {peer['from']} -> {peer['to']} 使用了 0.0.0.0/0，"
                        f"建议明确指定需要的子网"
                    )
    
    def _check_allowed_ips_conflicts(self):
        """检查AllowedIPs冲突"""
        # 按源节点分组
        node_peers = defaultdict(list)
        for peer in self.generated_peers:
            node_peers[peer['from']].append(peer)
        
        # 检查每个节点的AllowedIPs
        for node, peers in node_peers.items():
            # 收集所有AllowedIPs
            all_ips = []
            for peer in peers:
                for ip in peer.get('allowed_ips', []):
                    try:
                        network = ipaddress.ip_network(ip)
                        all_ips.append((network, peer['to']))
                    except ValueError:
                        self.logger.error(f"无效的IP地址: {ip}")
            
            # 检查重叠
            for i, (net1, peer1) in enumerate(all_ips):
                for net2, peer2 in all_ips[i+1:]:
                    if net1.overlaps(net2) and net1 != net2:
                        self.logger.warning(
                            f"节点 {node} 的 AllowedIPs 存在重叠: "
                            f"{peer1}({net1}) 和 {peer2}({net2})"
                        )
    
    def _analyze_routing_paths(self):
        """分析路由路径，确定每个节点可以到达的子网"""
        # 构建连接图
        graph = defaultdict(set)
        peer_allowed_ips = defaultdict(lambda: defaultdict(set))
        
        for peer in self.generated_peers:
            from_node = peer['from']
            to_node = peer['to']
            graph[from_node].add(to_node)
            
            # 记录每个连接的 allowed_ips
            for ip in peer.get('allowed_ips', []):
                peer_allowed_ips[from_node][to_node].add(ip)
        
        # 对每个节点进行路由分析
        for node_name in self._node_map:
            reachable = self._find_reachable_subnets(node_name, graph, peer_allowed_ips)
            self._routing_table[node_name] = reachable
            
            if reachable:
                self.logger.debug(f"节点 {node_name} 可达子网: {reachable}")
    
    def _find_reachable_subnets(self, start_node: str, graph: Dict[str, Set[str]], 
                               peer_allowed_ips: Dict[str, Dict[str, Set[str]]]) -> Set[str]:
        """查找从指定节点可达的所有子网"""
        visited = set()
        reachable = set()
        queue = [(start_node, set())]
        
        while queue:
            current, path = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            # 添加当前节点的子网
            node_group = self._node_groups.get(current)
            if node_group:
                subnet = self._group_subnets.get(node_group)
                if subnet:
                    reachable.add(subnet)
            
            # 探索相邻节点
            for neighbor in graph.get(current, []):
                if neighbor not in path:  # 避免循环
                    # 检查是否可以通过这个连接到达
                    allowed = peer_allowed_ips[current][neighbor]
                    for ip in allowed:
                        reachable.add(ip)
                    
                    new_path = path | {current}
                    queue.append((neighbor, new_path))
        
        return reachable
    
    def _generate_relay_routing_scripts(self):
        """为中继节点生成路由脚本"""
        for node in self.generated_nodes:
            if node.get('role') == 'relay' or node.get('enable_ip_forward'):
                post_up_scripts = []
                post_down_scripts = []
                
                # 启用 IP 转发
                post_up_scripts.append("sysctl -w net.ipv4.ip_forward=1")
                post_down_scripts.append("sysctl -w net.ipv4.ip_forward=0")
                
                # 获取该节点连接的所有子网
                node_name = node['name']
                connected_subnets = set()
                
                for peer in self.generated_peers:
                    if peer['from'] == node_name:
                        for ip in peer.get('allowed_ips', []):
                            if '/' in ip and not ip.endswith('/32'):
                                connected_subnets.add(ip)
                
                # 添加路由规则
                for subnet in connected_subnets:
                    post_up_scripts.append(f"ip route add {subnet} dev %i")
                    post_down_scripts.append(f"ip route del {subnet} dev %i || true")
                
                # 合并用户自定义脚本
                if node.get('post_up'):
                    if isinstance(node['post_up'], list):
                        post_up_scripts.extend(node['post_up'])
                    else:
                        post_up_scripts.append(node['post_up'])
                
                if node.get('post_down'):
                    if isinstance(node['post_down'], list):
                        post_down_scripts.extend(node['post_down'])
                    else:
                        post_down_scripts.append(node['post_down'])
                
                # 更新节点配置
                if post_up_scripts:
                    node['post_up'] = post_up_scripts
                if post_down_scripts:
                    node['post_down'] = post_down_scripts
    
    def to_traditional_format(self) -> Dict[str, Any]:
        """转换为传统的配置格式"""
        return {
            'nodes': self.generated_nodes,
            'peers': self.generated_peers
        }