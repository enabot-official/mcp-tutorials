# MCP 是什么

> 如果你想直接用自然语言指挥 EBO 机器人，你其实不需要深入理解 MCP——按 [入门教程](ebo-mcp-getting-started.md) 配好就能用。这篇是给想知道"背后是怎么回事"的读者看的。

## 本文目标

读完你应该能够：

- 说清楚 MCP 解决了什么问题
- 理解 MCP 的基本架构（host / client / server）
- 知道什么时候该用 MCP

## 背景：为什么需要 MCP

过去，每个 AI 应用要连接一个外部系统（比如日历、机器人、数据库），都得单独写一套集成代码。N 个应用 × M 个系统 = N×M 套适配，谁都没法复用。

MCP（Model Context Protocol，模型上下文协议）就是为解决这个 N×M 问题而生的开放标准：外部系统按统一规范把自己暴露成「MCP Server」，AI 应用作为「MCP Client」按统一方式调用。一次适配，处处可用。

对这一场景，这意味着：EBO 机器人只要提供一个 MCP 接口，豆包、WorkBuddy、千问、CodeX 等任何支持 MCP 的 Agent 都能控制它——这也是[实战一](project-01-morning-briefing.md)中同一套任务在不同 Agent 下动作一致的原因。

## 核心概念与架构

```
   AI Agent (Host)           MCP Client           MCP Server          外部系统
  ┌───────────────┐       ┌──────────┐       ┌──────────┐       ┌─────────┐
  │ WorkBuddy /   │◄─────►│ 协议连接  │◄─────►│ EBO MCP  │◄─────►│ EBO 机器人│
  │ 豆包 / CodeX  │       │ (HTTP)   │       │ Service  │       │         │
  └───────────────┘       └──────────┘       └──────────┘       └─────────┘
```

- Host（宿主）：用户直接打交道的 AI 应用，如 WorkBuddy、豆包。它理解你的自然语言，决定调用哪些工具
- Client（客户端）：Host 内部的协议组件，负责与 Server 建立连接、收发消息
- Server（服务端）：把外部系统的能力按 MCP 规范暴露出来。EBO 的 Server 暴露了 15 个工具（见[工具参考](ebo-mcp-tools-reference.md)）

传输方式常见的有两种：
- HTTP / streamable HTTP：EBO 机器人用这种，走网络，配置一个 URL + Token 即可（[实战一、入门教程](ebo-mcp-getting-started.md)）
- stdio：本地进程通信，米家设备集成用这种（[实战二](project-02-smart-home.md)）

## MCP 能做什么 / 不能做什么

能做（以 EBO 为例）：
- 让 AI 调用工具控制真实世界：移动、导航、拍照、播报、跟随、音乐、回充
- 让 AI 查询状态并据此决策：电量、任务、视野中检测到的人
- 把多个系统串成一条自动化流程：日程 → 机器人 → 智能家居（两个实战项目）

不能做（重要，避免误解）：
- MCP 本身不提供"推理能力"，它只是把工具交给 AI；怎么组合工具是 AI 的事
- 不保证物理执行成功——下发命令返回 OK 只代表"消息送出"，要靠状态查询复核（见[排错文档](ebo-mcp-troubleshooting.md)）
- 不等于实时音视频回传——EBO 的 MCP 只支持让机器人"说"，实时画面要走 RTSP 局域网流

## 与其他方案的区别

| 方案 | 特点 | 与 MCP 的关系 |
| --- | --- | --- |
| Function Calling | 模型厂商专有的工具调用格式，各家用各家的 | MCP 是开放标准，跨厂商通用 |
| 传统插件 | 通常绑定单一应用，生态封闭 | MCP 强调一次适配、多应用复用 |
| 直接调 HTTP API | 你自己写代码实现集成 | MCP 把"描述能力"标准化，AI 能自动发现和理解工具 |

## 小结与延伸阅读

一句话：MCP 让 AI Agent 用统一方式发现并调用外部能力。对本教程来说，它让"用自然语言指挥 EBO 机器人"成为实现，且不受具体 Agent 限制。

- [MCP 官方文档](https://modelcontextprotocol.io/)
- 下一步：[快速开始](02-quickstart.md) → [工具、资源与提示词](03-tools-resources.md) → [EBO 控制示例](04-ebo-robot-demo.md)
