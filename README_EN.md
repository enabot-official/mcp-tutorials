# MCP Tutorials

Bilingual (Chinese / English) tutorials and examples for [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) on Enabot EBO robots.

> The EBO Robot MCP Getting Started guide is ready; other articles are being prepared.

## Language

- 中文 ([README.md](README.md))
- English (current)

## Contents

### Start Here

- **[EBO Robot MCP Getting Started](docs/en-US/ebo-mcp-getting-started.md)** — from getting your token to controlling your robot in plain language, including Claude Desktop setup, example commands, model comparison, and FAQ

### Going Further

- **[EBO MCP Troubleshooting and Best Practices](docs/en-US/ebo-mcp-troubleshooting.md)** — config pitfalls, connection checks, sequential actions, on-site failure diagnosis, multiple robots, and security

### More Tutorials (in progress)

1. [What is MCP](docs/en-US/01-mcp-intro.md) — background, core concepts, use cases
2. [Quickstart](docs/en-US/02-quickstart.md) — setup and your first MCP server / client
3. [Tools, Resources and Prompts](docs/en-US/03-tools-resources.md) — the three primitives
4. [EBO Robot Control Demo](docs/en-US/04-ebo-robot-demo.md) — driving EBO actions through MCP

## Layout

```
mcp-tutorials/
├── README.md          # Chinese entry point
├── README_EN.md       # English entry point
├── docs/
│   ├── zh-CN/         # Chinese docs
│   └── en-US/         # English docs
├── examples/          # Runnable example code
└── assets/            # Images and diagrams
```

## Conventions

- Keep code identifiers, commands, and MCP terms (tool / resource / prompt) in English
- Maintain one standalone article per language; do not interleave translations
- Put runnable code in `examples/` and reference it with relative paths from docs

## License

[MIT](LICENSE)
