# WireGuard 智能路由系统设计与实现

## 1. 理论基础

### 1.1 网络拓扑理论

#### Hub-and-Spoke + Mesh 混合架构

```
Group1 (A,B,C) ←→ Hub(D,H) ←→ Group2 (E,F)
     ↑mesh↑              ↑mesh↑
```

**设计原理：**
- **局部 Mesh**：同组内节点直接连接，减少延迟
- **中央 Hub**：跨组通信通过中继节点，简化路由
- **冗余设计**：多个中继节点提供故障切换能力

#### 单向连接模型

**NAT 穿透限制：**
- 客户端（A,B,C,E,F）可以主动连接中继（D,H）
- 中继节点无法主动连接 NAT 后的客户端
- 符合实际网络环境中的连接限制

### 1.2 路由优化理论

#### 多路径路由（Multipath Routing）

**基本概念：**
- **主路径**：默认使用的最优路径
- **备用路径**：主路径故障时的替代路径
- **负载均衡**：在多条路径间分配流量

**度量标准：**
1. **延迟（Latency/RTT）**：数据包往返时间
2. **带宽（Bandwidth）**：链路容量
3. **丢包率（Packet Loss）**：网络可靠性指标
4. **抖动（Jitter）**：延迟变化程度

#### 动态路由选择算法

**路径评分公式：**
```
Score = α × RTT + β × Loss% + γ × Jitter
```

其中：
- α, β, γ 是权重系数
- RTT 越小越好
- Loss% 越小越好
- Jitter 越小越好

**路径选择策略：**
1. **最短路径优先**：选择 RTT 最小的路径
2. **可靠性优先**：选择丢包率最低的路径
3. **综合评分**：基于多个指标的加权评分

## 2. 系统架构设计

### 2.1 模块架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Configuration  │    │  Visualization  │
│                 │    │    Loader       │    │     Engine      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │    Smart Builder Core     │
                    │  ┌─────────────────────┐  │
                    │  │  Route Optimizer    │  │
                    │  │  ┌───────────────┐  │  │
                    │  │  │ Path Analyzer │  │  │
                    │  │  └───────────────┘  │  │
                    │  └─────────────────────┘  │
                    └───────────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │    Configuration Engine   │
                    │  ┌─────────────────────┐  │
                    │  │  Template Renderer  │  │
                    │  │  ┌───────────────┐  │  │
                    │  │  │ Key Manager   │  │  │
                    │  │  └───────────────┘  │  │
                    │  └─────────────────────┘  │
                    └───────────────────────────┘
```

### 2.2 核心组件

#### Smart Builder (`smart_builder.py`)
- **功能**：构建智能对等配置
- **特性**：支持多路径、自动密钥生成
- **算法**：路径分组、优先级排序

#### Route Optimizer (`route_optimizer.py`)
- **功能**：网络性能测量和路径优化
- **特性**：RTT 测量、丢包检测、路径比较
- **输出**：优化建议和性能报告

#### Configuration Engine
- **功能**：配置文件生成和模板渲染
- **特性**：Jinja2 模板、自动化脚本生成
- **输出**：WireGuard 配置、启动脚本、优化脚本

## 3. 实现细节

### 3.1 多路径配置生成

#### 配置文件结构

**节点配置 (`nodes_mesh_relay.json`)：**
```json
{
  "nodes": [
    {
      "name": "A",
      "role": "client",
      "wireguard_ip": "10.96.1.2",
      "endpoints": [
        {
          "name": "group",
          "allowed_peers": ["B","C"],
          "endpoint": "192.168.1.10:51820"
        },
        {
          "name": "relay",
          "allowed_peers": ["D","H"],
          "endpoint": "192.168.1.10:51821"
        }
      ]
    }
  ]
}
```

**拓扑配置 (`topology_multipath.json`)：**
```json
{
  "peers": [
    {
      "from": "A",
      "to": "D",
      "endpoint": "relay",
      "allowed_ips": ["10.96.0.1/32", "10.96.2.0/24"],
      "priority": 1
    },
    {
      "from": "A",
      "to": "H",
      "endpoint": "relay",
      "allowed_ips": ["10.96.0.2/32", "10.96.2.0/24"],
      "priority": 2
    }
  ]
}
```

#### 智能配置构建算法

```python
def build_smart_peer_configs(nodes_path, topology_path, enable_multipath=True):
    # 1. 加载配置和密钥
    nodes = load_nodes(nodes_path)
    peers = load_topology(topology_path)

    # 2. 自动生成缺失的密钥
    for node in nodes:
        if not key_exists(node['name']):
            generate_keypair(node['name'])

    # 3. 按路径分组
    route_groups = group_by_src_dst(peers)

    # 4. 处理多路径
    for (src, dst), relations in route_groups.items():
        if enable_multipath and len(relations) > 1:
            # 主路径 + 备用路径
            primary = min(relations, key=lambda x: x.get('priority', 999))
            backups = [r for r in relations if r != primary]

            add_peer_config(src, dst, primary, is_primary=True)
            for backup in backups:
                add_peer_config(src, dst, backup, is_primary=False)
        else:
            # 单路径
            add_peer_config(src, dst, relations[0])

    return peer_configs
```

### 3.2 路由优化实现

#### 网络测量算法

```python
def ping_test(target_ip, count=5):
    """执行 ping 测试，返回 (平均RTT, RTT标准差, 丢包率)"""
    cmd = ["ping", "-n", str(count), "-w", "3000", target_ip]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 解析 ping 结果
    rtts = extract_rtt_values(result.stdout)

    if rtts:
        avg_rtt = statistics.mean(rtts)
        std_rtt = statistics.stdev(rtts) if len(rtts) > 1 else 0.0
        loss_rate = (count - len(rtts)) / count * 100
        return avg_rtt, std_rtt, loss_rate
    else:
        return float('inf'), float('inf'), 100.0
```

#### 路径评分和选择

```python
def calculate_path_score(rtt, loss, jitter, weights=(1.0, 2.0, 0.5)):
    """计算路径评分，分数越低越好"""
    w_rtt, w_loss, w_jitter = weights

    # 归一化处理
    normalized_rtt = min(rtt / 100.0, 10.0)  # RTT 超过 100ms 视为很差
    normalized_loss = loss / 100.0           # 丢包率百分比
    normalized_jitter = min(jitter / 10.0, 5.0)  # 抖动超过 10ms 视为很差

    score = (w_rtt * normalized_rtt +
             w_loss * normalized_loss +
             w_jitter * normalized_jitter)

    return score

def select_best_route(route_metrics):
    """选择最佳路由"""
    best_route = None
    best_score = float('inf')

    for route in route_metrics:
        if route.packet_loss >= 50:  # 丢包率超过 50% 视为不可用
            continue

        score = calculate_path_score(
            route.rtt_avg,
            route.packet_loss,
            route.rtt_std
        )

        if score < best_score:
            best_score = score
            best_route = route

    return best_route
```

### 3.3 自动化脚本生成

#### 路由优化脚本模板

```bash
#!/bin/bash
# Auto-generated route optimization script
# For node: {node_name}

# Function to test route latency
test_route() {
    local target_ip=$1
    local route_name=$2
    local ping_result=$(ping -c 3 -W 1 $target_ip 2>/dev/null | grep 'avg')
    if [ $? -eq 0 ]; then
        local avg_time=$(echo $ping_result | cut -d'/' -f5)
        echo "Route $route_name: ${avg_time}ms"
        echo $avg_time
    else
        echo "Route $route_name: FAILED"
        echo 9999
    fi
}

# Test all available routes
{route_tests}

# Select best route (lowest latency)
{route_selection}

echo "Route optimization complete."
# TODO: Update WireGuard configuration based on results
```

#### 动态脚本生成算法

```python
def generate_route_script(node_name, peer_configs):
    """生成路由优化脚本"""
    script_lines = [base_template_header]

    # 按目标网络分组
    target_groups = group_peers_by_target(peer_configs)

    for network, peers in target_groups.items():
        if len(peers) > 1:  # 多路径可用
            # 生成测试代码
            for i, peer in enumerate(peers):
                script_lines.append(
                    f"route_{i}_time=$(test_route {network} \"via_{peer['peer_name']}\")"
                )

            # 生成选择逻辑
            script_lines.extend(generate_selection_logic(len(peers)))

    return "\n".join(script_lines)
```

## 4. 使用方法

### 4.1 基础使用

#### 快速开始

```bash
# 1. 生成智能配置（一键完成）
python -m wg_mesh_gen.cli smart-gen \
  -n examples/nodes_mesh_relay.json \
  -t examples/topology_multipath.json \
  -o out_smart

# 2. 查看生成的文件
ls out_smart/
# A.conf  A.sh  A_route_optimizer.sh
# B.conf  B.sh  B_route_optimizer.sh
# ...

# 3. 部署配置到节点
scp out_smart/A.* user@node-a:/etc/wireguard/

# 4. 启动 WireGuard
sudo wg-quick up A

# 5. 运行路由优化
./A_route_optimizer.sh
```

#### 传统方式对比

```bash
# 传统方式（多步骤）
python -m wg_mesh_gen.cli update -n nodes.json     # 生成密钥
python -m wg_mesh_gen.cli gen -n nodes.json -t topology.json -o out  # 生成配置
# 手动选择和优化路径

# 智能方式（一步完成）
python -m wg_mesh_gen.cli smart-gen -n nodes.json -t topology.json -o out
# 自动密钥生成 + 多路径配置 + 路由优化脚本
```

### 4.2 高级配置

#### 自定义路由权重

```python
# 在 route_optimizer.py 中修改权重
weights = (
    1.0,  # RTT 权重
    3.0,  # 丢包率权重（更重要）
    0.5   # 抖动权重
)
```

#### 禁用多路径

```bash
# 生成传统单路径配置
python -m wg_mesh_gen.cli smart-gen \
  -n nodes.json \
  -t topology.json \
  -o out \
  --disable-multipath
```

#### 自定义测量参数

```python
# 在 RouteOptimizer 类中调整
class RouteOptimizer:
    def __init__(self):
        self.ping_count = 10      # 增加 ping 次数提高准确性
        self.ping_timeout = 5     # 增加超时时间
        self.test_interval = 60   # 测试间隔（秒）
```

### 4.3 监控和维护

#### 定期路由优化

```bash
# 添加到 crontab，每 5 分钟优化一次
*/5 * * * * /etc/wireguard/A_route_optimizer.sh >> /var/log/wg_route_opt.log 2>&1
```

#### 性能监控

```bash
# 查看路由优化日志
tail -f /var/log/wg_route_opt.log

# 监控 WireGuard 状态
watch -n 5 'wg show'

# 检查网络连通性
ping -c 5 10.96.2.2  # 测试到对端的连通性
```

#### 故障排除

```bash
# 检查配置文件语法
wg-quick strip A.conf

# 测试特定路径
ping -c 10 -I wg0 10.96.0.1  # 通过 D 节点
ping -c 10 -I wg0 10.96.0.2  # 通过 H 节点

# 查看路由表
ip route show table all | grep wg0
```

## 5. 性能优化

### 5.1 网络层优化

#### MTU 调优

```bash
# 在 WireGuard 配置中设置最优 MTU
[Interface]
MTU = 1420  # 避免分片，提高性能
```

#### 拥塞控制

```bash
# 启用 BBR 拥塞控制算法
echo 'net.core.default_qdisc=fq' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_congestion_control=bbr' >> /etc/sysctl.conf
sysctl -p
```

### 5.2 应用层优化

#### 智能 KeepAlive

```python
# 根据路径类型调整 KeepAlive
def calculate_keepalive(is_primary, base_keepalive=25):
    if is_primary:
        return base_keepalive
    else:
        # 备用路径使用更长的 KeepAlive 减少开销
        return base_keepalive * 2
```

#### 动态路径切换

```python
# 基于性能阈值的自动切换
def should_switch_path(current_rtt, backup_rtt, threshold=1.5):
    """当备用路径比主路径快 50% 以上时切换"""
    return backup_rtt * threshold < current_rtt
```

### 5.3 系统级优化

#### 内核参数调优

```bash
# 网络缓冲区优化
echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_rmem = 4096 87380 134217728' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_wmem = 4096 65536 134217728' >> /etc/sysctl.conf

# UDP 缓冲区优化（WireGuard 使用 UDP）
echo 'net.core.netdev_max_backlog = 5000' >> /etc/sysctl.conf
echo 'net.core.netdev_budget = 600' >> /etc/sysctl.conf
```

#### CPU 亲和性

```bash
# 将 WireGuard 进程绑定到特定 CPU 核心
taskset -c 0,1 wg-quick up A
```

## 6. 扩展和定制

### 6.1 自定义度量算法

#### 带宽测量集成

```python
def measure_bandwidth(target_ip, duration=10):
    """使用 iperf3 测量带宽"""
    cmd = ["iperf3", "-c", target_ip, "-t", str(duration), "-J"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        data = json.loads(result.stdout)
        return data['end']['sum_received']['bits_per_second']
    return 0
```

#### 复合评分算法

```python
def advanced_path_score(rtt, loss, jitter, bandwidth, weights=(1.0, 2.0, 0.5, 1.5)):
    """高级路径评分算法"""
    w_rtt, w_loss, w_jitter, w_bw = weights

    # 归一化处理
    norm_rtt = min(rtt / 100.0, 10.0)
    norm_loss = loss / 100.0
    norm_jitter = min(jitter / 10.0, 5.0)
    norm_bw = max(0, (100_000_000 - bandwidth) / 100_000_000)  # 带宽越高越好

    score = (w_rtt * norm_rtt +
             w_loss * norm_loss +
             w_jitter * norm_jitter +
             w_bw * norm_bw)

    return score
```

### 6.2 集成外部监控

#### Prometheus 指标导出

```python
from prometheus_client import Gauge, start_http_server

# 定义指标
route_rtt = Gauge('wireguard_route_rtt_ms', 'Route RTT in milliseconds', ['src', 'dst', 'via'])
route_loss = Gauge('wireguard_route_loss_percent', 'Route packet loss percentage', ['src', 'dst', 'via'])

def export_metrics(route_metrics):
    """导出路由指标到 Prometheus"""
    for metric in route_metrics:
        route_rtt.labels(
            src=metric.source,
            dst=metric.target,
            via=metric.via
        ).set(metric.rtt_avg)

        route_loss.labels(
            src=metric.source,
            dst=metric.target,
            via=metric.via
        ).set(metric.packet_loss)

# 启动 HTTP 服务器
start_http_server(8000)
```

#### Grafana 仪表板

```json
{
  "dashboard": {
    "title": "WireGuard Smart Routing",
    "panels": [
      {
        "title": "Route RTT",
        "type": "graph",
        "targets": [
          {
            "expr": "wireguard_route_rtt_ms",
            "legendFormat": "{{src}} -> {{dst}} via {{via}}"
          }
        ]
      },
      {
        "title": "Packet Loss",
        "type": "graph",
        "targets": [
          {
            "expr": "wireguard_route_loss_percent",
            "legendFormat": "{{src}} -> {{dst}} via {{via}}"
          }
        ]
      }
    ]
  }
}
```

### 6.3 API 接口

#### RESTful API 设计

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/routes', methods=['GET'])
def get_routes():
    """获取所有路由信息"""
    routes = get_current_routes()
    return jsonify(routes)

@app.route('/api/routes/optimize', methods=['POST'])
def optimize_routes():
    """触发路由优化"""
    node = request.json.get('node')
    result = run_route_optimization(node)
    return jsonify(result)

@app.route('/api/routes/switch', methods=['POST'])
def switch_route():
    """手动切换路由"""
    src = request.json.get('src')
    dst = request.json.get('dst')
    via = request.json.get('via')

    result = switch_route_manually(src, dst, via)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## 7. 未来发展方向

### 7.1 机器学习集成

#### 智能路径预测

```python
import tensorflow as tf
from sklearn.ensemble import RandomForestRegressor

class RoutePredictor:
    """基于历史数据预测最优路径"""

    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100)
        self.features = ['time_of_day', 'day_of_week', 'historical_rtt', 'historical_loss']

    def train(self, historical_data):
        """训练预测模型"""
        X = self.extract_features(historical_data)
        y = self.extract_labels(historical_data)
        self.model.fit(X, y)

    def predict_best_route(self, current_context):
        """预测当前最优路径"""
        features = self.extract_features([current_context])
        prediction = self.model.predict(features)
        return prediction[0]
```

#### 自适应权重调整

```python
class AdaptiveWeightOptimizer:
    """自适应调整路由评分权重"""

    def __init__(self):
        self.weights = {'rtt': 1.0, 'loss': 2.0, 'jitter': 0.5}
        self.performance_history = []

    def update_weights(self, route_performance):
        """基于实际性能调整权重"""
        # 使用强化学习算法调整权重
        reward = self.calculate_reward(route_performance)
        self.adjust_weights_based_on_reward(reward)

    def calculate_reward(self, performance):
        """计算性能奖励"""
        # 综合考虑用户体验指标
        return -performance['avg_rtt'] - 10 * performance['loss_rate']
```

### 7.2 分布式协调

#### 集群路由协调

```python
class DistributedRouteCoordinator:
    """分布式路由协调器"""

    def __init__(self, cluster_nodes):
        self.cluster_nodes = cluster_nodes
        self.consensus_algorithm = RaftConsensus()

    def coordinate_route_changes(self, proposed_changes):
        """协调集群内的路由变更"""
        # 使用 Raft 算法达成共识
        consensus = self.consensus_algorithm.propose(proposed_changes)

        if consensus.accepted:
            self.apply_route_changes(proposed_changes)
            return True
        return False

    def share_performance_data(self, local_metrics):
        """共享性能数据到集群"""
        for node in self.cluster_nodes:
            node.receive_metrics(local_metrics)
```

### 7.3 安全增强

#### 路由安全验证

```python
class RouteSecurityValidator:
    """路由安全验证器"""

    def __init__(self):
        self.trusted_relays = set(['D', 'H'])
        self.security_policies = self.load_security_policies()

    def validate_route(self, route_path):
        """验证路由路径的安全性"""
        # 检查路径是否通过可信中继
        for hop in route_path:
            if hop.node_type == 'relay' and hop.node_id not in self.trusted_relays:
                return False, f"Untrusted relay: {hop.node_id}"

        # 检查路径长度
        if len(route_path) > self.security_policies['max_hops']:
            return False, "Route too long"

        return True, "Route validated"

    def detect_route_anomalies(self, current_routes, historical_routes):
        """检测路由异常"""
        anomalies = []

        for route in current_routes:
            if self.is_anomalous_route(route, historical_routes):
                anomalies.append(route)

        return anomalies
```

这个智能路由系统为 WireGuard 网络提供了完整的多路径支持、自动优化和扩展能力，能够适应各种复杂的网络环境和需求。