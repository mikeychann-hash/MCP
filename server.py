#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Runtime v3.0 - Full Server (Production, tolerant LSP-framed stdio)

Key fixes & features:
- LSP-style stdio framing with Content-Length (tolerant of preamble/noise)
- No stray output on stdout (JSON-RPC only); logging to stderr
- Numeric tools (stats, normalize, Welch t-test, math eval + meta)
- YOLO shell tool (guarded by MCP_RUNTIME_ALLOW_SHELL)
- Redis-backed memory, file indexing, agent snapshots
- Lazy sentence-transformers embeddings; semantic search
- Task queue + job history (Redis)
- Auto-logging of tool calls (if Redis available)
- Prompt helper for numeric analysis

Install deps:
    pip install "mcp[cli]" numpy scipy sympy redis sentence-transformers anyio
"""

from __future__ import annotations

import asyncio
import functools
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import anyio
import numpy as np
import redis
import sympy as sp
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.server.fastmcp import FastMCP
from mcp.server.session import SessionMessage
from mcp.types import CallToolResult, TextContent, JSONRPCMessage
from scipy import stats as scipy_stats
from sentence_transformers import SentenceTransformer

import logging

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
log = logging.getLogger("mcp")

# -----------------------------------------------------------------------------
# Server setup
# -----------------------------------------------------------------------------

mcp = FastMCP(name="RuntimeV3")
PROJECT_ROOT = Path(os.getenv("MCP_RUNTIME_PROJECT_ROOT", os.getcwd())).resolve()

# -----------------------------------------------------------------------------
# Redis Memory Client and Key Prefixes
# -----------------------------------------------------------------------------

REDIS_HOST = os.getenv("MCP_MEMORY_REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("MCP_MEMORY_REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("MCP_MEMORY_REDIS_DB", "5"))
REDIS_CONNECT_TIMEOUT = int(os.getenv("MCP_REDIS_CONNECT_TIMEOUT", "5"))
REDIS_SOCKET_TIMEOUT = int(os.getenv("MCP_REDIS_SOCKET_TIMEOUT", "5"))

# Initialize Redis client without blocking ping
redis_client: Optional[redis.Redis] = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
    socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
    socket_timeout=REDIS_SOCKET_TIMEOUT,
)
MEMORY_ENABLED = False  # Will be set to True after successful async check

async def _check_redis_connection() -> None:
    """Non-blocking Redis connection check during startup."""
    global MEMORY_ENABLED, redis_client
    try:
        # Test connection asynchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, redis_client.ping)
        MEMORY_ENABLED = True
        log.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT} DB={REDIS_DB}")
    except Exception as e:
        redis_client = None
        MEMORY_ENABLED = False
        log.warning(f"Redis not available: {e}. Memory features disabled.")

# Key prefixes
REDIS_MEMORY_PREFIX = "mem:"
REDIS_FILE_INDEX_PREFIX = "file_index:"
REDIS_AGENT_SNAPSHOT_PREF = "agent_snap:"
REDIS_EMBED_FILE_PREFIX = "emb:file:"
REDIS_EMBED_AGENT_PREFIX = "emb:agent:"
REDIS_TASK_QUEUE_KEY = "task_queue"
REDIS_TASK_HISTORY_PREF = "job_history:"

# -----------------------------------------------------------------------------
# Embedding / Semantic Search Config (LAZY LOADING)
# -----------------------------------------------------------------------------

EMBED_MODEL_NAME = os.getenv(
    "MCP_EMBED_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
EMBED_DIM = int(os.getenv("MCP_EMBED_DIM", "384"))  # all-MiniLM-L6-v2 is 384-d

_embed_model: Optional[SentenceTransformer] = None


def _get_embed_model() -> SentenceTransformer:
    """Lazy-load the embedding model only when first needed."""
    global _embed_model
    if _embed_model is None:
        log.info(f"Loading embedding model: {EMBED_MODEL_NAME} (this may take a moment)...")
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        log.info("Embedding model loaded successfully")
    return _embed_model


def _embed_text(text: str) -> List[float]:
    model = _get_embed_model()
    vec = model.encode([text], normalize_embeddings=True)[0]
    return [float(x) for x in vec]


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if len(vec_a) != len(vec_b) or len(vec_a) == 0:
        return 0.0
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

INDEXED_EXTENSIONS = {
    ".json", ".log", ".txt", ".md",
    ".py", ".js", ".ts", ".tsx",
    ".css", ".html", ".yml", ".yaml",
}
MAX_INDEX_FILE_SIZE_BYTES = int(os.getenv("MCP_INDEX_MAX_SIZE", str(2 * 1024 * 1024)))
MAX_INDEX_CONTENT_CHARS = int(os.getenv("MCP_INDEX_MAX_CHARS", "2000"))


def _ensure_list_of_numbers(values: Any, param_name: str) -> np.ndarray:
    """Convert input to 1D numpy array of floats."""
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{param_name} must be a list of numbers, got {type(values).__name__}")
    try:
        arr = np.array(values, dtype=float).astype(float)
    except Exception as exc:
        raise ValueError(f"{param_name} must contain only numeric values: {exc}") from exc
    if arr.ndim != 1:
        raise ValueError(f"{param_name} must be 1D (list of numbers), got shape {arr.shape}")
    return arr


def _bool_from_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")


def _should_index_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() not in INDEXED_EXTENSIONS:
        return False
    try:
        size = path.stat().st_size
    except OSError:
        return False
    return size <= MAX_INDEX_FILE_SIZE_BYTES


def _build_file_index_entry(path: Path) -> Dict[str, Any]:
    rel_path = path.relative_to(PROJECT_ROOT).as_posix()
    try:
        stat = path.stat()
        size = stat.st_size
        mtime = stat.st_mtime
    except OSError as exc:
        raise RuntimeError(f"Failed to stat file {path}: {exc}") from exc
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"Failed to read file {path}: {exc}") from exc

    snippet = text[:MAX_INDEX_CONTENT_CHARS]
    return {
        "path": rel_path,
        "abs_path": str(path),
        "size": size,
        "mtime": mtime,
        "snippet": snippet,
    }


def _snapshot_to_text(agent_id: str, state: Any) -> str:
    try:
        body = json.dumps(state, indent=2, ensure_ascii=False)
    except Exception:
        body = str(state)
    return f"Agent: {agent_id}\n{body}"


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    try:
        json.dumps(value)
        return value
    except Exception:
        return repr(value)


def _safe_json_dumps(obj: Any, context: str = "") -> str:
    """
    Safely serialize object to JSON with fallback for non-serializable types.

    Args:
        obj: Object to serialize
        context: Description of what's being serialized (for logging)

    Returns:
        JSON string
    """
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        log.warning(f"JSON serialization failed for {context}: {e}. Using fallback.")
        # Try with custom JSON encoder
        try:
            return json.dumps(obj, default=str, ensure_ascii=False)
        except Exception as e2:
            log.error(f"Fallback serialization also failed for {context}: {e2}")
            # Last resort: use repr
            return json.dumps({"_repr": repr(obj), "_error": str(e)})


# Wrap tools to auto-log calls into Redis
_original_tool_decorator = mcp.tool


def _log_tool_call(tool_name: str, args: Any, kwargs: Any) -> None:
    if not MEMORY_ENABLED or not redis_client:
        return
    entry = {
        "tool": tool_name,
        "args": _json_safe(list(args)),
        "kwargs": _json_safe(kwargs),
        "timestamp": time.time(),
    }
    key = f"tool_log:{time.time()}:{tool_name}"
    try:
        redis_client.set(key, json.dumps(entry), ex=86400)
    except Exception:
        pass


def _auto_logging_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            _log_tool_call(func.__name__, args, kwargs)
        finally:
            return func(*args, **kwargs)
    return wrapper


def tool_with_logging(*d_args, **d_kwargs):
    # Supports both @mcp.tool() and @mcp.tool
    def decorator(func):
        wrapped = _auto_logging_decorator(func)
        return _original_tool_decorator(*d_args, **d_kwargs)(wrapped)

    if len(d_args) == 1 and callable(d_args[0]) and not d_kwargs:
        func = d_args[0]
        wrapped = _auto_logging_decorator(func)
        return _original_tool_decorator()(wrapped)
    return decorator


mcp.tool = tool_with_logging

# -----------------------------------------------------------------------------
# Built-in Tools
# -----------------------------------------------------------------------------


@mcp.tool()
def ping() -> str:
    """Simple ping tool to verify server is responding."""
    return "pong"


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the provided message."""
    return f"Echo: {message}"


@mcp.tool()
def server_status() -> Dict[str, Any]:
    """Get server status and configuration."""
    return {
        "server_name": "RuntimeV3",
        "project_root": str(PROJECT_ROOT),
        "memory_enabled": MEMORY_ENABLED,
        "redis_config": {
            "host": REDIS_HOST,
            "port": REDIS_PORT,
            "db": REDIS_DB,
        } if MEMORY_ENABLED else None,
        "embed_model": EMBED_MODEL_NAME,
        "shell_enabled": _bool_from_env("MCP_RUNTIME_ALLOW_SHELL", False),
    }


# -----------------------------------------------------------------------------
# Numeric Tools
# -----------------------------------------------------------------------------


@mcp.tool()
def column_stats(values: List[float]) -> Dict[str, float]:
    """Compute mean, median, std, min, max, count for a numeric list."""
    arr = _ensure_list_of_numbers(values, "values")
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "count": int(len(arr)),
    }


@mcp.tool()
def normalize(values: List[float], method: str = "zscore") -> List[float]:
    """Normalize values via 'zscore' or 'minmax'."""
    arr = _ensure_list_of_numbers(values, "values")
    if method == "zscore":
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            return [0.0] * len(arr)
        normalized = (arr - mean) / std
    elif method == "minmax":
        min_val = np.min(arr)
        max_val = np.max(arr)
        if max_val == min_val:
            return [0.5] * len(arr)
        normalized = (arr - min_val) / (max_val - min_val)
    else:
        raise ValueError(f"Unknown normalization method: {method}")
    return [float(x) for x in normalized]


@mcp.tool()
def ttest_independent(group_a: List[float], group_b: List[float]) -> Dict[str, float]:
    """Welch's t-test (independent) with NaN-safe policy."""
    arr_a = _ensure_list_of_numbers(group_a, "group_a")
    arr_b = _ensure_list_of_numbers(group_b, "group_b")
    t_stat, p_val = scipy_stats.ttest_ind(arr_a, arr_b, equal_var=False, nan_policy="omit")
    return {"t_statistic": float(t_stat), "p_value": float(p_val)}


@mcp.tool()
def math_eval(expr: str) -> Dict[str, Any]:
    """Evaluate a math expression with SymPy; returns simplified + numeric value."""
    try:
        sym_expr = sp.sympify(expr)
        simplified = sp.simplify(sym_expr)
        try:
            numeric_val = float(simplified.evalf())
        except Exception:
            numeric_val = None
        return {"original": expr, "simplified": str(simplified), "numeric": numeric_val}
    except Exception as exc:
        return {"original": expr, "error": str(exc)}


# -----------------------------------------------------------------------------
# Shell Tool (Controlled by Environment Variable)
# -----------------------------------------------------------------------------


@mcp.tool()
def shell(command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
    """Execute a shell command when MCP_RUNTIME_ALLOW_SHELL=true."""
    if not _bool_from_env("MCP_RUNTIME_ALLOW_SHELL", False):
        raise RuntimeError("Shell tool is disabled. Set MCP_RUNTIME_ALLOW_SHELL=true to enable.")

    work_dir = Path(cwd) if cwd else PROJECT_ROOT
    if not work_dir.is_absolute():
        work_dir = PROJECT_ROOT / work_dir
    work_dir = work_dir.resolve()

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": int(result.returncode)}
    except subprocess.TimeoutExpired:
        raise RuntimeError("Command timed out after 30 seconds")
    except Exception as exc:
        raise RuntimeError(f"Command failed: {exc}")


# -----------------------------------------------------------------------------
# Memory Tools
# -----------------------------------------------------------------------------


@mcp.tool()
def set_memory(key: str, value: str) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    redis_client.set(REDIS_MEMORY_PREFIX + key, value)
    return {"ok": True, "key": key}


@mcp.tool()
def get_memory(key: str) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    val = redis_client.get(REDIS_MEMORY_PREFIX + key)
    return {"key": key, "value": val}


@mcp.tool()
def delete_memory(key: str) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    deleted = redis_client.delete(REDIS_MEMORY_PREFIX + key)
    return {"ok": True, "deleted": int(deleted)}


@mcp.tool()
def list_memory_keys(prefix: str = "") -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    pattern = REDIS_MEMORY_PREFIX + prefix + "*"
    keys = redis_client.keys(pattern)
    clean = [k.replace(REDIS_MEMORY_PREFIX, "", 1) for k in keys]
    return {"keys": clean, "count": len(clean)}


# -----------------------------------------------------------------------------
# File Indexing Tools
# -----------------------------------------------------------------------------


@mcp.tool()
def index_project_files(root_dir: str = ".") -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")

    root_path = Path(root_dir)
    if not root_path.is_absolute():
        root_path = PROJECT_ROOT / root_path
    root_path = root_path.resolve()

    indexed = 0
    for fpath in root_path.rglob("*"):
        if _should_index_file(fpath):
            try:
                entry = _build_file_index_entry(fpath)
                key = REDIS_FILE_INDEX_PREFIX + entry["path"]
                redis_client.set(key, json.dumps(entry))
                indexed += 1
            except Exception:
                continue
    return {"indexed": indexed, "root": str(root_path)}


@mcp.tool()
def index_single_file(file_path: str, embed: bool = True) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")

    fpath = Path(file_path)
    if not fpath.is_absolute():
        fpath = PROJECT_ROOT / fpath
    fpath = fpath.resolve()

    if not _should_index_file(fpath):
        raise ValueError(f"File not eligible for indexing: {fpath}")

    entry = _build_file_index_entry(fpath)
    key = REDIS_FILE_INDEX_PREFIX + entry["path"]
    redis_client.set(key, json.dumps(entry))

    result: Dict[str, Any] = {"indexed": True, "path": entry["path"]}
    if embed:
        text = entry["snippet"]
        emb = _embed_text(text)
        emb_key = REDIS_EMBED_FILE_PREFIX + entry["path"]
        emb_data = {"path": entry["path"], "text": text, "embedding": emb}
        redis_client.set(emb_key, json.dumps(emb_data))
        result["embedded"] = True
    return result


@mcp.tool()
def search_indexed_files(query: str, limit: int = 10) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")

    pattern = REDIS_FILE_INDEX_PREFIX + "*"
    keys = redis_client.keys(pattern)
    matches = []

    q = query.lower()
    for k in keys:
        raw = redis_client.get(k)
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except Exception:
            continue
        snippet = entry.get("snippet", "")
        if q in snippet.lower():
            matches.append({"path": entry.get("path"), "snippet": snippet[:200]})
        if len(matches) >= limit:
            break
    return {"query": query, "count": len(matches), "matches": matches}


# -----------------------------------------------------------------------------
# Agent Snapshot Tools
# -----------------------------------------------------------------------------


@mcp.tool()
def save_agent_snapshot(agent_id: str, state: Any, embed: bool = True) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")

    key = REDIS_AGENT_SNAPSHOT_PREF + agent_id
    redis_client.set(key, json.dumps(state))

    result: Dict[str, Any] = {"saved": True, "agent_id": agent_id}
    if embed:
        text = _snapshot_to_text(agent_id, state)
        emb = _embed_text(text)
        emb_key = REDIS_EMBED_AGENT_PREFIX + agent_id
        emb_data = {"agent_id": agent_id, "text": text, "embedding": emb}
        redis_client.set(emb_key, json.dumps(emb_data))
        result["embedded"] = True
    return result


@mcp.tool()
def load_agent_snapshot(agent_id: str) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    raw = redis_client.get(REDIS_AGENT_SNAPSHOT_PREF + agent_id)
    if not raw:
        return {"agent_id": agent_id, "found": False}
    try:
        state = json.loads(raw)
    except Exception:
        state = raw
    return {"agent_id": agent_id, "found": True, "state": state}


@mcp.tool()
def list_agent_snapshots() -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    keys = redis_client.keys(REDIS_AGENT_SNAPSHOT_PREF + "*")
    agent_ids = [k.replace(REDIS_AGENT_SNAPSHOT_PREF, "", 1) for k in keys]
    return {"agent_ids": agent_ids, "count": len(agent_ids)}


@mcp.tool()
def delete_agent_snapshot(agent_id: str) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    snap_key = REDIS_AGENT_SNAPSHOT_PREF + agent_id
    emb_key = REDIS_EMBED_AGENT_PREFIX + agent_id
    deleted_snap = redis_client.delete(snap_key)
    deleted_emb = redis_client.delete(emb_key)
    return {"agent_id": agent_id, "deleted_snapshot": bool(deleted_snap), "deleted_embedding": bool(deleted_emb)}


@mcp.tool()
def clear_all_agent_snapshots() -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    snap_keys = redis_client.keys(REDIS_AGENT_SNAPSHOT_PREF + "*")
    emb_keys = redis_client.keys(REDIS_EMBED_AGENT_PREFIX + "*")
    deleted = 0
    for k in list(snap_keys) + list(emb_keys):
        redis_client.delete(k)
        deleted += 1
    return {"ok": True, "deleted": deleted}


# -----------------------------------------------------------------------------
# Semantic Search Tools
# -----------------------------------------------------------------------------


@mcp.tool()
def semantic_search_files(query: str, top_k: int = 5) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    q_vec = _embed_text(query)
    keys = redis_client.keys(REDIS_EMBED_FILE_PREFIX + "*")
    scored = []
    for k in keys:
        raw = redis_client.get(k)
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except Exception:
            continue
        emb = entry.get("embedding")
        if not isinstance(emb, list):
            continue
        score = _cosine_similarity(q_vec, emb)
        scored.append({"path": entry.get("path"), "text": entry.get("text"), "score": float(score)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"query": query, "matches": scored[:top_k]}


@mcp.tool()
def semantic_search_agents(query: str, top_k: int = 5) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    q_vec = _embed_text(query)
    keys = redis_client.keys(REDIS_EMBED_AGENT_PREFIX + "*")
    scored = []
    for k in keys:
        raw = redis_client.get(k)
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except Exception:
            continue
        emb = entry.get("embedding")
        if not isinstance(emb, list):
            continue
        score = _cosine_similarity(q_vec, emb)
        scored.append({"agent_id": entry.get("agent_id"), "text": entry.get("text"), "score": float(score)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"query": query, "matches": scored[:top_k]}


# -----------------------------------------------------------------------------
# Task Queue / Job History
# -----------------------------------------------------------------------------


@mcp.tool()
def queue_task(name: str, payload: Any = None) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    task_id = str(uuid.uuid4())
    task = {"id": task_id, "name": name, "payload": payload, "queued_at": time.time(), "status": "queued"}
    redis_client.rpush(REDIS_TASK_QUEUE_KEY, json.dumps(task))
    return {"queued": True, "task": task}


@mcp.tool()
def get_next_task() -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    raw = redis_client.lpop(REDIS_TASK_QUEUE_KEY)
    if raw is None:
        return {"task": None}
    task = json.loads(raw)
    task["status"] = "in_progress"
    task["started_at"] = time.time()
    return {"task": task}


@mcp.tool()
def finish_task(task_id: str, result: Any = None) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    hist_key = REDIS_TASK_HISTORY_PREF + str(time.time())
    entry = {"task_id": task_id, "finished_at": time.time(), "result": result}
    redis_client.set(hist_key, json.dumps(entry))
    return {"ok": True, "history_key": hist_key}


@mcp.tool()
def task_history(limit: int = 50) -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    keys = sorted(redis_client.keys(REDIS_TASK_HISTORY_PREF + "*"), reverse=True)
    results = []
    for k in keys[:limit]:
        raw = redis_client.get(k)
        if not raw:
            continue
        try:
            entry = json.loads(raw)
            entry["key"] = k
            results.append(entry)
        except Exception:
            continue
    return {"count": len(results), "entries": results}


@mcp.tool()
def clear_task_history(prefix: str = "") -> Dict[str, Any]:
    if not MEMORY_ENABLED or not redis_client:
        raise RuntimeError("Redis memory is not enabled.")
    pattern = REDIS_TASK_HISTORY_PREF + prefix + "*"
    keys = redis_client.keys(pattern)
    deleted = 0
    for k in keys:
        redis_client.delete(k)
        deleted += 1
    return {"ok": True, "deleted": deleted}


# -----------------------------------------------------------------------------
# Prompt Helper
# -----------------------------------------------------------------------------


@mcp.prompt()
def analyze_numeric_series_prompt(description: str, question: str) -> str:
    return (
        "You are analyzing numeric data for the user.\n\n"
        f"Data description:\n{description}\n\n"
        "You will be given results from tools like column_stats, normalize, "
        "ttest_independent, or math_eval. Explain results clearly and highlight "
        "practical conclusions.\n\n"
        f"User question:\n{question}\n"
    )


# -----------------------------------------------------------------------------
# Advanced Example: math_eval_with_meta
# -----------------------------------------------------------------------------


@dataclass
class EvalSummary:
    ok: bool
    message: str
    numeric: Optional[float]


@mcp.tool()
def math_eval_with_meta(expr: str) -> CallToolResult:
    try:
        sym_expr = sp.sympify(expr)
        simplified = sp.simplify(sym_expr)
        try:
            numeric_val = float(simplified.evalf())
        except Exception:
            numeric_val = None
        visible_text = f"Expression: {expr}\nSimplified: {simplified}\n"
        if numeric_val is not None:
            visible_text += f"Numeric: {numeric_val}\n"
        summary = EvalSummary(ok=True, message="Expression evaluated successfully.", numeric=numeric_val)
        return CallToolResult(content=[TextContent(type="text", text=visible_text)], _meta={"summary": summary.__dict__})
    except Exception as exc:
        visible_text = f"Failed to evaluate expression: {exc}"
        summary = EvalSummary(ok=False, message=str(exc), numeric=None)
        return CallToolResult(content=[TextContent(type="text", text=visible_text)], _meta={"summary": summary.__dict__})


# -----------------------------------------------------------------------------
# Tolerant LSP-style stdio transport (Content-Length framing)
# -----------------------------------------------------------------------------


@asynccontextmanager
async def _stdio_server() -> anyio.abc.AsyncResource:
    """
    Official LSP-like framing used by MCP stdio clients, **tolerant** of
    non-framed preamble/noise:
      Content-Length: <N>\r\n
      \r\n
      <N bytes of UTF-8 JSON>
    """
    a_stdin = anyio.wrap_file(sys.stdin.buffer)   # binary async
    a_stdout = anyio.wrap_file(sys.stdout.buffer) # binary async

    send_stream: MemoryObjectSendStream[SessionMessage]
    recv_stream: MemoryObjectReceiveStream[SessionMessage]
    send_stream, recv_stream = anyio.create_memory_object_stream(0)

    write_stream: MemoryObjectSendStream[SessionMessage]
    write_recv: MemoryObjectReceiveStream[SessionMessage]
    write_stream, write_recv = anyio.create_memory_object_stream(0)

    async def read_packet() -> bytes | None:
        """
        Read a framed packet; skip any non-header noise until a header block
        containing Content-Length is found.
        """
        while True:
            headers: dict[str, str] = {}
            # Read one header block
            while True:
                line = await a_stdin.readline()
                if line == b"":
                    return None  # EOF
                # Normalize line ending
                if line.endswith(b"\r\n"):
                    line = line[:-2]
                elif line.endswith(b"\n"):
                    line = line[:-1]

                if line == b"":
                    # End of headers
                    break

                if b":" in line:
                    k, v = line.split(b":", 1)
                    headers[k.decode("ascii", "ignore").strip().lower()] = v.decode("ascii", "ignore").strip()
                else:
                    # Ignore non-header noise (preambles, '?', etc.)
                    continue

            length_str = headers.get("content-length")
            if not length_str:
                # Not a framed block; keep scanning
                log.debug("Skipping non-framed input (no Content-Length).")
                continue

            try:
                length = int(length_str)
            except ValueError:
                log.debug("Skipping invalid Content-Length: %r", length_str)
                continue

            body = await a_stdin.read(length)
            if not body or len(body) < length:
                log.error("Truncated body from stdin")
                return None

            return body

    async def reader():
        try:
            async with send_stream:
                while True:
                    body = await read_packet()
                    if body is None:
                        break
                    try:
                        msg = JSONRPCMessage.model_validate_json(body.decode("utf-8"))
                        await send_stream.send(SessionMessage(msg))
                    except Exception as exc:
                        log.error(f"Failed to parse JSON-RPC message: {exc}")
                        log.debug(f"Problem JSON: {body[:200]!r}")
        except anyio.ClosedResourceError:
            log.debug("Reader: stdin closed")
        except Exception as e:
            log.error(f"Reader error: {e}")

    async def writer():
        try:
            async with write_recv:
                async for sess in write_recv:
                    payload = sess.message.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
                    header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
                    await a_stdout.write(header + payload)
                    await a_stdout.flush()
        except anyio.ClosedResourceError:
            log.debug("Writer: stdout closed")
        except Exception as e:
            log.error(f"Writer error: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(reader)
        tg.start_soon(writer)
        yield recv_stream, write_stream


def main() -> None:
    async def _run() -> None:
        # Check Redis connection asynchronously during startup
        await _check_redis_connection()

        log.info("Starting MCP Runtime v3.0...")
        log.info(f"Project root: {PROJECT_ROOT}")
        log.info(f"Memory enabled: {MEMORY_ENABLED}")
        async with _stdio_server() as (read_stream, write_stream):
            log.info("stdio transport ready, initializing MCP server...")
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                mcp._mcp_server.create_initialization_options(),
            )
    asyncio.run(_run())


if __name__ == "__main__":
    main()
