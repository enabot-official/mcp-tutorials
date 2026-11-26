# MCP Tutorials

Bilingual (Chinese / English) tutorials and real-world projects for [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) on Enabot EBO robots.

> Complete first version — from zero basics to three full real-world projects. All screenshots are redacted; no real tokens, endpoints, device IDs, or LAN IPs are included.

## Language

- 中文 ([README.md](README.md))
- English (current)

## Learning Path

### ① Getting Started

1. [EBO Robot MCP Getting Started](docs/en-US/ebo-mcp-getting-started.md) — from token to plain-language control: Claude Desktop setup, example commands, model comparison, FAQ (with screenshots)
2. [Quickstart: Your First Command in 5 Minutes](docs/en-US/02-quickstart.md) — condensed version, fastest path to one run
3. [What is MCP](docs/en-US/01-mcp-intro.md) — protocol background, architecture, can/cannot

### ② Understanding Capabilities

4. [Tools, Resources and Prompts](docs/en-US/03-tools-resources.md) — MCP's three primitives, with EBO examples
5. [EBO MCP Tool Reference](docs/en-US/ebo-mcp-tools-reference.md) — all 15 tools, purposes, parameter tables, `moveId` chart, and calling conventions
6. [EBO Robot Control Demo](docs/en-US/04-ebo-robot-demo.md) — the natural-language-to-action chain, safety, and troubleshooting

### ③ Going Further

7. [EBO MCP Troubleshooting and Best Practices](docs/en-US/ebo-mcp-troubleshooting.md) — config pitfalls, connection checks, sequential execution with status polling, on-site failure diagnosis, the follow-mode pitfall, multiple robots, A/V limits (with screenshots)
8. [Prompt Template Collection](docs/en-US/ebo-mcp-prompts.md) — field-tested templates: navigate+photo, wake-up detection, schedule broadcast, stop following, docking, multiple robots, smart-home integration

### ④ Real Projects

9. [Project 1: Morning Schedule Briefing](docs/en-US/project-01-morning-briefing.md) — runs daily at 08:00: five-step SOP, state-verification polling, wake-up loop, 9 pitfalls, evolution history
10. [Project 2: Smart Home Integration (Door Welcome)](docs/en-US/project-02-smart-home.md) — EBO + Mijia dual MCP channels: 8-step flow, name tri-state, core code, 13 pitfalls, config parameter table
11. [Project 3: Turning EBO into a Voice Assistant](docs/en-US/project-03-voice-assistant.md) — RTSP audio + ASR + Agent bridge: three implementation stages, wake-word phonetic matching, audio/environment pitfalls, and the real reason the E2E loop is still blocked

> All three projects come from real, live-running systems — complete cases for taking MCP from "it works" to "it runs stably long-term". Project 3 also honestly documents what is not yet working and why.

## Layout

```
mcp-tutorials/
├── README.md / README_EN.md      # Chinese / English entry + learning path
├── docs/
│   ├── zh-CN/ / en-US/           # 11 articles each, standalone
│   │   ├── 01~04                 # basics and control demo
│   │   ├── ebo-mcp-*             # getting started / tools / troubleshooting / prompts
│   │   └── project-01/02/03      # three real-world projects
├── assets/                       # 8 bilingual screenshots (redacted)
├── examples/                     # Runnable example code
└── LICENSE
```

## Conventions

- Keep code identifiers, commands, and MCP terms (tool / resource / prompt) in English
- One standalone article per language; no interleaved translations
- Always use placeholders for real tokens, endpoints, device IDs, and LAN IPs; all images are redacted
- Sequential-execution guidance always stresses `robot_status` verification — sent does not mean executed

## License

[MIT](LICENSE)
