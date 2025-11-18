/**
 * Database Layer - SQLite3 Storage
 * Manages conversations, token stats, cache entries, and reference items
 */

import Database from 'better-sqlite3';
import { getConfig } from '../config/index.js';
import fs from 'fs';
import path from 'path';

export interface Conversation {
  id: string;
  title: string;
  model: string;
  created_at: number;
  updated_at: number;
  total_tokens: number;
  message_count: number;
  metadata?: string; // JSON string
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokens: number;
  created_at: number;
  is_compressed: boolean;
}

export interface TokenStat {
  id: string;
  conversation_id: string;
  timestamp: number;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  model: string;
}

export interface CacheEntry {
  id: string;
  key: string;
  value: string;
  tokens_saved: number;
  hit_count: number;
  created_at: number;
  last_accessed: number;
  expires_at: number;
}

export interface Reference {
  id: string;
  conversation_id: string;
  type: string; // 'file', 'url', 'code', 'note'
  content: string;
  title: string;
  tokens: number;
  created_at: number;
  metadata?: string; // JSON string
}

/**
 * Database Manager Class
 */
export class DatabaseManager {
  private db: Database.Database;
  private initialized = false;

  constructor() {
    const config = getConfig();
    const dbPath = config.database.path;

    // Ensure directory exists (Windows-compatible)
    const dbDir = path.dirname(dbPath);
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }

    // Initialize database
    this.db = new Database(dbPath, {
      verbose: config.server.logLevel === 'debug' ? console.log : undefined,
    });

    // Set pragmas for performance and reliability
    this.db.pragma('journal_mode = WAL');
    this.db.pragma('synchronous = NORMAL');
    this.db.pragma(`busy_timeout = ${config.database.busyTimeout}`);

    this.initializeTables();
    this.initialized = true;
  }

  /**
   * Initialize database tables
   */
  private initializeTables(): void {
    // Conversations table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        model TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        total_tokens INTEGER DEFAULT 0,
        message_count INTEGER DEFAULT 0,
        metadata TEXT
      )
    `);

    // Messages table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
        content TEXT NOT NULL,
        tokens INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        is_compressed INTEGER DEFAULT 0,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
      )
    `);

    // Token stats table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS token_stats (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        input_tokens INTEGER NOT NULL,
        output_tokens INTEGER NOT NULL,
        cached_tokens INTEGER DEFAULT 0,
        model TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
      )
    `);

    // Cache entries table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS cache_entries (
        id TEXT PRIMARY KEY,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL,
        tokens_saved INTEGER DEFAULT 0,
        hit_count INTEGER DEFAULT 0,
        created_at INTEGER NOT NULL,
        last_accessed INTEGER NOT NULL,
        expires_at INTEGER NOT NULL
      )
    `);

    // Reference items table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS reference_items (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        type TEXT NOT NULL,
        content TEXT NOT NULL,
        title TEXT NOT NULL,
        tokens INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        metadata TEXT,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
      )
    `);

    // Create indexes for performance
    this.db.exec(`
      CREATE INDEX IF NOT EXISTS idx_messages_conversation
        ON messages(conversation_id, created_at);
      CREATE INDEX IF NOT EXISTS idx_token_stats_conversation
        ON token_stats(conversation_id, timestamp);
      CREATE INDEX IF NOT EXISTS idx_cache_key
        ON cache_entries(key);
      CREATE INDEX IF NOT EXISTS idx_cache_expires
        ON cache_entries(expires_at);
      CREATE INDEX IF NOT EXISTS idx_references_conversation
        ON reference_items(conversation_id, created_at);
    `);
  }

  // ==================== Conversation Operations ====================

  createConversation(conversation: Omit<Conversation, 'created_at' | 'updated_at'>): Conversation {
    const now = Date.now();
    const fullConversation: Conversation = {
      ...conversation,
      created_at: now,
      updated_at: now,
    };

    const stmt = this.db.prepare(`
      INSERT INTO conversations (id, title, model, created_at, updated_at, total_tokens, message_count, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      fullConversation.id,
      fullConversation.title,
      fullConversation.model,
      fullConversation.created_at,
      fullConversation.updated_at,
      fullConversation.total_tokens,
      fullConversation.message_count,
      fullConversation.metadata
    );

    return fullConversation;
  }

  getConversation(id: string): Conversation | null {
    const stmt = this.db.prepare('SELECT * FROM conversations WHERE id = ?');
    return stmt.get(id) as Conversation | null;
  }

  getAllConversations(): Conversation[] {
    const stmt = this.db.prepare('SELECT * FROM conversations ORDER BY updated_at DESC');
    return stmt.all() as Conversation[];
  }

  updateConversation(id: string, updates: Partial<Conversation>): void {
    const fields = Object.keys(updates).filter(k => k !== 'id');
    if (fields.length === 0) return;

    const setClause = fields.map(f => `${f} = ?`).join(', ');
    const values = fields.map(f => updates[f as keyof Conversation]);

    const stmt = this.db.prepare(`
      UPDATE conversations
      SET ${setClause}, updated_at = ?
      WHERE id = ?
    `);

    stmt.run(...values, Date.now(), id);
  }

  deleteConversation(id: string): void {
    const stmt = this.db.prepare('DELETE FROM conversations WHERE id = ?');
    stmt.run(id);
  }

  // ==================== Message Operations ====================

  addMessage(message: Omit<Message, 'created_at'>): Message {
    const fullMessage: Message = {
      ...message,
      created_at: Date.now(),
    };

    const stmt = this.db.prepare(`
      INSERT INTO messages (id, conversation_id, role, content, tokens, created_at, is_compressed)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      fullMessage.id,
      fullMessage.conversation_id,
      fullMessage.role,
      fullMessage.content,
      fullMessage.tokens,
      fullMessage.created_at,
      fullMessage.is_compressed ? 1 : 0
    );

    // Update conversation stats
    this.updateConversationStats(message.conversation_id);

    return fullMessage;
  }

  getMessages(conversationId: string): Message[] {
    const stmt = this.db.prepare(`
      SELECT * FROM messages
      WHERE conversation_id = ?
      ORDER BY created_at ASC
    `);
    const messages = stmt.all(conversationId) as any[];
    return messages.map(m => ({ ...m, is_compressed: Boolean(m.is_compressed) }));
  }

  updateMessage(id: string, updates: Partial<Message>): void {
    const fields = Object.keys(updates).filter(k => k !== 'id' && k !== 'created_at');
    if (fields.length === 0) return;

    const setClause = fields.map(f => `${f} = ?`).join(', ');
    const values = fields.map(f => {
      const val = updates[f as keyof Message];
      return f === 'is_compressed' ? (val ? 1 : 0) : val;
    });

    const stmt = this.db.prepare(`UPDATE messages SET ${setClause} WHERE id = ?`);
    stmt.run(...values, id);
  }

  private updateConversationStats(conversationId: string): void {
    const stats = this.db.prepare(`
      SELECT COUNT(*) as count, SUM(tokens) as total
      FROM messages
      WHERE conversation_id = ?
    `).get(conversationId) as { count: number; total: number };

    this.updateConversation(conversationId, {
      message_count: stats.count,
      total_tokens: stats.total || 0,
    });
  }

  // ==================== Token Stats Operations ====================

  addTokenStat(stat: Omit<TokenStat, 'timestamp'>): TokenStat {
    const fullStat: TokenStat = {
      ...stat,
      timestamp: Date.now(),
    };

    const stmt = this.db.prepare(`
      INSERT INTO token_stats (id, conversation_id, timestamp, input_tokens, output_tokens, cached_tokens, model)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      fullStat.id,
      fullStat.conversation_id,
      fullStat.timestamp,
      fullStat.input_tokens,
      fullStat.output_tokens,
      fullStat.cached_tokens,
      fullStat.model
    );

    return fullStat;
  }

  getTokenStats(conversationId: string): TokenStat[] {
    const stmt = this.db.prepare(`
      SELECT * FROM token_stats
      WHERE conversation_id = ?
      ORDER BY timestamp DESC
    `);
    return stmt.all(conversationId) as TokenStat[];
  }

  getAggregateTokenStats(): {
    total_input: number;
    total_output: number;
    total_cached: number;
    total_requests: number;
  } {
    const stmt = this.db.prepare(`
      SELECT
        SUM(input_tokens) as total_input,
        SUM(output_tokens) as total_output,
        SUM(cached_tokens) as total_cached,
        COUNT(*) as total_requests
      FROM token_stats
    `);
    return stmt.get() as any;
  }

  // ==================== Cache Operations ====================

  addCacheEntry(entry: Omit<CacheEntry, 'created_at' | 'last_accessed'>): CacheEntry {
    const now = Date.now();
    const fullEntry: CacheEntry = {
      ...entry,
      created_at: now,
      last_accessed: now,
    };

    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO cache_entries
      (id, key, value, tokens_saved, hit_count, created_at, last_accessed, expires_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      fullEntry.id,
      fullEntry.key,
      fullEntry.value,
      fullEntry.tokens_saved,
      fullEntry.hit_count,
      fullEntry.created_at,
      fullEntry.last_accessed,
      fullEntry.expires_at
    );

    return fullEntry;
  }

  getCacheEntry(key: string): CacheEntry | null {
    const stmt = this.db.prepare(`
      SELECT * FROM cache_entries
      WHERE key = ? AND expires_at > ?
    `);
    const entry = stmt.get(key, Date.now()) as CacheEntry | null;

    if (entry) {
      // Update last accessed and hit count
      this.db.prepare(`
        UPDATE cache_entries
        SET last_accessed = ?, hit_count = hit_count + 1
        WHERE key = ?
      `).run(Date.now(), key);
    }

    return entry;
  }

  getAllCacheEntries(): CacheEntry[] {
    const stmt = this.db.prepare(`
      SELECT * FROM cache_entries
      WHERE expires_at > ?
      ORDER BY last_accessed DESC
    `);
    return stmt.all(Date.now()) as CacheEntry[];
  }

  cleanExpiredCache(): number {
    const stmt = this.db.prepare('DELETE FROM cache_entries WHERE expires_at <= ?');
    const result = stmt.run(Date.now());
    return result.changes;
  }

  getCacheStats(): {
    total_entries: number;
    total_hits: number;
    tokens_saved: number;
  } {
    const stmt = this.db.prepare(`
      SELECT
        COUNT(*) as total_entries,
        SUM(hit_count) as total_hits,
        SUM(tokens_saved) as tokens_saved
      FROM cache_entries
      WHERE expires_at > ?
    `);
    return stmt.get(Date.now()) as any;
  }

  // ==================== Reference Operations ====================

  addReference(reference: Omit<Reference, 'created_at'>): Reference {
    const fullReference: Reference = {
      ...reference,
      created_at: Date.now(),
    };

    const stmt = this.db.prepare(`
      INSERT INTO reference_items (id, conversation_id, type, content, title, tokens, created_at, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      fullReference.id,
      fullReference.conversation_id,
      fullReference.type,
      fullReference.content,
      fullReference.title,
      fullReference.tokens,
      fullReference.created_at,
      fullReference.metadata
    );

    return fullReference;
  }

  getReferences(conversationId: string): Reference[] {
    const stmt = this.db.prepare(`
      SELECT * FROM reference_items
      WHERE conversation_id = ?
      ORDER BY created_at DESC
    `);
    return stmt.all(conversationId) as Reference[];
  }

  getAllReferences(): Reference[] {
    const stmt = this.db.prepare('SELECT * FROM reference_items ORDER BY created_at DESC');
    return stmt.all() as Reference[];
  }

  deleteReference(id: string): void {
    const stmt = this.db.prepare('DELETE FROM reference_items WHERE id = ?');
    stmt.run(id);
  }

  // ==================== Utility Methods ====================

  close(): void {
    if (this.initialized) {
      this.db.close();
      this.initialized = false;
    }
  }

  /**
   * Execute a transaction
   */
  transaction<T>(fn: () => T): T {
    return this.db.transaction(fn)();
  }
}

// Singleton instance
let dbInstance: DatabaseManager | null = null;

export function getDatabase(): DatabaseManager {
  if (!dbInstance) {
    dbInstance = new DatabaseManager();
  }
  return dbInstance;
}

export function closeDatabase(): void {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}
