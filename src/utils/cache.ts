/**
 * Intelligent Caching Layer
 * Manages prompt caching and context reuse with LRU eviction
 */

import { getDatabase } from '../storage/database.js';
import { getConfig } from '../config/index.js';
import { countTokens } from './tokenizer.js';
import crypto from 'crypto';

export interface CacheOptions {
  ttl?: number; // Time to live in milliseconds
  prefix?: string; // Cache key prefix
  model?: string; // Model for token counting
}

export interface CacheResult<T> {
  hit: boolean;
  value: T | null;
  tokensSaved: number;
}

/**
 * Cache Manager Class
 */
export class CacheManager {
  private config = getConfig();
  private db = getDatabase();

  /**
   * Generate cache key from input
   */
  protected generateKey(input: any, prefix: string = ''): string {
    const normalized = typeof input === 'string' ? input : JSON.stringify(input);
    const hash = crypto.createHash('sha256').update(normalized).digest('hex');
    return prefix ? `${prefix}:${hash}` : hash;
  }

  /**
   * Get item from cache
   */
  async get<T = any>(
    key: string,
    options: CacheOptions = {}
  ): Promise<CacheResult<T>> {
    if (!this.config.cache.enabled) {
      return { hit: false, value: null, tokensSaved: 0 };
    }

    const fullKey = options.prefix ? `${options.prefix}:${key}` : key;
    const entry = this.db.getCacheEntry(fullKey);

    if (entry) {
      try {
        const value = JSON.parse(entry.value) as T;
        return {
          hit: true,
          value,
          tokensSaved: entry.tokens_saved,
        };
      } catch (error) {
        console.error('Error parsing cache entry:', error);
        return { hit: false, value: null, tokensSaved: 0 };
      }
    }

    return { hit: false, value: null, tokensSaved: 0 };
  }

  /**
   * Set item in cache
   */
  async set<T = any>(
    key: string,
    value: T,
    options: CacheOptions = {}
  ): Promise<void> {
    if (!this.config.cache.enabled) {
      return;
    }

    const fullKey = options.prefix ? `${options.prefix}:${key}` : key;
    const ttl = options.ttl || this.config.cache.ttl;
    const expiresAt = Date.now() + ttl;

    // Count tokens saved
    const valueStr = JSON.stringify(value);
    const tokens = countTokens(valueStr, options.model).tokens;

    this.db.addCacheEntry({
      id: crypto.randomUUID(),
      key: fullKey,
      value: valueStr,
      tokens_saved: tokens,
      hit_count: 0,
      expires_at: expiresAt,
    });

    // Clean up if cache is too large
    await this.evictIfNeeded();
  }

  /**
   * Get or compute value with caching
   */
  async getOrCompute<T = any>(
    key: string,
    compute: () => Promise<T> | T,
    options: CacheOptions = {}
  ): Promise<{ value: T; fromCache: boolean; tokensSaved: number }> {
    const cached = await this.get<T>(key, options);

    if (cached.hit && cached.value !== null) {
      return {
        value: cached.value,
        fromCache: true,
        tokensSaved: cached.tokensSaved,
      };
    }

    // Compute new value
    const value = await compute();
    await this.set(key, value, options);

    return {
      value,
      fromCache: false,
      tokensSaved: 0,
    };
  }

  /**
   * Cache function result based on arguments
   */
  memoize<Args extends any[], Result>(
    fn: (...args: Args) => Promise<Result> | Result,
    options: CacheOptions = {}
  ): (...args: Args) => Promise<{ value: Result; fromCache: boolean }> {
    return async (...args: Args) => {
      const key = this.generateKey(args, options.prefix);
      const result = await this.getOrCompute(key, () => fn(...args), options);
      return {
        value: result.value,
        fromCache: result.fromCache,
      };
    };
  }

  /**
   * Invalidate cache entry
   */
  async invalidate(key: string, prefix?: string): Promise<void> {
    const fullKey = prefix ? `${prefix}:${key}` : key;
    // Delete by setting expire time to past
    const entry = this.db.getCacheEntry(fullKey);
    if (entry) {
      this.db.addCacheEntry({
        ...entry,
        expires_at: 0,
      });
    }
  }

  /**
   * Clear all cache entries
   */
  async clear(): Promise<void> {
    const entries = this.db.getAllCacheEntries();
    for (const entry of entries) {
      this.db.addCacheEntry({
        ...entry,
        expires_at: 0,
      });
    }
  }

  /**
   * Clean expired entries
   */
  async cleanExpired(): Promise<number> {
    return this.db.cleanExpiredCache();
  }

  /**
   * Evict least recently used entries if cache is too large
   */
  private async evictIfNeeded(): Promise<void> {
    const entries = this.db.getAllCacheEntries();

    if (entries.length > this.config.cache.maxSize) {
      // Sort by last accessed (oldest first)
      entries.sort((a, b) => a.last_accessed - b.last_accessed);

      // Remove oldest entries
      const toRemove = entries.length - this.config.cache.maxSize;
      for (let i = 0; i < toRemove; i++) {
        const entry = entries[i]!;
        this.db.addCacheEntry({
          id: entry.id,
          key: entry.key,
          value: entry.value,
          tokens_saved: entry.tokens_saved,
          hit_count: entry.hit_count,
          expires_at: 0,
        });
      }
    }
  }

  /**
   * Get cache statistics
   */
  getStats(): {
    entries: number;
    hits: number;
    tokensSaved: number;
    hitRate: number;
  } {
    const stats = this.db.getCacheStats();
    const hitRate = stats.total_entries > 0
      ? (stats.total_hits / stats.total_entries) * 100
      : 0;

    return {
      entries: stats.total_entries,
      hits: stats.total_hits,
      tokensSaved: stats.tokens_saved,
      hitRate: Math.round(hitRate * 100) / 100,
    };
  }
}

/**
 * Prompt Cache Manager
 * Specialized caching for LLM prompts with prefix caching support
 */
export class PromptCacheManager extends CacheManager {
  /**
   * Cache a conversation context for reuse
   */
  async cacheConversationContext(
    conversationId: string,
    messages: Array<{ role: string; content: string }>,
    model: string = 'claude-3-5-sonnet'
  ): Promise<string> {
    const key = `conversation:${conversationId}`;
    await this.set(key, messages, {
      prefix: 'prompt',
      model,
      ttl: 7200000, // 2 hours
    });
    return key;
  }

  /**
   * Retrieve cached conversation context
   */
  async getCachedContext(
    conversationId: string
  ): Promise<CacheResult<Array<{ role: string; content: string }>>> {
    const key = `conversation:${conversationId}`;
    return await this.get(key, { prefix: 'prompt' });
  }

  /**
   * Cache a compressed version of context
   */
  async cacheCompressedContext(
    originalContext: string,
    compressed: string,
    model: string = 'claude-3-5-sonnet'
  ): Promise<void> {
    const key = this.generateKey(originalContext);
    await this.set(
      key,
      { original: originalContext, compressed },
      {
        prefix: 'compressed',
        model,
        ttl: 3600000, // 1 hour
      }
    );
  }

  /**
   * Get compressed context if available
   */
  async getCompressedContext(
    originalContext: string
  ): Promise<string | null> {
    const key = this.generateKey(originalContext);
    const result = await this.get<{ original: string; compressed: string }>(
      key,
      { prefix: 'compressed' }
    );
    return result.value?.compressed || null;
  }

  /**
   * Cache summarized content
   */
  async cacheSummary(
    content: string,
    summary: string,
    model: string = 'claude-3-5-sonnet'
  ): Promise<void> {
    const key = this.generateKey(content);
    await this.set(
      key,
      { content, summary },
      {
        prefix: 'summary',
        model,
        ttl: 7200000, // 2 hours
      }
    );
  }

  /**
   * Get cached summary
   */
  async getSummary(content: string): Promise<string | null> {
    const key = this.generateKey(content);
    const result = await this.get<{ content: string; summary: string }>(
      key,
      { prefix: 'summary' }
    );
    return result.value?.summary || null;
  }
}

// Singleton instances
let cacheInstance: CacheManager | null = null;
let promptCacheInstance: PromptCacheManager | null = null;

export function getCache(): CacheManager {
  if (!cacheInstance) {
    cacheInstance = new CacheManager();
  }
  return cacheInstance;
}

export function getPromptCache(): PromptCacheManager {
  if (!promptCacheInstance) {
    promptCacheInstance = new PromptCacheManager();
  }
  return promptCacheInstance;
}
