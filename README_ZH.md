# WireGuard 配置生成器

[![Python 版本](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![许可证](https://img.shields.io/badge/license-BSD--3--Clause-green.svg)](LICENSE)
[![代码风格](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![包管理器](https://img.shields.io/badge/package%20manager-uv-blue.svg)](https://github.com/astral-sh/uv)
[![测试](https://img.shields.io/badge/tests-62%2F62%20passing-brightgreen.svg)](tests/)

[English](README.md) | [中文](README_ZH.md)

---

基于模块化架构的 WireGuard VPN 配置生成器，支持 TOML 格式、Jinja2 模板和安全密钥管理。

## 特性

- **TOML 配置格式**：人类可读的配置文件格式
- **模块化架构**：独立的加载、验证、渲染和密钥管理模块
- **安全密钥存储**：密钥与配置分离存储，权限为 0600
- **Python 加密库**：使用 Python `cryptography` 库原生生成密钥（无需 `wg` 命令）
- **多层验证**：TOML 语法、JSON Schema 和业务逻辑验证
- **Jinja2 模板**：基于模板的灵活配置渲染
- **客户端模式**：支持全局路由（0.0.0.0/0）和本地路由（仅子网）模式
- **可选 DNS**：每个客户端可单独配置 DNS 服务器
- **并行生成**：大型网络的并发配置生成
- **密钥保留**：重新生成时自动复用现有密钥
- **JSON 迁移**：将旧版 JSON 配置转换为 TOML 格式

## 拓扑结构

本工具为**简单星型拓扑**网络生成配置：
- **1 台服务器**，具有公网端点
- **N 台客户端**连接到服务器
- 不支持 mesh、hub-spoke 或中继配置

## 快速开始

### 安装

```bash
# 安装 uv 包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆仓库
git clone https://github.com/yourusername/wireguard-configure-generator.git
cd wireguard-configure-generator

# 安装依赖
uv sync
```

### 基本用法

1. **创建 TOML 配置文件**：

```toml
[common]
network_name = "my-vpn"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "vpn-server"
endpoint = "vpn.example.com"
vlan_ipv4_addr = "10.0.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "laptop"
vlan_ipv4_addr = "10.0.0.2"
port = 51821
dns1 = "1.1.1.1"
dns2 = "8.8.8.8"
gen_global = true
gen_local = false
```

2. **验证配置**：

```bash
uv run wg-mesh-gen validate -c network.toml
```

3. **生成 WireGuard 配置**：

```bash
uv run wg-mesh-gen generate -c network.toml -o output/
```

## CLI 命令

<details>
<summary><b>wg-mesh-gen generate</b> - 生成 WireGuard 配置</summary>

```bash
uv run wg-mesh-gen generate [选项]

选项:
  -c, --config PATH        TOML 配置文件（必需）
  -o, --output PATH        输出目录（默认：.）
  -k, --keys PATH          密钥存储文件（默认：keys.json）
  --parallel               启用大型网络的并行生成
  --force                  覆盖现有配置文件
  --refresh-force          重新生成所有密钥（忽略现有 keys.json）
  --help                   显示此帮助信息并退出
```

**示例**:

```bash
# 使用默认设置生成
uv run wg-mesh-gen generate -c network.toml -o /etc/wireguard

# 使用自定义密钥存储
uv run wg-mesh-gen generate -c network.toml -k my-keys.json

# 启用大型网络的并行生成
uv run wg-mesh-gen generate -c network.toml --parallel

# 强制覆盖现有文件
uv run wg-mesh-gen generate -c network.toml --force

# 重新生成所有密钥（密钥轮换）
uv run wg-mesh-gen generate -c network.toml --refresh-force --force
```

</details>

<details>
<summary><b>wg-mesh-gen validate</b> - 验证 TOML 配置</summary>

```bash
uv run wg-mesh-gen validate [选项]

选项:
  -c, --config PATH   TOML 配置文件（必需）
  -k, --keys PATH     要验证的密钥存储文件（可选）
  --strict            将警告视为错误
  --help              显示此帮助信息并退出
```

**验证检查**:
- TOML 语法正确性
- JSON Schema 验证（必需字段、数据类型、端口范围）
- 业务逻辑验证（唯一名称/IP、子网成员关系、gen_global/gen_local 约束）
- 可选密钥存储验证（密钥存在性、格式验证）

**示例**:

```bash
# 仅验证 TOML 配置
uv run wg-mesh-gen validate -c network.toml

# 验证配置和密钥
uv run wg-mesh-gen validate -c network.toml -k keys.json

# 严格模式（警告导致退出码 1）
uv run wg-mesh-gen validate -c network.toml -k keys.json --strict
```

</details>

<details>
<summary><b>wg-mesh-gen migrate</b> - 迁移旧版 JSON 到 TOML</summary>

```bash
uv run wg-mesh-gen migrate [选项]

选项:
  -i, --input PATH    旧版 JSON 配置文件（必需）
  -o, --output PATH   输出 TOML 文件（必需）
  -k, --keys PATH     输出密钥存储文件（默认：keys.json）
  --force             覆盖现有文件
  --help              显示此帮助信息并退出
```

**迁移功能**:
- 将 JSON 结构转换为 TOML 格式
- 提取嵌入的密钥到单独的 `keys.json` 文件
- 重命名 `ipv4_addr` 字段为 `endpoint`（新字段名）
- 验证输出的 TOML 配置
- 为密钥存储设置 0600 权限

**示例**:

```bash
# 使用默认密钥存储进行迁移
uv run wg-mesh-gen migrate -i config.json -o network.toml

# 指定自定义密钥存储路径
uv run wg-mesh-gen migrate -i config.json -o network.toml -k custom-keys.json

# 强制覆盖现有文件
uv run wg-mesh-gen migrate -i config.json -o network.toml --force
```

</details>

## 配置格式

<details>
<summary><b>TOML 配置结构</b></summary>

```toml
# 公共网络设置
[common]
network_name = "my-network"           # 网络标识符（用于配置文件名）
network_ipv4_addr = "10.0.0.0/24"     # VPN 子网（CIDR 表示法）

# 服务器配置
[server]
name = "vpn-server"                   # 服务器标识符
endpoint = "vpn.example.com"          # 公网端点（IPv4/IPv6/主机名）
vlan_ipv4_addr = "10.0.0.1"           # 服务器 VPN IP（必须在子网内）
port = 51820                          # WireGuard 监听端口（1024-65535）
interface = "eth0"                    # NAT 的物理接口（iptables PostUp/PostDown）

# 客户端配置（支持多个客户端）
[[clients]]
name = "laptop"                       # 客户端标识符（唯一）
vlan_ipv4_addr = "10.0.0.2"           # 客户端 VPN IP（唯一，必须在子网内）
port = 51821                          # 客户端监听端口（可选）
dns1 = "1.1.1.1"                      # 主 DNS（可选）
dns2 = "8.8.8.8"                      # 辅助 DNS（可选）
gen_global = true                     # 生成 AllowedIPs=0.0.0.0/0 的配置
gen_local = false                     # 生成 AllowedIPs=子网 的配置

[[clients]]
name = "phone"
vlan_ipv4_addr = "10.0.0.3"
port = 51822
gen_global = false
gen_local = true                      # gen_global/gen_local 至少一个为 true
```

</details>

<details>
<summary><b>密钥存储格式</b></summary>

密钥单独存储在权限为 0600 的 `keys.json` 文件中：

```json
{
  "version": "1.0",
  "server": {
    "private_key": "cG9ydHMyNWNyeXB0b2dyYXBoeWxpYnJhcnk=",
    "public_key": "c2VydmVycHVibGlja2V5",
    "preshared_key": "cHJlc2hhcmVka2V5Zm9yc2VydmVy"
  },
  "clients": {
    "laptop": {
      "private_key": "Y2xpZW50bGFwdG9wcHJpdmF0ZWtleQ==",
      "public_key": "Y2xpZW50bGFwdG9wcHVibGlja2V5",
      "preshared_key": "cHJlc2hhcmVka2V5Zm9ybGFwdG9w"
    },
    "phone": {...}
  }
}
```

**安全特性**:
- 自动设置 0600 权限（仅所有者可读写）
- 重新生成时保留密钥（除非使用 `--refresh-force`）
- 使用 Python `cryptography` 库生成 Curve25519 密钥
- Base64 编码的 32 字节密钥（44 字符）

</details>

## 生成的文件

**文件命名规范**:
- 服务器：`wg-{network_name}-server-{server_name}.conf`
- 客户端（全局）：`wg-{network_name}-client-{client_name}-global.conf`
- 客户端（本地）：`wg-{network_name}-client-{client_name}-local.conf`

**示例**：网络名为 "my-vpn"，服务器名为 "vpn-server"，客户端名为 "laptop"：
- `wg-my-vpn-server-vpn-server.conf`（1 个服务器配置）
- `wg-my-vpn-client-laptop-global.conf`（AllowedIPs=0.0.0.0/0）
- `wg-my-vpn-client-laptop-local.conf`（AllowedIPs=10.0.0.0/24）

## 开发

<details>
<summary><b>测试</b></summary>

```bash
# 运行所有测试
uv run pytest

# 运行并显示覆盖率
uv run pytest --cov=wg_mesh_gen --cov-report=term-missing

# 运行特定测试套件
uv run pytest tests/unit/           # 仅单元测试
uv run pytest tests/integration/    # 仅集成测试
uv run pytest tests/contract/       # 仅 CLI 契约测试

# 运行详细输出的测试
uv run pytest -v -s
```

**测试覆盖率**：62/62 测试通过（100%）
- 契约测试：24/24（CLI 命令）
- 集成测试：5/5（端到端工作流）
- 单元测试：33/33（模块函数）

</details>

<details>
<summary><b>代码质量</b></summary>

```bash
# 检查并修复代码
uv run ruff check --fix .

# 格式化代码
uv run ruff format .

# 检查类型（如果使用 mypy）
uv run mypy src/
```

**代码标准**:
- Python 3.12+
- 所有函数使用类型提示
- Google 风格文档字符串
- Ruff 代码检查（行长度：88）

</details>

## 项目结构

```
wireguard-configure-generator/
├── src/wg_mesh_gen/
│   ├── __init__.py
│   ├── cli.py              # 基于 Click 的 CLI
│   ├── loader.py           # TOML/JSON 加载
│   ├── validator.py        # 多层验证
│   ├── key_manager.py      # 密钥生成和存储
│   ├── renderer.py         # Jinja2 模板渲染
│   ├── migrator.py         # JSON 到 TOML 迁移
│   ├── models.py           # 数据模型
│   └── templates/
│       ├── server.conf.j2  # 服务器配置模板
│       └── client.conf.j2  # 客户端配置模板
├── tests/
│   ├── contract/           # CLI 命令测试
│   ├── integration/        # 端到端测试
│   └── unit/               # 模块单元测试
├── examples/
│   ├── star-network.toml   # 示例配置
│   └── legacy-config.json  # 旧版 JSON 示例
├── pyproject.toml
├── README.md
├── README_ZH.md
└── CLAUDE.md               # 开发指南
```

## 许可证

BSD 3-Clause License

Copyright (c) 2022-2025, DengQi
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
