# WireGuard AllowedIPs 配置最佳实践

## 概述

在WireGuard中，`AllowedIPs`是一个关键配置项，它定义了：
- **对于出站流量**：哪些目标IP地址应该通过这个peer发送
- **对于入站流量**：允许这个peer使用哪些源IP地址

## 常见问题

### 1. 子网重叠
当多个peer的AllowedIPs存在重叠时，会导致路由歧义。

**错误示例**：
```yaml
peers:
  - name: DirectPeer
    allowed_ips: 10.96.0.3/32
  - name: RelayPeer
    allowed_ips: 10.96.0.0/16  # 包含了10.96.0.3！
```

### 2. 双向连接配置错误
自动创建双向连接时使用相同的AllowedIPs会导致配置错误。

**错误示例**：
```yaml
# A->B: allowed_ips = [10.96.0.3/32]
# 自动创建 B->A 时错误地使用相同的 allowed_ips
```

## 最佳实践

### 1. 避免子网重叠
为不同类型的连接使用不重叠的IP范围：

```yaml
peers:
  # 直连peer - 使用具体的/32地址
  - from: A
    to: B
    allowed_ips:
      - 10.96.0.3/32
  
  # 中继连接 - 只路由非直连的子网
  - from: A
    to: Relay
    allowed_ips:
      - 10.96.0.1/32    # 中继节点自身
      - 10.96.4.0/24    # 其他子网
```

### 2. 明确定义双向连接
每个方向应该有自己的AllowedIPs配置：

```yaml
peers:
  # A 到 B
  - from: A
    to: B
    allowed_ips:
      - 10.96.0.3/32    # B的IP
  
  # B 到 A
  - from: B
    to: A
    allowed_ips:
      - 10.96.0.2/32    # A的IP
```

### 3. 中继节点配置
中继节点应该只包含需要通过它访问的网络：

```yaml
# 客户端到中继
- from: Client
  to: Relay
  allowed_ips:
    - 10.96.0.1/32      # 中继节点IP
    - 10.96.4.0/24      # 远程子网1
    - 10.96.8.0/24      # 远程子网2
    # 不包含本地可直达的IP
```

### 4. 使用最小必要原则
只配置实际需要的IP范围，避免使用过大的子网：

```yaml
# 好的做法
allowed_ips:
  - 10.96.0.1/32
  - 10.96.0.2/32
  - 10.96.0.3/32

# 避免（除非确实需要整个子网）
allowed_ips:
  - 10.96.0.0/16
```

## 示例配置

### Mesh网络示例
```yaml
# 三个节点的全连接mesh
peers:
  # A <-> B
  - from: A
    to: B
    endpoint: 192.168.1.11:51820
    allowed_ips: [10.96.0.3/32]
  
  - from: B
    to: A
    endpoint: 192.168.1.10:51820
    allowed_ips: [10.96.0.2/32]
  
  # A <-> C
  - from: A
    to: C
    endpoint: 192.168.1.12:51820
    allowed_ips: [10.96.0.4/32]
  
  - from: C
    to: A
    endpoint: 192.168.1.10:51820
    allowed_ips: [10.96.0.2/32]
  
  # B <-> C
  - from: B
    to: C
    endpoint: 192.168.1.12:51820
    allowed_ips: [10.96.0.4/32]
  
  - from: C
    to: B
    endpoint: 192.168.1.11:51820
    allowed_ips: [10.96.0.3/32]
```

### Hub-and-Spoke示例
```yaml
# 中心节点连接多个分支
peers:
  # 分支1到中心
  - from: Branch1
    to: Hub
    endpoint: hub.example.com:51820
    allowed_ips:
      - 10.0.0.1/32       # Hub IP
      - 10.0.2.0/24       # Branch2 subnet
      - 10.0.3.0/24       # Branch3 subnet
  
  # 分支2到中心
  - from: Branch2
    to: Hub
    endpoint: hub.example.com:51820
    allowed_ips:
      - 10.0.0.1/32       # Hub IP
      - 10.0.1.0/24       # Branch1 subnet
      - 10.0.3.0/24       # Branch3 subnet
```

## 故障排查

### 检查路由表
```bash
# 查看WireGuard接口的路由
ip route show table all | grep wg0

# 查看peer的AllowedIPs
wg show wg0 allowed-ips
```

### 常见错误信息
1. "Packet denied by AllowedIPs" - 检查源IP是否在AllowedIPs中
2. "Multiple peers with overlapping AllowedIPs" - 检查并消除重叠的子网

## 工具支持

本项目的构建器已经修复了以下问题：
1. 不再自动创建具有相同AllowedIPs的双向连接
2. 支持为每个方向单独配置AllowedIPs
3. 在生成配置时会合并重复peer的AllowedIPs

使用时请确保：
- 明确定义每个连接方向
- 使用不重叠的IP范围
- 遵循最小必要原则