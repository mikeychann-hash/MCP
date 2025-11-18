#!/usr/bin/env node

/**
 * MCP Token Optimizer Server
 * Intelligent token optimization and context management for LLM applications
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { getConfig } from './config/index.js';
import { getDatabase, closeDatabase } from './storage/database.js';

// Tool imports
import { manageConversation, ManageConversationInputSchema } from './tools/manage_conversation.js';
import { compressContext, CompressContextInputSchema } from './tools/compress_context.js';
import { countTokensTool, CountTokensInputSchema } from './tools/count_tokens.js';
import { smartCache, SmartCacheInputSchema } from './tools/smart_cache.js';
import { trackReferences, TrackReferencesInputSchema } from './tools/track_references.js';
import { optimizeQuery, OptimizeQueryInputSchema } from './tools/optimize_query.js';

// Resource imports
import { getConversationHistory } from './resources/conversation_history.js';
import { getTokenStats } from './resources/token_stats.js';
import { getCacheStats } from './resources/cache_stats.js';
import { getOptimizationTips } from './resources/optimization_tips.js';
import { getReferenceLibrary } from './resources/reference_library.js';

// Prompt imports
import { generateSummarizePrompt } from './prompts/summarize_context.js';
import { generateCompressPrompt } from './prompts/compress_conversation.js';
import { generateExtractPrompt } from './prompts/extract_essentials.js';

/**
 * Main server class
 */
class TokenOptimizerServer {
  private server: Server;
  private config = getConfig();

  constructor() {
    this.server = new Server(
      {
        name: this.config.server.name,
        version: this.config.server.version,
      },
      {
        capabilities: {
          tools: {},
          resources: {},
          prompts: {},
        },
      }
    );

    this.setupHandlers();
    this.setupErrorHandling();
  }

  /**
   * Setup request handlers
   */
  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'manage_conversation',
          description: 'Create, update, retrieve, and delete conversations with automatic token tracking',
          inputSchema: {
            type: 'object',
            properties: {
              action: {
                type: 'string',
                enum: ['create', 'add_message', 'get', 'list', 'delete'],
                description: 'Action to perform',
              },
              conversation_id: {
                type: 'string',
                description: 'UUID of the conversation (required for add_message, get, delete)',
              },
              title: {
                type: 'string',
                description: 'Conversation title (required for create)',
              },
              model: {
                type: 'string',
                description: 'LLM model name (default: claude-3-5-sonnet)',
              },
              role: {
                type: 'string',
                enum: ['user', 'assistant', 'system'],
                description: 'Message role (required for add_message)',
              },
              content: {
                type: 'string',
                description: 'Message content (required for add_message)',
              },
              include_messages: {
                type: 'boolean',
                description: 'Include messages in response (default: true)',
              },
              limit: {
                type: 'number',
                description: 'Limit number of results (default: 20)',
              },
            },
            required: ['action'],
          },
        },
        {
          name: 'compress_context',
          description: 'Intelligently compress conversation context to reduce token usage while preserving essential information',
          inputSchema: {
            type: 'object',
            properties: {
              conversation_id: {
                type: 'string',
                description: 'UUID of the conversation to compress',
              },
              strategy: {
                type: 'string',
                enum: ['summarize', 'remove_old', 'compress_similar', 'smart'],
                description: 'Compression strategy (default: smart)',
              },
              target_ratio: {
                type: 'number',
                description: 'Target compression ratio 0.1-0.9 (default: 0.5)',
              },
              preserve_recent: {
                type: 'number',
                description: 'Number of recent messages to preserve (default: 5)',
              },
            },
            required: ['conversation_id'],
          },
        },
        {
          name: 'count_tokens',
          description: 'Count tokens for text, messages, or conversations with multi-LLM support and optimization recommendations',
          inputSchema: {
            type: 'object',
            properties: {
              input: {
                description: 'Text string, array of messages, or structured data to count',
              },
              model: {
                type: 'string',
                description: 'LLM model for token counting (default: claude-3-5-sonnet)',
              },
              include_recommendations: {
                type: 'boolean',
                description: 'Include optimization recommendations (default: true)',
              },
              conversation_id: {
                type: 'string',
                description: 'Optional conversation ID for context',
              },
            },
            required: ['input'],
          },
        },
        {
          name: 'smart_cache',
          description: 'Intelligent caching for prompts and contexts with automatic reuse detection to save tokens',
          inputSchema: {
            type: 'object',
            properties: {
              action: {
                type: 'string',
                enum: ['store', 'retrieve', 'check', 'stats', 'clear'],
                description: 'Cache operation to perform',
              },
              key: {
                type: 'string',
                description: 'Cache key (optional for store, required for retrieve)',
              },
              content: {
                type: 'string',
                description: 'Content to cache (required for store/check)',
              },
              model: {
                type: 'string',
                description: 'Model for token counting (default: claude-3-5-sonnet)',
              },
              ttl: {
                type: 'number',
                description: 'Time to live in milliseconds',
              },
              prefix: {
                type: 'string',
                description: 'Cache key prefix for organization',
              },
            },
            required: ['action'],
          },
        },
        {
          name: 'track_references',
          description: 'Track and manage reference materials (files, URLs, code snippets, notes) with token counting',
          inputSchema: {
            type: 'object',
            properties: {
              action: {
                type: 'string',
                enum: ['add', 'get', 'list', 'delete', 'search'],
                description: 'Reference operation to perform',
              },
              conversation_id: {
                type: 'string',
                description: 'Conversation UUID (required for add)',
              },
              reference_id: {
                type: 'string',
                description: 'Reference UUID (required for get/delete)',
              },
              type: {
                type: 'string',
                enum: ['file', 'url', 'code', 'note', 'document'],
                description: 'Type of reference',
              },
              title: {
                type: 'string',
                description: 'Reference title (required for add)',
              },
              content: {
                type: 'string',
                description: 'Reference content (required for add)',
              },
              metadata: {
                type: 'object',
                description: 'Additional metadata',
              },
              search_query: {
                type: 'string',
                description: 'Search query (required for search)',
              },
            },
            required: ['action'],
          },
        },
        {
          name: 'optimize_query',
          description: 'Analyze and optimize queries for better token efficiency and clarity',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'Query text to optimize',
              },
              context: {
                type: 'string',
                description: 'Optional context for combined analysis',
              },
              model: {
                type: 'string',
                description: 'Model for token counting (default: claude-3-5-sonnet)',
              },
              optimization_goal: {
                type: 'string',
                enum: ['reduce_tokens', 'improve_clarity', 'both'],
                description: 'Optimization goal (default: both)',
              },
              max_tokens: {
                type: 'number',
                description: 'Maximum token constraint',
              },
            },
            required: ['query'],
          },
        },
      ],
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        const { name, arguments: args } = request.params;

        switch (name) {
          case 'manage_conversation': {
            const validated = ManageConversationInputSchema.parse(args);
            const result = await manageConversation(validated);
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(result, null, 2),
                },
              ],
            };
          }

          case 'compress_context': {
            const validated = CompressContextInputSchema.parse(args);
            const result = await compressContext(validated);
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(result, null, 2),
                },
              ],
            };
          }

          case 'count_tokens': {
            const validated = CountTokensInputSchema.parse(args);
            const result = await countTokensTool(validated);
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(result, null, 2),
                },
              ],
            };
          }

          case 'smart_cache': {
            const validated = SmartCacheInputSchema.parse(args);
            const result = await smartCache(validated);
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(result, null, 2),
                },
              ],
            };
          }

          case 'track_references': {
            const validated = TrackReferencesInputSchema.parse(args);
            const result = await trackReferences(validated);
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(result, null, 2),
                },
              ],
            };
          }

          case 'optimize_query': {
            const validated = OptimizeQueryInputSchema.parse(args);
            const result = await optimizeQuery(validated);
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(result, null, 2),
                },
              ],
            };
          }

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error: any) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                success: false,
                error: error.message || 'Unknown error',
              }, null, 2),
            },
          ],
          isError: true,
        };
      }
    });

    // List available resources
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => ({
      resources: [
        {
          uri: 'conversation-history://all',
          name: 'All Conversations',
          description: 'List all conversations with token metadata',
          mimeType: 'application/json',
        },
        {
          uri: 'conversation-history://{conversation_id}',
          name: 'Conversation History',
          description: 'Detailed history of a specific conversation',
          mimeType: 'application/json',
        },
        {
          uri: 'token-stats://aggregate',
          name: 'Aggregate Token Statistics',
          description: 'Overall token usage statistics across all conversations',
          mimeType: 'application/json',
        },
        {
          uri: 'token-stats://{conversation_id}',
          name: 'Conversation Token Stats',
          description: 'Token statistics for a specific conversation',
          mimeType: 'application/json',
        },
        {
          uri: 'cache-stats://current',
          name: 'Cache Statistics',
          description: 'Cache performance and usage statistics',
          mimeType: 'application/json',
        },
        {
          uri: 'optimization-tips://general',
          name: 'General Optimization Tips',
          description: 'General tips for token optimization',
          mimeType: 'application/json',
        },
        {
          uri: 'optimization-tips://{conversation_id}',
          name: 'Conversation Optimization Tips',
          description: 'Context-specific optimization recommendations',
          mimeType: 'application/json',
        },
        {
          uri: 'reference-library://all',
          name: 'All References',
          description: 'Library of all tracked reference materials',
          mimeType: 'application/json',
        },
        {
          uri: 'reference-library://{conversation_id}',
          name: 'Conversation References',
          description: 'References for a specific conversation',
          mimeType: 'application/json',
        },
      ],
    }));

    // Handle resource reads
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      try {
        const { uri } = request.params;
        const [scheme, path] = uri.split('://');

        let content: string;

        switch (scheme) {
          case 'conversation-history':
            if (path === 'all') {
              content = await getConversationHistory({});
            } else {
              content = await getConversationHistory({ conversation_id: path });
            }
            break;

          case 'token-stats':
            if (path === 'aggregate') {
              content = await getTokenStats({});
            } else {
              content = await getTokenStats({ conversation_id: path });
            }
            break;

          case 'cache-stats':
            content = await getCacheStats();
            break;

          case 'optimization-tips':
            if (path === 'general') {
              content = await getOptimizationTips({});
            } else {
              content = await getOptimizationTips({ conversation_id: path });
            }
            break;

          case 'reference-library':
            if (path === 'all') {
              content = await getReferenceLibrary({});
            } else {
              content = await getReferenceLibrary({ conversation_id: path });
            }
            break;

          default:
            throw new Error(`Unknown resource scheme: ${scheme}`);
        }

        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: content,
            },
          ],
        };
      } catch (error: any) {
        throw new Error(`Error reading resource: ${error.message}`);
      }
    });

    // List available prompts
    this.server.setRequestHandler(ListPromptsRequestSchema, async () => ({
      prompts: [
        {
          name: 'summarize_context',
          description: 'Generate a comprehensive summary of conversation context',
          arguments: [
            {
              name: 'conversation_id',
              description: 'UUID of conversation to summarize (optional)',
              required: false,
            },
            {
              name: 'focus',
              description: 'Specific aspect to focus on in summary',
              required: false,
            },
            {
              name: 'max_summary_tokens',
              description: 'Maximum tokens for the summary',
              required: false,
            },
          ],
        },
        {
          name: 'compress_conversation',
          description: 'Generate a compressed version of conversation while preserving essentials',
          arguments: [
            {
              name: 'conversation_id',
              description: 'UUID of conversation to compress',
              required: true,
            },
            {
              name: 'target_reduction_percent',
              description: 'Target reduction percentage (default: 50)',
              required: false,
            },
            {
              name: 'preserve_recent_count',
              description: 'Number of recent messages to preserve (default: 5)',
              required: false,
            },
          ],
        },
        {
          name: 'extract_essentials',
          description: 'Extract only essential information from context (facts, code, decisions, etc.)',
          arguments: [
            {
              name: 'conversation_id',
              description: 'UUID of conversation to extract from (optional)',
              required: false,
            },
            {
              name: 'content',
              description: 'Direct content to extract from (optional)',
              required: false,
            },
            {
              name: 'extract_type',
              description: 'Type of extraction: facts, code, decisions, questions, or all (default: all)',
              required: false,
            },
            {
              name: 'model',
              description: 'Model for token counting (default: claude-3-5-sonnet)',
              required: false,
            },
          ],
        },
      ],
    }));

    // Handle prompt requests
    this.server.setRequestHandler(GetPromptRequestSchema, async (request) => {
      try {
        const { name, arguments: args } = request.params;

        let prompt: string;

        switch (name) {
          case 'summarize_context':
            prompt = await generateSummarizePrompt(args || {});
            break;

          case 'compress_conversation':
            if (!args?.conversation_id) {
              throw new Error('conversation_id is required for compress_conversation');
            }
            prompt = await generateCompressPrompt(args as any);
            break;

          case 'extract_essentials':
            prompt = await generateExtractPrompt(args || {});
            break;

          default:
            throw new Error(`Unknown prompt: ${name}`);
        }

        return {
          messages: [
            {
              role: 'user',
              content: {
                type: 'text',
                text: prompt,
              },
            },
          ],
        };
      } catch (error: any) {
        throw new Error(`Error generating prompt: ${error.message}`);
      }
    });
  }

  /**
   * Setup error handling and cleanup
   */
  private setupErrorHandling(): void {
    // Cleanup on exit
    const cleanup = () => {
      console.error('Shutting down server...');
      closeDatabase();
      process.exit(0);
    };

    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);

    // Handle uncaught errors
    process.on('uncaughtException', (error) => {
      console.error('Uncaught exception:', error);
      cleanup();
    });

    process.on('unhandledRejection', (reason) => {
      console.error('Unhandled rejection:', reason);
      cleanup();
    });
  }

  /**
   * Start the server
   */
  async start(): Promise<void> {
    try {
      // Initialize database
      getDatabase();
      console.error('Database initialized');

      // Create transport
      const transport = new StdioServerTransport();
      console.error('Transport created');

      // Connect server to transport
      await this.server.connect(transport);
      console.error(`${this.config.server.name} v${this.config.server.version} running on stdio`);
    } catch (error) {
      console.error('Failed to start server:', error);
      process.exit(1);
    }
  }
}

/**
 * Main entry point
 */
async function main() {
  const server = new TokenOptimizerServer();
  await server.start();
}

// Run the server
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
