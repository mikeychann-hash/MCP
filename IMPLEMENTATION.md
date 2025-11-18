# MCP Token Optimizer - Implementation Guide

## Overview

This is a production-ready MCP (Model Context Protocol) server for intelligent token optimization and context management. It provides comprehensive tools for managing conversations, compressing context, counting tokens, intelligent caching, tracking references, and optimizing queries across multiple LLM providers.

## Architecture

### Technology Stack
- **Runtime**: Node.js 20+
- **Language**: TypeScript 5.3.3 (strict mode)
- **MCP SDK**: @modelcontextprotocol/sdk v1.0.0
- **Database**: SQLite3 (better-sqlite3)
- **Token Counting**: tiktoken (GPT models) + @anthropic-ai/tokenizer (Claude models)
- **Validation**: Zod schemas
- **Transport**: stdio only

### Directory Structure

```
/home/user/MCP/
├── src/
│   ├── index.ts                    # Main MCP server
│   ├── config/
│   │   └── index.ts                # Configuration management
│   ├── storage/
│   │   └── database.ts             # SQLite database layer
│   ├── utils/
│   │   ├── tokenizer.ts            # Multi-LLM token counting
│   │   └── cache.ts                # Intelligent caching
│   ├── tools/
│   │   ├── manage_conversation.ts  # Conversation CRUD
│   │   ├── compress_context.ts     # Context compression
│   │   ├── count_tokens.ts         # Token counting
│   │   ├── smart_cache.ts          # Smart caching
│   │   ├── track_references.ts     # Reference tracking
│   │   └── optimize_query.ts       # Query optimization
│   ├── resources/
│   │   ├── conversation_history.ts # Conversation resource
│   │   ├── token_stats.ts          # Token statistics
│   │   ├── cache_stats.ts          # Cache statistics
│   │   ├── optimization_tips.ts    # Optimization tips
│   │   └── reference_library.ts    # Reference library
│   └── prompts/
│       ├── summarize_context.ts    # Summarization prompt
│       ├── compress_conversation.ts# Compression prompt
│       └── extract_essentials.ts   # Extraction prompt
├── package.json
├── tsconfig.json
└── .gitignore
```

## Installation

### 1. Install Dependencies

```bash
cd /home/user/MCP
npm install
```

### 2. Build the Project

```bash
npm run build
```

This will compile TypeScript to JavaScript in the `build/` directory.

### 3. Verify Build

```bash
ls -la build/
```

You should see compiled JavaScript files.

## Features Implemented

### Tools (6)

1. **manage_conversation**
   - Create, update, retrieve, and delete conversations
   - Automatic token tracking per message
   - Multi-conversation management

2. **compress_context**
   - Strategies: summarize, remove_old, compress_similar, smart
   - Configurable compression ratio (0.1-0.9)
   - Preserves recent messages
   - Token savings calculation

3. **count_tokens**
   - Multi-LLM support (Claude, GPT, others)
   - Text, messages, or structured data
   - Token percentage of model limit
   - Optimization recommendations

4. **smart_cache**
   - Store/retrieve cached content
   - Automatic token savings tracking
   - LRU eviction policy
   - Hit rate statistics

5. **track_references**
   - Track files, URLs, code, notes, documents
   - Token counting per reference
   - Search and filter capabilities
   - Conversation-scoped or global

6. **optimize_query**
   - Analyze queries for verbosity
   - Remove filler words
   - Improve clarity
   - Token reduction suggestions

### Resources (5)

1. **conversation-history**
   - URI: `conversation-history://all` or `conversation-history://{id}`
   - Full conversation history with token metadata

2. **token-stats**
   - URI: `token-stats://aggregate` or `token-stats://{id}`
   - Detailed token usage statistics
   - Cache efficiency metrics

3. **cache-stats**
   - URI: `cache-stats://current`
   - Cache performance metrics
   - Hit rate analysis

4. **optimization-tips**
   - URI: `optimization-tips://general` or `optimization-tips://{id}`
   - Context-aware optimization recommendations
   - Prioritized action items

5. **reference-library**
   - URI: `reference-library://all` or `reference-library://{id}`
   - Library of tracked references
   - Type-based filtering

### Prompts (3)

1. **summarize_context**
   - Comprehensive conversation summarization
   - Configurable focus areas
   - Token limit support

2. **compress_conversation**
   - Intelligent context compression
   - Target reduction percentage
   - Preserves essential information

3. **extract_essentials**
   - Extract facts, code, decisions, Q&A
   - Type-specific extraction
   - Structured output

## Database Schema

### Tables

- **conversations**: Conversation metadata
- **messages**: Individual messages with tokens
- **token_stats**: Token usage tracking
- **cache_entries**: Cached content with hit tracking
- **references**: Reference materials library

### Indexes

Optimized indexes for:
- Message retrieval by conversation
- Token stats by conversation and timestamp
- Cache lookups by key
- Reference searches

## Configuration

Platform-aware configuration:
- **Windows**: `%APPDATA%\mcp-token-optimizer\token-optimizer.db`
- **macOS**: `~/Library/Application Support/mcp-token-optimizer/token-optimizer.db`
- **Linux**: `~/.local/share/mcp-token-optimizer/token-optimizer.db`

Configurable settings:
- Token limits per model
- Cache size and TTL
- Compression parameters
- Log level

## Token Counting

### Supported Models

- **Claude**: claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus (200k tokens)
- **GPT**: gpt-4, gpt-4-turbo (128k), gpt-3.5-turbo (16k)
- **Fallback**: Generic estimation for other models

### Features

- Accurate per-model token counting
- Message formatting overhead calculation
- Cache-aware token counting
- Batch processing support

## Error Handling

- Zod schema validation for all inputs
- Graceful error responses
- Database transaction safety
- Proper cleanup on shutdown

## Windows Compatibility

- Windows-compatible path handling
- No POSIX-specific features
- SQLite WAL mode for better concurrency
- Proper signal handling (SIGINT, SIGTERM)

## Usage Example

After building, you can test the server:

```bash
# Start the server
node build/index.js

# Or use in development mode
npm run dev
```

The server runs on stdio and communicates via MCP protocol.

## Testing Tools

You can test individual tools:

```javascript
// Example: Count tokens
{
  "tool": "count_tokens",
  "arguments": {
    "input": "Hello, world!",
    "model": "claude-3-5-sonnet"
  }
}

// Example: Create conversation
{
  "tool": "manage_conversation",
  "arguments": {
    "action": "create",
    "title": "My Conversation",
    "model": "claude-3-5-sonnet"
  }
}
```

## Performance

- SQLite WAL mode for concurrent reads
- Indexed queries for fast lookups
- LRU cache eviction
- Batch token counting
- Lazy database initialization

## Security

- Input validation with Zod
- SQL injection prevention (prepared statements)
- No eval or dynamic code execution
- Sandboxed database access

## Future Enhancements

Potential improvements:
- REST API support
- WebSocket transport
- Real-time token monitoring
- Advanced compression algorithms
- Multi-database support
- Prompt template library
- Export/import functionality

## Support

For issues or questions:
1. Check the implementation code
2. Review MCP SDK documentation
3. Verify TypeScript compilation
4. Check database file permissions

## License

MIT License - See package.json for details
