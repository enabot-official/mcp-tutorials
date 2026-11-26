# EBO 机器人 MCP 教程

让 AI Agent 用自然语言控制 Enabot EBO 机器人——从第一次成功调用，到三个可以直接改造的实战项目。

[English](README_EN.md) · 中英双语 · 配套代码可运行

> **5 分钟目标**：连接机器人 → 拿到状态 → 发出第一条指令。跟着[快速开始](docs/zh-CN/02-quickstart.md)走，并用[自检脚本](examples/00-connection-check/README.md)确认真的连通。

![MCP 服务连接成功，15/15 工具已启用](assets/mcp-connected-CN.png)

## 支持机型

| 机型 | MCP 支持 | 工具能力 | 本库项目 |
| --- | --- | --- | --- |
| EBO MAX | 支持 | 15 个完整工具 | 三个实战项目均在该机型实测 |
| EBO Air2 Plus | 支持 | 11 个核心工具 | 未实测，详见[机型对比](docs/zh-CN/ebo-mcp-getting-started.md#ebo-max-和-ebo-air2-plus-有什么区别) |

其他机型暂不支持 MCP。所有截图与代码均已脱敏，不含真实令牌、接口地址、设备号或内网 IP。

## 三个实战项目

| 项目 | 展示什么 | 工程价值 |
| --- | --- | --- |
| [早间日程播报](docs/zh-CN/project-01-morning-briefing.md) | 定时任务 + AI 编排 + 多步控制 | 入门价值高 |
| [智能家居联动](docs/zh-CN/project-02-smart-home.md) | Python 常驻程序 + 双 MCP 通道 | 工程价值高 |
| [语音助手](docs/zh-CN/project-03-voice-assistant.md) | RTSP + ASR + Agent + TTS | 技术探索价值高 |

配套代码在 [examples/](examples/README.md)，包含连通性自检、最小调用示例和三个项目的完整脚本。

## 语言

- [English](README_EN.md)
- 中文（当前）

## 学习路径

### ① 入门

1. [EBO 机器人 MCP 入门教程](docs/zh-CN/ebo-mcp-getting-started.md) — 从获取令牌到用自然语言指挥机器人：WorkBuddy 配置、指令示例、机型对比、FAQ（含截图）
2. [快速开始：5 分钟发出第一条指令](docs/zh-CN/02-quickstart.md) — 精简版，快速完成第一次调用
3. [MCP 是什么](docs/zh-CN/01-mcp-intro.md) — 协议背景、架构、能与不能

### ② 理解能力

4. [工具、资源与提示词](docs/zh-CN/03-tools-resources.md) — MCP 三个核心原语，用 EBO 举例
5. [EBO MCP 工具参考](docs/zh-CN/ebo-mcp-tools-reference.md) — 全部 15 个工具的用途、参数表、`moveId` 对照表与调用约定
6. [EBO 机器人控制示例](docs/zh-CN/04-ebo-robot-demo.md) — 从自然语言到动作的流程、安全与排查

### ③ 进阶

7. [EBO MCP 排错与最佳实践](docs/zh-CN/ebo-mcp-troubleshooting.md) — 配置问题、连接排查、顺序执行与状态轮询、动作失败现场排查、跟随停止问题、多机器人、音视频边界（含截图）
8. [常用提示词模板集](docs/zh-CN/ebo-mcp-prompts.md) — 导航拍照、叫早检测、日程播报、停止跟随、回桩、多机器人、智能家居联动的实测模板

### ④ 实战项目

9. [实战一：早间日程播报](docs/zh-CN/project-01-morning-briefing.md) — 每天 08:00 定时运行：五步流程、状态轮询复核、叫早循环、常见问题、演进历史
10. [实战二：智能家居联动（开门迎宾）](docs/zh-CN/project-02-smart-home.md) — EBO + 米家双 MCP 通道：8 步流程、人名三态、核心代码、已知问题、配置参数表
11. [实战三：把 EBO 改造成语音助手](docs/zh-CN/project-03-voice-assistant.md) — RTSP 音频 + ASR + Agent 桥接：三阶段实现、唤醒词谐音匹配、音质与环境影响、尚未跑通环节的原因

> 三个实战项目均来自实际运行的环境，展示如何把 MCP 从"调通"用到长期稳定运行。实战三也记录了尚未跑通的环节及其原因。

## 目录结构

```
mcp-tutorials/
├── README.md / README_EN.md      # 中英入口 + 学习路径
├── docs/
│   ├── zh-CN/ / en-US/           # 各 11 篇，独立成文
│   │   ├── 01~04                 # 基础概念与控制示例
│   │   ├── ebo-mcp-*             # 入门 / 工具 / 排错 / 提示词
│   │   └── project-01/02/03      # 三个实战项目
├── assets/                       # 8 张中英截图（已脱敏）
├── examples/
│   ├── 00-connection-check/      # 连通性自检 + 最小 Python 调用示例
│   └── 01/02/03-*                # 三个项目的可运行代码 + 依赖清单
└── LICENSE
```

## 约定

- 代码标识符、命令行、MCP 术语（tool / resource / prompt）保留英文，不翻译
- 每种语言独立成文，不做逐段中英对照
- 真实令牌、接口地址、设备号、内网 IP 一律用占位符，图片均已脱敏
- 顺序执行类操作必须强调 `robot_status` 复核——下发成功不等于执行完成

## 许可

[MIT](LICENSE)
