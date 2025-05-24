# WireGuard Mesh + 中继节点 D/H 拓扑设计

## 1. 背景与目标

* **部署节点**：A、B、C（同属4级 NAT）；E、F（另一个4级 NAT）；中继节点D、H（公网可达）。
* **连接需求**：

  1. A/B/C间双向直连；E/F间双向直连；A/B/C与E/F不直接互连。
  2. A/B/C通过D或H访问E/F，E/F也可通过D或H访问A/B/C（双向中继）。
  3. D与H双向互联，H为D备份；若D故障，A/B/C仍可经H与E/F互通。
  4. D/H不主动发起连接，仅被动接收并转发。
* **安全策略**：暂不做流量过滤，完整中继转发。

## 2. 拓扑设计

```
[ A,B,C ]
    \       |
     \      | WireGuard peer
      \     |
       >-- D --<\
      /           \
[ E,F ]          [ H ]
      \           /
       \         /
        \       /
         >-----<
      D <--> H 双向互联
```

* A/B/C、E/F各自配置对D、H的Peer。
* D/H各建两个WireGuard接口，分别服务A/B/C与E/F子网，并启用IP转发。

## 3. IP 规划与路由

* 使用**10.96.0.0/20**作为WG虚拟网段：

  * A/B/C：10.96.0.0/22
  * E/F：10.96.4.0/22

### 3.1 静态路由与配置示例

**A/B/C配置**：

```ini
[Interface]
Address = 10.96.0.x/22
PrivateKey = <私钥>

[Peer]
PublicKey = <D公钥>
Endpoint = D_IP:51820
AllowedIPs = 10.96.4.0/22
PersistentKeepalive = 25

[Peer]
PublicKey = <H公钥>
Endpoint = H_IP:51820
AllowedIPs = 10.96.4.0/22
PersistentKeepalive = 25
```

**E/F配置**：

```ini
[Interface]
Address = 10.96.4.x/22
PrivateKey = <私钥>

[Peer]
PublicKey = <D公钥>
Endpoint = D_IP:51820
AllowedIPs = 10.96.0.0/22
PersistentKeepalive = 25

[Peer]
PublicKey = <H公钥>
Endpoint = H_IP:51820
AllowedIPs = 10.96.0.0/22
PersistentKeepalive = 25
```

**D/H配置**（以D为例）：

```bash
# 启用IP转发
sysctl -w net.ipv4.ip_forward=1

# wg0 服务A/B/C子网
ip link add wg0 type wireguard
wg set wg0 private-key /etc/wireguard/d.key listen-port 51820 peer <A/B/C公钥> allowed-ips 10.96.0.0/22
ip addr add 10.96.0.1/22 dev wg0

# wg1 服务E/F子网
ip link add wg1 type wireguard
wg set wg1 private-key /etc/wireguard/d.key listen-port 51821 peer <E/F公钥> allowed-ips 10.96.4.0/22
ip addr add 10.96.4.1/22 dev wg1

# 静态路由
ip route add 10.96.0.0/22 dev wg0
ip route add 10.96.4.0/22 dev wg1
```

### 3.2 负载均衡方案

为了分摊D/H中继节点负载并保证高可用，可选以下几种实现方式：

#### 3.2.1 DNS 轮询

* **原理**：将同一域名（如 `wg.example.com`）解析到D和H两台服务器的公网IP。客户端在每次DNS查询时随机或按顺序获得不同IP。
* **配置示例**（DNS记录）：

  ```dns
  wg.example.com. 60 IN A D_IP
  wg.example.com. 60 IN A H_IP
  ```
* **优点**：实现简单，无需额外组件。
* **缺点**：客户端DNS缓存可能导致短期内流量不均衡，故障检测不及时。

#### 3.2.2 HAProxy UDP 负载均衡

* **原理**：部署一台或多台HAProxy实例，将WireGuard UDP端口流量转发至D/H两台节点。
* **配置示例**（`/etc/haproxy/haproxy.cfg`）：

  ```cfg
  global
      maxconn 4096
  defaults
      mode udp
      timeout client  10s
      timeout server  10s

  frontend wg_frontend
      bind *:51820
      default_backend wg_backends

  backend wg_backends
      balance roundrobin
      server D   D_IP:51820 check
      server H   H_IP:51820 check
  ```
* **优点**：支持健康检查、灵活的调度算法。
* **缺点**：增加中间层，可能引入额外延迟和单点。

#### 3.2.3 Keepalived + VRRP 虚拟 IP

* **原理**：在D/H节点上部署Keepalived，通过VRRP协议共享一个VIP。主节点（D）持有VIP，故障时VIP漂移到备节点（H）。客户端仅连接VIP。
* **配置示例**（`/etc/keepalived/keepalived.conf`）：

  ```conf
  vrrp_script chk_wg {
      script "pidof wireguard"
      interval 2
      weight 2
  }

  vrrp_instance VI_1 {
      state MASTER       # D 上配置 MASTER，H 上将 state 改为 BACKUP
      interface eth0     # 公网网卡
      virtual_router_id 51
      priority 100       # 主节点优先级
      advert_int 1
      authentication {
          auth_type PASS
          auth_pass secret
      }
      virtual_ipaddress {
          198.51.100.10/24  # 共享 VIP
      }
      track_script {
          chk_wg
      }
  }
  ```
* **优点**：客户端配置固定，不受后端节点IP变更影响；自动故障切换。
* **缺点**：仅实现主动/被动切换，无法同时利用两节点带宽。

#### 3.2.4 客户端多Peer策略

* **原理**：在客户端（A/B/C/E/F）配置两个Peer（D和H），AllowedIPs相同，WireGuard内核会对Endpoint做最优选择并在一个Peer失败时切换。
* **示例改动**：已在3.1静态配置中演示。确保 `PersistentKeepalive` 存在，可快速发现Peer故障并重连。

### 3.3 全局可达性与直接直连 全局可达性与直接直连

为了满足「在任意节点通过一个WG内网IP访问A, B, C, D, E, F, H」的需求，可在每个节点上添加两种Peer配置：

#### 3.3.1 仅中继路由模式（默认）

* 客户端（A/B/C/E/F）仅配置对D/H的Peer，AllowedIPs覆盖整个10.96.0.0/20。这样，无论访问哪个节点，流量都会通过D或H中继路由，保证全网可达。

#### 3.3.2 半Mesh模式（组内直连）

* **设计目标**：仅允许组内节点（A/B/C 或 E/F）点对点直连，其它跨组访问仍通过 D/H 中继。
* **优点**：组内低延迟直连；跨组访问无需额外配置即可通过中继转发。
* **缺点**：需要每台节点维护同组内所有节点公钥及Endpoint配置。

#### A/B/C 组配置示例

```ini
[Peer]
# B (组内直连)
PublicKey = <B公钥>
Endpoint  = B_IP:51820
AllowedIPs = 10.96.0.2/32
PersistentKeepalive = 25

[Peer]
# C (组内直连)
PublicKey = <C公钥>
Endpoint  = C_IP:51820
AllowedIPs = 10.96.0.3/32
PersistentKeepalive = 25

[Peer]
# D (跨组中继)
PublicKey = <D公钥>
Endpoint  = D_IP:51820
AllowedIPs = 10.96.4.0/22
PersistentKeepalive = 25

[Peer]
# H (备份中继)
PublicKey = <H公钥>
Endpoint  = H_IP:51820
AllowedIPs = 10.96.4.0/22
PersistentKeepalive = 25
```

#### E/F 组配置示例

```ini
[Peer]
# F (组内直连)
PublicKey = <F公钥>
Endpoint  = F_IP:51820
AllowedIPs = 10.96.4.2/32
PersistentKeepalive = 25

[Peer]
# E (组内直连)
PublicKey = <E公钥>
Endpoint  = E_IP:51820
AllowedIPs = 10.96.4.3/32
PersistentKeepalive = 25

[Peer]
# D (跨组中继)
PublicKey = <D公钥>
Endpoint  = D_IP:51820
AllowedIPs = 10.96.0.0/22
PersistentKeepalive = 25

[Peer]
# H (备份中继)
PublicKey = <H公钥>
Endpoint  = H_IP:51820
AllowedIPs = 10.96.0.0/22
PersistentKeepalive = 25
```

## 5. 配置文件设计

为实现配置驱动的WireGuard生成工具，拆分以下三个配置文件：

### 5.1 节点信息配置 (nodes.json)

* **说明**：

  * `role`：节点类型，`client` 为终端节点（如 A/B/C/E/F/G/I/J/K）、`relay` 为中继节点（D/H）。
  * `wireguard_ip`：WireGuard 虚拟网段内地址。
  * `endpoints`：支持多端口多分组暴露，按 `allowed_peers` 列表自动筛选允许连接来源。

* **Schema 示例**：

```json
{
  "nodes": [
    {
      "name": "A",
      "role": "client",
      "wireguard_ip": "10.96.0.2",
      "endpoints": [
        { "allowed_peers": ["D","H","G"], "endpoint": "A_IP:51820" }
      ]
    },
    {
      "name": "D",
      "role": "relay",
      "wireguard_ip": "10.96.0.1",
      "endpoints": [
        { "allowed_peers": ["A","B","C","G"], "endpoint": "D_client_IP:51820" },
        { "allowed_peers": ["E","F"],         "endpoint": "D_peer_IP:51821" }
      ]
    },
    {
      "name": "H",
      "role": "relay",
      "wireguard_ip": "10.96.4.1",
      "endpoints": [
        { "allowed_peers": ["A","B","C","G"], "endpoint": "H_client_IP:51820" },
        { "allowed_peers": ["E","F"],         "endpoint": "H_peer_IP:51821" }
      ]
    },
    {
      "name": "G",
      "role": "client",
      "wireguard_ip": "10.96.0.5",
      "endpoints": [
        # G 位于 A/B/C 局域网，可直连组内节点
        { "allowed_peers": ["A","B","C"], "endpoint": "G_local_IP:51820" },
        # 通过端口映射对外暴露给 I/J/K 组
        { "allowed_peers": ["I","J","K"], "endpoint": "G_public_IP:51830" }
      ]
    }
    // I/J/K 等其它节点同理添加
  ]
}
```

节点 G 示例展示如何在同组内提供局域网接口，又通过不同端口映射对另一 NAT 组（I/J/K）暴露服务。

### 5.2 拓扑信息配置 (topology.json) 拓扑信息配置 (topology.json) 拓扑信息配置 (topology.json)

* 定义各节点间的Peer关系，以及AllowedIPs范围
* Schema 示例：

```json
{
  "peers": [
    { "from": "A", "to": "B", "allowed_ips": ["10.96.0.3/32"] },
    { "from": "A", "to": "C", "allowed_ips": ["10.96.0.4/32"] },
    { "from": "A", "to": "D", "allowed_ips": ["10.96.4.0/22"] },
    { "from": "A", "to": "H", "allowed_ips": ["10.96.4.0/22"] },
    { "from": "E", "to": "D", "allowed_ips": ["10.96.0.0/22"] }
    // ... 其他 Peer 关系
  ]
}
```

### 5.3 密钥信息配置 (keys.json)

* 存储各节点 WireGuard 私钥、公钥及 PresharedKey
* Schema 示例：

```json
{
  "keys": [
    { "name": "A", "private_key": "...", "public_key": "...", "psk": "..." },
    { "name": "B", "private_key": "...", "public_key": "...", "psk": "..." },
    { "name": "D", "private_key": "...", "public_key": "...", "psk": "..." }
  ]
}
```

## 6. 待确认事项

待确认事项

1. 负载均衡方式选择及部署工具（DNS、HAProxy、Keepalived）。

2. 各节点WireGuard私有与虚拟IP最后分配。

3. 是否启用“零配置全网Mesh模式”以优化直连。

4. 其他容灾或性能测试需求。

5. 负载均衡方式选择及部署工具（DNS、HAProxy、Keepalived）。

6. 各节点WireGuard私有与虚拟IP最后分配。

7. 其他容灾或性能测试需求。

---

请审阅并确认以上配置细节，以便落地部署！
