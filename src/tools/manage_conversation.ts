/**
 * Tool: manage_conversation
 * Create, update, retrieve, and delete conversations with token tracking
 */

import { z } from 'zod';
import { getDatabase } from '../storage/database.js';
import { countTokens, countMessageTokens } from '../utils/tokenizer.js';
import crypto from 'crypto';

// Input schemas
const CreateConversationSchema = z.object({
  action: z.literal('create'),
  title: z.string().min(1),
  model: z.string().default('claude-3-5-sonnet'),
  metadata: z.record(z.any()).optional(),
});

const AddMessageSchema = z.object({
  action: z.literal('add_message'),
  conversation_id: z.string().uuid(),
  role: z.enum(['user', 'assistant', 'system']),
  content: z.string().min(1),
});

const GetConversationSchema = z.object({
  action: z.literal('get'),
  conversation_id: z.string().uuid(),
  include_messages: z.boolean().default(true),
});

const ListConversationsSchema = z.object({
  action: z.literal('list'),
  limit: z.number().int().positive().default(20),
});

const DeleteConversationSchema = z.object({
  action: z.literal('delete'),
  conversation_id: z.string().uuid(),
});

export const ManageConversationInputSchema = z.discriminatedUnion('action', [
  CreateConversationSchema,
  AddMessageSchema,
  GetConversationSchema,
  ListConversationsSchema,
  DeleteConversationSchema,
]);

export type ManageConversationInput = z.infer<typeof ManageConversationInputSchema>;

/**
 * Handle conversation management operations
 */
export async function manageConversation(input: ManageConversationInput): Promise<any> {
  const db = getDatabase();

  switch (input.action) {
    case 'create': {
      const id = crypto.randomUUID();
      const conversation = db.createConversation({
        id,
        title: input.title,
        model: input.model,
        total_tokens: 0,
        message_count: 0,
        metadata: input.metadata ? JSON.stringify(input.metadata) : undefined,
      });

      return {
        success: true,
        conversation: {
          id: conversation.id,
          title: conversation.title,
          model: conversation.model,
          created_at: conversation.created_at,
          total_tokens: conversation.total_tokens,
          message_count: conversation.message_count,
        },
        message: `Conversation "${input.title}" created successfully`,
      };
    }

    case 'add_message': {
      const conversation = db.getConversation(input.conversation_id);
      if (!conversation) {
        return {
          success: false,
          error: 'Conversation not found',
        };
      }

      // Count tokens in the message
      const tokenCount = countTokens(input.content, conversation.model);

      // Add message to database
      const message = db.addMessage({
        id: crypto.randomUUID(),
        conversation_id: input.conversation_id,
        role: input.role,
        content: input.content,
        tokens: tokenCount.tokens,
        is_compressed: false,
      });

      // Get updated conversation stats
      const updatedConversation = db.getConversation(input.conversation_id)!;

      return {
        success: true,
        message: {
          id: message.id,
          role: message.role,
          tokens: message.tokens,
          created_at: message.created_at,
        },
        conversation: {
          total_tokens: updatedConversation.total_tokens,
          message_count: updatedConversation.message_count,
        },
      };
    }

    case 'get': {
      const conversation = db.getConversation(input.conversation_id);
      if (!conversation) {
        return {
          success: false,
          error: 'Conversation not found',
        };
      }

      const result: any = {
        success: true,
        conversation: {
          id: conversation.id,
          title: conversation.title,
          model: conversation.model,
          created_at: conversation.created_at,
          updated_at: conversation.updated_at,
          total_tokens: conversation.total_tokens,
          message_count: conversation.message_count,
          metadata: conversation.metadata ? JSON.parse(conversation.metadata) : undefined,
        },
      };

      if (input.include_messages) {
        const messages = db.getMessages(input.conversation_id);
        result.messages = messages.map(m => ({
          id: m.id,
          role: m.role,
          content: m.content,
          tokens: m.tokens,
          is_compressed: m.is_compressed,
          created_at: m.created_at,
        }));

        // Calculate total tokens from messages
        const totalTokens = countMessageTokens(
          messages.map(m => ({ role: m.role, content: m.content })),
          conversation.model
        );
        result.actual_tokens = totalTokens.tokens;
      }

      return result;
    }

    case 'list': {
      const conversations = db.getAllConversations();
      const limited = conversations.slice(0, input.limit);

      return {
        success: true,
        conversations: limited.map(c => ({
          id: c.id,
          title: c.title,
          model: c.model,
          created_at: c.created_at,
          updated_at: c.updated_at,
          total_tokens: c.total_tokens,
          message_count: c.message_count,
        })),
        total: conversations.length,
        showing: limited.length,
      };
    }

    case 'delete': {
      const conversation = db.getConversation(input.conversation_id);
      if (!conversation) {
        return {
          success: false,
          error: 'Conversation not found',
        };
      }

      db.deleteConversation(input.conversation_id);

      return {
        success: true,
        message: `Conversation "${conversation.title}" deleted successfully`,
      };
    }

    default:
      return {
        success: false,
        error: 'Invalid action',
      };
  }
}
