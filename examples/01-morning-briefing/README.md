# 实战一配套代码：早间日程播报

对应教程：[实战一：早间日程播报](../../docs/zh-CN/project-01-morning-briefing.md)。

这套流程不依赖任何 pip/npm 第三方包，只需要本机命令行工具与 Python 标准库。

## 环境

| 依赖 | 用途 |
| --- | --- |
| WorkBuddy 自动化平台 | 每天 08:00 触发，把 SOP 注入 Agent |
| wecom-cli | 查日程、验证企业微信鉴权 |
| curl | 以 HTTP POST 直调 EBO MCP 端点 |
| Python 3 | 解析 JSON、判定视野人数、时间口语化，只用标准库 json / pathlib / re |
| bash / Git Bash | 串起调用、等待和循环 |

连接信息从 `~/.workbuddy/mcp.json` 的 `mcpServers["ebo-robot"]` 读取，脚本里不保存凭据。

## 文件

| 文件 | 作用 |
| --- | --- |
| `ebo_call.sh` | 通用调用封装：传工具名和参数 JSON，发一条 JSON-RPC 请求 |
| `wake_loop.sh` | 叫早循环：播报后等待，读状态判断视野中是否有人，最多 10 轮 |
| `dock_poll.sh` | 回桩轮询：先停止当前动作再回桩，最多 6 次确认状态 |
| `format_time.py` | 把 `14:30` 转成适合朗读的「下午2点30分」 |
| `build_speeches.py` | 从日程字段生成逐条播报文案 |

## 用法

在机器人完成建图、地图里存在对应地点名之后运行。调用 id 从 1 开始递增：

```bash
bash ebo_call.sh 1 robot_list_locations '{}'
bash ebo_call.sh 2 robot_navigate '{"locationName":"客厅","findTarget":"","objId":"","needReturn":false,"lang":"zh-CN"}'
bash ebo_call.sh 3 robot_status '{}'
```

`build_speeches.py` 依赖 `format_time.py`，两者放在同一目录。

## 两个易错点

1. 跟随会抢占回桩指令，必须先 `robot_stop_patrol` 再 `robot_go_home`。
2. Windows 下 Python 输出带 `\r`，URL 尾部若残留会让 curl 报 `Malformed input to a URL`；`ebo_call.sh` 已显式剥离。
