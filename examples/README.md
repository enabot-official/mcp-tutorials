# 配套代码

三个实战项目的可运行代码。代码均来自实际项目，已做脱敏：不含真实令牌、接口地址、内网 IP 或设备号。使用时通过环境变量或 `~/.workbuddy/mcp.json` 注入自己的连接信息。

| 目录 | 对应教程 | 内容 |
| --- | --- | --- |
| [01-morning-briefing/](01-morning-briefing/README.md) | [实战一：早间日程播报](../docs/zh-CN/project-01-morning-briefing.md) | MCP 直调封装、叫早循环、回桩轮询、播报文案生成 |
| [02-smart-home/](02-smart-home/README.md) | [实战二：智能家居联动](../docs/zh-CN/project-02-smart-home.md) | 完整常驻程序 `door_welcome.py`、依赖清单、运行脚本 |
| [03-voice-assistant/](03-voice-assistant/README.md) | [实战三：语音助手](../docs/zh-CN/project-03-voice-assistant.md) | ASR 固定切段、VAD 交互转写、语音闭环桥接三个脚本 |

## 使用前必读

- 每个目录下的代码都可能在真机上驱动移动、跟随、灯光或音乐，运行前确认机器人周围环境和人员安全。
- 令牌一律从环境变量或本机配置读取，**不要写进代码、不要提交到仓库**。
- 依赖版本是项目实测可用的版本，改动前先看对应教程的"环境与依赖"章节。

## 最小起步

只想验证 MCP 连通性，不需要跑完整项目时，用 `01-morning-briefing/ebo_call.sh` 发一条只读调用：

```bash
bash examples/01-morning-briefing/ebo_call.sh 1 robot_list_locations '{}'
```

该脚本会从 `~/.workbuddy/mcp.json` 读取连接信息，先确认该文件里已配置名为 `ebo-robot` 的服务。
