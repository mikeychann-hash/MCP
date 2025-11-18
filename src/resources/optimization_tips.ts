/**
 * Resource: optimization-tips
 * Provides contextual tips for token optimization
 */

import { getDatabase } from '../storage/database.js';
import { countMessageTokens, calculateTokenPercentage } from '../utils/tokenizer.js';
import { getCache } from '../utils/cache.js';

export interface OptimizationTipsParams {
  conversation_id?: string;
  model?: string;
}

/**
 * Generate optimization tips based on current state
 */
function generateTips(context: {
  hasConversations: boolean;
  totalTokens: number;
  messageCount: number;
  model: string;
  cacheHitRate: number;
  hasCompressedMessages: boolean;
}): Array<{
  category: string;
  priority: 'high' | 'medium' | 'low';
  tip: string;
  action: string;
}> {
  const tips: Array<any> = [];
  const tokenPercentage = calculateTokenPercentage(context.totalTokens, context.model);

  // Token usage tips
  if (tokenPercentage > 75) {
    tips.push({
      category: 'token_management',
      priority: 'high',
      tip: 'Token usage is approaching model limit',
      action: 'Use compress_context tool to reduce token count',
    });
  } else if (tokenPercentage > 50) {
    tips.push({
      category: 'token_management',
      priority: 'medium',
      tip: 'Token usage is moderate',
      action: 'Consider summarizing older messages to free up context',
    });
  }

  // Message count tips
  if (context.messageCount > 50) {
    tips.push({
      category: 'conversation_length',
      priority: 'medium',
      tip: 'Conversation has many messages',
      action: 'Use compress_context with "remove_old" strategy',
    });
  }

  // Cache tips
  if (context.cacheHitRate < 20 && context.hasConversations) {
    tips.push({
      category: 'caching',
      priority: 'medium',
      tip: 'Cache hit rate is low',
      action: 'Use smart_cache to store frequently used prompts',
    });
  } else if (context.cacheHitRate > 50) {
    tips.push({
      category: 'caching',
      priority: 'low',
      tip: 'Cache is performing well',
      action: 'Continue using cached prompts for token savings',
    });
  }

  // Compression tips
  if (!context.hasCompressedMessages && context.messageCount > 20) {
    tips.push({
      category: 'compression',
      priority: 'medium',
      tip: 'No messages have been compressed yet',
      action: 'Try compress_context to reduce token usage',
    });
  }

  // General best practices
  tips.push({
    category: 'best_practices',
    priority: 'low',
    tip: 'Use optimize_query before sending long prompts',
    action: 'Optimize queries to remove filler words and improve clarity',
  });

  tips.push({
    category: 'best_practices',
    priority: 'low',
    tip: 'Track reference materials separately',
    action: 'Use track_references for code snippets, docs, and URLs',
  });

  if (tokenPercentage < 30) {
    tips.push({
      category: 'efficiency',
      priority: 'low',
      tip: 'Token usage is healthy',
      action: 'Continue current practices',
    });
  }

  return tips;
}

/**
 * Get optimization tips resource
 */
export async function getOptimizationTips(
  params: OptimizationTipsParams = {}
): Promise<string> {
  const db = getDatabase();
  const cache = getCache();
  const cacheStats = cache.getStats();

  if (params.conversation_id) {
    // Tips for specific conversation
    const conversation = db.getConversation(params.conversation_id);
    if (!conversation) {
      return JSON.stringify({
        error: 'Conversation not found',
      }, null, 2);
    }

    const messages = db.getMessages(params.conversation_id);
    const hasCompressed = messages.some(m => m.is_compressed);

    const actualTokens = countMessageTokens(
      messages.map(m => ({ role: m.role, content: m.content })),
      conversation.model
    ).tokens;

    const tips = generateTips({
      hasConversations: true,
      totalTokens: actualTokens,
      messageCount: messages.length,
      model: conversation.model,
      cacheHitRate: cacheStats.hitRate,
      hasCompressedMessages: hasCompressed,
    });

    return JSON.stringify({
      conversation: {
        id: conversation.id,
        title: conversation.title,
        model: conversation.model,
        current_tokens: actualTokens,
        message_count: messages.length,
      },
      tips: tips,
    }, null, 2);
  } else {
    // General tips
    const conversations = db.getAllConversations();
    const totalMessages = conversations.reduce((sum, c) => sum + c.message_count, 0);
    const totalTokens = conversations.reduce((sum, c) => sum + c.total_tokens, 0);
    const model = params.model || 'claude-3-5-sonnet';

    // Check if any messages are compressed
    let hasCompressed = false;
    for (const conv of conversations.slice(0, 10)) { // Check first 10
      const messages = db.getMessages(conv.id);
      if (messages.some(m => m.is_compressed)) {
        hasCompressed = true;
        break;
      }
    }

    const tips = generateTips({
      hasConversations: conversations.length > 0,
      totalTokens: totalTokens,
      messageCount: totalMessages,
      model: model,
      cacheHitRate: cacheStats.hitRate,
      hasCompressedMessages: hasCompressed,
    });

    return JSON.stringify({
      overview: {
        total_conversations: conversations.length,
        total_messages: totalMessages,
        total_tokens: totalTokens,
        cache_hit_rate: cacheStats.hitRate,
      },
      tips: tips,
      resources: {
        documentation: 'See MCP server documentation for detailed guides',
        tools_available: [
          'manage_conversation',
          'compress_context',
          'count_tokens',
          'smart_cache',
          'track_references',
          'optimize_query',
        ],
      },
    }, null, 2);
  }
}

/**
 * Get optimization tips URI
 */
export function getOptimizationTipsUri(conversationId?: string): string {
  if (conversationId) {
    return `optimization-tips://${conversationId}`;
  }
  return 'optimization-tips://general';
}
