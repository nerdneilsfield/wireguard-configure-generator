# WireGuard 连接验证指南

## 问题解决：双向密钥配置

### 原始问题
之前的配置存在一个关键问题：虽然客户端（A、B、C、E、F）可以主动连接到中继节点（D、H），但中继节点没有客户端的公钥和 PSK，导致连接无法建立。

### WireGuard 连接原理
WireGuard 连接是**双向认证**的：
1. **发起方**需要目标的公钥、PSK 和 endpoint
2. **接收方**需要发起方的公钥和 PSK（但不需要 endpoint）
3. 双方都必须有对方的密钥才能建立连接

### 解决方案：被动连接配置

#### 配置类型说明

**主动连接（Active Connection）**：
```ini
[Peer]
# D via relay
PublicKey = 6OertAhECJX5472uSfFcsGRp13y6yNvIyxLvFiHhR3A=
PresharedKey = GKB3GE/e/BEJyDJ0BGIKT8h8WVzCq1nYXlvNkm6QP0k=
Endpoint = 203.0.113.5:51820          # 有 endpoint
AllowedIPs = 10.96.0.1/32,10.96.2.0/24
PersistentKeepalive = 25               # 有 keepalive
```

**被动连接（Passive Connection）**：
```ini
[Peer]
# A (passive connection - no endpoint)
PublicKey = zTka9nwja46fi2/ewtuX0IeeIYlXLK8ObJh130pcl3U=
PresharedKey = uAxR3rqGICHcBc5o/M3azdkoIVUDhgXWbdMwsnaI+Eo=
AllowedIPs = 10.96.1.2/32             # 没有 endpoint
                                       # 没有 keepalive
```

## 修复后的配置结构

### 客户端配置（以 A 为例）

```ini
[Interface]
Address = 10.96.1.2
PrivateKey = QDc6kmgvyQDdbuC3afuF/A3C1q1TnextBzp/4Jlw4HU=
ListenPort = 51820

# 同组 mesh 连接
[Peer]
# B via group
PublicKey = VAMJ5bbXR2pkZToXPB3AjmpHnqSsj+N7fYTHn7pag3E=
PresharedKey = gMkHPLaIh+hogdqxsDPFIYxbenvWLnUqXcUL+4n1TEk=
Endpoint = 192.168.1.11:51820
AllowedIPs = 10.96.1.3/32
PersistentKeepalive = 25

# 主路径到中继 D
[Peer]
# D via relay
PublicKey = 6OertAhECJX5472uSfFcsGRp13y6yNvIyxLvFiHhR3A=
PresharedKey = GKB3GE/e/BEJyDJ0BGIKT8h8WVzCq1nYXlvNkm6QP0k=
Endpoint = 203.0.113.5:51820
AllowedIPs = 10.96.0.1/32,10.96.2.2/32,10.96.2.3/32
PersistentKeepalive = 25

# 备用路径到中继 H
[Peer]
# H via relay
PublicKey = pRWwBfbsGKni6uesyP+Luml7GcPkayuvdALQHmd62mI=
PresharedKey = CP9N+bYJqyln/8KvfaEixr7exogMWApVGT7Hc8VFHXk=
Endpoint = 198.51.100.10:51820
AllowedIPs = 10.96.0.2/32,10.96.2.2/32,10.96.2.3/32
PersistentKeepalive = 25
```

### 中继节点配置（以 D 为例）

```ini
[Interface]
Address = 10.96.0.1
PrivateKey = uLSQyaCJ1/+nllpEe9xJY6iLqtDMkgHYxQO9WDhYZnI=
ListenPort = 51820

# 被动连接：只有密钥，等待客户端连接
[Peer]
# A (passive connection - no endpoint)
PublicKey = zTka9nwja46fi2/ewtuX0IeeIYlXLK8ObJh130pcl3U=
PresharedKey = uAxR3rqGICHcBc5o/M3azdkoIVUDhgXWbdMwsnaI+Eo=
AllowedIPs = 10.96.1.2/32

[Peer]
# B (passive connection - no endpoint)
PublicKey = VAMJ5bbXR2pkZToXPB3AjmpHnqSsj+N7fYTHn7pag3E=
PresharedKey = gMkHPLaIh+hogdqxsDPFIYxbenvWLnUqXcUL+4n1TEk=
AllowedIPs = 10.96.1.3/32

# ... 其他客户端的被动连接

# 主动连接：到其他中继节点
[Peer]
# H via relay
PublicKey = pRWwBfbsGKni6uesyP+Luml7GcPkayuvdALQHmd62mI=
PresharedKey = CP9N+bYJqyln/8KvfaEixr7exogMWApVGT7Hc8VFHXk=
Endpoint = 198.51.100.10:51820
AllowedIPs = 10.96.0.2/32
PersistentKeepalive = 25
```

## 连接流程验证

### 1. A 连接到 D 的过程

1. **A 发起连接**：
   - A 使用 D 的公钥加密数据
   - A 向 `203.0.113.5:51820` 发送握手包
   - A 使用 PSK 进行额外认证

2. **D 响应连接**：
   - D 收到来自 A 的握手包
   - D 在配置中找到 A 的公钥和 PSK
   - D 验证 A 的身份并响应握手
   - 连接建立成功

### 2. 跨组通信：A 访问 E

1. **路由查找**：A 要访问 E（10.96.2.2）
2. **路径选择**：根据 AllowedIPs，流量通过 D 或 H
3. **数据转发**：
   - A → D：通过已建立的 WireGuard 隧道
   - D → E：D 作为中继转发数据
   - E ← D ← A：返回路径

### 3. 故障切换：D 掉线时

1. **检测故障**：A 检测到 D 连接超时
2. **路径切换**：A 自动使用备用路径通过 H
3. **重新路由**：A → H → E 的新路径建立

## 配置验证方法

### 1. 语法验证

```bash
# 检查配置文件语法
wg-quick strip A.conf
wg-quick strip D.conf
```

### 2. 连接测试

```bash
# 启动 WireGuard
sudo wg-quick up A
sudo wg-quick up D

# 检查连接状态
sudo wg show

# 测试连通性
ping 10.96.0.1  # A ping D
ping 10.96.2.2  # A ping E (通过 D)
```

### 3. 路由验证

```bash
# 查看路由表
ip route show table all | grep wg0

# 追踪路径
traceroute 10.96.2.2

# 监控流量
sudo tcpdump -i wg0
```

## 故障排除

### 常见问题

1. **握手失败**
   ```
   [#] wg show
   peer: pRWwBfbsGKni6uesyP+Luml7GcPkayuvdALQHmd62mI=
     endpoint: 198.51.100.10:51820
     allowed ips: 10.96.0.2/32
     latest handshake: 1 minute, 23 seconds ago  # 正常
   ```

2. **公钥不匹配**
   ```
   # 检查公钥是否一致
   wg pubkey < /etc/wireguard/A_private.key
   ```

3. **PSK 不匹配**
   ```
   # 重新生成 PSK
   wg genpsk
   ```

### 调试命令

```bash
# 详细日志
sudo wg-quick up A --verbose

# 内核日志
dmesg | grep wireguard

# 网络命名空间测试
sudo ip netns exec test-ns ping 10.96.2.2
```

## 性能优化建议

### 1. MTU 优化

```ini
[Interface]
MTU = 1420  # 避免分片
```

### 2. 缓冲区调优

```bash
# 增加网络缓冲区
echo 'net.core.rmem_max = 26214400' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 26214400' >> /etc/sysctl.conf
```

### 3. CPU 亲和性

```bash
# 绑定 WireGuard 到特定 CPU
echo 2 > /proc/irq/24/smp_affinity
```

## 安全考虑

### 1. 密钥管理

- 定期轮换 PSK
- 使用硬件安全模块（HSM）存储私钥
- 实施密钥托管策略

### 2. 网络隔离

- 使用防火墙限制 AllowedIPs
- 实施网络分段
- 监控异常流量

### 3. 访问控制

- 基于时间的访问控制
- 多因素认证集成
- 审计日志记录

这个修复确保了 WireGuard 网络的正确连接，解决了密钥配置不完整的问题。
