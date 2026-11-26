# 配套代码

三个实战项目的可运行代码。代码均来自实际项目，已做脱敏：不含真实令牌、接口地址、内网 IP 或设备号。使用时通过环境变量或 `~/.workbuddy/mcp.json` 注入自己的连接信息。

| 目录 | 对应教程 | 内容 |
| --- | --- | --- |
| [00-connection-check/](00-connection-check/README.md) | — | 连通性自检（零依赖）与最小 Python 调用示例 |
| [01-morning-briefing/](01-morning-briefing/README.md) | [实战一：早间日程播报](../docs/zh-CN/project-01-morning-briefing.md) | MCP 直调封装、叫早循环、回桩轮询、播报文案生成 |
| [02-smart-home/](02-smart-home/README.md) | [实战二：智能家居联动](../docs/zh-CN/project-02-smart-home.md) | 完整常驻程序 `door_welcome.py`、依赖清单、运行脚本 |
| [03-voice-assistant/](03-voice-assistant/README.md) | [实战三：语音助手](../docs/zh-CN/project-03-voice-assistant.md) | ASR 固定切段、VAD 交互转写、语音闭环桥接三个脚本 |

## 使用前必读

- 每个目录下的代码都可能在真机上驱动移动、跟随、灯光或音乐，运行前确认机器人周围环境和人员安全。
- 令牌一律从环境变量或本机配置读取，**不要写进代码、不要提交到仓库**。
- 依赖版本是项目实测可用的版本，改动前先看对应教程的"环境与依赖"章节。

## 验证状态与已知限制

代码与教程来自同一套真机环境，记录如下，便于判断能否直接复用：

| 项目 | 测试机型 | 验证时间 | 通过条件 | 已知限制 |
| --- | --- | --- | --- | --- |
| 连通性自检 / 最小示例 | EBO MAX | 2026-11 | 自检全部 `[OK]`；`robot_status` 有返回 | 需先填入自己的令牌与接入地址 |
| 早间日程播报 | EBO MAX | 2026-11 | 五步流程按序执行，`robot_status` 复核通过 | 依赖 WorkBuddy 定时任务；地点名须与 APP 建图一致 |
| 智能家居联动 | EBO MAX | 2026-11-24 ~ 11-26 | 门磁触发后完成导航、识别、播报、开灯、跟随 | 需米家账号与硬件；TTS 完成时间靠字数估算 |
| 语音助手 | EBO MAX | 2026-11-24 ~ 11-26 | RTSP 音频转写、VAD 交互脚本跑通 | 端到端语音闭环尚未跑通，见实战三文档 |

运行环境：Python 3.11+（项目 2、3 用 `uv` 管理）；MCP 客户端为 WorkBuddy；机器人通过局域网接入。依赖的具体版本见各项目的 `requirements.txt` 与对应教程章节。

> 这些代码不是下载即用的通用产品：需要你自己的机器人、令牌，项目 2 还需要米家设备，项目 3 还需要局域网 RTSP。上表说明它们在什么条件下被验证过，不代表在任意环境都能直接运行。

## 最小起步

先跑连通性自检，确认配置可用（只需 Python，无需安装依赖）：

```bash
python examples/00-connection-check/check_connection.py
```

脚本会检查配置、连接、工具列表，并调用只读的 `robot_status` 验证机器人真实响应；令牌不会打印。

也可直接用 `01-morning-briefing/ebo_call.sh` 发一条只读调用：

```bash
bash examples/01-morning-briefing/ebo_call.sh 1 robot_list_locations '{}'
```

两个脚本都从 `~/.workbuddy/mcp.json` 读取连接信息，请先确认该文件里已配置名为 `ebo-robot` 的服务。
