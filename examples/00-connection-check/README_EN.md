# Connectivity Check and Minimal Example

Before running any project, use the scripts here to confirm the configuration actually works.

| Script | Purpose | Dependencies |
| --- | --- | --- |
| `check_connection.py` | Step-by-step check: config, connection, tool list, robot response | Python standard library only |
| `minimal_call.py` | Minimal MCP call: connect, list tools, call, read result | `mcp` official SDK |

## Connectivity check

Only the Python standard library is needed — no `mcp` or other third-party package.

## Run

```bash
python examples/00-connection-check/check_connection.py
```

It reads the `ebo-robot` service from `~/.workbuddy/mcp.json` by default. Use `--config` for another path:

```bash
python examples/00-connection-check/check_connection.py --config /path/to/mcp.json
```

## What it checks

Each step prints a result:

```
[OK] Config found: ~/.workbuddy/mcp.json
[OK] Endpoint and token present (token hidden)
[OK] MCP connection established
[OK] Tools available: 15
[OK] Required tools present
[OK] Robot responded to robot_status

All checks passed. The connection is usable.
```

Checks in order:

1. Config file exists and is valid JSON
2. The `ebo-robot` service is configured, with endpoint and token filled in (token is never printed)
3. The MCP service is reachable
4. The tool list loads and required tools (`robot_status` / `robot_speak` / `robot_navigate`) are present
5. A read-only `robot_status` call confirms the robot actually responds

On failure it distinguishes network errors, authentication failures (wrong or expired token), empty tool lists, and an offline robot, with a specific next step for each. The token stays in memory only — never logged or printed.

> Note: the connection icon and 15/15 tool count in the client UI only prove the tool list loaded, not that the robot can respond. The final read-only call in this script is the real proof of connectivity.

## Minimal call example

`minimal_call.py` shows the shortest path to building on EBO: connect, list tools, call `robot_status`, and read the result. No Agent, no third-party devices, no scheduled tasks — understand this and you can start writing your own app.

Install the official SDK:

```bash
pip install "mcp>=1.20.0"
```

Pass credentials through environment variables, never in code:

```bash
export EBO_URL="https://<EBO_MCP_ENDPOINT>/api/v1/mcp"
export EBO_TOKEN="<YOUR_TOKEN>"
python examples/00-connection-check/minimal_call.py
```

Key points (SDK v2.x): `ClientSession` must be entered with `async with` to start its internal dispatcher, then call `initialize()`. Connect with `create_mcp_http_client(headers=...)` + `streamable_http_client(url, http_client=...)`. See the [troubleshooting guide](../../docs/en-US/ebo-mcp-troubleshooting.md) for more pitfalls.
