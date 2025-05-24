# 1. 详细需求说明 (Detailed Requirements)

**1.1 性能指标**  

- 每次“生成配置”操作应在 **N** 秒内完成（取决于节点数量，一般规模不大的话应在 1~2 秒）。  
- 可以同时对 **M** 个节点进行配置生成，不出现明显卡顿。  

**1.2 安全策略**  

- `wg_data.json`（存储私钥、公钥、PSK 等）必须设置合适的文件权限；  
- 如果要在日志中输出关键信息，需避免打印私钥或带敏感字段的内容；  
- CLI 命令中若设置 `--show-secrets` 才能查看私钥，默认应隐藏或掩码处理。  

**1.3 异常处理**  

- TOML 或 JSON 解析失败：立即报错并退出 CLI，给出可读的错误信息；  
- 缺少必要字段（如节点名、网卡 IP）时，提示用户检查配置；  
- 多网卡情况：如果配置信息中声明要使用 `eth1` 但并未在对应节点下找到该网卡，也要报错提醒。  

**1.4 其他需求**  

- 兼容 Python 3.9+；  
- 支持自定义模板目录；若用户不给出模板，提供内置示例模板；  
- 需提供日志等级（debug/info/warning/error）切换。

---

# 2. 数据结构 / 数据模型文档

假设我们使用 **Pydantic** 进行类型校验，下面给出一个示例模型定义（仅作参考）：

```python
# models.py
from pydantic import BaseModel, Field
from typing import List, Optional

class InterfaceModel(BaseModel):
    interface_name: str
    ip_address: str
    port: int

class ServerModel(BaseModel):
    name: str
    interfaces: List[InterfaceModel]
    # 是否需要更多服务器端字段...

class ClientModel(BaseModel):
    name: str
    interfaces: List[InterfaceModel]
    # 是否需要更多客户端字段...

class NetworkConfig(BaseModel):
    name: str
    default_port: int
    mesh_enabled: bool

class TomlConfig(BaseModel):
    logging: dict             # {"level": "info", "file": ...}
    templates: dict           # {"dir": "./templates"}
    network: NetworkConfig
    server: List[ServerModel] # 可视需求改成只允许一个server，也可支持多server
    client: List[ClientModel]

# JSON 数据结构
class NodeDynamicData(BaseModel):
    name: str
    privkey: Optional[str]
    pubkey: Optional[str]
    psk: Optional[str]
    mesh_peers: List[str]

class JsonData(BaseModel):
    server: NodeDynamicData
    clients: List[NodeDynamicData]
```

- **字段取值范围**  
  - `port` 通常在 1~65535 之间。  
  - `ip_address` 需是可解析的 IPv4/IPv6 地址（可考虑使用正则或专门的 IP 字段校验）。  
  - `mesh_peers` 存放其他节点名称的字符串列表，可为空。

- **可选参数**  
  - `psk` 如果不使用预共享密钥，可以不填或置为 `None`；  
  - `logging.file` 可以为空字符串，表示只输出到 stdout。

---

# 3. 接口设计 / API 约定 (API Specs)

如果我们要提供 **HTTP API**（例如基于 FastAPI），可以这样定义：  

```
POST /api/v1/nodes
  - body: { "name": "clientC", "interfaces": [...], ... }
  - response: { "message": "Node created", "node_id": 123 }

GET /api/v1/nodes/{node_name}
  - response: { "name": "...", "privkey": "...", "pubkey": "...", ... }

PUT /api/v1/nodes/{node_name}
  - body: { "mesh_peers": ["clientA", "clientB"] }
  - response: { "message": "Node updated" }

POST /api/v1/generate
  - body: { "output_dir": "..." } // 也可不传
  - response: { "message": "Config generated", "files": [...] }
```

- **请求参数**  
  - `query` 参数用于分页、过滤等（若有需要）；  
  - `body` 参数通常是 JSON，包含节点信息或输出目录设定。  

- **返回格式**  
  - 一般返回 JSON，附带 `message`、`data` 或错误信息；  
  - 若生成配置成功，可返回生成的文件名列表或访问 URL。  

- **异常 / 错误码**  
  - 400 (Bad Request)：当请求体缺少必要字段；  
  - 404 (Not Found)：当查无此节点；  
  - 500 (Server Error)：内部异常（解析 TOML/JSON 失败等）。

如果暂时只需 CLI，不做 HTTP API，可跳过该部分。若日后需要 Web/GUI，可参照此思路。

---

# 4. 系统架构 / 模块划分 (Architecture / High-level Design)

```
                +---------------------+
                |   CLI / Web / GUI  |
                +---------+----------+
                          | (调用)
                          v
                   +-------------+
                   |   Core.py   |
                   |(核心业务逻辑|
                   |合并TOML+JSON)
                   +------+------+
                          |
             +------------+------------+
             |                         |
             v                         v
  +--------------------+     +------------------+
  | Toml Config Loader |     | Json Data Loader |
  +--------------------+     +------------------+
       ^              ^            ^         ^
       | (读取文件)   |            |         |
       |             |            |         |
 +------+-------+  +---+       +----+    +-------+
 | wg_manager.  |  |   |       |    |    |  FS/OS|
 |toml          |  |   |       |    |    | (存储)|
 +--------------+  +---+       +----+    +-------+

```

- **CLI / Web / GUI**：多个前端入口；核心功能仍在 `core.py`；  
- **Core.py**：  
  - 合并 TOML 中节点信息 + JSON 中密钥 + 用户设置；  
  - 调用 `render.py` 生成配置文件；  
  - 在多网卡 / mesh_peers 情况下进行逻辑判断。  
- **TomlConfigLoader / JsonDataLoader**：解耦读取与校验逻辑；  
- **文件系统**：存放 TOML、JSON、模板文件、以及生成的 `.conf`。  

若有更多模块（如 `logging_manager.py`、`keys_manager.py`），可在图中继续扩展。

---

# 5. 流程图 / 时序图 (Flowchart / Sequence Diagram)

### 5.1 生成配置流程图

```
┌───────────────────┐
│ CLI: wg-mesh gen  │
└─────────┬─────────┘
          │
          v
┌───────────────────┐
│Load Toml Config   │
└─────────┬─────────┘
          │
          v
┌───────────────────┐
│Load JSON Data     │
└─────────┬─────────┘
          │
          v
┌──────────────────────────────────┐
│Validate/merge Node Info & Keys  │
├──────────────────────────────────┤
│If missing keys => Gen & Save    │
└─────────┬───────────────────────┘
          │
          v
┌──────────────────────────────────┐
│Mesh logic: build peer mapping   │
└─────────┬───────────────────────┘
          │
          v
┌──────────────────────────────────┐
│Render with Jinja2 => *.conf     │
└─────────┬───────────────────────┘
          │
          v
┌──────────────────────────────────┐
│Output success or error          │
└──────────────────────────────────┘
```

---

# 6. 示例输入输出 / 测试用例 (Examples / Test Cases)

### 6.1 场景：单网卡 Server + 客户端

- **输入**  
  - `wg_manager.toml`:

    ```toml
    [network]
    name = "test-net"
    default_port = 51820
    mesh_enabled = false

    [[server]]
    name = "wg-server-1"
    [[server.interfaces]]
    interface_name = "eth0"
    ip_address = "1.2.3.4"
    port = 51820

    [[client]]
    name = "clientA"
    [[client.interfaces]]
    interface_name = "eth0"
    ip_address = "10.0.0.2"
    port = 51820
    ```

  - `wg_data.json`:

    ```json
    {
      "server": {
        "name": "wg-server-1",
        "privkey": null,
        "pubkey": null,
        "psk": null,
        "mesh_peers": []
      },
      "clients": [
        {
          "name": "clientA",
          "privkey": null,
          "pubkey": null,
          "psk": null,
          "mesh_peers": []
        }
      ]
    }
    ```

- **期望输出**  
  - CLI：`wg-mesh generate`  
  - 自动生成 server 及 client 密钥，并写回 `wg_data.json`；  
  - 在 `out/` 目录下生成 `wg-test-net-server-wg-server-1.conf`、`wg-test-net-client-clientA.conf`；  
  - 结果配置里 `[Peer]` 仅 server<->client 相互对接，client 不对其他节点 Mesh。

### 6.2 场景：多网卡 + Mesh

- **输入**  
  - `wg_manager.toml`: server 拥有 `eth0`、`eth1`; clientA、clientB 各有一个接口； `mesh_enabled = true`。  
  - `wg_data.json`: clientA 的 `mesh_peers = ["clientB"]`; clientB 的 `mesh_peers = ["clientA"]`; server 没有 mesh_peers。  
- **期望输出**  
  - 生成 3 份配置，clientA 与 clientB 彼此在 `[Peer]` 中都有对方信息；  
  - server 配置中包含 clientA、clientB 的 `[Peer]`；  
  - client 里还指定 Endpoint = server 的 `eth0` IP/port (或者 `eth1`，根据逻辑规则)。

### 6.3 异常情况

- 缺失 `name` 或 `ip_address`：命令行应报错，退出，提示“配置文件中缺少节点必填字段”。  
- 端口字段非数值：报错“端口需为整数类型”。  
- JSON 中有节点名“clientC”，但 TOML 未定义“clientC”，则提示不匹配，要求用户手动处理或自动删除 JSON 节点。

---

# 7. 配置文件示例 (Configuration Example)

**7.1 TOML 示例**  

```toml
[logging]
level = "debug"
file = "logs/wg_manager.log"

[templates]
dir = "./templates"

[network]
name = "my-wg-network"
default_port = 51820
mesh_enabled = true

[[server]]
name = "wg-server-1"
[[server.interfaces]]
interface_name = "eth0"
ip_address = "1.2.3.4"
port = 51820

[[server.interfaces]]
interface_name = "eth1"
ip_address = "10.0.0.5"
port = 51821

[[client]]
name = "clientA"
[[client.interfaces]]
interface_name = "eth0"
ip_address = "10.0.0.2"
port = 51820

[[client]]
name = "clientB"
[[client.interfaces]]
interface_name = "eth0"
ip_address = "10.0.0.3"
port = 51820
```

**7.2 JSON 示例**  

```json
{
  "server": {
    "name": "wg-server-1",
    "privkey": "XXX",
    "pubkey": "YYY",
    "psk": "ZZZ",
    "mesh_peers": []
  },
  "clients": [
    {
      "name": "clientA",
      "privkey": "AAA",
      "pubkey": "BBB",
      "psk": "CCC",
      "mesh_peers": ["clientB"]
    },
    {
      "name": "clientB",
      "privkey": "DDD",
      "pubkey": "EEE",
      "psk": "FFF",
      "mesh_peers": ["clientA"]
    }
  ]
}
```
