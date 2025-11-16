# MCP Runtime v3 — Python Server (with Original Runtime Lineage)

This project provides a production‑ready **Model Context Protocol (MCP)** server for Claude Desktop/CLI. It exposes a local toolbelt (numeric analysis, Redis memory, file indexing, task queue, semantic search, etc.) over stdio using the official `FastMCP.run_stdio()` transport. The goal is **fast, stable startup on Windows** and a consistent interface for Claude to call local capabilities.

---

## Why/What (short version)

- **Why**: Give Claude a **single, local toolbelt** it can call via MCP without heavy JSON schemas in-context.
- **What**: A Python server (`server.py`) that registers tools for math/stats, shell (opt‑in), Redis‑based memory and queues, project file indexing, and optional embeddings for semantic search.
- **How**: Claude launches the server with `command: python.exe` and `args: [server.py]`. The server answers the JSON‑RPC `initialize` handshake and exposes tools.

---

## Background: Original (pre‑MCP) Runtime lineage

Before converting to a first‑class MCP server, your stack used an **optimized Claude CLI runtime** (v2.5–v2.6) to **reduce token use** and centralize execution in one Python backend. That approach featured:

- A lightweight **command dispatcher** (`tool_runner_v2.py`) implementing operations such as `stats`, `ttest`, `math`, `normalize`, `list`, and an opt‑in **YOLO `shell`**.
- An optional **persistent microserver** (`runtime_server.py`) to keep a “hot” Python process for speed.
- A **bootstrap script** (`claude_init.ai`) that wires Claude CLI to route structured tasks to the Python backend automatically.
- A design goal of **90–97% token savings** by removing bulky MCP/tool schemas from prompt context and offloading computation locally.
- Redis caching, concurrency limits, and a simple folder layout with example data, plus `start_safe.sh/.bat` launchers.

This MCP server keeps the same spirit—**local, Python‑first execution**—but surfaces it via **standard MCP** so both Claude Desktop and CLI can discover and call tools consistently. fileciteturn4file0

---

## What changed in v3 (MCP)

| Area | v2.x (CLI Runtime) | v3 (MCP Server) |
|---|---|---|
| Transport | Ad‑hoc CLI dispatch / optional FastAPI | **Official MCP stdio** (`run_stdio`) |
| Discovery | `--list` ops or docs | **Automatic tool discovery** via MCP |
| Token use | Very low (Python backend) | **Also low**; no giant schemas in prompt |
| Startup | Fast, but occasionally heavy imports | **Fast & deterministic** (lazy imports; embeddings off by default) |
| Desktop integration | Indirect (CLI‑first) | **Native Desktop “Extensions/Tools”** panel |
| Safety | Local workspace; YOLO optional | Same; + `dangerouslyAllowPaths` controls FS reach |

---

## Features (server.py)

- **Tools**: `ping`, `echo`, `server_status`, `column_stats`, `normalize`, `ttest_independent`, `math_eval`, `math_eval_with_meta`, `shell` (opt‑in), `set_memory`, `get_memory`, `delete_memory`, `list_memory_keys`, `index_project_files`, `index_single_file`, `search_indexed_files`, `save_agent_snapshot`, `load_agent_snapshot`, `list_agent_snapshots`, `delete_agent_snapshot`, `clear_all_agent_snapshots`, `semantic_search_files`, `semantic_search_agents`, `queue_task`, `get_next_task`, `finish_task`, `task_history`, `clear_task_history`.
- **Embeddings**: `sentence-transformers` **lazy‑loaded** and **disabled by default** (`MCP_ENABLE_EMBEDDINGS=1` to enable).
- **Redis** (optional): memory, indexing metadata, embeddings, task queue/history. **Short timeouts** so startup never blocks.
- **Logging to stderr** only; stdout reserved for JSON‑RPC frames.
- **Windows‑ready**: tested layout/paths; tolerant of slow imports.

---

## Install

```powershell
# (Recommended) venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Dependencies
pip install "mcp[cli]" numpy scipy sympy redis sentence-transformers anyio
```

> Redis is optional. If it’s not running, the server still starts (features using Redis are disabled gracefully).

---

## Configure Claude Desktop

Edit `C:\\Users\\<You>\\AppData\\Roaming\\Claude\\claude_desktop_config.json` and add:

```jsonc
{
  "mcpServers": {
    "runtime-v3": {
      "command": "C:\\\\Users\\\\Admin\\\\AppData\\\\Local\\\\Programs\\\\Python\\\\Python312\\\\python.exe",
      "args": ["C:\\\\Users\\\\Admin\\\\Documents\\\\mcp_runtime_v3\\\\server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "MCP_RUNTIME_PROJECT_ROOT": "C:\\\\Users\\\\Admin\\\\Documents\\\\mcp_runtime_v3",
        "MCP_ENABLE_EMBEDDINGS": "0",
        "MCP_MEMORY_REDIS_HOST": "127.0.0.1",
        "MCP_MEMORY_REDIS_PORT": "6379",
        "MCP_MEMORY_REDIS_DB": "5"
      },
      "autoStart": true
    }
  },
  "dangerouslyAllowPaths": [
    "C:\\\\Users\\\\Admin\\\\Documents\\\\mcp_runtime_v3",
    "C:\\\\Users\\\\Admin\\\\AppData\\\\Local\\\\Programs\\\\Python\\\\Python312"
  ]
}
```

Open **Claude Desktop → Settings → Developer → Extensions/Tools** and confirm `runtime-v3` appears (tool list should load immediately).

---

## Run manually (sanity check)

```powershell
"C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe" `
  "C:\Users\Admin\Documents\mcp_runtime_v3\server.py"
```
You’ll see logs on **stderr** (e.g., startup info).

---

## Environment variables

- `PYTHONUNBUFFERED=1` — flush logs promptly
- `MCP_RUNTIME_PROJECT_ROOT` — project root for indexing
- `MCP_ENABLE_EMBEDDINGS` — `0` (default) / `1` to enable embeddings
- `MCP_MEMORY_REDIS_HOST/PORT/DB` — Redis connection (optional)
- `MCP_RUNTIME_ALLOW_SHELL` — set to `true` to enable the `shell` tool

---

## Troubleshooting

- **Desktop says “initializing…”** — Ensure `server.py` uses `await mcp.run_stdio()` (this build does) and there are **no prints to stdout** (logs go to stderr). Keep `MCP_ENABLE_EMBEDDINGS=0` to avoid slow Torch imports. Redis timeouts are short, so it won’t block startup.
- **Missing Content‑Length** — Caused by non‑framed bytes on stdin; Desktop is fine, but avoid wrapping the process with anything that writes to its stdin.
- **Windows paths in JSON** — Escape backslashes: `C:\\\\path\\\\to\\\\file.py`.

---

## Security

- `shell` tool is **off by default**. Explicitly set `MCP_RUNTIME_ALLOW_SHELL=true` to enable.
- Use `dangerouslyAllowPaths` to restrict file access locations.
- Be mindful of what is indexed/embedded; embeddings or logs may enter Redis for debugging.

---

## Appendix: Mapping from Original Runtime → MCP Server

- **tool_runner_v2.py** → replaced by **native MCP tools** (same operations exposed as MCP tool calls).
- **runtime_server.py** (FastAPI hot runtime) → unnecessary; MCP server runs persistently when Desktop starts it.
- **claude_init.ai** → not required for Desktop; you can still keep a CLI bootstrap if desired.
- **README_Optimized.md** → still relevant for philosophy & token savings; MCP v3 keeps the Python‑first execution model.

This repository keeps your original design goals—**token efficiency, speed, local control**—and standardizes them behind the MCP interface for better Desktop/CLI integration.
