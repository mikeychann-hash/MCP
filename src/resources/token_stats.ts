/**
 * Resource: token-stats
 * Provides detailed token usage statistics
 */

import { getDatabase } from '../storage/database.js';

export interface TokenStatsParams {
  conversation_id?: string;
  time_range?: 'day' | 'week' | 'month' | 'all';
}

/**
 * Get token statistics resource
 */
export async function getTokenStats(
  params: TokenStatsParams = {}
): Promise<string> {
  const db = getDatabase();

  // Calculate time range
  let since = 0;
  if (params.time_range) {
    const now = Date.now();
    switch (params.time_range) {
      case 'day':
        since = now - 24 * 60 * 60 * 1000;
        break;
      case 'week':
        since = now - 7 * 24 * 60 * 60 * 1000;
        break;
      case 'month':
        since = now - 30 * 24 * 60 * 60 * 1000;
        break;
      default:
        since = 0;
    }
  }

  if (params.conversation_id) {
    // Get stats for specific conversation
    const conversation = db.getConversation(params.conversation_id);
    if (!conversation) {
      return JSON.stringify({
        error: 'Conversation not found',
      }, null, 2);
    }

    const stats = db.getTokenStats(params.conversation_id)
      .filter(s => s.timestamp >= since);

    const total_input = stats.reduce((sum, s) => sum + s.input_tokens, 0);
    const total_output = stats.reduce((sum, s) => sum + s.output_tokens, 0);
    const total_cached = stats.reduce((sum, s) => sum + s.cached_tokens, 0);

    return JSON.stringify({
      conversation: {
        id: conversation.id,
        title: conversation.title,
        model: conversation.model,
      },
      time_range: params.time_range || 'all',
      statistics: {
        total_input_tokens: total_input,
        total_output_tokens: total_output,
        total_cached_tokens: total_cached,
        total_tokens: total_input + total_output,
        net_tokens: total_input + total_output - total_cached,
        cache_savings_percent: total_input > 0
          ? Math.round((total_cached / total_input) * 100)
          : 0,
        request_count: stats.length,
      },
      history: stats.map(s => ({
        timestamp: new Date(s.timestamp).toISOString(),
        input_tokens: s.input_tokens,
        output_tokens: s.output_tokens,
        cached_tokens: s.cached_tokens,
        model: s.model,
      })),
    }, null, 2);
  } else {
    // Get aggregate stats
    const aggStats = db.getAggregateTokenStats();

    // Get per-model breakdown
    const conversations = db.getAllConversations();
    const byModel = conversations.reduce((acc, c) => {
      if (!acc[c.model]) {
        acc[c.model] = {
          conversation_count: 0,
          total_tokens: 0,
          message_count: 0,
        };
      }
      acc[c.model].conversation_count++;
      acc[c.model].total_tokens += c.total_tokens;
      acc[c.model].message_count += c.message_count;
      return acc;
    }, {} as Record<string, any>);

    return JSON.stringify({
      time_range: params.time_range || 'all',
      aggregate: {
        total_input_tokens: aggStats.total_input,
        total_output_tokens: aggStats.total_output,
        total_cached_tokens: aggStats.total_cached,
        total_requests: aggStats.total_requests,
        net_tokens: aggStats.total_input + aggStats.total_output - aggStats.total_cached,
        cache_efficiency_percent: aggStats.total_input > 0
          ? Math.round((aggStats.total_cached / aggStats.total_input) * 100)
          : 0,
      },
      by_model: byModel,
      conversation_count: conversations.length,
    }, null, 2);
  }
}

/**
 * Get token stats URI
 */
export function getTokenStatsUri(conversationId?: string): string {
  if (conversationId) {
    return `token-stats://${conversationId}`;
  }
  return 'token-stats://aggregate';
}
