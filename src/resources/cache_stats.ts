/**
 * Resource: cache-stats
 * Provides cache performance and usage statistics
 */

import { getDatabase } from '../storage/database.js';
import { getCache } from '../utils/cache.js';

/**
 * Get cache statistics resource
 */
export async function getCacheStats(): Promise<string> {
  const db = getDatabase();
  const cache = getCache();

  // Get cache stats
  const stats = cache.getStats();

  // Get all cache entries
  const entries = db.getAllCacheEntries();

  // Group by prefix
  const byPrefix: Record<string, {
    count: number;
    total_hits: number;
    tokens_saved: number;
  }> = {};

  entries.forEach(entry => {
    const prefix = entry.key.split(':')[0] || 'default';
    if (!byPrefix[prefix]) {
      byPrefix[prefix] = {
        count: 0,
        total_hits: 0,
        tokens_saved: 0,
      };
    }
    byPrefix[prefix].count++;
    byPrefix[prefix].total_hits += entry.hit_count;
    byPrefix[prefix].tokens_saved += entry.tokens_saved;
  });

  // Get top entries by hit count
  const topEntries = [...entries]
    .sort((a, b) => b.hit_count - a.hit_count)
    .slice(0, 10)
    .map(e => ({
      key: e.key,
      hit_count: e.hit_count,
      tokens_saved: e.tokens_saved,
      created_at: new Date(e.created_at).toISOString(),
      last_accessed: new Date(e.last_accessed).toISOString(),
      expires_at: new Date(e.expires_at).toISOString(),
    }));

  // Calculate efficiency metrics
  const avgHitsPerEntry = stats.entries > 0
    ? Math.round(stats.hits / stats.entries)
    : 0;

  const avgTokensSavedPerHit = stats.hits > 0
    ? Math.round(stats.tokensSaved / stats.hits)
    : 0;

  return JSON.stringify({
    summary: {
      total_entries: stats.entries,
      total_hits: stats.hits,
      total_tokens_saved: stats.tokensSaved,
      hit_rate_percent: stats.hitRate,
      avg_hits_per_entry: avgHitsPerEntry,
      avg_tokens_saved_per_hit: avgTokensSavedPerHit,
    },
    by_prefix: byPrefix,
    top_entries: topEntries,
    performance: {
      cache_effectiveness: stats.hitRate > 50 ? 'excellent' :
                          stats.hitRate > 25 ? 'good' :
                          stats.hitRate > 10 ? 'fair' : 'poor',
      recommendation: stats.hitRate < 10
        ? 'Consider reviewing cache strategy and TTL settings'
        : stats.hitRate > 50
        ? 'Cache is performing well'
        : 'Cache performance is acceptable',
    },
  }, null, 2);
}

/**
 * Get cache stats URI
 */
export function getCacheStatsUri(): string {
  return 'cache-stats://current';
}
