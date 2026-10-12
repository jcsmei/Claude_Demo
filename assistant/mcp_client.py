"""The MCP client: calls a tool on an outside MCP server.

The project's own MCP server is in mcp_server.py.  This file is the
other direction: it connects to Tavily's hosted MCP server and calls
its search tool.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from mcp import Client
from mcp.client.streamable_http import (create_mcp_http_client,
                                        streamable_http_client)

TAVILY_MCP_URL = "https://mcp.tavily.com/mcp/"
# Tavily's MCP server offers several tools.  Only the plain search is
# used: the crawl and research tools can spend many credits per call.
TAVILY_TOOL = "tavily_search"
WEB_RESULTS = 3
TIMEOUT_SECONDS = 15


async def _call_tavily(query, key):
    """Call the search tool on Tavily's MCP server, as an MCP client."""
    # The key travels in a header, not in the address, so that it
    # cannot end up in a log of requested addresses.
    http = create_mcp_http_client(headers={"Authorization": f"Bearer {key}"})
    async with http:
        transport = streamable_http_client(TAVILY_MCP_URL, http_client=http)
        async with Client(transport) as client:
            return await asyncio.wait_for(
                client.call_tool(
                    TAVILY_TOOL,
                    {"query": query, "max_results": WEB_RESULTS},
                ),
                timeout=TIMEOUT_SECONDS,
            )


def call_tavily(query, key):
    """Run `_call_tavily` from ordinary, non-async code."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_call_tavily(query, key))
    # Already inside an event loop: run in a thread with its own loop.
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _call_tavily(query, key)).result()
