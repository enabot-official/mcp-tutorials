# 连通性自检与最小示例

在跑任何项目之前，先用这里的脚本确认配置是否真的可用。

本目录包含两个脚本：

| 脚本 | 用途 | 依赖 |
| --- | --- | --- |
| `check_connection.py` | 逐步自检：配置、连接、工具列表、机器人响应 | 仅 Python 标准库 |
| `minimal_call.py` | 最小 MCP 调用示例：连接、列工具、调用、读结果 | `mcp` 官方 SDK |

## 连通性自检

只用 Python 标准库，不用安装 `mcp` 或其他第三方包。

## 运行

```bash
python examples/00-connection-check/check_connection.py
```

配置文件默认读 `~/.workbuddy/mcp.json` 里名为 `ebo-robot` 的服务；也可以用 `--config` 指定其他路径：

```bash
python examples/00-connection-check/check_connection.py --config /path/to/mcp.json
```

## 检查内容

按顺序输出每一步结果：

```
[OK] Config found: ~/.workbuddy/mcp.json
[OK] Endpoint and token present (token hidden)
[OK] MCP connection established
[OK] Tools available: 15
[OK] Required tools present
[OK] Robot responded to robot_status

All checks passed. The connection is usable.
```

检查项：

1. 配置文件是否存在、是否是合法 JSON
2. `ebo-robot` 服务是否配置、地址与令牌是否填写（令牌不打印）
3. 能否连上 MCP 服务
4. 工具列表能否拉取、必需工具（`robot_status` / `robot_speak` / `robot_navigate`）是否存在
5. 调用只读工具 `robot_status`，确认机器人真实响应

失败时会区分网络不通、鉴权失败（令牌错误或过期）、工具列表异常、机器人离线等情况，并给出对应的排查方向。令牌全程只在内存里使用，不写日志、不打印。

> 注意：只看客户端界面的连接图标和 15/15 工具数，只能证明工具列表加载成功，不代表机器人真的能响应命令。这个脚本最后一步的只读调用才是实际连通的证据。

## 最小调用示例

`minimal_call.py` 展示基于 EBO 开发的最短流程：建立连接、列出工具、调用 `robot_status`、读取返回。没有 Agent、没有第三方设备、没有定时任务——看懂它就能开始写自己的应用。

依赖官方 SDK：

```bash
pip install "mcp>=1.20.0"
```

凭据通过环境变量传入，不写进代码：

```bash
export EBO_URL="https://<EBO_MCP_ENDPOINT>/api/v1/mcp"
export EBO_TOKEN="<YOUR_TOKEN>"
python examples/00-connection-check/minimal_call.py
```

关键写法（SDK v2.x）：`ClientSession` 必须用 `async with` 进入才会启动内部 dispatcher，之后调用 `initialize()`；连接用 `create_mcp_http_client(headers=...)` + `streamable_http_client(url, http_client=...)`。更多易错点见[排错文档](../../docs/zh-CN/ebo-mcp-troubleshooting.md)。
