#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
minimal_call.py - 最小的 EBO MCP 调用示例

只做四件事：建立连接 -> 列出工具 -> 调用 robot_status -> 读取返回。
不需要 Agent、不需要第三方设备、不需要定时任务。看懂这个就能开始基于 EBO 开发。

依赖：mcp（官方 SDK）
    pip install "mcp>=1.20.0"

运行（凭据通过环境变量传入，不要写进代码）：
    export EBO_URL="https://<EBO_MCP_ENDPOINT>/api/v1/mcp"
    export EBO_TOKEN="<YOUR_TOKEN>"
    python minimal_call.py

Windows PowerShell:
    $env:EBO_URL="https://<EBO_MCP_ENDPOINT>/api/v1/mcp"
    $env:EBO_TOKEN="<YOUR_TOKEN>"
    python minimal_call.py
"""
import asyncio
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def main():
    url = os.environ.get('EBO_URL', '')
    token = os.environ.get('EBO_TOKEN', '')
    if not url or not token or token.startswith('<'):
        print('请先设置 EBO_URL 和 EBO_TOKEN 环境变量（见文件顶部说明）。')
        return

    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client, create_mcp_http_client

    headers = {'Authorization': f'Bearer {token}'}
    http = create_mcp_http_client(headers=headers)
    streams = streamable_http_client(url, http_client=http)
    read, write = await streams.__aenter__()
    # ClientSession 必须用 async with 进入，才会启动内部 dispatcher
    session_ctx = ClientSession(read, write)
    session = await session_ctx.__aenter__()
    try:
        # 1) 初始化握手
        await session.initialize()

        # 2) 列出工具
        tools = await session.list_tools()
        names = [t.name for t in tools.tools]
        print(f'可用工具 {len(names)} 个：{", ".join(names)}')

        # 3) 调用只读工具
        result = await session.call_tool('robot_status', {})
        texts = [c.text for c in result.content if getattr(c, 'text', None)]
        print('robot_status 返回：')
        print('\n'.join(texts) if texts else '(空)')
    finally:
        await session_ctx.__aexit__(None, None, None)
        await streams.__aexit__(None, None, None)
        await http.aclose()


if __name__ == '__main__':
    asyncio.run(main())
