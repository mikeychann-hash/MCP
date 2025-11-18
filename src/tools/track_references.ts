/**
 * Tool: track_references
 * Track and manage reference materials (files, URLs, code snippets, notes)
 */

import { z } from 'zod';
import { getDatabase } from '../storage/database.js';
import { countTokens } from '../utils/tokenizer.js';
import crypto from 'crypto';

export const TrackReferencesInputSchema = z.object({
  action: z.enum(['add', 'get', 'list', 'delete', 'search']),
  conversation_id: z.string().uuid().optional(),
  reference_id: z.string().uuid().optional(),
  type: z.enum(['file', 'url', 'code', 'note', 'document']).optional(),
  title: z.string().optional(),
  content: z.string().optional(),
  metadata: z.record(z.any()).optional(),
  search_query: z.string().optional(),
});

export type TrackReferencesInput = z.infer<typeof TrackReferencesInputSchema>;

/**
 * Track references tool
 */
export async function trackReferences(input: TrackReferencesInput): Promise<any> {
  const db = getDatabase();

  switch (input.action) {
    case 'add': {
      if (!input.conversation_id || !input.type || !input.title || !input.content) {
        return {
          success: false,
          error: 'conversation_id, type, title, and content are required for add action',
        };
      }

      // Verify conversation exists
      const conversation = db.getConversation(input.conversation_id);
      if (!conversation) {
        return {
          success: false,
          error: 'Conversation not found',
        };
      }

      // Count tokens
      const tokens = countTokens(input.content, conversation.model).tokens;

      // Create reference
      const reference = db.addReference({
        id: crypto.randomUUID(),
        conversation_id: input.conversation_id,
        type: input.type,
        title: input.title,
        content: input.content,
        tokens,
        metadata: input.metadata ? JSON.stringify(input.metadata) : undefined,
      });

      return {
        success: true,
        action: 'add',
        reference: {
          id: reference.id,
          type: reference.type,
          title: reference.title,
          tokens: reference.tokens,
          created_at: reference.created_at,
        },
        message: `Reference "${input.title}" added successfully`,
      };
    }

    case 'get': {
      if (!input.reference_id) {
        return {
          success: false,
          error: 'reference_id is required for get action',
        };
      }

      const references = db.getAllReferences();
      const reference = references.find(r => r.id === input.reference_id);

      if (!reference) {
        return {
          success: false,
          error: 'Reference not found',
        };
      }

      return {
        success: true,
        action: 'get',
        reference: {
          id: reference.id,
          conversation_id: reference.conversation_id,
          type: reference.type,
          title: reference.title,
          content: reference.content,
          tokens: reference.tokens,
          created_at: reference.created_at,
          metadata: reference.metadata ? JSON.parse(reference.metadata) : undefined,
        },
      };
    }

    case 'list': {
      let references;

      if (input.conversation_id) {
        references = db.getReferences(input.conversation_id);
      } else {
        references = db.getAllReferences();
      }

      // Filter by type if specified
      if (input.type) {
        references = references.filter(r => r.type === input.type);
      }

      // Calculate total tokens
      const totalTokens = references.reduce((sum, r) => sum + r.tokens, 0);

      return {
        success: true,
        action: 'list',
        references: references.map(r => ({
          id: r.id,
          conversation_id: r.conversation_id,
          type: r.type,
          title: r.title,
          tokens: r.tokens,
          created_at: r.created_at,
          preview: r.content.substring(0, 100) + (r.content.length > 100 ? '...' : ''),
        })),
        total_count: references.length,
        total_tokens: totalTokens,
      };
    }

    case 'delete': {
      if (!input.reference_id) {
        return {
          success: false,
          error: 'reference_id is required for delete action',
        };
      }

      db.deleteReference(input.reference_id);

      return {
        success: true,
        action: 'delete',
        message: 'Reference deleted successfully',
      };
    }

    case 'search': {
      if (!input.search_query) {
        return {
          success: false,
          error: 'search_query is required for search action',
        };
      }

      let references;
      if (input.conversation_id) {
        references = db.getReferences(input.conversation_id);
      } else {
        references = db.getAllReferences();
      }

      // Simple search in title and content
      const query = input.search_query.toLowerCase();
      const matches = references.filter(r =>
        r.title.toLowerCase().includes(query) ||
        r.content.toLowerCase().includes(query)
      );

      return {
        success: true,
        action: 'search',
        query: input.search_query,
        matches: matches.map(r => ({
          id: r.id,
          conversation_id: r.conversation_id,
          type: r.type,
          title: r.title,
          tokens: r.tokens,
          created_at: r.created_at,
          preview: r.content.substring(0, 150) + (r.content.length > 150 ? '...' : ''),
        })),
        total_matches: matches.length,
      };
    }

    default:
      return {
        success: false,
        error: 'Invalid action',
      };
  }
}
