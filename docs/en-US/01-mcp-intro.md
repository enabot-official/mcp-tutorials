# What is MCP

> If you just want to control your EBO robot in plain language, you don't need to understand MCP deeply — follow the [Getting Started](ebo-mcp-getting-started.md) and you're set. This article is for readers who want to know "what's going on behind the scenes".

## What you'll learn

- What problem MCP solves
- The basic architecture (host / client / server)
- When to use MCP

## Background: why MCP exists

Previously, every AI app connecting to an external system (a calendar, a robot, a database) had to write its own integration code. N apps × M systems = N×M adapters, none reusable.

MCP (Model Context Protocol) is the **open standard** built to solve this N×M problem: external systems expose themselves as an "MCP Server" following a common spec, and AI apps act as "MCP Clients" calling them a common way. Adapt once, use everywhere.

For our scenario, this means: **once the EBO robot provides an MCP interface, any MCP-capable Agent — Doubao, WorkBuddy, Qwen, CodeX — can control it**. This is the basis for "one task card, different Agents, identical robot actions" in [Project 1](project-01-morning-briefing.md).

## Core concepts and architecture

```
   AI Agent (Host)           MCP Client           MCP Server          External
  ┌───────────────┐       ┌──────────┐       ┌──────────┐       ┌─────────┐
  │ WorkBuddy /   │◄─────►│ protocol │◄─────►│ EBO MCP  │◄─────►│ EBO     │
  │ Doubao / CodeX│       │ (HTTP)   │       │ Service  │       │ robot   │
  └───────────────┘       └──────────┘       └──────────┘       └─────────┘
```

- **Host**: the AI app you interact with — WorkBuddy, Claude Desktop. It understands your natural language and decides which tools to call
- **Client**: the protocol component inside the Host, managing the connection and message exchange with the Server
- **Server**: exposes an external system's capabilities per the MCP spec. EBO's Server exposes 15 tools (see [Tool Reference](ebo-mcp-tools-reference.md))

Common transports:
- **HTTP / streamable HTTP**: used by the EBO robot; over the network, configured with a URL + token ([Getting Started](ebo-mcp-getting-started.md))
- **stdio**: local process communication, used for Mijia device integration ([Project 2](project-02-smart-home.md))

## What MCP can and cannot do

**Can** (EBO examples):
- Let AI call tools that affect the real world: move, navigate, photo, speak, follow, music, dock
- Let AI query state and decide: battery, task, detected people
- Chain multiple systems into one automation: schedule → robot → smart home (both projects)

**Cannot** (important, to avoid misunderstandings):
- MCP itself provides no "reasoning" — it just hands tools to the AI; combining tools is the AI's job
- It doesn't guarantee physical execution — an OK return only means "sent"; verify with state queries ([Troubleshooting](ebo-mcp-troubleshooting.md))
- It isn't real-time A/V streaming — EBO's MCP only makes the robot "speak"; live video uses the RTSP LAN stream

## How it differs from other approaches

| Approach | Trait | Relation to MCP |
| --- | --- | --- |
| Function Calling | Vendor-specific tool-call format, each different | MCP is an open standard, cross-vendor |
| Traditional plugins | Bound to one app, closed ecosystem | MCP emphasizes adapt-once, reuse-many |
| Direct HTTP API | You write the integration yourself | MCP standardizes "capability description" so AI can auto-discover tools |

## Summary and further reading

In short: **MCP lets AI Agents discover and call external capabilities in a uniform way**. For this tutorial, it makes "control the EBO robot in plain language" possible, without being tied to a specific Agent.

- [MCP official documentation](https://modelcontextprotocol.io/)
- Next: [Quickstart](02-quickstart.md) → [Tools, Resources and Prompts](03-tools-resources.md) → [EBO Control Demo](04-ebo-robot-demo.md)
