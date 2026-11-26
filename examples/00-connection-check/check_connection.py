#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_connection.py - EBO MCP 连通性自检

按顺序检查：
  1. 配置文件是否存在、能否解析
  2. ebo-robot 服务是否配置，地址与令牌是否填写（令牌不会打印）
  3. 能否连上 MCP 服务
  4. 工具列表能否拉取、数量是否正常
  5. 调用只读工具 robot_status，确认机器人真实响应

只使用 Python 标准库，无需安装任何依赖。每一步输出 [OK] / [FAIL]，
失败时给出具体排查建议。令牌全程只在内存里使用，不写入日志、不打印。

运行：
    python check_connection.py
    python check_connection.py --config /path/to/mcp.json
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

SERVER_NAME = 'ebo-robot'
CONFIG_PATH = os.path.expanduser('~/.workbuddy/mcp.json')
REQUIRED_TOOLS = ['robot_status', 'robot_speak', 'robot_navigate']


def ok(msg):
    print(f'[OK] {msg}')


def fail(msg, hint):
    print(f'[FAIL] {msg}')
    print(f'       -> {hint}')


def load_config(path):
    if not os.path.exists(path):
        fail(f'Config not found: {path}',
             'Create the file using the config example in the getting-started guide.')
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fail(f'Config is not valid JSON: {e}',
             'Fix the JSON syntax and try again.')
        return None
    ok(f'Config found: {path}')
    return data


def get_server(data):
    servers = (data or {}).get('mcpServers', {})
    if SERVER_NAME not in servers:
        fail(f'Service "{SERVER_NAME}" not found in mcpServers',
             f'Add a "{SERVER_NAME}" entry, or rename your server to match.')
        return None
    srv = servers[SERVER_NAME]
    url = srv.get('url', '')
    headers = srv.get('headers', {})
    auth = headers.get('Authorization', '')
    if not url.startswith('http://') and not url.startswith('https://'):
        fail('Endpoint URL missing or invalid',
             'Set "url" to the endpoint shown in the Yibao Robot app.')
        return None
    if not auth or '<YOUR_TOKEN>' in auth:
        fail('Token missing or still a placeholder',
             'Replace <YOUR_TOKEN> with the token from the app.')
        return None
    ok('Endpoint and token present (token hidden)')
    return {'url': url, 'auth': auth}


def rpc(url, auth, method, params, req_id=1, timeout=15):
    """Send one JSON-RPC request; return parsed result or raise a classified error."""
    body = json.dumps({
        'jsonrpc': '2.0', 'id': req_id, 'method': method, 'params': params,
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'Authorization': auth,
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'User-Agent': 'ebo-connection-check',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}') from e
    except urllib.error.URLError as e:
        raise RuntimeError(f'network: {e.reason}') from e

    # Streamable HTTP may return SSE (data: lines) or plain JSON.
    text = raw
    if 'data:' in raw:
        chunks = [ln[5:].strip() for ln in raw.splitlines() if ln.startswith('data:')]
        text = chunks[-1] if chunks else raw
    try:
        msg = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f'unparseable response: {e}') from e
    if 'error' in msg:
        raise RuntimeError(f'RPC error: {msg["error"]}')
    return msg.get('result')


def classify_and_report(err):
    s = str(err).lower()
    if 'http 401' in s or 'http 403' in s:
        fail('Authentication failed',
             'Token is wrong or expired; renew it in the app and update mcp.json.')
    elif 'network' in s or 'urlopen' in s or 'timed out' in s or 'timeout' in s:
        fail('Network / connection failed',
             'Check WiFi, endpoint address, and whether the robot is online.')
    elif 'rpc error' in s:
        fail('MCP rejected the request',
             'Check the endpoint path (must end with /api/v1/mcp) and server version.')
    else:
        fail(f'Unexpected response: {err}',
             'Confirm the endpoint is an EBO MCP service and try again.')


def main():
    parser = argparse.ArgumentParser(description='Check EBO MCP connectivity')
    parser.add_argument('--config', default=CONFIG_PATH, help='path to mcp.json')
    args = parser.parse_args()

    print('EBO MCP connectivity check\n')
    data = load_config(args.config)
    if data is None:
        return 1
    srv = get_server(data)
    if srv is None:
        return 1

    # Step 3 + 4: connect and list tools
    try:
        result = rpc(srv['url'], srv['auth'], 'tools/list', {}, req_id=1)
    except Exception as e:
        classify_and_report(e)
        return 1
    ok('MCP connection established')

    tools = (result or {}).get('tools', []) if isinstance(result, dict) else []
    if not tools:
        fail('Tool list is empty',
             'The service responded but exposed no tools; verify the endpoint.')
        return 1
    ok(f'Tools available: {len(tools)}')
    names = {t.get('name') for t in tools if isinstance(t, dict)}
    missing = [t for t in REQUIRED_TOOLS if t not in names]
    if missing:
        fail(f'Required tools missing: {", ".join(missing)}',
             'Model or firmware may not support them; check the model comparison.')
        return 1
    ok('Required tools present')

    # Step 5: read-only call to verify the robot actually responds
    try:
        status = rpc(srv['url'], srv['auth'], 'tools/call',
                     {'name': 'robot_status', 'arguments': {}}, req_id=2)
    except Exception as e:
        classify_and_report(e)
        return 1
    if status is None:
        fail('robot_status returned no result',
             'Service is reachable but the robot did not respond; check if it is offline.')
        return 1
    ok('Robot responded to robot_status')
    print('\nAll checks passed. The connection is usable.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
