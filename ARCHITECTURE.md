# MCP Token Optimizer - Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Component Breakdown](#component-breakdown)
4. [Data Flow](#data-flow)
5. [MCP Protocol Integration](#mcp-protocol-integration)
6. [Storage Layer Design](#storage-layer-design)
7. [Token Optimization Strategies](#token-optimization-strategies)
8. [Performance Optimizations](#performance-optimizations)
9. [Security Considerations](#security-considerations)
10. [Platform Compatibility](#platform-compatibility)

---

## System Overview

The MCP Token Optimizer is a **Model Context Protocol (MCP) server** designed to provide intelligent token management for Large Language Model applications. The architecture follows a **layered design pattern** with clear separation of concerns, enabling maintainability, testability, and extensibility.

### Design Principles

1. **Separation of Concerns** - Each layer has a single, well-defined responsibility
2. **Type Safety** - Full TypeScript strict mode with runtime validation
3. **Platform Agnostic** - Cross-platform support (Windows, macOS, Linux)
4. **Performance First** - Optimized for low latency and high throughput
5. **Security by Design** - Input validation, SQL injection prevention, safe error handling
6. **Graceful Degradation** - System remains functional even when optional components fail

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Protocol** | @modelcontextprotocol/sdk | MCP protocol implementation |
| **Transport** | stdio (STDIN/STDOUT) | Communication channel |
| **Language** | TypeScript 5.3+ | Type-safe development |
| **Runtime** | Node.js 20+ | JavaScript execution |
| **Database** | SQLite 3 (better-sqlite3) | Data persistence |
| **Validation** | Zod 3.22+ | Runtime schema validation |
| **Tokenization** | tiktoken + @anthropic-ai/tokenizer | Multi-LLM token counting |

---

## Architecture Diagram

### High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      MCP Client (Claude)                       │
│              (Claude Desktop, Claude CLI, Custom)              │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                   ┌───────┴────────┐
                   │  stdio (JSON)  │
                   └───────┬────────┘
                           │
┌──────────────────────────┴─────────────────────────────────────┐
│                    MCP Token Optimizer Server                  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              MCP Protocol Layer (index.ts)               │ │
│  │  • StdioServerTransport                                  │ │
│  │  • Request routing (tools, resources, prompts)           │ │
│  │  • Error handling & response formatting                  │ │
│  └────┬───────────────────┬────────────────────┬────────────┘ │
│       │                   │                    │              │
│  ┌────┴────┐      ┌───────┴────────┐    ┌─────┴──────┐       │
│  │ Tools   │      │   Resources    │    │  Prompts   │       │
│  │  (6)    │      │      (5)       │    │    (3)     │       │
│  └────┬────┘      └───────┬────────┘    └─────┬──────┘       │
│       │                   │                    │              │
│  ┌────┴───────────────────┴────────────────────┴────────────┐ │
│  │                   Business Logic Layer                    │ │
│  │  • Conversation management                                │ │
│  │  • Context compression (4 strategies)                     │ │
│  │  • Token counting & analysis                              │ │
│  │  • Cache management                                       │ │
│  │  • Reference tracking                                     │ │
│  │  • Query optimization                                     │ │
│  └────┬───────────────────┬────────────────────┬────────────┘ │
│       │                   │                    │              │
│  ┌────┴─────┐      ┌──────┴──────┐      ┌─────┴──────┐       │
│  │Tokenizer │      │    Cache    │      │   Config   │       │
│  │  utils/  │      │   utils/    │      │  config/   │       │
│  │tokenizer │      │   cache     │      │   index    │       │
│  └────┬─────┘      └──────┬──────┘      └─────┬──────┘       │
│       │                   │                    │              │
│  ┌────┴───────────────────┴────────────────────┴────────────┐ │
│  │              Data Persistence Layer                       │ │
│  │                 storage/database.ts                       │ │
│  │  • SQLite database manager                                │ │
│  │  • CRUD operations                                        │ │
│  │  • Transaction support                                    │ │
│  └────────────────────────┬──────────────────────────────────┘ │
│                           │                                    │
│  ┌────────────────────────┴──────────────────────────────────┐ │
│  │                SQLite Database (WAL mode)                 │ │
│  │  Tables: conversations, messages, token_stats,            │ │
│  │          cache_entries, references                        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibilities | Dependencies |
|-------|------------------|--------------|
| **MCP Protocol** | Request routing, response formatting, error handling | @modelcontextprotocol/sdk |
| **Tools** | Tool implementations, input validation | Zod, Business Logic |
| **Resources** | Dynamic data resources, URI routing | Database, Cache |
| **Prompts** | Prompt generation, template rendering | Database, Tokenizer |
| **Business Logic** | Core algorithms, data processing | Utilities, Database |
| **Utilities** | Token counting, caching, configuration | tiktoken, @anthropic-ai/tokenizer |
| **Data Persistence** | Database operations, transactions | better-sqlite3 |

---

## Component Breakdown

### 1. MCP Protocol Layer (`src/index.ts`)

**Purpose**: Handle MCP protocol communication and request routing

**Responsibilities**:
- Initialize MCP server with capabilities
- Set up stdio transport
- Route requests to appropriate handlers
- Format responses according to MCP spec
- Handle errors gracefully
- Manage server lifecycle

**Key Classes/Functions**:
```typescript
class TokenOptimizerServer {
  private server: Server;
  private config: Config;

  constructor() { /* Initialize server */ }
  private setupHandlers() { /* Register request handlers */ }
  private setupErrorHandling() { /* Setup cleanup */ }
  async start() { /* Start server */ }
}
```

**Request Handlers**:
- `ListToolsRequestSchema` - List available tools
- `CallToolRequestSchema` - Execute tool with validation
- `ListResourcesRequestSchema` - List available resources
- `ReadResourceRequestSchema` - Read resource by URI
- `ListPromptsRequestSchema` - List available prompts
- `GetPromptRequestSchema` - Generate prompt

### 2. Tools Layer (`src/tools/`)

**Purpose**: Implement 6 MCP tools for token optimization

#### Tool Architecture Pattern

Each tool follows this structure:
```typescript
// 1. Define Zod input schema
export const ToolInputSchema = z.object({
  // ... schema definition
});

// 2. Export type from schema
export type ToolInput = z.infer<typeof ToolInputSchema>;

// 3. Implement tool function
export async function toolHandler(input: ToolInput): Promise<ToolOutput> {
  // Input is already validated by Zod
  // Implement business logic
  return { success: true, /* ... */ };
}
```

#### Tool Implementations

**manage_conversation** (`src/tools/manage_conversation.ts`)
- **Actions**: create, add_message, get, list, delete
- **Schema**: Discriminated union based on action
- **Features**: UUID generation, automatic token tracking, cascade deletion
- **Database Operations**: CRUD on conversations and messages tables

**compress_context** (`src/tools/compress_context.ts`)
- **Strategies**: summarize, remove_old, compress_similar, smart
- **Algorithm**: Multi-stage compression with configurable target ratio
- **Caching**: Results cached to avoid recomputation
- **Output**: Token savings calculation and compression ratio

**count_tokens** (`src/tools/count_tokens.ts`)
- **Input Types**: string, message array, structured object
- **Models**: Claude, GPT, generic
- **Features**: Automatic model detection, overhead calculation, recommendations
- **Output**: Token count, percentage, optimization suggestions

**smart_cache** (`src/tools/smart_cache.ts`)
- **Actions**: store, retrieve, check, stats, clear
- **Strategy**: LRU eviction with TTL
- **Tracking**: Hit count, token savings, timestamps
- **Organization**: Prefix-based key namespacing

**track_references** (`src/tools/track_references.ts`)
- **Actions**: add, get, list, delete, search
- **Types**: file, url, code, note, document
- **Features**: Token counting per reference, full-text search
- **Scope**: Conversation-scoped or global references

**optimize_query** (`src/tools/optimize_query.ts`)
- **Analysis**: Verbosity detection, repetition finding, filler words
- **Goals**: reduce_tokens, improve_clarity, both
- **Output**: Optimized query, original/optimized token counts, suggestions

### 3. Resources Layer (`src/resources/`)

**Purpose**: Provide dynamic read-only data via URI scheme

#### Resource URI Patterns

Each resource supports multiple URI patterns:
```
<scheme>://<path>
```

**conversation-history**
- `conversation-history://all` - All conversations
- `conversation-history://{id}` - Specific conversation

**token-stats**
- `token-stats://aggregate` - Aggregate statistics
- `token-stats://{id}` - Conversation-specific stats

**cache-stats**
- `cache-stats://current` - Current cache metrics

**optimization-tips**
- `optimization-tips://general` - General tips
- `optimization-tips://{id}` - Conversation-specific tips

**reference-library**
- `reference-library://all` - All references
- `reference-library://{id}` - Conversation references

#### Resource Implementation Pattern

```typescript
export async function getResource(params: ResourceParams): Promise<string> {
  // 1. Fetch data from database/cache
  const data = await fetchData(params);

  // 2. Process and format
  const formatted = formatData(data);

  // 3. Return JSON string
  return JSON.stringify(formatted, null, 2);
}
```

### 4. Prompts Layer (`src/prompts/`)

**Purpose**: Generate intelligent prompts for LLM operations

#### Prompt Implementations

**summarize_context** (`src/prompts/summarize_context.ts`)
- **Inputs**: conversation_id, focus, max_summary_tokens
- **Output**: Structured prompt for summarization
- **Features**: Context-aware, token-limited, focused summaries

**compress_conversation** (`src/prompts/compress_conversation.ts`)
- **Inputs**: conversation_id, target_reduction_percent, preserve_recent_count
- **Output**: Prompt for compression with specific targets
- **Features**: Preserves essential info, technical details, recent messages

**extract_essentials** (`src/prompts/extract_essentials.ts`)
- **Inputs**: conversation_id/content, extract_type, model
- **Types**: facts, code, decisions, questions, all
- **Output**: Structured extraction prompt
- **Features**: Type-specific extraction, preserves context

### 5. Utilities Layer (`src/utils/`)

#### Tokenizer (`src/utils/tokenizer.ts`)

**Purpose**: Multi-LLM token counting

**Architecture**:
```typescript
// Model family detection
function detectModelFamily(model: string): ModelFamily {
  // Returns: 'claude' | 'gpt' | 'other'
}

// Dispatch to appropriate tokenizer
function countTokens(text: string, model: string): TokenCount {
  const family = detectModelFamily(model);
  switch (family) {
    case 'claude': return countClaudeTokens(text);
    case 'gpt': return countGPTTokens(text, model);
    default: return estimateTokens(text);
  }
}
```

**Tokenization Libraries**:
- **Claude**: `@anthropic-ai/tokenizer` - Official Anthropic tokenizer
- **GPT**: `tiktoken` - Official OpenAI tokenizer
- **Fallback**: 4 chars ≈ 1 token estimation

**Features**:
- Message overhead calculation (role tags, formatting)
- Model limit percentage
- Optimization recommendations
- Batch processing
- Cache-aware counting

#### Cache (`src/utils/cache.ts`)

**Purpose**: Intelligent prompt and result caching

**Architecture**:
```typescript
class CacheManager {
  private cache: Map<string, CacheEntry>;
  private maxSize: number;
  private defaultTTL: number;

  async get(key: string): Promise<CacheResult> { /* LRU + TTL */ }
  async set(key: string, value: any): Promise<void> { /* Eviction */ }
  getStats(): CacheStats { /* Hit rate, savings */ }
}
```

**Eviction Strategy**:
1. **TTL Check**: Remove expired entries first
2. **LRU Eviction**: Remove least recently used if over maxSize
3. **Hit Tracking**: Update last_accessed and hit_count on access

**Persistence**:
- In-memory cache for speed
- Database backing for cache entries (optional persistence)
- Automatic cleanup of expired entries

### 6. Storage Layer (`src/storage/database.ts`)

**Purpose**: SQLite database management

**Architecture**:
```typescript
class DatabaseManager {
  private db: Database.Database;

  // Conversation operations
  createConversation(conv: Conversation): Conversation;
  getConversation(id: string): Conversation | null;
  updateConversation(id: string, updates: Partial<Conversation>): void;
  deleteConversation(id: string): void;

  // Message operations
  addMessage(msg: Message): Message;
  getMessages(convId: string): Message[];

  // Token stats operations
  addTokenStat(stat: TokenStat): TokenStat;
  getTokenStats(convId: string): TokenStat[];
  getAggregateTokenStats(): AggregateStats;

  // Cache operations
  addCacheEntry(entry: CacheEntry): CacheEntry;
  getCacheEntry(key: string): CacheEntry | null;
  cleanExpiredCache(): number;

  // Reference operations
  addReference(ref: Reference): Reference;
  getReferences(convId: string): Reference[];
  deleteReference(id: string): void;

  // Transaction support
  transaction<T>(fn: () => T): T;
}
```

**Database Configuration**:
```typescript
// SQLite optimizations
this.db.pragma('journal_mode = WAL');  // Write-Ahead Logging
this.db.pragma('synchronous = NORMAL'); // Balance safety/speed
this.db.pragma('busy_timeout = 5000');  // Wait up to 5s for locks
```

### 7. Configuration Layer (`src/config/index.ts`)

**Purpose**: Platform-aware configuration management

**Architecture**:
```typescript
// Zod schema for validation
const ConfigSchema = z.object({
  database: z.object({ /* ... */ }),
  tokenLimits: z.object({ /* ... */ }),
  cache: z.object({ /* ... */ }),
  compression: z.object({ /* ... */ }),
  server: z.object({ /* ... */ }),
});

// Platform-specific paths
function getDataDirectory(): string {
  if (os.platform() === 'win32') {
    return path.join(process.env.APPDATA, 'mcp-token-optimizer');
  } else if (os.platform() === 'darwin') {
    return path.join(os.homedir(), 'Library', 'Application Support', 'mcp-token-optimizer');
  } else {
    return path.join(os.homedir(), '.local', 'share', 'mcp-token-optimizer');
  }
}

// Singleton pattern
let cachedConfig: Config | null = null;
export function getConfig(): Config {
  if (!cachedConfig) {
    cachedConfig = loadConfig();
  }
  return cachedConfig;
}
```

---

## Data Flow

### Tool Execution Flow

```
1. Client sends MCP request
   └─> JSON-RPC message via stdio

2. MCP Server receives request
   └─> StdioServerTransport reads from STDIN

3. Request routing
   └─> CallToolRequestSchema handler invoked

4. Input validation
   └─> Zod schema validates arguments
   └─> Throws error if invalid

5. Tool execution
   └─> Tool handler function called
   └─> Database queries (if needed)
   └─> Cache lookups (if applicable)
   └─> Token counting (if required)

6. Response formatting
   └─> Result wrapped in MCP response format
   └─> Errors caught and formatted

7. Response sent
   └─> JSON-RPC response via stdio
   └─> Client receives result
```

### Resource Access Flow

```
1. Client requests resource
   └─> ReadResourceRequestSchema

2. URI parsing
   └─> Extract scheme and path
   └─> Example: "conversation-history://abc-123"

3. Resource handler dispatch
   └─> Match scheme to handler function

4. Data fetching
   └─> Query database
   └─> Apply filters/transformations

5. Response formatting
   └─> Format as JSON
   └─> Include metadata

6. Response sent
   └─> MCP resource response
```

### Database Transaction Flow

```
1. Tool needs to modify data
   └─> Example: add_message

2. Begin transaction (implicit)
   └─> better-sqlite3 auto-transactions

3. Execute operations
   └─> INSERT message
   └─> UPDATE conversation stats
   └─> Multiple related operations

4. Commit (automatic)
   └─> All operations succeed
   └─> Database updated atomically

5. Rollback on error
   └─> Any operation fails
   └─> All changes reverted
   └─> Error propagated to caller
```

---

## MCP Protocol Integration

### Protocol Version

- **MCP Version**: 1.0
- **Transport**: stdio (STDIN/STDOUT)
- **Message Format**: JSON-RPC 2.0

### Capabilities Declaration

```typescript
{
  capabilities: {
    tools: {},      // Supports tool listing and calling
    resources: {},  // Supports resource listing and reading
    prompts: {},    // Supports prompt listing and generation
  }
}
```

### Request/Response Patterns

**Tool Call**:
```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "count_tokens",
    "arguments": {
      "input": "Hello, world!",
      "model": "claude-3-5-sonnet"
    }
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\":true,\"tokens\":4,...}"
      }
    ]
  }
}
```

**Resource Read**:
```json
// Request
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "resources/read",
  "params": {
    "uri": "token-stats://aggregate"
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "contents": [
      {
        "uri": "token-stats://aggregate",
        "mimeType": "application/json",
        "text": "{...}"
      }
    ]
  }
}
```

---

## Storage Layer Design

### Database Schema

#### Conversations Table
```sql
CREATE TABLE conversations (
  id TEXT PRIMARY KEY,              -- UUID
  title TEXT NOT NULL,              -- Conversation title
  model TEXT NOT NULL,              -- LLM model name
  created_at INTEGER NOT NULL,      -- Unix timestamp (ms)
  updated_at INTEGER NOT NULL,      -- Unix timestamp (ms)
  total_tokens INTEGER DEFAULT 0,   -- Cached token count
  message_count INTEGER DEFAULT 0,  -- Cached message count
  metadata TEXT                     -- JSON metadata (optional)
);
```

#### Messages Table
```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,              -- UUID
  conversation_id TEXT NOT NULL,    -- Foreign key
  role TEXT NOT NULL                -- 'user', 'assistant', 'system'
    CHECK(role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,            -- Message content
  tokens INTEGER NOT NULL,          -- Token count
  created_at INTEGER NOT NULL,      -- Unix timestamp (ms)
  is_compressed INTEGER DEFAULT 0,  -- Boolean flag
  FOREIGN KEY (conversation_id)
    REFERENCES conversations(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_messages_conversation
  ON messages(conversation_id, created_at);
```

#### Token Stats Table
```sql
CREATE TABLE token_stats (
  id TEXT PRIMARY KEY,              -- UUID
  conversation_id TEXT NOT NULL,    -- Foreign key
  timestamp INTEGER NOT NULL,       -- Unix timestamp (ms)
  input_tokens INTEGER NOT NULL,    -- Tokens sent
  output_tokens INTEGER NOT NULL,   -- Tokens received
  cached_tokens INTEGER DEFAULT 0,  -- Tokens cached
  model TEXT NOT NULL,              -- Model used
  FOREIGN KEY (conversation_id)
    REFERENCES conversations(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_token_stats_conversation
  ON token_stats(conversation_id, timestamp);
```

#### Cache Entries Table
```sql
CREATE TABLE cache_entries (
  id TEXT PRIMARY KEY,              -- UUID
  key TEXT UNIQUE NOT NULL,         -- Cache key
  value TEXT NOT NULL,              -- Cached content
  tokens_saved INTEGER DEFAULT 0,   -- Token savings
  hit_count INTEGER DEFAULT 0,      -- Access count
  created_at INTEGER NOT NULL,      -- Unix timestamp (ms)
  last_accessed INTEGER NOT NULL,   -- Unix timestamp (ms)
  expires_at INTEGER NOT NULL       -- Unix timestamp (ms)
);

CREATE INDEX idx_cache_key ON cache_entries(key);
CREATE INDEX idx_cache_expires ON cache_entries(expires_at);
```

#### References Table
```sql
CREATE TABLE references (
  id TEXT PRIMARY KEY,              -- UUID
  conversation_id TEXT NOT NULL,    -- Foreign key
  type TEXT NOT NULL,               -- Reference type
  content TEXT NOT NULL,            -- Reference content
  title TEXT NOT NULL,              -- Reference title
  tokens INTEGER NOT NULL,          -- Token count
  created_at INTEGER NOT NULL,      -- Unix timestamp (ms)
  metadata TEXT,                    -- JSON metadata (optional)
  FOREIGN KEY (conversation_id)
    REFERENCES conversations(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_references_conversation
  ON references(conversation_id, created_at);
```

### Data Access Patterns

**Read Heavy Operations**:
- Message retrieval for conversations
- Token statistics aggregation
- Cache lookups

**Optimization**: Indexed queries, prepared statements, WAL mode

**Write Operations**:
- Message insertion with conversation updates
- Token stat recording
- Cache entry creation

**Optimization**: Batch updates, transaction bundling

---

## Token Optimization Strategies

### 1. Context Compression

**Summarize Strategy**:
```
Input: [msg1, msg2, msg3, ..., msgN]
Process:
  1. Extract key topics from old messages
  2. Generate summary
  3. Keep recent N messages
Output: [summary, msgN-4, msgN-3, msgN-2, msgN-1, msgN]
Compression: 60-80%
```

**Remove Old Strategy**:
```
Input: [msg1, msg2, msg3, ..., msgN]
Process:
  1. Drop oldest messages
  2. Keep recent N messages
Output: [msgN-4, msgN-3, msgN-2, msgN-1, msgN]
Compression: 30-50%
```

**Compress Similar Strategy**:
```
Input: [user, user, user, assistant, assistant]
Process:
  1. Group consecutive same-role messages
  2. Combine and truncate groups
Output: [user_combined, assistant_combined]
Compression: 20-40%
```

**Smart Strategy** (Multi-stage):
```
Stage 1: Remove old if count > 2 * preserve_recent
Stage 2: Compress similar consecutive messages
Stage 3: Remove more old if still > target_tokens
Result: Adaptive compression based on content
Compression: 50-70%
```

### 2. Caching Strategy

**LRU Eviction**:
```
1. On cache.set():
   - Remove expired entries (TTL check)
   - If size > maxSize:
     - Sort by last_accessed (ascending)
     - Remove oldest entries
   - Add new entry

2. On cache.get():
   - Check expiration
   - Update last_accessed
   - Increment hit_count
   - Return value or null
```

**Token Savings Calculation**:
```typescript
tokensSaved = originalTokens - cachedTokens
cacheEfficiency = (tokensSaved / originalTokens) * 100
```

### 3. Query Optimization

**Verbosity Detection**:
```typescript
const fillerWords = ['just', 'really', 'very', 'actually', 'basically', 'literally'];
const fillerCount = countOccurrences(query, fillerWords);
const verbosityRatio = fillerCount / wordCount;
```

**Repetition Detection**:
```typescript
const phrases = extractPhrases(query, 3); // 3-gram
const duplicates = findDuplicates(phrases);
const repetitionRatio = duplicates.length / phrases.length;
```

---

## Performance Optimizations

### Database Optimizations

**WAL Mode** (Write-Ahead Logging):
- Allows concurrent reads during writes
- Improves read performance
- Better crash recovery

**Prepared Statements**:
```typescript
// Cached and reused
const stmt = db.prepare('SELECT * FROM conversations WHERE id = ?');
stmt.get(id); // Fast execution
```

**Indexed Queries**:
```sql
-- Index on frequently queried columns
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);

-- Query optimizer uses index
SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at;
```

### Caching Optimizations

**LRU Eviction**:
- O(1) access time with Map
- O(log n) sorting for eviction
- Lazy cleanup of expired entries

**TTL-Based Expiration**:
```typescript
// Check on access, not periodic cleanup
if (entry.expires_at < Date.now()) {
  this.cache.delete(key);
  return null;
}
```

### Token Counting Optimizations

**Model-Specific Tokenizers**:
- Claude: Native Anthropic tokenizer (~1ms/1k tokens)
- GPT: tiktoken library (~5ms/1k tokens)
- Fallback: Estimation (~0.1ms/1k tokens)

**Batch Processing**:
```typescript
// Process multiple texts in single call
function batchCountTokens(texts: string[]): TokenCount[] {
  return texts.map(text => countTokens(text));
}
```

---

## Security Considerations

### Input Validation

**Zod Schema Validation**:
```typescript
// All inputs validated before processing
const validated = ToolInputSchema.parse(args);
// Throws if invalid, includes detailed error
```

**SQL Injection Prevention**:
```typescript
// Always use prepared statements
const stmt = db.prepare('SELECT * FROM users WHERE id = ?');
stmt.get(userId); // Safe from SQL injection
```

### Data Isolation

**Conversation Scoping**:
- Messages scoped to conversation_id
- Foreign key constraints enforced
- Cascade deletion for data integrity

### Error Handling

**Safe Error Messages**:
```typescript
try {
  // Operation
} catch (error: any) {
  return {
    success: false,
    error: error.message || 'Unknown error',
    // No stack traces exposed to client
  };
}
```

### No Dynamic Code

- No `eval()` usage
- No `Function()` constructor
- No dynamic `require()`
- All code statically analyzable

---

## Platform Compatibility

### Windows Compatibility

**Signal Handling**:
```typescript
// No SIGALRM on Windows
process.on('SIGINT', cleanup);  // Ctrl+C
process.on('SIGTERM', cleanup); // Terminate request
```

**Path Handling**:
```typescript
// Cross-platform path joining
const dbPath = path.join(getDataDirectory(), 'token-optimizer.db');
// Works on Windows (\), Unix (/)
```

**Data Directories**:
```typescript
// Windows: %APPDATA%\mcp-token-optimizer\
// macOS: ~/Library/Application Support/mcp-token-optimizer/
// Linux: ~/.local/share/mcp-token-optimizer/
```

### Cross-Platform Testing

**Supported Platforms**:
- Windows 11 (primary)
- Windows 10
- macOS 12+ (Monterey and later)
- Linux (Ubuntu 20.04+, Debian 11+)

**Platform-Specific Features**:
- Batch scripts for Windows (.bat)
- Shell scripts for Unix (future .sh)
- Platform detection in configuration

---

## Scalability Considerations

### Current Limitations

- **Single Server Instance**: No horizontal scaling
- **In-Memory Cache**: Limited by RAM
- **SQLite**: Single-writer limitation

### Future Scaling Options

1. **Database Scaling**:
   - PostgreSQL for multi-writer support
   - Read replicas for query scaling
   - Connection pooling

2. **Cache Scaling**:
   - Redis for distributed caching
   - Cache cluster for high availability
   - Persistent cache backing

3. **Processing Scaling**:
   - Worker pool for parallel compression
   - Job queue for async operations
   - Load balancing for multiple instances

---

## Extension Points

### Adding New Tools

1. Create tool file in `src/tools/`
2. Define Zod input schema
3. Implement tool handler function
4. Register in `src/index.ts`

### Adding New Resources

1. Create resource file in `src/resources/`
2. Define URI scheme
3. Implement resource handler
4. Register in `src/index.ts`

### Adding New Compression Strategies

1. Add strategy to enum in `compress_context.ts`
2. Implement compression algorithm
3. Update strategy switch statement
4. Add tests for new strategy

---

## Monitoring & Observability

### Current Logging

```typescript
// Server lifecycle
console.error('Database initialized');
console.error('Server running on stdio');

// Error logging
console.error('Error:', error.message);
```

### Future Monitoring

- **Structured Logging**: Winston/Pino with log levels
- **Performance Metrics**: Tool execution times, database query profiling
- **Health Checks**: Server health endpoint
- **Alerting**: Error rate monitoring, resource usage alerts

---

## Conclusion

The MCP Token Optimizer architecture is designed for:

✅ **Maintainability** - Clear layer separation, single responsibility
✅ **Performance** - Optimized database, caching, tokenization
✅ **Security** - Input validation, SQL injection prevention
✅ **Reliability** - Error handling, graceful degradation
✅ **Extensibility** - Plugin points for tools, resources, prompts
✅ **Compatibility** - Cross-platform support

This architecture supports the current feature set while providing a solid foundation for future enhancements including multi-user support, distributed caching, and advanced analytics.

---

**Document Version**: 1.0
**Last Updated**: November 18, 2024
**Maintained By**: MCP Token Optimizer Team
