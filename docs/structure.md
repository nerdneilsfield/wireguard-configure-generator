# 综合架构设计 ─ 模板与可视化集成

## 1. 目标

构建一套高度模块化、可配置、可视化的WireGuard配置生成器，支持：

1. 配置驱动（JSON schema）── 节点、拓扑、密钥配置；
2. 模板渲染（Jinja2）── 生成 `.conf` 与 `wg-quick` 脚本；
3. 拓扑可视化（NetworkX + Matplotlib）── 生成网络关系图；
4. CLI 接口（Click/Argparse）── 一键生成、验证、可视化。

## 2. 目录结构

```
wg_conf_gen/
├── config/
│   ├── nodes.json         # 节点信息
│   ├── topology.json      # 拓扑关系
│   └── keys.json          # 密钥信息
├── templates/             # Jinja2 模板
│   ├── interface.conf.j2  # WireGuard 配置模板
│   └── wg-quick.sh.j2     # 启动脚本模板
├── wg_conf_gen/           # 源代码模块
│   ├── __init__.py
│   ├── cli.py             # CLI 入口（generate/validate/visualize）
│   ├── loader.py          # 配置加载与 JSON schema 校验
│   ├── models.py          # 数据模型：Node/Peer/Endpoint/Topology
│   ├── builder.py         # 构建 PeerConfig 列表
│   ├── renderer.py        # 渲染模块（Jinja2）
│   ├── visualizer.py      # 可视化模块（NetworkX + Matplotlib）
│   ├── storage.py         # 安全密钥存储模块（SQLite keystore）
│   └── utils.py           # 通用工具函数
├── examples/              # 示例脚本和演示
│   └── generate_example.sh
├── tests/                 # 单元测试
│   ├── test_loader.py
│   ├── test_builder.py
│   ├── test_renderer.py
│   └── test_visualizer.py
├── requirements.txt       # 依赖列表 (jsonschema, jinja2, networkx, matplotlib, click)
├── setup.py               # 安装/发布配置
└── README.md              # 项目说明
```

## 3. 模块职责

### 3.1 loader.py

* 加载并校验 `nodes.json`/`topology.json`，返回模型数据。

### 3.2 storage.py

* **安全密钥存储与管理**：使用 SQLite 数据库存储和检索 WireGuard 私钥、公钥和 PresharedKey，支持加密字段和访问控制。
* 核心类/函数：

  * `init_keystore(db_path: str)`：初始化 SQLite 数据库和表结构。
  * `save_key(name: str, private_key: str, public_key: str, psk: str)`：将密钥写入数据库。
  * `load_key(name: str) -> KeyPair`：从数据库读取密钥。
  * 可选支持数据库加密（如 SQLCipher）。

### 3.3 models.py

* 加载并校验 `nodes.json`/`topology.json`/`keys.json`，返回模型数据。

### 3.2 models.py

* 定义数据类：`Node`, `Endpoint`, `PeerConfig`, `Topology`。

### 3.3 builder.py

* 基于模型和密钥，生成每个节点的 `PeerConfig` 列表，包括：

  * 对应的 `PublicKey`, `Endpoint`, `AllowedIPs`, `PSK`, `Keepalive`。

### 3.4 renderer.py

* 使用 Jinja2 渲染模板：

  * `interface.conf.j2` → `.conf` 文件
  * `wg-quick.sh.j2` → 启动脚本

### 3.5 visualizer.py

* 利用 NetworkX 构建图：

  * 节点属性：`role`, 子网组
  * 边属性：组内直连 vs 中继
* 使用 Matplotlib 渲染并保存拓扑图（PNG/SVG）。

### 3.6 cli.py

* CLI 命令：

  * `generate`：生成所有配置文件；
  * `validate`：校验 JSON 配置；
  * `visualize`：绘制并输出拓扑图；
  * 支持 `--config-dir`、`--output-dir` 等选项。

## 4. 工作流程示例

```bash
# 1. 校验配置
$ wg-gen validate --config-dir ./config

# 2. 生成配置
$ wg-gen generate --config-dir ./config --output-dir ./out

# 3. 可视化拓扑
$ wg-gen visualize --config-dir ./config --output ./out/topology.png
```

---

此方案整合了配置管理、模板渲染与可视化功能，便于后续扩展和维护。请确认或提出补充意见！
