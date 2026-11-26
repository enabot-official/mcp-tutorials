# MCP 教程

面向 Enabot EBO 机器人的 [MCP（Model Context Protocol）](https://modelcontextprotocol.io/) 教程与示例，中英双语。

> EBO 机器人 MCP 入门教程已完成，其余文档整理中。

## 语言

- [English](README_EN.md)
- 中文（当前）

## 文档导航

### 推荐入门

- **[EBO 机器人 MCP 入门教程](docs/zh-CN/ebo-mcp-getting-started.md)** — 从获取令牌到用大白话指挥机器人，含 Claude Desktop 配置、指令示例、机型对比与常见问题

### 进阶

- **[EBO MCP 排错与最佳实践](docs/zh-CN/ebo-mcp-troubleshooting.md)** — 配置踩坑、连接排查、顺序执行与状态轮询、动作失败现场排查、跟随停止坑、多机器人、音视频边界
- **[EBO MCP 工具参考](docs/zh-CN/ebo-mcp-tools-reference.md)** — 全部 15 个工具的用途、参数表与调用约定（状态、导航、移动、跟随、语音、音乐、拍摄）

### 更多教程（整理中）

1. [MCP 是什么](docs/zh-CN/01-mcp-intro.md) — 协议背景、核心概念、适用场景
2. [快速开始](docs/zh-CN/02-quickstart.md) — 环境准备、第一个 MCP Server / Client
3. [工具、资源与提示词](docs/zh-CN/03-tools-resources.md) — Tools / Resources / Prompts 三件套
4. [EBO 机器人控制示例](docs/zh-CN/04-ebo-robot-demo.md) — 通过 MCP 驱动 EBO 执行动作

## 目录结构

```
mcp-tutorials/
├── README.md          # 本文件，中文导航
├── README_EN.md       # 英文导航
├── docs/
│   ├── zh-CN/         # 中文文档
│   └── en-US/         # 英文文档
├── examples/          # 可运行示例代码
└── assets/            # 图片与示意图
```

## 约定

- 代码标识符、命令行、MCP 术语（tool / resource / prompt）保留英文，不翻译
- 每种语言独立成文，不做逐段中英对照
- 示例放在 `examples/`，文档中以相对路径引用

## 许可

[MIT](LICENSE)
