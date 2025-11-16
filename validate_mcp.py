#!/usr/bin/env python3
"""
MCP Runtime v3.0 - Validation Client

Launches server.py, initializes an MCP session, lists tools, calls ping,
and prints a JSON summary. All output sticks to ASCII so it can run in any
Windows console.
"""

import asyncio
import json
import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COMMAND = sys.executable
SERVER_SCRIPT = Path(__file__).parent / "server.py"
ENV = {
    "PYTHONUNBUFFERED": "1",
    "MCP_RUNTIME_ALLOW_SHELL": "false",
    "MCP_MEMORY_REDIS_HOST": "localhost",
    "MCP_MEMORY_REDIS_PORT": "6379",
    "MCP_MEMORY_REDIS_DB": "5",
}
INIT_TIMEOUT = 180  # seconds

if not SERVER_SCRIPT.is_file():
    print(f"ERROR: Server script not found: {SERVER_SCRIPT}", file=sys.stderr)
    sys.exit(1)

if not Path(COMMAND).is_file():
    print(f"ERROR: Python interpreter not found: {COMMAND}", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(level: str, message: str) -> None:
    print(f"[{level}] {message}", flush=True)


async def run_with_timeout(description: str, coro, timeout: float):
    log("INFO", f"{description} (timeout {timeout}s)")
    try:
        result = await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError as exc:
        log("ERROR", f"{description} timed out after {timeout}s")
        raise RuntimeError(f"{description} timed out after {timeout}s") from exc
    except Exception as exc:
        log("ERROR", f"{description} failed: {exc}")
        raise
    else:
        log("OK", f"{description} completed")
        return result

# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

async def main() -> None:
    params = StdioServerParameters(
        command=COMMAND,
        args=[str(SERVER_SCRIPT)],
        env=ENV,
    )

    print("=" * 60)
    print("MCP RUNTIME V3.0 - VALIDATION TEST")
    print("=" * 60)
    log("INFO", f"Python executable: {COMMAND}")
    log("INFO", f"Server script: {SERVER_SCRIPT}")
    log("INFO", f"Initialization timeout: {INIT_TIMEOUT}s")

    log("INFO", "Starting MCP server subprocess")
    async with stdio_client(params) as (read_stream, write_stream):
        log("OK", "Server process started")
        session = ClientSession(read_stream, write_stream)

        init_result = await run_with_timeout(
            "Session initialization",
            session.initialize(),
            INIT_TIMEOUT,
        )

        tools_response = await run_with_timeout(
            "Listing tools",
            session.list_tools(),
            120,
        )
        tool_names = [tool.name for tool in tools_response.tools]
        log("OK", f"Discovered {len(tool_names)} tools")
        if tool_names:
            print("First tools: " + ", ".join(tool_names[:10]))
            if len(tool_names) > 10:
                print(f"... plus {len(tool_names) - 10} more")

        ping_result = await run_with_timeout(
            "Calling ping",
            session.call_tool("ping"),
            60,
        )
        ping_text = [c.text for c in ping_result.content if c.type == "text"]
        ping_output = ping_text[0] if ping_text else "(no text)"

        status_output = None
        if "server_status" in tool_names:
            status_result = await run_with_timeout(
                "Calling server_status",
                session.call_tool("server_status"),
                60,
            )
            status_text = [c.text for c in status_result.content if c.type == "text"]
            if status_text:
                try:
                    status_output = json.loads(status_text[0])
                except json.JSONDecodeError:
                    status_output = status_text[0]

        summary = {
            "status": "success",
            "server_info": {
                "protocol_version": init_result.protocolVersion,
                "server_name": init_result.serverInfo.name if init_result.serverInfo else "unknown",
                "server_version": init_result.serverInfo.version if init_result.serverInfo else "unknown",
            },
            "capabilities": {
                "tools": init_result.capabilities.tools.model_dump() if init_result.capabilities.tools else None,
                "prompts": init_result.capabilities.prompts.model_dump() if init_result.capabilities.prompts else None,
                "resources": init_result.capabilities.resources.model_dump() if init_result.capabilities.resources else None,
            },
            "tool_count": len(tool_names),
            "tools": tool_names,
            "ping_response": ping_output,
            "server_status": status_output,
        }

        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(json.dumps(summary, indent=2))
        print("=" * 60)
        log("OK", "Validation completed successfully")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        log("WARN", "Validation interrupted by user")
        sys.exit(130)
    except Exception as exc:
        log("ERROR", f"Validation failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
