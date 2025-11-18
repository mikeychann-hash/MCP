/**
 * Resource: reference-library
 * Provides access to tracked reference materials
 */

import { getDatabase } from '../storage/database.js';

export interface ReferenceLibraryParams {
  conversation_id?: string;
  type?: string;
  limit?: number;
}

/**
 * Get reference library resource
 */
export async function getReferenceLibrary(
  params: ReferenceLibraryParams = {}
): Promise<string> {
  const db = getDatabase();
  const limit = params.limit || 100;

  let references;

  if (params.conversation_id) {
    references = db.getReferences(params.conversation_id);
  } else {
    references = db.getAllReferences();
  }

  // Filter by type if specified
  if (params.type) {
    references = references.filter(r => r.type === params.type);
  }

  // Limit results
  references = references.slice(0, limit);

  // Group by type
  const byType: Record<string, any[]> = {};
  references.forEach(ref => {
    if (!byType[ref.type]) {
      byType[ref.type] = [];
    }
    byType[ref.type]!.push(ref);
  });

  // Calculate statistics
  const totalTokens = references.reduce((sum, r) => sum + r.tokens, 0);
  const avgTokens = references.length > 0
    ? Math.round(totalTokens / references.length)
    : 0;

  // Get type distribution
  const typeStats = Object.entries(byType).map(([type, refs]) => ({
    type,
    count: refs.length,
    total_tokens: refs.reduce((sum: number, r: any) => sum + r.tokens, 0),
  }));

  return JSON.stringify({
    summary: {
      total_references: references.length,
      total_tokens: totalTokens,
      avg_tokens_per_reference: avgTokens,
      types: Object.keys(byType),
    },
    type_distribution: typeStats,
    references: references.map(r => ({
      id: r.id,
      conversation_id: r.conversation_id,
      type: r.type,
      title: r.title,
      tokens: r.tokens,
      created_at: new Date(r.created_at).toISOString(),
      preview: r.content.substring(0, 150) + (r.content.length > 150 ? '...' : ''),
      metadata: r.metadata ? JSON.parse(r.metadata) : undefined,
    })),
  }, null, 2);
}

/**
 * Get reference library URI
 */
export function getReferenceLibraryUri(conversationId?: string, type?: string): string {
  if (conversationId) {
    return `reference-library://${conversationId}${type ? `?type=${type}` : ''}`;
  }
  return `reference-library://all${type ? `?type=${type}` : ''}`;
}
