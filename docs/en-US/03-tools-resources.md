# Tools, Resources and Prompts

MCP defines three core primitives: **tools**, **resources**, and **prompts**. Understanding them tells you what an MCP Server can offer an AI.

## What you'll learn

Master MCP's three core primitives, with EBO examples.

## Tools: exposing capabilities to the model

A tool is an "executable action" — the AI decides to call it, producing side effects or a result. All 15 EBO tools are tools:

| Type | Example | Trait |
| --- | --- | --- |
| Query | `robot_status`, `robot_list_locations` | No side effect, reads state |
| Action | `robot_navigate`, `robot_speak`, `robot_take_photo` | Side effect, changes robot/real world |
| Control | `robot_stop_patrol`, `robot_move`, `robot_go_home` | Changes current task state |

Each tool has a name, description, and parameter schema (see [Tool Reference](ebo-mcp-tools-reference.md)). The AI uses the description to decide when to call it and what parameters to fill.

**Key insight**: a tool returning "OK" usually means only "command sent", not "action physically completed". This is especially true for EBO's action tools — verify with `robot_status` polling, the core topic of the [Troubleshooting guide](ebo-mcp-troubleshooting.md).

## Resources: exposing readable context data

A resource is "readable data", like a file, that the AI reads on demand as context. It's usually static or semi-static information with no side effects.

EBO's current MCP interface exposes capabilities mainly as tools (even status queries are a tool, not a resource), so this tutorial doesn't dwell on resources. In many MCP Servers, however, resources expose documents, config, or database content. For example, a calendar Server might expose "today's schedule" as a resource for the AI to read.

## Prompts: reusable prompt templates

A prompt is a pre-defined prompt template a Server offers for users/Agents to use on demand. It codifies "how to use these tools well".

For our scenario, the most useful prompts are **task templates**, e.g. complete instructions like "wake up and broadcast the schedule" or "welcome someone at the door". This tutorial includes a [Prompt Template Collection](ebo-mcp-prompts.md) you can copy directly or adapt.

## How the three work together

Take Project 1's morning briefing:

- **Prompt**: the user says "wake me up every morning and broadcast my schedule" (defines intent)
- **Tools**: the AI calls `robot_navigate`, `robot_speak`, `robot_follow`, `robot_status`, `robot_go_home` in sequence
- **Resource**: if a calendar resource exists, the AI reads today's schedule as broadcast content (this project uses a separate MCP to read the schedule)

Together, the three let a single natural-language sentence become a cross-system automation.

## Design tips and common pitfalls

1. **Write clear tool descriptions**: the AI relies entirely on them. Calling out special values like `moveId=5` (full stop) in the description significantly reduces misuse
2. **Pair action tools with a state-query tool**: hardware without completion feedback needs a query tool so the AI can close the loop — exactly EBO's design
3. **Keep parameter names consistent**: names like locations must match real data (map labels) exactly; provide a list tool so the AI can fetch exact values first
4. **Don't assume return = success**: state "OK means sent only" in tool descriptions or docs to prevent AI misjudgment

Further reading: [MCP spec: tools / resources / prompts](https://modelcontextprotocol.io/docs/concepts/tools).
