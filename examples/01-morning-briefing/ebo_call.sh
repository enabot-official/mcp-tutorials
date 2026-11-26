#!/usr/bin/env bash
# EBO MCP direct call helper. Usage: ebo_call.sh <id> <tool_name> <arguments_json>
# Reads URL and Authorization from mcp.json at runtime; credentials are never printed.
ID="$1"
NAME="$2"
ARGS="$3"
CFG=$(python -c 'import json,pathlib,os; s=json.loads(pathlib.Path(os.path.expanduser("~/.workbuddy/mcp.json")).read_text(encoding="utf-8"))["mcpServers"]["ebo-robot"]; print(s["url"]); print(s["headers"]["Authorization"])')
{ read -r URL; read -r AUTH; } <<< "$CFG"
URL=${URL%$'\r'}
AUTH=${AUTH%$'\r'}
curl -s -X POST "$URL" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":${ID},\"method\":\"tools/call\",\"params\":{\"name\":\"${NAME}\",\"arguments\":${ARGS}}}"
