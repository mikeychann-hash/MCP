/**
 * Resource: conversation-history
 * Provides access to conversation history with token metadata
 */

import { getDatabase } from '../storage/database.js';
import { countMessageTokens } from '../utils/tokenizer.js';

export interface ConversationHistoryParams {
  conversation_id?: string;
  limit?: number;
  include_tokens?: boolean;
}

/**
 * Get conversation history resource
 */
export async function getConversationHistory(
  params: ConversationHistoryParams = {}
): Promise<string> {
  const db = getDatabase();
  const limit = params.limit || 50;
  const includeTokens = params.include_tokens !== false;

  if (params.conversation_id) {
    // Get specific conversation
    const conversation = db.getConversation(params.conversation_id);
    if (!conversation) {
      return JSON.stringify({
        error: 'Conversation not found',
      }, null, 2);
    }

    const messages = db.getMessages(params.conversation_id);

    // Calculate actual token count
    let actualTokens = 0;
    if (includeTokens && messages.length > 0) {
      actualTokens = countMessageTokens(
        messages.map(m => ({ role: m.role, content: m.content })),
        conversation.model
      ).tokens;
    }

    return JSON.stringify({
      conversation: {
        id: conversation.id,
        title: conversation.title,
        model: conversation.model,
        created_at: new Date(conversation.created_at).toISOString(),
        updated_at: new Date(conversation.updated_at).toISOString(),
        total_tokens: conversation.total_tokens,
        actual_tokens: actualTokens,
        message_count: conversation.message_count,
      },
      messages: messages.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        tokens: m.tokens,
        is_compressed: m.is_compressed,
        created_at: new Date(m.created_at).toISOString(),
      })),
    }, null, 2);
  } else {
    // Get all conversations
    const conversations = db.getAllConversations().slice(0, limit);

    return JSON.stringify({
      conversations: conversations.map(c => ({
        id: c.id,
        title: c.title,
        model: c.model,
        created_at: new Date(c.created_at).toISOString(),
        updated_at: new Date(c.updated_at).toISOString(),
        total_tokens: c.total_tokens,
        message_count: c.message_count,
      })),
      total: conversations.length,
    }, null, 2);
  }
}

/**
 * Get conversation history URI
 */
export function getConversationHistoryUri(conversationId?: string): string {
  if (conversationId) {
    return `conversation-history://${conversationId}`;
  }
  return 'conversation-history://all';
}
