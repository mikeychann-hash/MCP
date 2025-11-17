# MCP Runtime v3 - Installation Guide

## Dependencies Overview

### Python Packages (7 required)
| Package | Version | Purpose | Size |
|---------|---------|---------|------|
| `mcp[cli]` | ≥1.0.0 | MCP protocol framework | ~2 MB |
| `numpy` | ≥1.24.0 | Numeric operations | ~20 MB |
| `scipy` | ≥1.10.0 | Statistical analysis | ~40 MB |
| `sympy` | ≥1.12 | Symbolic math | ~15 MB |
| `redis` | ≥4.5.0 | Redis client | ~1 MB |
| `sentence-transformers` | ≥2.2.0 | Embeddings (optional) | ~500 MB* |
| `anyio` | ≥3.6.0 | Async I/O | ~1 MB |

**Total**: ~600 MB (with embeddings) or ~80 MB (without embeddings)

*sentence-transformers downloads AI models on first use, which can be large.

### External Services (optional)
- **Redis Server**: Bundled Windows version included (`redis-win/`, 22 MB)

---

## Installation Locations

### 1. Python Packages → Virtual Environment (Recommended)

**Location**: `.venv/` directory in your project folder

```
C:\Users\Admin\Documents\mcp_runtime_v3\.venv\
  ├─ Scripts\
  │   ├─ python.exe           ← Python interpreter
  │   ├─ pip.exe              ← Package manager
  │   └─ Activate.ps1         ← Activation script
  └─ Lib\
      └─ site-packages\       ← All Python packages installed here
          ├─ mcp\
          ├─ numpy\
          ├─ scipy\
          ├─ sympy\
          ├─ redis\
          ├─ sentence_transformers\
          └─ anyio\
```

**Why virtual environment?**
- ✅ Isolated from system Python
- ✅ Different projects can have different versions
- ✅ Easy to delete and recreate
- ✅ Doesn't require admin rights

### 2. Sentence Transformers Models → Hugging Face Cache

**Location**: `%USERPROFILE%\.cache\huggingface\` (Windows) or `~/.cache/huggingface/` (Linux/Mac)

```
C:\Users\Admin\.cache\huggingface\
  └─ hub\
      └─ models--sentence-transformers--all-MiniLM-L6-v2\
          └─ snapshots\
              └─ <hash>\
                  ├─ pytorch_model.bin  (90 MB)
                  ├─ config.json
                  └─ tokenizer files
```

**Note**: Models are downloaded **only once** and reused across projects.

### 3. Redis Server → Project Directory (Bundled)

**Location**: `redis-win/` subfolder in your project

```
C:\Users\Admin\Documents\mcp_runtime_v3\redis-win\
  ├─ redis-server.exe         (1.6 MB)
  ├─ redis-cli.exe            (500 KB)
  ├─ redis-benchmark.exe
  └─ redis.windows.conf
```

**Redis Data** (runtime):
```
C:\Users\Admin\Documents\mcp_runtime_v3\
  └─ dump.rdb                 (Created when Redis saves data)
```

---

## Step-by-Step Installation

### Windows Installation

#### Step 1: Install Python 3.12

1. Download from [python.org](https://www.python.org/downloads/)
2. **Check "Add Python to PATH"** during installation
3. Install to: `C:\Users\Admin\AppData\Local\Programs\Python\Python312\`

**Verify**:
```powershell
python --version
# Should show: Python 3.12.x
```

#### Step 2: Create Virtual Environment

```powershell
cd C:\Users\Admin\Documents\mcp_runtime_v3

# Create venv
python -m venv .venv

# Activate
.\.venv\Scripts\Activate.ps1
```

**If you see "running scripts is disabled" error**:
```powershell
# Run as Administrator once:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Step 3: Install Python Dependencies

**With virtual environment activated**:
```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# OR install manually:
pip install "mcp[cli]" numpy scipy sympy redis sentence-transformers anyio
```

**Installation time**: ~5-10 minutes (depending on internet speed)

**Verify installation**:
```powershell
pip list
# Should show all 7+ packages
```

#### Step 4: (Optional) Test Embeddings

**Skip this if you set `MCP_ENABLE_EMBEDDINGS=0`** (default is disabled)

```powershell
python -c "from sentence_transformers import SentenceTransformer; print('Testing...'); model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print('OK')"
```

**First run**: Downloads ~90 MB model to `.cache\huggingface\`
**Subsequent runs**: Uses cached model (instant)

#### Step 5: Redis Setup (Optional)

**Option A: Use Bundled Redis** (Recommended)
```powershell
# Redis is already in redis-win/ folder
# Server will auto-start it when needed
# No manual installation required
```

**Option B: Install Redis as Windows Service**
```powershell
cd redis-win
redis-server.exe --service-install redis.windows.conf
redis-server.exe --service-start
```

**Option C: Skip Redis** (Memory features disabled)
- Just don't start Redis
- Server will work fine, memory tools will return "Redis not enabled"

---

### Linux/macOS Installation

#### Step 1: Install Python 3.12

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

**macOS**:
```bash
brew install python@3.12
```

#### Step 2: Create Virtual Environment

```bash
cd /path/to/mcp_runtime_v3

# Create venv
python3.12 -m venv .venv

# Activate
source .venv/bin/activate
```

#### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4: Install Redis (Optional)

**Ubuntu/Debian**:
```bash
sudo apt install redis-server
sudo systemctl start redis
```

**macOS**:
```bash
brew install redis
brew services start redis
```

**Verify**:
```bash
redis-cli ping
# Should return: PONG
```

---

## Claude Desktop Configuration

### Where is the config file?

**Windows**:
```
C:\Users\<YourUsername>\AppData\Roaming\Claude\claude_desktop_config.json
```

**macOS**:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux**:
```
~/.config/Claude/claude_desktop_config.json
```

### Configuration Template

**For Windows with venv**:
```json
{
  "mcpServers": {
    "runtime-v3": {
      "command": "C:\\Users\\Admin\\Documents\\mcp_runtime_v3\\.venv\\Scripts\\python.exe",
      "args": ["-u", "C:\\Users\\Admin\\Documents\\mcp_runtime_v3\\server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "MCP_RUNTIME_PROJECT_ROOT": "C:\\Users\\Admin\\Documents\\mcp_runtime_v3",
        "MCP_MEMORY_REDIS_HOST": "localhost",
        "MCP_MEMORY_REDIS_PORT": "6379",
        "MCP_MEMORY_REDIS_DB": "5",
        "MCP_REDIS_CONNECT_TIMEOUT": "5",
        "MCP_REDIS_SOCKET_TIMEOUT": "5"
      },
      "autoStart": true
    }
  },
  "dangerouslyAllowPaths": [
    "C:\\Users\\Admin\\Documents\\mcp_runtime_v3"
  ]
}
```

**For macOS/Linux**:
```json
{
  "mcpServers": {
    "runtime-v3": {
      "command": "/path/to/mcp_runtime_v3/.venv/bin/python",
      "args": ["-u", "/path/to/mcp_runtime_v3/server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "MCP_RUNTIME_PROJECT_ROOT": "/path/to/mcp_runtime_v3",
        "MCP_MEMORY_REDIS_HOST": "localhost",
        "MCP_MEMORY_REDIS_PORT": "6379",
        "MCP_MEMORY_REDIS_DB": "5"
      },
      "autoStart": true
    }
  }
}
```

**Critical**: Use the **venv Python path**, not system Python!

---

## Verifying Installation

### Test 1: Server Starts

```powershell
# Activate venv first
.\.venv\Scripts\Activate.ps1

# Run server manually
python -u server.py
```

**Expected output** (to stderr):
```
[INFO] Starting MCP Runtime v3.0...
[INFO] Project root: C:\Users\Admin\Documents\mcp_runtime_v3
[INFO] Memory enabled: True
[INFO] stdio transport ready, initializing MCP server...
```

Press `Ctrl+C` to stop. If you see these messages, installation is successful!

### Test 2: Dependencies Check

```powershell
python -c "import mcp, numpy, scipy, sympy, redis, anyio; print('All core dependencies OK')"
```

### Test 3: Redis Connection (if using Redis)

```powershell
python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping(); print('Redis OK')"
```

### Test 4: Claude Desktop Integration

1. Open Claude Desktop
2. Go to **Settings → Developer**
3. Check **Extensions/Tools** section
4. Should see "runtime-v3" listed
5. Click to expand - should show ~28 tools

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'mcp'"

**Cause**: Virtual environment not activated OR packages installed to wrong Python

**Fix**:
```powershell
# Make sure venv is activated
.\.venv\Scripts\Activate.ps1

# Reinstall
pip install -r requirements.txt

# Verify
where python
# Should show: C:\...\mcp_runtime_v3\.venv\Scripts\python.exe
```

### "sentence-transformers download is stuck"

**Cause**: Large model download (90 MB) can be slow

**Fix**:
```powershell
# Set longer timeout
$env:HF_HUB_DOWNLOAD_TIMEOUT = "600"

# Or disable embeddings entirely
$env:MCP_ENABLE_EMBEDDINGS = "0"
```

### Claude Desktop shows "Server disconnected"

**Check**:
1. Is `PYTHONUNBUFFERED=1` set in config? ← **Most common issue**
2. Is the Python path correct (venv, not system)?
3. Check stderr logs in Claude Desktop developer tools
4. Run server manually to see errors

### "Redis not available" warning

**This is normal if**:
- You didn't install Redis
- Redis isn't running
- You set a different host/port

**Server will work fine**, memory tools will just be disabled.

**To fix**: Start Redis or update `MCP_MEMORY_REDIS_HOST` in config

---

## Uninstallation

### Remove Python Packages

```powershell
# Just delete the venv folder
Remove-Item -Recurse -Force .venv
```

### Remove Embedding Models Cache

```powershell
# Windows
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface"

# Linux/macOS
rm -rf ~/.cache/huggingface
```

### Remove Redis Data

```powershell
# Stop Redis first
redis-cli shutdown

# Delete data file
Remove-Item dump.rdb
```

---

## Disk Space Requirements

| Component | Size | Location |
|-----------|------|----------|
| Python packages (venv) | ~80 MB | `.venv/` |
| Embedding models (if enabled) | ~100 MB | `%USERPROFILE%\.cache\huggingface\` |
| Redis binaries | 22 MB | `redis-win/` |
| Redis data (varies) | ~1-100 MB | `dump.rdb` |
| **Total** | **~200 MB** | Various |

---

## Quick Start Checklist

- [ ] Python 3.12 installed
- [ ] Virtual environment created (`.venv/`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Claude Desktop config updated with **venv Python path**
- [ ] **`PYTHONUNBUFFERED=1`** set in config
- [ ] Redis running (optional)
- [ ] Test: `python -u server.py` shows startup messages
- [ ] Test: Claude Desktop shows "runtime-v3" in Extensions/Tools

---

## Support

If you encounter issues:

1. **Check logs**: Claude Desktop → Settings → Developer → View Logs
2. **Run manually**: `python -u server.py` to see stderr output
3. **Verify paths**: Make sure all paths in config use venv Python
4. **Check firewall**: Redis needs localhost:6379 accessible
5. **Review**: `MCP_DISCONNECTION_FIXES.md` for connection issues
