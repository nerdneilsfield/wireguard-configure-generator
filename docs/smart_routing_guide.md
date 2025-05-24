# WireGuard 智能路由配置指南

## 概述

本项目现在支持智能路由配置，可以自动生成多路径 WireGuard 配置并提供路由优化功能。

## 主要特性

### ✅ 已解决的问题

1. **自动密钥生成**：`gen` 和 `smart-gen` 命令现在会自动生成缺失的密钥
2. **多路径路由**：支持为每个目标配置多条路径（主路径 + 备用路径）
3. **路由优化脚本**：自动生成路由测量和优化脚本
4. **CLI 参数继承**：所有子命令都支持 `-n`, `-t`, `-o` 参数覆盖

### 🚀 新功能

#### 1. 智能配置生成 (`smart-gen`)

```bash
# 生成智能配置（支持多路径）
python -m wg_mesh_gen.cli smart-gen \
  -n examples/nodes_mesh_relay.json \
  -t examples/topology_multipath.json \
  -o out_smart

# 禁用多路径（传统模式）
python -m wg_mesh_gen.cli smart-gen \
  -n examples/nodes_mesh_relay.json \
  -t examples/topology_multipath.json \
  -o out_smart \
  --disable-multipath
```

#### 2. 路由优化脚本

每个节点都会生成一个 `{节点名}_route_optimizer.sh` 脚本：

```bash
# 在节点 A 上运行路由优化
./A_route_optimizer.sh
```

脚本功能：
- 自动测量到各目标的延迟
- 比较多条路径的性能
- 推荐最优路径选择

## 网络架构

### 当前实现的拓扑

```
Group1 (A,B,C) ←→ Hub(D,H) ←→ Group2 (E,F)
     ↑mesh↑              ↑mesh↑
```

**特点：**
- A,B,C 内部 mesh 连接
- E,F 内部 mesh 连接  
- A,B,C,E,F 可以连接到 D,H（单向）
- D,H 互联（双向，提供冗余）

### 路由策略

#### 单路径模式（传统）
- A→E：A→D→E（固定路径）
- A→F：A→D→F（固定路径）

#### 多路径模式（智能）
- A→E：可选择 A→D→E 或 A→H→E
- A→F：可选择 A→D→F 或 A→H→F
- 自动测量选择最优路径

## 配置文件说明

### 多路径拓扑配置

```json
{
  "peers": [
    {
      "from": "A", 
      "to": "D", 
      "endpoint": "relay", 
      "allowed_ips": ["10.96.0.1/32", "10.96.2.2/32", "10.96.2.3/32"], 
      "priority": 1
    },
    {
      "from": "A", 
      "to": "H", 
      "endpoint": "relay", 
      "allowed_ips": ["10.96.0.2/32", "10.96.2.2/32", "10.96.2.3/32"], 
      "priority": 2
    }
  ]
}
```

**关键字段：**
- `priority`: 路径优先级（1=主路径，2=备用路径）
- `allowed_ips`: 精确指定可达的目标IP

## 使用流程

### 1. 基础配置生成

```bash
# 传统方式（需要先生成密钥）
python -m wg_mesh_gen.cli update -n examples/nodes_mesh_relay.json
python -m wg_mesh_gen.cli gen -n examples/nodes_mesh_relay.json -t examples/topology_new.json -o out

# 新方式（自动生成密钥）
python -m wg_mesh_gen.cli gen -n examples/nodes_mesh_relay.json -t examples/topology_new.json -o out
```

### 2. 智能配置生成

```bash
# 生成支持多路径的智能配置
python -m wg_mesh_gen.cli smart-gen \
  -n examples/nodes_mesh_relay.json \
  -t examples/topology_multipath.json \
  -o out_smart
```

### 3. 可视化拓扑

```bash
# 生成拓扑图
python -m wg_mesh_gen.cli vis \
  -n examples/nodes_mesh_relay.json \
  -t examples/topology_new.json \
  -i topology.png \
  -l shell
```

### 4. 路由优化

在每个节点上运行生成的优化脚本：

```bash
# 在节点 A 上
./A_route_optimizer.sh

# 输出示例：
# Testing routes to 10.96.2.2...
# Route via_D: 15.2ms
# Route via_H: 12.8ms
# Best route to 10.96.2.2: Route 1 (12.8ms)
```

## 高级功能

### 路由度量和优化

路由优化器会测量：
- **RTT（往返时间）**：延迟越低越好
- **丢包率**：丢包越少越好
- **稳定性**：RTT 标准差越小越好

### 动态路由切换

未来可以扩展为：
1. **定期测量**：cron 任务定期运行优化脚本
2. **自动切换**：基于测量结果自动更新 WireGuard 配置
3. **故障检测**：检测到路径故障时自动切换到备用路径

## 故障排除

### 常见问题

1. **密钥不存在错误**
   ```
   ValueError: No KeyPair for node 'A'
   ```
   **解决**：使用新的 `gen` 或 `smart-gen` 命令，会自动生成密钥

2. **模板找不到错误**
   ```
   TemplateNotFound: 'interface.conf.j2'
   ```
   **解决**：确保在项目根目录运行命令

3. **endpoint 不匹配错误**
   ```
   ValueError: Endpoint 'relay' not found for node 'D'
   ```
   **解决**：检查 nodes.json 和 topology.json 中的 endpoint 名称是否一致

### 调试技巧

```bash
# 验证配置文件
python -m wg_mesh_gen.cli valid -n examples/nodes_mesh_relay.json -t examples/topology_new.json

# 查看生成的配置
cat out_smart/A.conf

# 测试路由优化脚本
bash out_smart/A_route_optimizer.sh
```

## 下一步计划

1. **实时路由切换**：基于网络状况自动切换路径
2. **带宽测量**：除了延迟，还测量带宽
3. **Web 界面**：提供图形化的路由管理界面
4. **监控集成**：与 Prometheus/Grafana 集成
5. **负载均衡**：在多条路径间分配流量
