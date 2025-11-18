/**
 * Tool: compress_context
 * Intelligently compress conversation context to reduce token usage
 */

import { z } from 'zod';
import { getDatabase } from '../storage/database.js';
import { countTokens, countMessageTokens } from '../utils/tokenizer.js';
import { getPromptCache } from '../utils/cache.js';

export const CompressContextInputSchema = z.object({
  conversation_id: z.string().uuid(),
  strategy: z.enum(['summarize', 'remove_old', 'compress_similar', 'smart']).default('smart'),
  target_ratio: z.number().min(0.1).max(0.9).default(0.5),
  preserve_recent: z.number().int().positive().default(5),
});

export type CompressContextInput = z.infer<typeof CompressContextInputSchema>;

/**
 * Summarize messages into a concise summary
 */
function summarizeMessages(messages: Array<{ role: string; content: string }>): string {
  // Simple summarization strategy
  // In production, you'd call an LLM API for actual summarization
  const userMessages = messages.filter(m => m.role === 'user');
  const assistantMessages = messages.filter(m => m.role === 'assistant');

  const topics = new Set<string>();

  // Extract key topics (simple keyword extraction)
  for (const msg of userMessages) {
    const words = msg.content.toLowerCase().split(/\s+/);
    const keywords = words.filter(w => w.length > 5);
    keywords.slice(0, 3).forEach(k => topics.add(k));
  }

  const summary = [
    `Summary of ${messages.length} messages:`,
    `- User asked about: ${Array.from(topics).slice(0, 5).join(', ')}`,
    `- ${assistantMessages.length} responses provided`,
    `- Key topics discussed: ${Array.from(topics).slice(0, 3).join(', ')}`,
  ].join('\n');

  return summary;
}

/**
 * Remove old messages strategy
 */
function removeOldMessages(
  messages: Array<any>,
  preserveRecent: number
): Array<any> {
  if (messages.length <= preserveRecent) {
    return messages;
  }

  const toRemove = messages.length - preserveRecent;
  const oldMessages = messages.slice(0, toRemove);
  const recentMessages = messages.slice(toRemove);

  // Create summary of removed messages
  const summary = summarizeMessages(
    oldMessages.map(m => ({ role: m.role, content: m.content }))
  );

  // Return summary + recent messages
  return [
    {
      role: 'system',
      content: `[Compressed context]\n${summary}`,
      is_summary: true,
    },
    ...recentMessages,
  ];
}

/**
 * Compress similar consecutive messages
 */
function compressSimilarMessages(messages: Array<any>): Array<any> {
  const compressed: Array<any> = [];
  let currentGroup: Array<any> = [];

  for (const message of messages) {
    if (currentGroup.length === 0) {
      currentGroup.push(message);
      continue;
    }

    const lastMessage = currentGroup[currentGroup.length - 1];

    // Group consecutive messages from same role
    if (message.role === lastMessage.role) {
      currentGroup.push(message);
    } else {
      // Compress current group if needed
      if (currentGroup.length > 2) {
        const combinedContent = currentGroup.map(m => m.content).join('\n\n');
        compressed.push({
          ...currentGroup[0],
          content: `[${currentGroup.length} messages combined]\n${combinedContent.substring(0, 500)}...`,
          is_compressed: true,
        });
      } else {
        compressed.push(...currentGroup);
      }
      currentGroup = [message];
    }
  }

  // Handle last group
  if (currentGroup.length > 2) {
    const combinedContent = currentGroup.map(m => m.content).join('\n\n');
    compressed.push({
      ...currentGroup[0],
      content: `[${currentGroup.length} messages combined]\n${combinedContent.substring(0, 500)}...`,
      is_compressed: true,
    });
  } else {
    compressed.push(...currentGroup);
  }

  return compressed;
}

/**
 * Smart compression strategy (combines multiple techniques)
 */
function smartCompress(
  messages: Array<any>,
  targetRatio: number,
  preserveRecent: number
): Array<any> {
  let compressed = [...messages];
  const originalTokens = countMessageTokens(
    messages.map(m => ({ role: m.role, content: m.content }))
  ).tokens;

  const targetTokens = Math.ceil(originalTokens * targetRatio);

  // Step 1: Remove oldest messages if too many
  if (messages.length > preserveRecent * 2) {
    compressed = removeOldMessages(compressed, preserveRecent * 2);
  }

  // Step 2: Compress similar messages
  compressed = compressSimilarMessages(compressed);

  // Step 3: If still too many tokens, remove more old messages
  let currentTokens = countMessageTokens(
    compressed.map(m => ({ role: m.role, content: m.content }))
  ).tokens;

  while (currentTokens > targetTokens && compressed.length > preserveRecent) {
    compressed = removeOldMessages(compressed, compressed.length - 1);
    currentTokens = countMessageTokens(
      compressed.map(m => ({ role: m.role, content: m.content }))
    ).tokens;
  }

  return compressed;
}

/**
 * Handle context compression
 */
export async function compressContext(input: CompressContextInput): Promise<any> {
  const db = getDatabase();
  const cache = getPromptCache();

  // Get conversation
  const conversation = db.getConversation(input.conversation_id);
  if (!conversation) {
    return {
      success: false,
      error: 'Conversation not found',
    };
  }

  // Get messages
  const messages = db.getMessages(input.conversation_id);
  if (messages.length === 0) {
    return {
      success: false,
      error: 'No messages to compress',
    };
  }

  // Check cache for previously compressed version
  const cacheKey = `${input.conversation_id}:${input.strategy}:${input.target_ratio}`;
  const cached = await cache.get(cacheKey, { prefix: 'compress' });
  if (cached.hit && cached.value) {
    return {
      success: true,
      from_cache: true,
      ...cached.value,
    };
  }

  // Calculate original token count
  const originalTokens = countMessageTokens(
    messages.map(m => ({ role: m.role, content: m.content })),
    conversation.model
  ).tokens;

  // Apply compression strategy
  let compressedMessages: Array<any>;
  switch (input.strategy) {
    case 'summarize':
      compressedMessages = [
        {
          role: 'system',
          content: summarizeMessages(messages.map(m => ({ role: m.role, content: m.content }))),
        },
        ...messages.slice(-input.preserve_recent),
      ];
      break;

    case 'remove_old':
      compressedMessages = removeOldMessages(messages, input.preserve_recent);
      break;

    case 'compress_similar':
      compressedMessages = compressSimilarMessages(messages);
      break;

    case 'smart':
    default:
      compressedMessages = smartCompress(messages, input.target_ratio, input.preserve_recent);
      break;
  }

  // Calculate compressed token count
  const compressedTokens = countMessageTokens(
    compressedMessages.map(m => ({ role: m.role, content: m.content })),
    conversation.model
  ).tokens;

  const tokensSaved = originalTokens - compressedTokens;
  const compressionRatio = compressedTokens / originalTokens;

  const result = {
    success: true,
    original_tokens: originalTokens,
    compressed_tokens: compressedTokens,
    tokens_saved: tokensSaved,
    compression_ratio: Math.round(compressionRatio * 100) / 100,
    original_message_count: messages.length,
    compressed_message_count: compressedMessages.length,
    strategy: input.strategy,
    compressed_messages: compressedMessages.map(m => ({
      role: m.role,
      content: m.content.substring(0, 200) + (m.content.length > 200 ? '...' : ''),
      tokens: countTokens(m.content, conversation.model).tokens,
      is_compressed: m.is_compressed || false,
    })),
  };

  // Cache the result
  await cache.set(cacheKey, result, {
    prefix: 'compress',
    ttl: 1800000, // 30 minutes
  });

  return result;
}
