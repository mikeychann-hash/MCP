# MCP Runtime v3.0 - Windows Setup Guide

Complete setup instructions for installing and running the MCP Runtime v3.0 server on Windows 11.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Server](#running-the-server)
5. [Claude Desktop Integration](#claude-desktop-integration)
6. [Claude CLI Integration](#claude-cli-integration)
7. [Development Guide](#development-guide)
8. [Troubleshooting](#troubleshooting)
9. [Features](#features)
10. [Architecture](#architecture)

---

## Prerequisites

### Required Software

1. **Node.js 20 or higher**
   - Download: https://nodejs.org/
   - Verify installation: `node --version`
   - Should show v20.0.0 or higher

2. **npm 10 or higher** (included with Node.js)
   - Verify installation: `npm --version`
   - Should show 10.0.0 or higher

### Optional but Recommended

3. **Memurai** (Redis for Windows)
   - Download: https://www.memurai.com/
   - Required for memory features, semantic search, and caching
   - Alternative: Use Redis for Windows from https://github.com/microsoftarchive/redis/releases

4. **Git** (for version control)
   - Download: https://git-scm.com/
   - Recommended for managing code changes

5. **Visual Studio Code** (recommended IDE)
   - Download: https://code.visualstudio.com/
   - Install recommended extensions:
     - ESLint
     - Prettier
     - TypeScript and JavaScript Language Features

---

## Installation

### Quick Installation

1. **Open Command Prompt or PowerShell** in the project directory

2. **Run the installation script:**
   ```cmd
   install.bat
   ```

   This will:
   - Check Node.js installation
   - Install all npm dependencies
   - Create `.env` configuration file
   - Build the TypeScript project
   - Check for Memurai/Redis

### Manual Installation

If you prefer manual installation:

```cmd
# 1. Install dependencies
npm install

# 2. Copy environment template
copy .env.example .env

# 3. Build TypeScript
npm run build
```

---

## Configuration

### Environment Variables

Edit the `.env` file to customize your configuration:

```env
# Redis Configuration (Memurai on Windows)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=5
REDIS_ENABLED=true

# Project Settings
PROJECT_ROOT=C:\Users\YourUsername\Documents\MyProject
MAX_FILE_SIZE=2097152
MAX_FILE_CHARS=2000

# Security
ALLOW_SHELL_EXECUTION=false
RESTRICT_TO_PROJECT_ROOT=true

# Logging
LOG_LEVEL=info
DEBUG=false

# Features
ENABLE_SEMANTIC_SEARCH=true
ENABLE_FILE_INDEXING=true
ENABLE_MEMORY_PERSISTENCE=true
```

### Critical Configuration Options

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `REDIS_HOST` | Redis server hostname | `localhost` | Use `localhost` for local Memurai |
| `REDIS_PORT` | Redis server port | `6379` | Default Memurai port |
| `PROJECT_ROOT` | Working directory | Current dir | Absolute path recommended |
| `ALLOW_SHELL_EXECUTION` | Enable shell commands | `false` | **DANGEROUS** - only enable if needed |
| `LOG_LEVEL` | Logging verbosity | `info` | Options: debug, info, warn, error |

---

## Running the Server

### Production Mode

Use `start.bat` for production usage:

```cmd
start.bat
```

This script will:
1. ✅ Check Node.js installation and version
2. ✅ Verify project structure
3. ✅ Check dependencies
4. ✅ Verify build output
5. ✅ Load environment variables
6. ✅ Check Memurai/Redis service
7. ✅ Start the MCP server

**Press Ctrl+C to stop the server**

### Development Mode

Use `dev.bat` for development with auto-reload:

```cmd
dev.bat
```

Features:
- 🔄 Automatic reload on file changes
- 🔍 TypeScript compilation on-the-fly
- 🗺️ Source maps for debugging
- 📝 Detailed error messages

### Building

To rebuild TypeScript without starting:

```cmd
build.bat
```

### Testing

Run tests with Vitest:

```cmd
# Run all tests
test.bat

# Run with coverage report
test.bat --coverage
```

---

## Claude Desktop Integration

### Step 1: Locate Claude Desktop Configuration

Claude Desktop config is located at:
```
%APPDATA%\Claude\claude_desktop_config.json
```

Or navigate to:
```
C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json
```

### Step 2: Update Configuration

Add the MCP server to your config (replace paths with your actual paths):

```json
{
  "mcpServers": {
    "mcp-runtime-v3": {
      "command": "node",
      "args": [
        "C:\\Users\\YourUsername\\Documents\\mcp-runtime-v3\\dist\\index.js"
      ],
      "env": {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "5",
        "PROJECT_ROOT": "C:\\Users\\YourUsername\\Documents\\MyProject",
        "ALLOW_SHELL_EXECUTION": "false",
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

**Important:** Use double backslashes (`\\`) in JSON paths!

### Step 3: Restart Claude Desktop

1. Completely quit Claude Desktop
2. Relaunch the application
3. The MCP server will start automatically when Claude opens

### Step 4: Verify Connection

In Claude Desktop, you should see the MCP server connected. You can test it by asking:

> "What MCP tools are available?"

---

## Claude CLI Integration

### Step 1: Install Claude CLI

```cmd
npm install -g @anthropic-ai/claude-cli
```

### Step 2: Configure MCP Server

Create or edit `~/.config/claude/config.json`:

```json
{
  "mcpServers": {
    "mcp-runtime-v3": {
      "command": "node",
      "args": [
        "C:\\Users\\YourUsername\\Documents\\mcp-runtime-v3\\dist\\index.js"
      ],
      "env": {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "PROJECT_ROOT": "C:\\Users\\YourUsername\\Documents\\MyProject",
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

### Step 3: Verify Integration

```cmd
claude mcp list
```

Should show `mcp-runtime-v3` as connected.

---

## Development Guide

### Project Structure

```
mcp-runtime-v3/
├── src/                    # TypeScript source code
│   ├── index.ts           # Main entry point
│   ├── server.ts          # MCP server implementation
│   ├── tools/             # MCP tool implementations
│   ├── redis/             # Redis client and utilities
│   ├── embeddings/        # Semantic search with transformers
│   └── utils/             # Utility functions
├── dist/                  # Compiled JavaScript (generated)
├── node_modules/          # Dependencies (generated)
├── .env                   # Environment configuration
├── .env.example           # Configuration template
├── package.json           # Node.js configuration
├── tsconfig.json          # TypeScript configuration
├── start.bat              # Production startup script
├── install.bat            # Installation script
├── build.bat              # Build script
├── dev.bat                # Development mode script
├── test.bat               # Test runner script
└── README-SETUP.md        # This file
```

### Development Workflow

1. **Make Changes** in `src/` directory
2. **Development Server** will auto-reload:
   ```cmd
   dev.bat
   ```
3. **Run Tests** to verify:
   ```cmd
   test.bat
   ```
4. **Build Production** version:
   ```cmd
   build.bat
   ```
5. **Test Production** build:
   ```cmd
   start.bat
   ```

### Adding New Tools

Create a new file in `src/tools/`:

```typescript
import { z } from 'zod';

export const myNewTool = {
  name: 'my_new_tool',
  description: 'Description of what this tool does',
  inputSchema: z.object({
    param1: z.string().describe('Description of param1'),
    param2: z.number().optional().describe('Optional param2')
  }),
  handler: async (args: { param1: string; param2?: number }) => {
    // Implementation
    return {
      content: [
        {
          type: 'text',
          text: 'Result of the operation'
        }
      ]
    };
  }
};
```

Register it in `src/server.ts`.

### Code Style

Run linting and formatting:

```cmd
# Check code style
npm run lint
npm run format:check

# Auto-fix issues
npm run lint:fix
npm run format
```

---

## Troubleshooting

### Common Issues

#### 1. "Node.js is not installed"

**Solution:**
- Install Node.js 20+ from https://nodejs.org/
- Restart Command Prompt after installation
- Verify: `node --version`

#### 2. "Memurai service not found"

**Solution:**
- Install Memurai from https://www.memurai.com/
- Or install Redis for Windows
- Or set `REDIS_ENABLED=false` in `.env` (disables memory features)

#### 3. "Build failed" / TypeScript Errors

**Solution:**
- Check TypeScript errors in console
- Run `npm run typecheck` to see all errors
- Fix errors in `src/` directory
- Run `build.bat` again

#### 4. "Permission denied" when starting Memurai

**Solution:**
- Run Command Prompt as Administrator
- Or start Memurai service manually:
  ```cmd
  net start Memurai
  ```

#### 5. Port Already in Use

**Solution:**
- Check if another process is using port 6379:
  ```cmd
  netstat -ano | findstr :6379
  ```
- Kill the process or change `REDIS_PORT` in `.env`

#### 6. Claude Desktop Not Connecting

**Solution:**
- Verify paths in `claude_desktop_config.json` are correct
- Use double backslashes (`\\`) in JSON
- Check that `dist\index.js` exists (run `build.bat`)
- Restart Claude Desktop completely
- Check Claude Desktop logs in `%APPDATA%\Claude\logs\`

#### 7. "Module not found" Errors

**Solution:**
- Delete `node_modules` and reinstall:
  ```cmd
  rmdir /s /q node_modules
  npm install
  ```

#### 8. Slow First Startup

**Cause:** Downloading embedding models (~2GB)

**Solution:**
- First run may take 5-10 minutes
- Models are cached in `node_modules/.cache/`
- Subsequent runs will be fast

---

## Features

### Core MCP Tools

1. **Memory Management**
   - `set_memory` - Store persistent memory
   - `get_memory` - Retrieve memory by key
   - `list_memories` - List all stored memories
   - `delete_memory` - Remove memory

2. **Semantic Search**
   - `semantic_search` - AI-powered search across indexed content
   - `index_files` - Index files for semantic search
   - `search_similar` - Find similar content

3. **File Operations**
   - `read_file` - Read file contents
   - `write_file` - Write to files
   - `list_files` - List directory contents
   - `search_files` - Search by filename pattern

4. **Task Queue**
   - `queue_task` - Add task to queue
   - `get_tasks` - List queued tasks
   - `complete_task` - Mark task as done

5. **Development Tools**
   - `server_status` - Check server health
   - `ping` - Test connectivity
   - `echo` - Echo back input (for testing)

### Redis-Powered Features

When Redis/Memurai is enabled:
- ✅ Persistent memory across sessions
- ✅ Fast semantic search with vector storage
- ✅ File content indexing and caching
- ✅ Task queue management
- ✅ Performance metrics and monitoring

When Redis is disabled:
- ⚠️ In-memory storage only (lost on restart)
- ⚠️ Limited semantic search
- ⚠️ No persistent task queue

---

## Architecture

### Technology Stack

- **Runtime:** Node.js 20+
- **Language:** TypeScript 5.7+
- **MCP SDK:** @modelcontextprotocol/sdk
- **Redis Client:** ioredis (async)
- **Embeddings:** @xenova/transformers (ONNX runtime)
- **Testing:** Vitest
- **Linting:** ESLint + Prettier

### Key Design Principles

1. **Graceful Degradation**
   - Server works without Redis
   - Features auto-disable if dependencies unavailable

2. **Type Safety**
   - Strict TypeScript configuration
   - Zod schema validation for all inputs

3. **Performance**
   - Async/await throughout
   - Connection pooling for Redis
   - Caching for expensive operations

4. **Security**
   - Shell execution disabled by default
   - File operations restricted to project root
   - Input validation on all tools

5. **Developer Experience**
   - Hot reload in development
   - Source maps for debugging
   - Comprehensive error messages

---

## Additional Resources

### Documentation

- **MCP Protocol:** https://modelcontextprotocol.io/
- **Claude Desktop:** https://claude.ai/
- **Memurai:** https://docs.memurai.com/
- **TypeScript:** https://www.typescriptlang.org/

### Support

For issues and questions:
1. Check this troubleshooting guide
2. Review error messages in console
3. Check logs in `%APPDATA%\Claude\logs\` (for Claude Desktop)
4. Review `.env` configuration

---

## Quick Reference Commands

```cmd
# Installation
install.bat              # One-time setup

# Running
start.bat               # Production mode
dev.bat                 # Development mode with auto-reload

# Building
build.bat               # Compile TypeScript

# Testing
test.bat                # Run tests
test.bat --coverage     # Run tests with coverage

# npm scripts
npm run build           # Build TypeScript
npm run dev             # Development mode
npm start               # Start compiled server
npm test                # Run tests (watch mode)
npm run lint            # Check code style
npm run format          # Format code
```

---

## License

MIT License - See LICENSE file for details

---

**Happy Coding! 🚀**

For questions or issues, please refer to the troubleshooting section or check the project repository.
