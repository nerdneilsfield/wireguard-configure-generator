# **PRD：基于 TOML + JSON 的 WireGuard Mesh 管理工具**

## 1. 产品概述

### 1.1 背景

- 目前需要对多节点进行 WireGuard 配置管理，且要求支持 **Mesh 拓扑**、**多网卡**、**灵活的日志** 等；  
- 用户希望把可读性高、易手动编辑的 **TOML** 用于定义节点、网卡、网络等 “静态” 信息；  
- 所有自动生成或经常变动的敏感数据（如 **私钥、公钥、PSK** 等）则存放在 **JSON** 文件中，以区分手动配置与程序生成数据的来源；  
- 最终通过 **Jinja2** 渲染生成 `.conf` 文件，可命令行和编程调用；  
- 期望后续能扩展出 GUI / Web 接口，以及自动化打包成 **wheel** 发布。

### 1.2 目标

1. **配置分离**  
   - `wg_manager.toml`：用户手动维护的主要节点/网卡/网络配置；  
   - `wg_data.json`：程序维护的密钥及动态信息。  
2. **多网卡多节点支持**  
   - 每个节点可定义多块网卡（IP、端口、路由等），并在 Mesh 模式下灵活指定要连接哪块网卡。  
3. **Jinja2 模板**  
   - 使生成的 WireGuard 配置更灵活；可根据节点角色、路由需求（全局/内网/混合）自动生成对应 `.conf`。  
4. **Pydantic 校验**  
   - 对 TOML 读入的数据进行类型校验，保证节点信息、网卡信息等字段完整正确。  
5. **CLI + API**  
   - CLI：`wg-mesh` 等命令行入口；  
   - 同时也能在 Python 里 `import wg_manager` 来调用核心逻辑。  
6. **日志管理**  
   - 支持多种日志级别（debug/info/warning/error），并可选择输出到文件或控制台。  
7. **扩展性**  
   - 后续可对接 GUI / Web 界面，仅需复用同一套核心逻辑；  
   - 自动打包成 wheel，发布到 PyPI 或私有仓库，方便安装与维护。

---

## 2. 功能需求

### 2.1 静态配置 (TOML)

- **用途**：手动定义节点与网卡信息，以及通用参数（如网络名、默认端口等），并指定日志级别、模板目录等。  
- **示例**（`wg_manager.toml`）：

  ```toml
  [logging]
  level = "info"
  file = ""       # 若为空，输出到 stdout；否则写到指定文件

  [templates]
  dir = "./templates"

  [network]
  name = "my-wg-network"
  default_port = 51820
  mesh_enabled = true

  [[server]]
  name = "wg-server-1"
  # 多网卡信息
  [[server.interfaces]]
  interface_name = "eth0"
  ip_address = "1.2.3.4"
  port = 51820

  [[server.interfaces]]
  interface_name = "eth1"
  ip_address = "192.168.10.10"
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

### 2.2 动态数据 (JSON)

- **用途**：存储程序生成或经常变动的敏感信息。例如：  
  - 私钥 / 公钥 / PSK；  
  - 节点连接信息（如 `mesh_peers` 也可放在这里，或依需求放在 TOML 中）；  
  - 其他程序自动更新的数据。  
- **示例**（`wg_data.json`）：

  ```json
  {
    "server": {
      "name": "wg-server-1",
      "privkey": "...",
      "pubkey": "...",
      "psk": "...",
      "mesh_peers": []   // 如果服务器需要对等节点，也可在此管理
    },
    "clients": [
      {
        "name": "clientA",
        "privkey": "...",
        "pubkey": "...",
        "psk": "...",
        "mesh_peers": ["clientB"]
      },
      {
        "name": "clientB",
        "privkey": "...",
        "pubkey": "...",
        "psk": "...",
        "mesh_peers": []
      }
    ]
  }
  ```

### 2.3 多网卡与 Mesh

1. **多网卡**  
   - 在 `wg_manager.toml` 中，每个节点（server/client）可有多个 `interfaces`；  
   - 当生成配置时，需要对 `interfaces` 进行遍历，或根据某逻辑挑选出要暴露给对端的 IP + 端口。  
2. **Mesh**  
   - 由 JSON 中的 `mesh_peers` 字段决定各节点要与哪些对端直连；  
   - 生成 `[Peer]` 配置时，需要在 `TOML` 中读取对端节点的网卡信息（可能多个）并选择合适的 IP/端口；  
   - 可选择：  
     - **集中式**（仅 server 里存有所有 peer 的 `[Peer]`，client 间不直连），或  
     - **完全网状**（每个 client 都对等连接其他 client）。  
   - 也可在后续添加更复杂的逻辑（优先内网 IP，无效则用公网 IP 等）。

### 2.4 模板 (Jinja2)

- **模板存放**：`templates/`，包含：  
  - `server.conf.j2`、`client.conf.j2`、`mesh.conf.j2` 等（视需求拆分）。  
- **渲染逻辑**：  
  1. 载入 `wg_manager.toml`（静态信息）+ `wg_data.json`（动态信息）到内存；  
  2. 结合（server + clients）与其网卡列表 / 密钥等数据，生成渲染上下文；  
  3. 针对每个节点或网卡渲染对应 `.conf` 文件；  
  4. 输出到指定目录（可在 TOML `[templates]` 或 `[network]` 中指定 `output_dir`）。

### 2.5 CLI & API

1. **CLI**（示例采用 Typer）  
   - `wg-mesh init`：生成示例 `wg_manager.toml` 与 `wg_data.json`、`templates/` 目录；  
   - `wg-mesh add-node --name clientC --interface eth0 --ip 10.0.0.4 --port 51820`：更新 `wg_manager.toml` 或提示用户手动编辑；  
   - `wg-mesh genkey --node clientC`：如该节点在 JSON 中缺少私钥/公钥，就自动生成并写回；  
   - `wg-mesh generate --config wg_manager.toml --data wg_data.json --output out/`：合并两份配置，生成 .conf；  
   - `wg-mesh set-log-level debug`：动态调节日志级别；  
   - 等等。  
2. **API**  
   - 在 Python 里 `import wg_manager` 调用核心函数，如：  

     ```python
     from wg_manager.core import load_toml_config, load_json_data, generate_wireguard_configs

     # 加载静态 & 动态配置
     settings = load_toml_config("wg_manager.toml")
     data = load_json_data("wg_data.json")

     # 如果某节点缺密钥 => 生成
     # generate_keys_if_missing(data, "clientC")
     # 再写回 JSON

     # 最后渲染 .conf
     generate_wireguard_configs(settings, data, output_dir="out/")
     ```

### 2.6 日志管理

- **方案**：使用 Python 标准库 `logging` 或第三方 `loguru`；  
- **配置**：读取 `toml` 中 `[logging]` 配置（如 `level=info, file=logs/wg.log`）；  
- **初始化**：在程序入口统一设置日志级别、输出格式；  
- **CLI**：可提供 `--log-level` 临时覆盖。

---

## 3. 技术实现

### 3.1 目录结构示例

```
my_wg_project/
├── pyproject.toml        # Poetry / build / etc.
├── README.md
├── wg_manager.toml       # 用户手动维护的节点配置(多网卡等)
├── wg_data.json          # 动态生成的密钥和mesh信息
├── templates/
│   ├── server.conf.j2
│   └── client.conf.j2
├── wg_manager/
│   ├── __init__.py
│   ├── cli.py            # Typer命令行
│   ├── core.py           # 业务逻辑(merge数据、mesh生成、keys管理)
│   ├── models.py         # Pydantic或自定义类型校验
│   ├── render.py         # Jinja2渲染
│   └── utils.py          # 公共工具函数
└── tests/
    ├── test_core.py
    └── test_render.py
```

### 3.2 数据加载与合并

1. **载入 TOML**：通过 `tomllib` (Python 3.11+) 或 `toml` 第三方库；  
2. **载入 JSON**：Python 内置 `json`；  
3. **合并逻辑**：  
   - TOML 提供节点名、接口 IP/端口；  
   - JSON 提供该节点的私钥、公钥、PSK。  
   - 如果 JSON 中找不到对应节点(或网卡)的密钥，则调用 `wg genkey` / `wg pubkey` / `wg genpsk` 生成并写回 JSON；  
   - 生成 `.conf` 时，需要先看 JSON 里关于 `mesh_peers`，再根据 TOML 中的接口信息来生成 Endpoint 配置。

### 3.3 生成配置

1. **render.py**：  
   - 解析模板文件；  
   - 传入合并后的数据结构（节点、接口、密钥等）；  
   - 输出到指定目录，如 `out/server-eth0.conf` 或 `out/clientA.conf` 等。  
2. **多网卡逻辑**：  
   - 根据 TOML 中 `[server.interfaces]` / `[client.interfaces]` 可能生成多个配置文件，或在单个配置文件中写多 IP/端口；可选方式取决于具体需求。

---

## 4. 示例用例

1. **初次使用**  
   1) `wg-mesh init`：自动生成一份基本的 `wg_manager.toml`、`wg_data.json`、`templates/`；  
   2) 用户修改 `wg_manager.toml`，比如增加节点 / 修改接口 IP；  
   3) 执行 `wg-mesh generate`：若 JSON 缺少密钥，会自动生成；生成完 `.conf` 文件。  
2. **添加新节点**  
   1) 手动编辑 `wg_manager.toml`，在 `[client]` 块添加一个新的 `[[client]]`；  
   2) `wg-mesh genkey --node <new_node>`：给新节点生成密钥，写进 `wg_data.json`；  
   3) 再次 `wg-mesh generate`，即可得到对应 .conf。  
3. **查看节点**  
   - `wg-mesh list-nodes`：读取 TOML + JSON，输出节点及网卡、密钥信息概览（敏感信息可隐藏或提示 `--show-secrets` 选项）。

---

## 5. 日志与错误处理

1. **日志**  
   - 在 `cli.py` 或 `core.py` 中初始化 logging，根据 `wg_manager.toml` 的 `[logging]` 配置；  
   - CLI 命令中若出错，打出 `error` 日志并以非零状态退出；  
   - 调试时可启用 `--log-level debug`。  
2. **错误处理**  
   - TOML / JSON 文件格式错误：抛出解析异常并提示用户检查配置；  
   - 节点信息不一致：若 TOML 中有节点名但 JSON 中找不到相应数据，可自动初始化数据或警告。

---

## 6. 后续扩展

1. **GUI / Web**  
   - 在后续版本中添加 Web API (Flask / FastAPI) 或桌面 GUI，仅需在界面层调用同一套 `core.py` 函数；  
2. **IPv6 / 混合网段**  
   - 在 TOML 中给 `interfaces` 再添加一个 `ipv6_address` 字段；  
3. **大型 Mesh**  
   - 当节点数量很多时，可引入分层管理策略或自动发现机制；  
4. **更高级的数据库**  
   - 如果 JSON 不够满足需求，可切换到 SQLite / PostgreSQL，保留相同数据结构就行。

---

## 7. 里程碑与时间计划

1. **基础功能 (2~3 周)**  
   - 搭建项目结构、解析 TOML/JSON、Typer CLI 原型；  
   - 实现多网卡 & Mesh 基本逻辑；  
   - 完成日志系统；  
2. **测试 & 文档 (1~2 周)**  
   - 单元测试 & 集成测试；  
   - 编写使用说明、示例配置；  
3. **示例 & 打包 (1 周)**  
   - `wg-mesh init` 命令；  
   - 生成 wheel 包并验证安装使用流程；  
4. **发布 / 维护**  
   - 推送至 PyPI 或公司内部仓库，收集用户反馈，不断改进。

---

## 8. 风险与注意事项

1. **配置同步**  
   - 若用户在 TOML 中删除了节点但忘记清理 JSON 中对应数据，会出现不匹配；需要在生成时做好检测或自动清理。  
2. **并发修改**  
   - 多人或多进程同时编辑 TOML/JSON 可能导致冲突；需团队约定或加文件锁机制。  
3. **安全**  
   - JSON 内含私钥，应在文件系统权限上做好保护，或未来考虑加密存储。  
4. **多网卡策略**  
   - 需明确定义 “哪个网卡对外暴露作为 Endpoint” 的规则，或让用户自行在 TOML 里声明优先网卡。

---

## 9. 结论

通过本方案：

- **节点设置**（含多网卡）在 **TOML** 中，便于手动编辑、易读易维护；  
- **动态数据**（密钥、PSK、部分 Mesh 信息）在 **JSON**，由程序自动生成与更新；  
- **Jinja2** 渲染 WireGuard 配置，**Typer** 提供命令行入口，**Pydantic**（可选）做类型校验；  
- **多网卡** 与 **Mesh** 逻辑可在此框架内灵活扩展；  
- 日志管理和打包分发均有相应方案，后续可平滑升级至 GUI/Web 等更高级功能。
