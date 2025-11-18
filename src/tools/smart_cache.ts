/**
 * Tool: smart_cache
 * Intelligent caching for prompts and contexts with automatic reuse detection
 */

import { z } from 'zod';
import { getPromptCache } from '../utils/cache.js';
import { countTokens } from '../utils/tokenizer.js';
import crypto from 'crypto';

export const SmartCacheInputSchema = z.object({
  action: z.enum(['store', 'retrieve', 'check', 'stats', 'clear']),
  key: z.string().optional(),
  content: z.string().optional(),
  model: z.string().default('claude-3-5-sonnet'),
  ttl: z.number().positive().optional(), // TTL in milliseconds
  prefix: z.string().optional(),
});

export type SmartCacheInput = z.infer<typeof SmartCacheInputSchema>;

/**
 * Smart caching operations
 */
export async function smartCache(input: SmartCacheInput): Promise<any> {
  const cache = getPromptCache();

  switch (input.action) {
    case 'store': {
      if (!input.content) {
        return {
          success: false,
          error: 'Content is required for store action',
        };
      }

      // Generate key if not provided
      const key = input.key || crypto.createHash('sha256')
        .update(input.content)
        .digest('hex')
        .substring(0, 16);

      // Count tokens
      const tokens = countTokens(input.content, input.model).tokens;

      // Store in cache
      await cache.set(
        key,
        {
          content: input.content,
          model: input.model,
          tokens,
          stored_at: Date.now(),
        },
        {
          prefix: input.prefix || 'smart',
          ttl: input.ttl,
          model: input.model,
        }
      );

      return {
        success: true,
        action: 'store',
        key,
        tokens,
        message: 'Content cached successfully',
      };
    }

    case 'retrieve': {
      if (!input.key) {
        return {
          success: false,
          error: 'Key is required for retrieve action',
        };
      }

      const result = await cache.get(input.key, {
        prefix: input.prefix || 'smart',
      });

      if (result.hit && result.value) {
        return {
          success: true,
          action: 'retrieve',
          from_cache: true,
          tokens_saved: result.tokensSaved,
          content: result.value.content,
          model: result.value.model,
          tokens: result.value.tokens,
          stored_at: result.value.stored_at,
        };
      } else {
        return {
          success: false,
          action: 'retrieve',
          from_cache: false,
          error: 'Content not found in cache',
        };
      }
    }

    case 'check': {
      if (!input.content) {
        return {
          success: false,
          error: 'Content is required for check action',
        };
      }

      // Generate hash of content
      const hash = crypto.createHash('sha256')
        .update(input.content)
        .digest('hex')
        .substring(0, 16);

      const result = await cache.get(hash, {
        prefix: input.prefix || 'smart',
      });

      return {
        success: true,
        action: 'check',
        is_cached: result.hit,
        key: hash,
        tokens_saved: result.hit ? result.tokensSaved : 0,
      };
    }

    case 'stats': {
      const stats = cache.getStats();

      return {
        success: true,
        action: 'stats',
        cache_stats: {
          total_entries: stats.entries,
          total_hits: stats.hits,
          tokens_saved: stats.tokensSaved,
          hit_rate_percent: stats.hitRate,
        },
        message: `Cache contains ${stats.entries} entries with ${stats.hits} total hits`,
      };
    }

    case 'clear': {
      await cache.clear();

      return {
        success: true,
        action: 'clear',
        message: 'Cache cleared successfully',
      };
    }

    default:
      return {
        success: false,
        error: 'Invalid action',
      };
  }
}
