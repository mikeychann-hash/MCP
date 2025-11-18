# MCP Token Optimizer - API Reference

Complete API documentation for all tools, resources, and prompts.

**Version**: 1.0.0
**Protocol**: MCP 1.0
**Transport**: stdio

---

## Table of Contents

1. [Tools API](#tools-api)
   - [manage_conversation](#1-manage_conversation)
   - [compress_context](#2-compress_context)
   - [count_tokens](#3-count_tokens)
   - [smart_cache](#4-smart_cache)
   - [track_references](#5-track_references)
   - [optimize_query](#6-optimize_query)

2. [Resources API](#resources-api)
   - [conversation-history](#1-conversation-history)
   - [token-stats](#2-token-stats)
   - [cache-stats](#3-cache-stats)
   - [optimization-tips](#4-optimization-tips)
   - [reference-library](#5-reference-library)

3. [Prompts API](#prompts-api)
   - [summarize_context](#1-summarize_context)
   - [compress_conversation](#2-compress_conversation)
   - [extract_essentials](#3-extract_essentials)

4. [Error Codes](#error-codes)
5. [Response Formats](#response-formats)

---

## Tools API

### 1. manage_conversation

**Description**: Create, update, retrieve, and delete conversations with automatic token tracking.

#### Actions

##### create

Create a new conversation.

**Input Schema**:
```typescript
{
  action: 'create',
  title: string,              // Conversation title (required)
  model?: string,             // LLM model (default: 'claude-3-5-sonnet')
  metadata?: Record<string, any>  // Optional metadata
}
```

**Example Request**:
```json
{
  "name": "manage_conversation",
  "arguments": {
    "action": "create",
    "title": "Code Review Session",
    "model": "claude-3-5-sonnet",
    "metadata": {
      "project": "mcp-optimizer",
      "reviewer": "alice"
    }
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "conversation": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Code Review Session",
    "model": "claude-3-5-sonnet",
    "created_at": 1700000000000,
    "total_tokens": 0,
    "message_count": 0
  },
  "message": "Conversation \"Code Review Session\" created successfully"
}
```

##### add_message

Add a message to an existing conversation.

**Input Schema**:
```typescript
{
  action: 'add_message',
  conversation_id: string,    // UUID (required)
  role: 'user' | 'assistant' | 'system',  // Message role (required)
  content: string             // Message content (required)
}
```

**Example Request**:
```json
{
  "name": "manage_conversation",
  "arguments": {
    "action": "add_message",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "user",
    "content": "Please review this function: function add(a, b) { return a + b; }"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "message": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "role": "user",
    "tokens": 18,
    "created_at": 1700000001000
  },
  "conversation": {
    "total_tokens": 18,
    "message_count": 1
  }
}
```

##### get

Retrieve a conversation with optional messages.

**Input Schema**:
```typescript
{
  action: 'get',
  conversation_id: string,    // UUID (required)
  include_messages?: boolean  // Include messages (default: true)
}
```

**Example Request**:
```json
{
  "name": "manage_conversation",
  "arguments": {
    "action": "get",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "include_messages": true
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "conversation": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Code Review Session",
    "model": "claude-3-5-sonnet",
    "created_at": 1700000000000,
    "updated_at": 1700000001000,
    "total_tokens": 18,
    "message_count": 1,
    "metadata": {
      "project": "mcp-optimizer",
      "reviewer": "alice"
    }
  },
  "messages": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "role": "user",
      "content": "Please review this function: function add(a, b) { return a + b; }",
      "tokens": 18,
      "is_compressed": false,
      "created_at": 1700000001000
    }
  ],
  "actual_tokens": 22
}
```

##### list

List all conversations with pagination.

**Input Schema**:
```typescript
{
  action: 'list',
  limit?: number  // Max results (default: 20)
}
```

**Example Request**:
```json
{
  "name": "manage_conversation",
  "arguments": {
    "action": "list",
    "limit": 10
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "conversations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Code Review Session",
      "model": "claude-3-5-sonnet",
      "created_at": 1700000000000,
      "updated_at": 1700000001000,
      "total_tokens": 18,
      "message_count": 1
    }
  ],
  "total": 1,
  "showing": 1
}
```

##### delete

Delete a conversation and all its messages.

**Input Schema**:
```typescript
{
  action: 'delete',
  conversation_id: string  // UUID (required)
}
```

**Example Request**:
```json
{
  "name": "manage_conversation",
  "arguments": {
    "action": "delete",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "message": "Conversation \"Code Review Session\" deleted successfully"
}
```

---

### 2. compress_context

**Description**: Intelligently compress conversation context to reduce token usage while preserving essential information.

**Input Schema**:
```typescript
{
  conversation_id: string,    // UUID (required)
  strategy?: 'summarize' | 'remove_old' | 'compress_similar' | 'smart',  // Default: 'smart'
  target_ratio?: number,      // 0.1-0.9 (default: 0.5)
  preserve_recent?: number    // Number of recent messages to preserve (default: 5)
}
```

#### Compression Strategies

- **summarize**: Extract key topics and generate summary, keep recent messages
- **remove_old**: Drop oldest messages, keep recent N messages
- **compress_similar**: Combine consecutive messages from same role
- **smart**: Adaptive multi-stage compression (recommended)

**Example Request**:
```json
{
  "name": "compress_context",
  "arguments": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "strategy": "smart",
    "target_ratio": 0.5,
    "preserve_recent": 5
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "original_tokens": 15234,
  "compressed_tokens": 7412,
  "tokens_saved": 7822,
  "compression_ratio": 0.49,
  "original_message_count": 42,
  "compressed_message_count": 18,
  "strategy": "smart",
  "compressed_messages": [
    {
      "role": "system",
      "content": "[Compressed context]\nSummary of 24 messages:\n- User asked about: optimization, caching, performance\n- 12 responses provided...",
      "tokens": 245,
      "is_compressed": true
    },
    {
      "role": "user",
      "content": "What are the best practices for token optimization?",
      "tokens": 12,
      "is_compressed": false
    }
  ]
}
```

---

### 3. count_tokens

**Description**: Count tokens for text, messages, or conversations with multi-LLM support and optimization recommendations.

**Input Schema**:
```typescript
{
  input: string | Message[] | object,  // Text, messages, or structured data (required)
  model?: string,                       // LLM model (default: 'claude-3-5-sonnet')
  include_recommendations?: boolean,    // Include optimization tips (default: true)
  conversation_id?: string              // Optional conversation ID for context
}
```

#### Supported Models

- **Claude**: claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus
- **GPT**: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- **Other**: Generic fallback estimation

**Example Request (Text)**:
```json
{
  "name": "count_tokens",
  "arguments": {
    "input": "Hello, world! This is a test message for token counting.",
    "model": "claude-3-5-sonnet",
    "include_recommendations": true
  }
}
```

**Example Response (Text)**:
```json
{
  "success": true,
  "tokens": 14,
  "model": "claude-3-5-sonnet",
  "family": "claude",
  "percentage": 0.007,
  "limit": 200000,
  "recommendation": {
    "status": "safe",
    "percentage": 0.007,
    "action": "Token usage is healthy. No action needed.",
    "shouldCompress": false
  }
}
```

**Example Request (Messages)**:
```json
{
  "name": "count_tokens",
  "arguments": {
    "input": [
      { "role": "user", "content": "What is 2+2?" },
      { "role": "assistant", "content": "2+2 equals 4." }
    ],
    "model": "gpt-4"
  }
}
```

**Example Response (Messages)**:
```json
{
  "success": true,
  "tokens": 32,
  "model": "gpt-4",
  "family": "gpt",
  "percentage": 0.025,
  "limit": 128000,
  "breakdown": {
    "content_tokens": 18,
    "overhead_tokens": 14,
    "conversation_tokens": 3
  },
  "recommendation": {
    "status": "safe",
    "percentage": 0.025,
    "action": "Token usage is healthy. No action needed.",
    "shouldCompress": false
  }
}
```

---

### 4. smart_cache

**Description**: Intelligent caching for prompts and contexts with automatic reuse detection to save tokens.

**Input Schema**:
```typescript
{
  action: 'store' | 'retrieve' | 'check' | 'stats' | 'clear',  // Action (required)
  key?: string,            // Cache key (optional for store, required for retrieve)
  content?: string,        // Content to cache (required for store/check)
  model?: string,          // Model for token counting (default: 'claude-3-5-sonnet')
  ttl?: number,            // Time to live in milliseconds
  prefix?: string          // Cache key prefix for organization
}
```

##### store

Store content in cache.

**Example Request**:
```json
{
  "name": "smart_cache",
  "arguments": {
    "action": "store",
    "content": "You are a helpful coding assistant specialized in TypeScript and React...",
    "prefix": "system-prompts",
    "ttl": 3600000
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "key": "system-prompts:550e8400-e29b-41d4-a716-446655440002",
  "tokens": 145,
  "expires_at": 1700003600000,
  "message": "Content cached successfully"
}
```

##### retrieve

Retrieve cached content.

**Example Request**:
```json
{
  "name": "smart_cache",
  "arguments": {
    "action": "retrieve",
    "key": "system-prompts:550e8400-e29b-41d4-a716-446655440002"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "key": "system-prompts:550e8400-e29b-41d4-a716-446655440002",
  "content": "You are a helpful coding assistant specialized in TypeScript and React...",
  "tokens": 145,
  "hit_count": 12,
  "created_at": 1700000000000,
  "last_accessed": 1700000050000
}
```

##### check

Check if content is already cached.

**Example Request**:
```json
{
  "name": "smart_cache",
  "arguments": {
    "action": "check",
    "content": "You are a helpful coding assistant..."
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "exists": true,
  "key": "system-prompts:550e8400-e29b-41d4-a716-446655440002",
  "tokens_saved": 145,
  "message": "Content already cached"
}
```

##### stats

Get cache statistics.

**Example Request**:
```json
{
  "name": "smart_cache",
  "arguments": {
    "action": "stats"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "stats": {
    "total_entries": 15,
    "total_hits": 342,
    "tokens_saved": 45678,
    "hit_rate": 67.8,
    "avg_tokens_per_entry": 3045,
    "effectiveness": "high"
  }
}
```

##### clear

Clear cache entries.

**Example Request**:
```json
{
  "name": "smart_cache",
  "arguments": {
    "action": "clear",
    "prefix": "system-prompts"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "cleared": 5,
  "message": "Cleared 5 cache entries with prefix 'system-prompts'"
}
```

---

### 5. track_references

**Description**: Track and manage reference materials (files, URLs, code snippets, notes) with token counting.

**Input Schema**:
```typescript
{
  action: 'add' | 'get' | 'list' | 'delete' | 'search',  // Action (required)
  conversation_id?: string,      // Conversation UUID (required for add)
  reference_id?: string,         // Reference UUID (required for get/delete)
  type?: 'file' | 'url' | 'code' | 'note' | 'document',  // Type of reference
  title?: string,                // Reference title (required for add)
  content?: string,              // Reference content (required for add)
  metadata?: object,             // Additional metadata
  search_query?: string          // Search query (required for search)
}
```

##### add

Add a new reference.

**Example Request**:
```json
{
  "name": "track_references",
  "arguments": {
    "action": "add",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "code",
    "title": "Token Counter Implementation",
    "content": "function countTokens(text: string): number { /* ... */ }",
    "metadata": {
      "language": "typescript",
      "file": "src/utils/tokenizer.ts"
    }
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "reference": {
    "id": "770e8400-e29b-41d4-a716-446655440003",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "code",
    "title": "Token Counter Implementation",
    "tokens": 89,
    "created_at": 1700000002000
  },
  "message": "Reference added successfully"
}
```

##### get

Retrieve a specific reference.

**Example Request**:
```json
{
  "name": "track_references",
  "arguments": {
    "action": "get",
    "reference_id": "770e8400-e29b-41d4-a716-446655440003"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "reference": {
    "id": "770e8400-e29b-41d4-a716-446655440003",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "code",
    "title": "Token Counter Implementation",
    "content": "function countTokens(text: string): number { /* ... */ }",
    "tokens": 89,
    "created_at": 1700000002000,
    "metadata": {
      "language": "typescript",
      "file": "src/utils/tokenizer.ts"
    }
  }
}
```

##### list

List all references or filter by conversation.

**Example Request**:
```json
{
  "name": "track_references",
  "arguments": {
    "action": "list",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "references": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440003",
      "type": "code",
      "title": "Token Counter Implementation",
      "tokens": 89,
      "created_at": 1700000002000
    }
  ],
  "total": 1
}
```

##### delete

Delete a reference.

**Example Request**:
```json
{
  "name": "track_references",
  "arguments": {
    "action": "delete",
    "reference_id": "770e8400-e29b-41d4-a716-446655440003"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "message": "Reference deleted successfully"
}
```

##### search

Search references by content.

**Example Request**:
```json
{
  "name": "track_references",
  "arguments": {
    "action": "search",
    "search_query": "token counter"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "results": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440003",
      "type": "code",
      "title": "Token Counter Implementation",
      "preview": "function countTokens(text: string): number { ...",
      "tokens": 89,
      "relevance": 0.95
    }
  ],
  "total": 1
}
```

---

### 6. optimize_query

**Description**: Analyze and optimize queries for better token efficiency and clarity.

**Input Schema**:
```typescript
{
  query: string,              // Query text to optimize (required)
  context?: string,           // Optional context for combined analysis
  model?: string,             // Model for token counting (default: 'claude-3-5-sonnet')
  optimization_goal?: 'reduce_tokens' | 'improve_clarity' | 'both',  // Default: 'both'
  max_tokens?: number         // Maximum token constraint
}
```

**Example Request**:
```json
{
  "name": "optimize_query",
  "arguments": {
    "query": "I was just wondering if you could maybe help me understand how to really optimize my prompts for better token usage, basically.",
    "optimization_goal": "both",
    "model": "claude-3-5-sonnet"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "original": {
    "query": "I was just wondering if you could maybe help me understand how to really optimize my prompts for better token usage, basically.",
    "tokens": 28,
    "issues": [
      {
        "type": "filler_words",
        "words": ["just", "maybe", "really", "basically"],
        "impact": "moderate"
      },
      {
        "type": "verbosity",
        "score": 0.65,
        "impact": "high"
      }
    ]
  },
  "optimized": {
    "query": "Help me optimize my prompts for better token usage.",
    "tokens": 11,
    "improvements": [
      "Removed filler words (4)",
      "Simplified structure",
      "Preserved core meaning"
    ]
  },
  "analysis": {
    "tokens_saved": 17,
    "reduction_percent": 60.7,
    "clarity_score": 0.92,
    "recommendations": [
      {
        "priority": "high",
        "suggestion": "Remove unnecessary qualifiers like 'just', 'really'",
        "tokens_saved": 4
      },
      {
        "priority": "medium",
        "suggestion": "Use direct language instead of 'I was wondering if'",
        "tokens_saved": 5
      }
    ]
  }
}
```

---

## Resources API

### 1. conversation-history

**Description**: List all conversations with token metadata or get detailed history of a specific conversation.

#### URIs

##### All Conversations
**URI**: `conversation-history://all`

**Example Response**:
```json
{
  "conversations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Code Review Session",
      "model": "claude-3-5-sonnet",
      "created_at": 1700000000000,
      "updated_at": 1700000001000,
      "total_tokens": 1245,
      "message_count": 8,
      "last_message": "Let's review the token optimization strategies..."
    }
  ],
  "total": 1
}
```

##### Specific Conversation
**URI**: `conversation-history://{conversation_id}`

**Example Response**:
```json
{
  "conversation": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Code Review Session",
    "model": "claude-3-5-sonnet",
    "created_at": 1700000000000,
    "updated_at": 1700000001000,
    "total_tokens": 1245,
    "message_count": 8
  },
  "messages": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "role": "user",
      "content": "Please review this code...",
      "tokens": 125,
      "is_compressed": false,
      "created_at": 1700000001000
    }
  ],
  "statistics": {
    "avg_tokens_per_message": 155,
    "total_user_tokens": 678,
    "total_assistant_tokens": 567,
    "compression_ratio": 0
  }
}
```

---

### 2. token-stats

**Description**: Overall token usage statistics across all conversations or for a specific conversation.

#### URIs

##### Aggregate Statistics
**URI**: `token-stats://aggregate`

**Example Response**:
```json
{
  "overview": {
    "total_conversations": 25,
    "total_messages": 450,
    "total_input_tokens": 125000,
    "total_output_tokens": 95000,
    "total_cached_tokens": 28000,
    "total_tokens": 220000
  },
  "by_model": {
    "claude-3-5-sonnet": {
      "conversations": 18,
      "input_tokens": 95000,
      "output_tokens": 72000,
      "cached_tokens": 22000
    },
    "gpt-4": {
      "conversations": 7,
      "input_tokens": 30000,
      "output_tokens": 23000,
      "cached_tokens": 6000
    }
  },
  "cache_efficiency": {
    "cache_hit_rate": 12.7,
    "tokens_saved": 28000,
    "estimated_cost_savings": "$42.50"
  },
  "trends": {
    "daily_average": 8800,
    "weekly_average": 61600,
    "peak_day": "2024-11-15",
    "peak_tokens": 15200
  }
}
```

##### Conversation-Specific Statistics
**URI**: `token-stats://{conversation_id}`

**Example Response**:
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Code Review Session",
  "model": "claude-3-5-sonnet",
  "statistics": {
    "total_tokens": 1245,
    "input_tokens": 678,
    "output_tokens": 567,
    "cached_tokens": 145,
    "message_count": 8,
    "avg_tokens_per_message": 155
  },
  "timeline": [
    {
      "timestamp": 1700000001000,
      "cumulative_tokens": 125,
      "message_tokens": 125
    },
    {
      "timestamp": 1700000010000,
      "cumulative_tokens": 289,
      "message_tokens": 164
    }
  ],
  "token_limit": {
    "model_limit": 200000,
    "current_usage": 1245,
    "percentage": 0.62,
    "status": "safe"
  }
}
```

---

### 3. cache-stats

**Description**: Cache performance and usage statistics.

**URI**: `cache-stats://current`

**Example Response**:
```json
{
  "overview": {
    "total_entries": 15,
    "total_hits": 342,
    "total_misses": 163,
    "hit_rate": 67.8,
    "tokens_saved": 45678,
    "avg_tokens_per_entry": 3045
  },
  "performance": {
    "effectiveness": "high",
    "avg_hit_count": 22.8,
    "most_cached_prefix": "system-prompts",
    "cache_size_bytes": 1024000
  },
  "top_entries": [
    {
      "key": "system-prompts:550e8400-e29b-41d4-a716-446655440002",
      "hits": 89,
      "tokens_saved": 12905,
      "last_accessed": 1700000050000
    },
    {
      "key": "compress:550e8400-e29b-41d4-a716-446655440000:smart:0.5",
      "hits": 45,
      "tokens_saved": 6750,
      "last_accessed": 1700000045000
    }
  ],
  "by_prefix": {
    "system-prompts": {
      "entries": 5,
      "hits": 234,
      "tokens_saved": 34560
    },
    "compress": {
      "entries": 7,
      "hits": 98,
      "tokens_saved": 10890
    },
    "summaries": {
      "entries": 3,
      "hits": 10,
      "tokens_saved": 228
    }
  },
  "recommendations": [
    {
      "priority": "low",
      "suggestion": "Cache hit rate is healthy",
      "action": "Continue current caching strategy"
    }
  ]
}
```

---

### 4. optimization-tips

**Description**: General tips for token optimization or context-specific optimization recommendations.

#### URIs

##### General Tips
**URI**: `optimization-tips://general`

**Example Response**:
```json
{
  "overview": {
    "total_conversations": 25,
    "total_messages": 450,
    "total_tokens": 125000,
    "cache_hit_rate": 67.8
  },
  "tips": [
    {
      "category": "token_management",
      "priority": "medium",
      "tip": "Token usage is moderate across conversations",
      "action": "Consider compressing older messages in long conversations"
    },
    {
      "category": "caching",
      "priority": "low",
      "tip": "Cache is performing well",
      "action": "Continue using cached prompts for token savings"
    },
    {
      "category": "best_practices",
      "priority": "low",
      "tip": "Use optimize_query before sending long prompts",
      "action": "Optimize queries to remove filler words and improve clarity"
    },
    {
      "category": "best_practices",
      "priority": "low",
      "tip": "Track reference materials separately",
      "action": "Use track_references for code snippets, docs, and URLs"
    }
  ],
  "resources": {
    "documentation": "See MCP server documentation for detailed guides",
    "tools_available": [
      "manage_conversation",
      "compress_context",
      "count_tokens",
      "smart_cache",
      "track_references",
      "optimize_query"
    ]
  }
}
```

##### Conversation-Specific Tips
**URI**: `optimization-tips://{conversation_id}`

**Example Response**:
```json
{
  "conversation": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Code Review Session",
    "model": "claude-3-5-sonnet",
    "current_tokens": 15234,
    "message_count": 42
  },
  "tips": [
    {
      "category": "token_management",
      "priority": "high",
      "tip": "Token usage is approaching model limit",
      "action": "Use compress_context tool to reduce token count"
    },
    {
      "category": "conversation_length",
      "priority": "medium",
      "tip": "Conversation has many messages",
      "action": "Use compress_context with 'remove_old' strategy"
    },
    {
      "category": "compression",
      "priority": "medium",
      "tip": "No messages have been compressed yet",
      "action": "Try compress_context to reduce token usage"
    }
  ]
}
```

---

### 5. reference-library

**Description**: Library of all tracked reference materials or references for a specific conversation.

#### URIs

##### All References
**URI**: `reference-library://all`

**Example Response**:
```json
{
  "overview": {
    "total_references": 15,
    "total_tokens": 12456,
    "by_type": {
      "code": 8,
      "url": 3,
      "file": 2,
      "note": 2
    }
  },
  "references": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440003",
      "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "code",
      "title": "Token Counter Implementation",
      "preview": "function countTokens(text: string): number { ...",
      "tokens": 89,
      "created_at": 1700000002000
    }
  ]
}
```

##### Conversation References
**URI**: `reference-library://{conversation_id}`

**Example Response**:
```json
{
  "conversation": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Code Review Session"
  },
  "references": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440003",
      "type": "code",
      "title": "Token Counter Implementation",
      "content": "function countTokens(text: string): number { /* ... */ }",
      "tokens": 89,
      "created_at": 1700000002000,
      "metadata": {
        "language": "typescript",
        "file": "src/utils/tokenizer.ts"
      }
    }
  ],
  "statistics": {
    "total_references": 1,
    "total_tokens": 89,
    "by_type": {
      "code": 1
    }
  }
}
```

---

## Prompts API

### 1. summarize_context

**Description**: Generate a comprehensive summary of conversation context.

**Arguments**:
```typescript
{
  conversation_id?: string,   // UUID of conversation to summarize (optional)
  focus?: string,             // Specific aspect to focus on in summary
  max_summary_tokens?: number // Maximum tokens for the summary
}
```

**Example Request**:
```json
{
  "name": "summarize_context",
  "arguments": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "focus": "technical decisions and code patterns",
    "max_summary_tokens": 500
  }
}
```

**Example Response** (Prompt):
```text
# Conversation Summarization Request

**Conversation:** Code Review Session
**Model:** claude-3-5-sonnet
**Messages:** 42
**Total Tokens:** 15234
**Created:** 2024-11-15T10:00:00.000Z

## Conversation History

[USER]: Please review this function: function add(a, b) { return a + b; }

[ASSISTANT]: The function is simple and correct. However, consider adding type annotations...

[USER]: How can I optimize this for token usage?

[ASSISTANT]: You can use the compress_context tool to reduce token count...

---

## Summarization Instructions

Please summarize the above conversation, focusing on:
- Main topics and themes discussed
- Key technical details or code snippets
- Important decisions or conclusions
- Questions asked and answers provided
- Any action items or next steps

**Special Focus:** technical decisions and code patterns

**Format Requirements:**
- Use clear section headers
- Bullet points for lists
- Preserve critical technical details
- Be concise but comprehensive
- Keep summary under 500 tokens

**Summary Structure:**

**Overview:**
[1-2 sentence high-level summary]

**Main Topics:**
- [topic 1 with brief context]
- [topic 2 with brief context]

**Technical Details:**
- [key technical points, code patterns, etc.]

**Key Takeaways:**
- [important conclusions or decisions]

**Unresolved Items:**
- [open questions or pending tasks]

Now provide the summary:
```

---

### 2. compress_conversation

**Description**: Generate a compressed version of conversation while preserving essentials.

**Arguments**:
```typescript
{
  conversation_id: string,           // UUID of conversation to compress (required)
  target_reduction_percent?: number, // Target reduction percentage (default: 50)
  preserve_recent_count?: number     // Number of recent messages to preserve (default: 5)
}
```

**Example Request**:
```json
{
  "name": "compress_conversation",
  "arguments": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "target_reduction_percent": 60,
    "preserve_recent_count": 8
  }
}
```

**Example Response** (Prompt):
```text
# Conversation Compression Request

You are an expert at compressing conversation context while preserving essential information.

## Original Conversation

**Title:** Code Review Session
**Model:** claude-3-5-sonnet
**Messages:** 42
**Current Tokens:** 15234
**Target:** Reduce by 60% to ~6094 tokens

## Full Conversation History

[Message 1-42 with full content...]

---

## Compression Instructions

Your task is to compress this conversation by 60% while:

**Preserve:**
- All technical code snippets and examples
- Key decisions and conclusions
- Important facts and data
- Action items and next steps
- The most recent 8 messages (keep verbatim)

**Compress:**
- Redundant explanations
- Small talk and pleasantries
- Repetitive questions/answers
- Verbose descriptions
- Intermediate discussion steps

**Format:**
Return a compressed conversation in this structure:

```json
{
  "summary": "[High-level summary of compressed content]",
  "key_points": [
    "[Essential point 1]",
    "[Essential point 2]"
  ],
  "code_snippets": [
    {
      "description": "[What this code does]",
      "code": "[The actual code]"
    }
  ],
  "decisions": [
    "[Important decision 1]"
  ],
  "recent_messages": [
    // Most recent 8 messages (verbatim)
  ]
}
```

**Target:** ~6094 tokens

Now compress the conversation:
```

---

### 3. extract_essentials

**Description**: Extract only essential information from context (facts, code, decisions, etc.).

**Arguments**:
```typescript
{
  conversation_id?: string,   // UUID of conversation to extract from (optional)
  content?: string,           // Direct content to extract from (optional)
  extract_type?: 'facts' | 'code' | 'decisions' | 'questions' | 'all',  // Default: 'all'
  model?: string              // Model for token counting (default: 'claude-3-5-sonnet')
}
```

**Example Request**:
```json
{
  "name": "extract_essentials",
  "arguments": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "extract_type": "all"
  }
}
```

**Example Response** (Prompt):
```text
# Essential Information Extraction

Extract essential information from the following conversation.

## Source Conversation

**Title:** Code Review Session
**Model:** claude-3-5-sonnet
**Messages:** 42
**Tokens:** 15234

## Full Content

[Message 1-42 with full content...]

---

## Extraction Instructions

Extract the following types of information:

### Facts
Objective, verifiable information:
- Technical specifications
- API endpoints
- Configuration values
- Version numbers
- File paths
- Error messages

### Code
All code snippets, commands, and technical examples:
- Function definitions
- Code blocks
- Command-line instructions
- Configuration snippets
- SQL queries

### Decisions
Important conclusions and choices:
- Architecture decisions
- Technology choices
- Approach selections
- Problem resolutions

### Questions
Unanswered or important questions:
- Open questions
- Clarification needs
- Pending items

## Output Format

Return a structured JSON object:

```json
{
  "facts": [
    {
      "category": "technical|configuration|version|path|error",
      "fact": "[The factual statement]",
      "context": "[Where/when this was mentioned]"
    }
  ],
  "code": [
    {
      "language": "[Programming language]",
      "description": "[What this code does]",
      "code": "[The actual code]",
      "context": "[Why this was shared]"
    }
  ],
  "decisions": [
    {
      "decision": "[What was decided]",
      "rationale": "[Why this was chosen]",
      "alternatives": "[What else was considered]"
    }
  ],
  "questions": [
    {
      "question": "[The question]",
      "status": "answered|unanswered",
      "answer": "[Answer if available]"
    }
  ],
  "statistics": {
    "total_facts": 0,
    "total_code_snippets": 0,
    "total_decisions": 0,
    "total_questions": 0,
    "answered_questions": 0
  }
}
```

Now extract the essential information:
```

---

## Error Codes

### Common Error Responses

**Conversation Not Found**:
```json
{
  "success": false,
  "error": "Conversation not found"
}
```

**Invalid Input**:
```json
{
  "success": false,
  "error": "Validation error",
  "details": [
    {
      "path": ["action"],
      "message": "Invalid enum value. Expected 'create' | 'add_message' | 'get' | 'list' | 'delete', received 'invalid'"
    }
  ]
}
```

**Missing Required Field**:
```json
{
  "success": false,
  "error": "Validation error",
  "details": [
    {
      "path": ["conversation_id"],
      "message": "Required"
    }
  ]
}
```

**Database Error**:
```json
{
  "success": false,
  "error": "Database operation failed",
  "message": "Internal server error"
}
```

**Cache Miss**:
```json
{
  "success": true,
  "exists": false,
  "message": "Content not found in cache"
}
```

---

## Response Formats

### Success Response

All successful tool calls return:
```json
{
  "success": true,
  // ... tool-specific data
}
```

### Error Response

All errors return:
```json
{
  "success": false,
  "error": "Error message",
  "details": []  // Optional validation details
}
```

### Resource Response

All resources return JSON strings in this format:
```json
{
  // Resource-specific data
}
```

---

## Rate Limits

Currently, there are no rate limits enforced. This may change in future versions.

---

## Best Practices

1. **Token Counting**: Always specify the correct model for accurate token counts
2. **Compression**: Start with 'smart' strategy, adjust based on results
3. **Caching**: Use prefixes to organize cache entries
4. **References**: Add metadata for better organization
5. **Optimization**: Run `optimize_query` before sending long prompts

---

**API Version**: 1.0.0
**Last Updated**: November 18, 2024
**Documentation**: [Full Documentation](README.md)
