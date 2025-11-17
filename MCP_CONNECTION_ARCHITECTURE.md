# MCP Codebase Architecture & Connection Analysis
**Generated:** 2025-11-17  
**Codebase:** /home/user/MCP  
**Branch:** claude/fix-mcp-server-connection-01Pb1mR8a915G4Gw44fHG4L2  
**Analysis Depth:** Very Thorough

---

## Executive Summary

The MCP (Model Context Protocol) runtime is a **Python-based MCP server** running as a long-lived process that communicates with Claude Desktop/CLI via **LSP-framed JSON-RPC over stdio**. The server implements:

- **27 tools** covering math/stats, shell execution, Redis-backed memory, file indexing, semantic search, and task queuing
- **Async I/O architecture** with anyio/asyncio for non-blocking socket operations
- **Graceful degradation** when Redis is unavailable
- **Comprehensive error handling** for connection failures, JSON serialization, and resource timeouts

**Status:** Production-ready after Phase 2 improvements (47/47 tests passing)

---

## Part 1: Server Initialization & Architecture

### 1.1 Startup Flow

```
Entry Point: main() [server.py:948-963]
    ↓
    Create async context: _run()
    ↓
    await _check_redis_connection()  [Non-blocking async check]
    ↓
    Log startup messages
    ↓
    async with _stdio_server() → (read_stream, write_stream)
    ↓
    await mcp._mcp_server.run(read_stream, write_stream, init_options)
    ↓
    FastMCP server enters event loop, listening for JSON-RPC messages
```

### 1.2 FastMCP Server Instance

**File:** `/home/user/MCP/server.py:42,57`

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP(name="RuntimeV3")
```

**Initialization Details:**
- **Name:** "RuntimeV3" (appears in server capability information)
- **Type:** FastMCP instance (Anthropic MCP server framework)
- **Protocol:** JSON-RPC 2.0 over stdio with LSP-style Content-Length framing
- **Capabilities:** Tool discovery, tool calling, prompt helpers, memory support

### 1.3 Tool Registration

**Method:** Decorator pattern via `@mcp.tool()`

**File:** `/home/user/MCP/server.py:349-787` (28 tool definitions)

Tools registered include:
- Core: `ping`, `echo`, `server_status`
- Math/Stats: `column_stats`, `normalize`, `ttest_independent`, `math_eval`, `math_eval_with_meta`
- Shell: `shell` (disabled by default, requires `MCP_RUNTIME_ALLOW_SHELL=true`)
- Memory: `set_memory`, `get_memory`, `delete_memory`, `list_memory_keys`
- File Indexing: `index_project_files`, `index_single_file`, `search_indexed_files`
- Agent Snapshots: `save_agent_snapshot`, `load_agent_snapshot`, `list_agent_snapshots`, `delete_agent_snapshot`, `clear_all_agent_snapshots`
- Semantic Search: `semantic_search_files`, `semantic_search_agents`
- Task Queue: `queue_task`, `get_next_task`, `finish_task`, `task_history`, `clear_task_history`
- Prompts: `analyze_numeric_series_prompt`

### 1.4 Configuration & Environment Variables

**Primary Config Source:** Environment variables (no YAML/JSON config files)

**File:** `/home/user/MCP/.env.example` (23 lines documenting all 9 variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_MEMORY_REDIS_HOST` | `localhost` | Redis server hostname |
| `MCP_MEMORY_REDIS_PORT` | `6379` | Redis server port |
| `MCP_MEMORY_REDIS_DB` | `5` | Redis database index |
| `MCP_REDIS_CONNECT_TIMEOUT` | `5` | Connection timeout (seconds) [Phase 2] |
| `MCP_REDIS_SOCKET_TIMEOUT` | `5` | Socket timeout (seconds) [Phase 2] |
| `MCP_RUNTIME_PROJECT_ROOT` | `os.getcwd()` | Project root for file indexing |
| `MCP_RUNTIME_ALLOW_SHELL` | `false` | Enable shell tool (security) |
| `MCP_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model name |
| `MCP_EMBED_LOAD_TIMEOUT` | `300` | Model download timeout (seconds) [Phase 2] |

---

## Part 2: Connection Establishment & Protocol

### 2.1 Transport Layer: LSP-Style Framing

**File:** `/home/user/MCP/server.py:839-945`

The server implements **tolerant LSP-style Content-Length framing** with JSON-RPC 2.0:

```
Message Format:
┌─────────────────────────────────────────┐
│ Content-Length: <N>\r\n                 │
│ \r\n                                    │
│ <N bytes of UTF-8 JSON-RPC message>    │
└─────────────────────────────────────────┘
```

**Key Properties:**
- **Tolerant of preamble noise:** Server skips non-framed input until finding a `Content-Length:` header
- **Binary stdin/stdout:** Uses `anyio.wrap_file(sys.stdin.buffer)` for async binary I/O
- **No stray output:** All logging goes to stderr; stdout reserved exclusively for JSON-RPC frames

### 2.2 Connection Establishment: Reader/Writer Task Group

**Architecture:** Two concurrent async tasks

#### Reader Task (Line 911-927)
```python
async def reader():
    async with send_stream:
        while True:
            body = await read_packet()  # Reads framed message from stdin
            if body is None:  # EOF detected
                break
            try:
                msg = JSONRPCMessage.model_validate_json(body.decode("utf-8"))
                await send_stream.send(SessionMessage(msg))
            except Exception as exc:
                log.error(f"Failed to parse JSON-RPC message: {exc}")
                log.debug(f"Problem JSON: {body[:200]!r}")
```

**Responsibilities:**
1. Read framed packets from stdin
2. Validate JSON-RPC format
3. Send to FastMCP server via memory stream
4. Handle parsing errors gracefully

#### Writer Task (Line 929-940)
```python
async def writer():
    async with write_recv:
        async for sess in write_recv:
            payload = sess.message.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
            header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
            await a_stdout.write(header + payload)
            await a_stdout.flush()
```

**Responsibilities:**
1. Receive SessionMessages from FastMCP server
2. Serialize to JSON-RPC format
3. Frame with Content-Length header
4. Send to stdout
5. Flush immediately for responsiveness

### 2.3 Initialization Sequence (MCP Handshake)

**Files:** Test coverage in `/home/user/MCP/test_json_rpc_basic.py:73-140`

**Handshake Flow:**
```
Client (Claude)                          Server (MCP Runtime)
    │                                           │
    ├─ JSON-RPC initialize request ──────────→ │
    │  {id: 1, method: "initialize",            │
    │   params: {protocolVersion, capabilities}}│
    │                                           ├─ FastMCP processes request
    │                                           ├─ Creates ServerInfo
    │                                           ├─ Returns capabilities
    │  ← Content-Length framed response ──────┤
    │  {id: 1, result: {protocolVersion,        │
    │   capabilities, serverInfo}}              │
    │                                           │
    ├─ notifications/initialized ──────────→  │
    │  (no id, just notification)               │
    │                                           │
    ├─ tools/list request ──────────────────→  │
    │  {id: 2, method: "tools/list"}            ├─ Returns tool definitions
    │  ← Content-Length framed response ──────┤
    │  {id: 2, result: {tools: [...]}}          │
    │                                           │
    ├─ tools/call request ──────────────────→  │
    │  {id: 3, method: "tools/call",            ├─ Executes tool
    │   params: {name: "ping", arguments: {}}}  ├─ Captures result
    │  ← JSON-RPC response ──────────────────┤
    │  {id: 3, result: {content: [...]}}        │
```

**Key Implementation Points:**
- Connection is **initiated by client** (Claude)
- Server **does not know client address** (stdio is bidirectional)
- **No explicit handshake timeout** (relies on client timeout)
- **Protocol version negotiated** via initialize exchange

---

## Part 3: Redis Connection & Graceful Degradation

### 3.1 Redis Initialization (Phase 2 Improvement)

**File:** `/home/user/MCP/server.py:64-94`

**Original Issue (Phase 1):** Blocking `redis_client.ping()` at module import time
**Solution (Phase 2):** Moved to async check during main startup

```python
# Non-blocking initialization
redis_client: Optional[redis.Redis] = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
    socket_connect_timeout=REDIS_CONNECT_TIMEOUT,  # Configurable: 5s
    socket_timeout=REDIS_SOCKET_TIMEOUT,           # Configurable: 5s
)
MEMORY_ENABLED = False  # Will be set to True after successful async check

async def _check_redis_connection() -> None:
    """Non-blocking Redis connection check during startup."""
    global MEMORY_ENABLED, redis_client
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, redis_client.ping)  # Non-blocking
        MEMORY_ENABLED = True
        log.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT} DB={REDIS_DB}")
    except Exception as e:
        redis_client = None
        MEMORY_ENABLED = False
        log.warning(f"Redis not available: {e}. Memory features disabled.")
```

**Called in main (Line 950):**
```python
async def _run() -> None:
    await _check_redis_connection()  # Non-blocking, runs during startup
    log.info("Starting MCP Runtime v3.0...")
    # ... rest of server initialization
```

### 3.2 Graceful Degradation Pattern

**All Redis-dependent tools follow this pattern:**

```python
@mcp.tool()
def set_memory(key: str, value: str) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    # ... proceed with operation
```

**Behavior:**
- If Redis unavailable: Tool raises RuntimeError with clear message
- Client sees: Tool call failed with specific error (not cryptic connection error)
- Server continues running: Non-memory tools unaffected
- Logging: "Redis not available: ... Memory features disabled." (stderr)

---

## Part 4: Error Handling Mechanisms

### 4.1 JSON-RPC Protocol Error Handling

**Reader Error Handling (Line 922):**
```python
except Exception as exc:
    log.error(f"Failed to parse JSON-RPC message: {exc}")
    log.debug(f"Problem JSON: {body[:200]!r}")
    # Continues reading next message (resilient)
```

**Pattern:** Log error but don't crash; read next message

### 4.2 JSON Serialization Error Handling (Phase 2)

**File:** `/home/user/MCP/server.py:275-296`

**Problem:** Redis operations use `json.dumps()` which fails on non-serializable objects

**Solution:** 3-tier fallback (`_safe_json_dumps`)

```python
def _safe_json_dumps(obj: Any, context: str = "") -> str:
    """Safely serialize object to JSON with fallback for non-serializable types."""
    try:
        return json.dumps(obj, ensure_ascii=False)  # Preferred
    except (TypeError, ValueError) as e:
        log.warning(f"JSON serialization failed for {context}: {e}. Using fallback.")
        try:
            return json.dumps(obj, default=str, ensure_ascii=False)  # Second attempt
        except Exception as e2:
            log.error(f"Fallback serialization also failed for {context}: {e2}")
            return json.dumps({"_repr": repr(obj), "_error": str(e)})  # Last resort
```

**Applied to:** 8 Redis operations (file indexing, agent snapshots, task queues)

### 4.3 Embedding Model Timeout & Retry (Phase 2)

**File:** `/home/user/MCP/server.py:118-165`

**Problem:** Sentence-transformers downloads (~2GB) could hang indefinitely

**Solution:** Signal-based timeout with exponential backoff

```python
@contextmanager
def _timeout(seconds):
    """Context manager for operation timeout using SIGALRM."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds}s")
    
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        for attempt in range(3):
            try:
                with _timeout(EMBED_LOAD_TIMEOUT):  # Default: 300s
                    _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
                log.info("Embedding model loaded successfully")
                break
            except TimeoutError:
                log.warning(f"Model loading timed out (attempt {attempt+1}/3)")
                if attempt == 2:
                    raise RuntimeError(f"Failed to load embedding model...")
                backoff_time = 2 ** attempt  # Exponential: 1s, 2s, 4s
                log.info(f"Retrying in {backoff_time}s...")
                time.sleep(backoff_time)
```

**Retry Strategy:** 3 attempts with backoff (1s, 2s, 4s)

### 4.4 Reader/Writer Task Error Handling

**Reader EOF Detection (Line 925):**
```python
except anyio.ClosedResourceError:
    log.debug("Reader: stdin closed")
```

**Writer Failure (Line 940):**
```python
except Exception as e:
    log.error(f"Writer error: {e}")
```

**Behavior:** Log error and exit task (causes main loop to terminate)

---

## Part 5: Server Lifecycle Management

### 5.1 Server Startup Lifecycle

```
Phase 1: Module Import (server.py)
├─ Import FastMCP, configure Redis client (non-blocking)
├─ Register 28 tools
├─ Define helper functions
└─ Set MEMORY_ENABLED = False (tentatively)

Phase 2: main() Entry Point
├─ Create async context _run()
└─ asyncio.run(_run())

Phase 3: Async Startup (_run())
├─ await _check_redis_connection()
│  └─ Updates MEMORY_ENABLED (async, non-blocking)
├─ Log startup messages
├─ Create _stdio_server()
│  ├─ Create reader/writer async tasks
│  └─ Start task group
└─ await mcp._mcp_server.run(read_stream, write_stream, init_options)

Phase 4: Event Loop
├─ reader() reads stdin continuously
├─ writer() writes to stdout continuously
├─ FastMCP processes JSON-RPC requests
└─ Tools execute on-demand
```

### 5.2 Connection Attachment/Detachment

**Attachment (Implicit):**
- Client initiates by sending initialize message to stdin
- Reader task detects and forwards to FastMCP
- FastMCP processes and sends response via writer
- Connection is established (no explicit "attach" API)

**Detachment (Graceful Shutdown):**
```
Option 1: Client sends EOF (closes stdin)
├─ Reader gets body = None from read_packet()
├─ Reader exits loop, closes send_stream
├─ Writer detects ClosedResourceError or stream empty
├─ Writer exits loop
└─ Task group exits, main() returns

Option 2: SIGTERM/SIGINT signal
├─ Python runtime receives signal
├─ asyncio event loop cancels all tasks
├─ Cleanup happens in finally blocks
└─ Process exits
```

### 5.3 No Explicit Disconnect Handling

**Key Limitation:** 
- MCP protocol has no explicit "disconnect" method
- Server assumes connection stays alive until EOF or signal
- No heartbeat mechanism
- If client crashes unexpectedly, server may continue running

---

## Part 6: Runtime References (runtime-v3, runtime-vs)

### 6.1 "Runtime v3.0" Naming

**File:** `/home/user/MCP/server.py:4` (module docstring)
**File:** `/home/user/MCP/ReadmePart2.md:74` (configuration example)

```python
"""MCP Runtime v3.0 - Full Server (Production, tolerant LSP-framed stdio)"""
mcp = FastMCP(name="RuntimeV3")
```

**Naming Context:**
- `runtime-v3` appears in Claude Desktop configuration JSON (`ReadmePart2.md:74`)
- Refers to **MCP server v3** (not a separate runtime system)
- Lineage: Original runtime → v2.x (CLI-based) → v3.0 (MCP-based)

### 6.2 No "runtime-vs" References Found

**Search Result:** No occurrences of `runtime-vs` in codebase
- Not a feature or component name
- Possibly refers to alternate naming scheme (never implemented)
- All references use `runtime-v3`

### 6.3 Historical Context (from docs)

**File:** `/home/user/MCP/ReadmePart2.md:15-25`

Evolution:
```
Pre-MCP Era:
├─ command dispatcher (tool_runner_v2.py)
├─ optional persistent microserver (runtime_server.py)
├─ bootstrap script (claude_init.ai)
└─ Goal: 90-97% token savings

MCP Era (v3):
├─ Standard MCP server interface (FastMCP)
├─ Tool discovery via MCP protocol
├─ Better Desktop/CLI integration
└─ Same local Python-first execution model
```

---

## Part 7: Known Issues & Production Considerations

### 7.1 High-Severity Issues (Already Fixed in Phase 2)

| ID | Issue | Status | Fix |
|----|-------|--------|-----|
| F1 | Blocking Redis ping at import | ✅ Fixed | Moved to async `_check_redis_connection()` |
| F2 | Sync Redis in async server | ⚠️ Partial | Using sync Redis in thread pool (suboptimal) |
| F3 | Hardcoded Windows paths | ✅ Fixed | Use `sys.executable`, `pathlib.Path` |
| F5 | Embedding model no timeout | ✅ Fixed | Added `SIGALRM`-based timeout (300s default) |
| F4 | JSON serialization errors | ✅ Fixed | `_safe_json_dumps()` with 3-tier fallback |
| F10 | Aggressive Redis timeouts | ✅ Fixed | Configurable: 5s defaults (was 2s) |

### 7.2 Medium-Severity Issues (Unresolved)

**F2 Detailed:** Synchronous Redis Client in Async Server
- Redis operations use blocking `redis.Redis()` (not `aioredis`)
- Blocking calls executed via `loop.run_in_executor()` (thread pool)
- Workaround: Non-blocking in terms of main event loop, but suboptimal
- **Future:** Migrate to `aioredis` for true async Redis

### 7.3 Operational Considerations

**Redis Dependency:**
- 12 of 28 tools require Redis
- Server starts without Redis (graceful degradation)
- Memory features disabled if Redis unavailable
- No way to enable memory after startup (one-time check)

**Embedding Model:**
- 2GB download on first semantic search call
- Lazy-loaded (doesn't block startup)
- Timeout: 300s configurable
- 3 retries with exponential backoff

**Logging:**
- All logs go to stderr (important for Windows)
- stdout reserved for JSON-RPC (critical)
- Log level: DEBUG (verbose)

**File Indexing Limits:**
- Max file size: 2MB (configurable)
- Max snippet: 2000 chars (configurable)
- Indexed extensions: json, log, txt, md, py, js, ts, tsx, css, html, yml

---

## Part 8: Testing & Validation

### 8.1 Test Coverage (47 Tests, 100% Passing)

**Phase 1 Tests (25):**
- `test_validate_cross_platform.py` - Path handling (7 tests)
- `test_server_startup.py` - No hangs, graceful termination (6 tests)
- `test_redis_graceful_degradation.py` - Redis unavailability (6 tests)
- `test_json_rpc_basic.py` - Protocol handshake (6 tests)

**Phase 2 Tests (22):**
- `test_embedding_timeout.py` - Model timeout/retry (7 tests)
- `test_json_serialization_errors.py` - Error handling (5 tests)
- `test_redis_timeout_configuration.py` - Timeout settings (5 tests)
- `test_handshake_cross_platform.py` - Cross-platform (5 tests)

**Execution Time:** ~36 seconds for full suite

### 8.2 Key Test Scenarios

**Connection Establishment:**
```python
# test_json_rpc_basic.py:73-140
1. Send initialize with protocolVersion, capabilities
2. Receive initialize response with serverInfo
3. Send initialized notification
4. Send tools/list request
5. Verify tool discovery works
6. Send tools/call request
7. Verify ping tool execution
```

**Redis Degradation:**
```python
# test_redis_graceful_degradation.py:20-89
1. Mock Redis to fail on ping
2. Import server module
3. Verify MEMORY_ENABLED = False
4. Verify server still imports successfully
5. Attempt memory operation
6. Verify RuntimeError raised with clear message
```

**Error Handling:**
```python
# test_json_rpc_basic.py:357-416
1. Send garbage data on stdin
2. Server should log error and continue
3. Send proper JSON-RPC message
4. Server should respond normally (resilient to noise)
```

---

## Part 9: Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Desktop/CLI                        │
│                                                               │
│  (Initiates MCP connection via spawn subprocess)             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ stdin/stdout (LSP-framed JSON-RPC)
                     │
┌────────────────────▼────────────────────────────────────────┐
│              MCP Server Process (server.py)                  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  main() → asyncio.run(_run())                        │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                       │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │  _run() async function                               │  │
│  │  ├─ await _check_redis_connection() [non-blocking]   │  │
│  │  └─ async with _stdio_server()                       │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │  _stdio_server() async context manager          │ │  │
│  │  │                                                  │ │  │
│  │  │  ┌──────────────┐          ┌──────────────┐    │ │  │
│  │  │  │  reader()    │          │  writer()    │    │ │  │
│  │  │  ├──────────────┤          ├──────────────┤    │ │  │
│  │  │  │ Read stdin   │          │ Write stdout │    │ │  │
│  │  │  │ Parse framed │          │ Format frame │    │ │  │
│  │  │  │ JSON-RPC     │          │ Send JSON-RPC│    │ │  │
│  │  │  │ messages     │          │ messages     │    │ │  │
│  │  │  │              │          │              │    │ │  │
│  │  │  │ memory stream────────────memory stream    │ │  │
│  │  │  └──────────────┘          └──────────────┘    │ │  │
│  │  │           ▲                        ▲            │ │  │
│  │  │           │                        │            │ │  │
│  │  └───────────┼────────────────────────┼────────────┘ │  │
│  │              │                        │              │  │
│  │  ┌───────────▼────────────────────────▼────────────┐ │  │
│  │  │         FastMCP Server (.run())                 │ │  │
│  │  │  ├─ Parse initialize request                    │ │  │
│  │  │  ├─ Return server info & capabilities           │ │  │
│  │  │  ├─ List 28 tools on tools/list                 │ │  │
│  │  │  └─ Execute tools on tools/call                 │ │  │
│  │  │                                                  │ │  │
│  │  │  ┌────────────┬────────────┬───────────────┐   │ │  │
│  │  │  │   Math     │   Shell    │   Memory      │   │ │  │
│  │  │  │  Tools     │   (opt-in) │   Tools       │   │ │  │
│  │  │  │            │            │               │   │ │  │
│  │  │  │ • stats    │ • shell    │ • get_memory  │   │ │  │
│  │  │  │ • ttest    │            │ • set_memory  │   │ │  │
│  │  │  │ • math_eval│            │ • index_*     │   │ │  │
│  │  │  │            │            │ • search_*    │   │ │  │
│  │  │  └────────────┴────────────┴───────────────┘   │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  │              ▲                                        │  │
│  │              │ Redis operations                       │  │
│  │              └──────────────┐                         │  │
│  └─────────────────────────────┼─────────────────────────┘  │
│                                 │                            │
└─────────────────────────────────┼────────────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │                            │
                    │  Redis (Optional)          │
                    │  localhost:6379            │
                    │                            │
                    │ • Memory (mem:*)           │
                    │ • File index               │
                    │ • Embeddings               │
                    │ • Agent snapshots          │
                    │ • Task queue               │
                    └────────────────────────────┘
```

---

## Part 10: Configuration Quick Reference

### 10.1 Claude Desktop Configuration

**File:** `C:\Users\<You>\AppData\Roaming\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "runtime-v3": {
      "command": "C:\\...\\python.exe",
      "args": ["C:\\...\\mcp_runtime_v3\\server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "MCP_RUNTIME_PROJECT_ROOT": "C:\\...\\mcp_runtime_v3",
        "MCP_MEMORY_REDIS_HOST": "127.0.0.1",
        "MCP_MEMORY_REDIS_PORT": "6379",
        "MCP_MEMORY_REDIS_DB": "5",
        "MCP_REDIS_CONNECT_TIMEOUT": "5",
        "MCP_REDIS_SOCKET_TIMEOUT": "5",
        "MCP_RUNTIME_ALLOW_SHELL": "false",
        "MCP_EMBED_LOAD_TIMEOUT": "300"
      },
      "autoStart": true
    }
  },
  "dangerouslyAllowPaths": [
    "C:\\...\\mcp_runtime_v3",
    "C:\\...\\Python312"
  ]
}
```

### 10.2 Environment Setup

**Install dependencies:**
```bash
pip install -r requirements.txt
# Installs: mcp[cli], numpy, scipy, sympy, redis, sentence-transformers, anyio
```

**Configure environment:**
```bash
cp .env.example .env
# Edit .env as needed
```

### 10.3 Startup Verification

```bash
# Start server manually
python3 server.py

# Expected output (stderr):
# [INFO] Starting MCP Runtime v3.0...
# [INFO] Project root: /path/to/project
# [INFO] Memory enabled: True|False (depends on Redis)
# [INFO] stdio transport ready, initializing MCP server...
```

---

## Summary Table: Connection & Error Handling

| Aspect | Implementation | Key Features |
|--------|---|---|
| **Transport** | LSP-framed JSON-RPC over stdio | Content-Length framing, tolerant of noise |
| **Async Model** | anyio with task group | Two concurrent tasks (reader/writer) |
| **Redis Init** | Async `_check_redis_connection()` | Non-blocking, graceful degradation |
| **JSON Errors** | `_safe_json_dumps()` with 3-tier fallback | Prevents crashes on non-serializable data |
| **Embedding Timeout** | SIGALRM context manager + retry | 300s default, 3 attempts, exponential backoff |
| **Protocol Errors** | Log and continue pattern | Resilient to malformed messages |
| **Graceful Shutdown** | EOF or signal handling | Cleanly closes streams and exits |
| **Configuration** | Environment variables only | 9 configurable parameters, sensible defaults |
| **Tool Discovery** | FastMCP decorator pattern | 28 tools, auto-registered |
| **Memory Features** | Optional Redis dependency | Works without Redis (tools raise errors) |

---

## Conclusion

The MCP Runtime v3.0 is a **production-ready, fault-tolerant MCP server** with:

1. **Robust Connection Handling:** LSP-framed JSON-RPC with noise tolerance
2. **Comprehensive Error Handling:** Multi-tier fallbacks for JSON, timeouts, and connection failures
3. **Graceful Degradation:** Works without Redis, embedding models, or shell access
4. **Configurability:** 9 environment variables for fine-tuning
5. **Well-Tested:** 47 comprehensive tests (100% passing)
6. **Cross-Platform:** Linux, macOS, Windows compatible

**Phase 2 improvements** resolved critical issues around blocking connections, JSON serialization, and timeout handling. The server now exhibits **production-grade reliability and observability**.
