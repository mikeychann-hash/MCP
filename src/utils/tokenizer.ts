/**
 * Multi-LLM Token Counter
 * Supports Claude (Anthropic), GPT (OpenAI), and other models
 */

import { encoding_for_model, get_encoding } from 'tiktoken';
import { countTokens as countAnthropicTokens } from '@anthropic-ai/tokenizer';

export type ModelFamily = 'claude' | 'gpt' | 'other';

export interface TokenCount {
  tokens: number;
  model: string;
  family: ModelFamily;
}

/**
 * Detect model family from model name
 */
export function detectModelFamily(model: string): ModelFamily {
  const modelLower = model.toLowerCase();

  if (modelLower.includes('claude') || modelLower.includes('anthropic')) {
    return 'claude';
  }

  if (modelLower.includes('gpt') || modelLower.includes('openai')) {
    return 'gpt';
  }

  return 'other';
}

/**
 * Count tokens for Claude models using Anthropic's tokenizer
 */
function countClaudeTokens(text: string): number {
  try {
    return countAnthropicTokens(text);
  } catch (error) {
    // Fallback to approximate counting (4 chars ≈ 1 token)
    console.error('Error counting Claude tokens, using fallback:', error);
    return Math.ceil(text.length / 4);
  }
}

/**
 * Count tokens for GPT models using tiktoken
 */
function countGPTTokens(text: string, model: string): number {
  try {
    // Map model names to tiktoken encodings
    const modelMap: Record<string, string> = {
      'gpt-4': 'gpt-4',
      'gpt-4-turbo': 'gpt-4',
      'gpt-4-32k': 'gpt-4',
      'gpt-3.5-turbo': 'gpt-3.5-turbo',
      'gpt-3.5-turbo-16k': 'gpt-3.5-turbo',
    };

    const tiktokenModel = modelMap[model] || 'gpt-3.5-turbo';
    const encoding = encoding_for_model(tiktokenModel as any);
    const tokens = encoding.encode(text);
    const count = tokens.length;
    encoding.free();

    return count;
  } catch (error) {
    console.error('Error counting GPT tokens, using fallback:', error);
    // Fallback to cl100k_base encoding
    try {
      const encoding = get_encoding('cl100k_base');
      const tokens = encoding.encode(text);
      const count = tokens.length;
      encoding.free();
      return count;
    } catch {
      // Ultimate fallback
      return Math.ceil(text.length / 4);
    }
  }
}

/**
 * Count tokens for any text with automatic model detection
 */
export function countTokens(text: string, model: string = 'claude-3-5-sonnet'): TokenCount {
  const family = detectModelFamily(model);
  let tokens: number;

  switch (family) {
    case 'claude':
      tokens = countClaudeTokens(text);
      break;
    case 'gpt':
      tokens = countGPTTokens(text, model);
      break;
    default:
      // Generic fallback for other models
      tokens = Math.ceil(text.length / 4);
  }

  return {
    tokens,
    model,
    family,
  };
}

/**
 * Count tokens for an array of messages
 */
export interface Message {
  role: string;
  content: string;
}

export function countMessageTokens(messages: Message[], model: string = 'claude-3-5-sonnet'): TokenCount {
  const family = detectModelFamily(model);

  // Calculate base tokens from message content
  let totalTokens = 0;

  for (const message of messages) {
    // Count content tokens
    const contentTokens = countTokens(message.content, model).tokens;
    totalTokens += contentTokens;

    // Add overhead for message formatting
    // Claude and GPT have different formatting overhead
    if (family === 'claude') {
      // Claude format: role + content + delimiters ≈ 4 tokens overhead
      totalTokens += 4;
    } else if (family === 'gpt') {
      // GPT format: more structured, ≈ 7 tokens overhead per message
      totalTokens += 7;
    } else {
      // Generic overhead
      totalTokens += 4;
    }
  }

  // Add conversation-level overhead
  if (family === 'gpt') {
    // GPT adds tokens for conversation start/end
    totalTokens += 3;
  }

  return {
    tokens: totalTokens,
    model,
    family,
  };
}

/**
 * Estimate tokens for structured data (JSON, etc.)
 */
export function countStructuredTokens(data: any, model: string = 'claude-3-5-sonnet'): TokenCount {
  const jsonString = JSON.stringify(data, null, 2);
  return countTokens(jsonString, model);
}

/**
 * Calculate token percentage relative to model limit
 */
export function calculateTokenPercentage(tokens: number, model: string): number {
  const limits: Record<string, number> = {
    'claude-3-5-sonnet': 200000,
    'claude-3-5-haiku': 200000,
    'claude-3-opus': 200000,
    'gpt-4': 128000,
    'gpt-4-turbo': 128000,
    'gpt-4-32k': 32768,
    'gpt-3.5-turbo': 16385,
    'gpt-3.5-turbo-16k': 16385,
  };

  const limit = limits[model] || 100000;
  return (tokens / limit) * 100;
}

/**
 * Check if tokens exceed model limit
 */
export function exceedsLimit(tokens: number, model: string): boolean {
  const percentage = calculateTokenPercentage(tokens, model);
  return percentage > 90; // Warning threshold at 90%
}

/**
 * Get recommended action based on token usage
 */
export interface TokenRecommendation {
  status: 'safe' | 'warning' | 'critical';
  percentage: number;
  action: string;
  shouldCompress: boolean;
}

export function getTokenRecommendation(tokens: number, model: string): TokenRecommendation {
  const percentage = calculateTokenPercentage(tokens, model);

  if (percentage < 50) {
    return {
      status: 'safe',
      percentage,
      action: 'Token usage is healthy. No action needed.',
      shouldCompress: false,
    };
  } else if (percentage < 75) {
    return {
      status: 'warning',
      percentage,
      action: 'Consider compressing older messages or summarizing context.',
      shouldCompress: true,
    };
  } else if (percentage < 90) {
    return {
      status: 'critical',
      percentage,
      action: 'Urgently compress context or remove old messages to avoid hitting limit.',
      shouldCompress: true,
    };
  } else {
    return {
      status: 'critical',
      percentage,
      action: 'CRITICAL: Token limit nearly reached. Immediate compression required.',
      shouldCompress: true,
    };
  }
}

/**
 * Estimate compression potential
 */
export function estimateCompressionSavings(
  text: string,
  compressionRatio: number = 0.5
): {
  original: number;
  estimated: number;
  saved: number;
} {
  const original = countTokens(text).tokens;
  const estimated = Math.ceil(original * compressionRatio);
  const saved = original - estimated;

  return { original, estimated, saved };
}

/**
 * Batch count tokens for multiple texts
 */
export function batchCountTokens(
  texts: string[],
  model: string = 'claude-3-5-sonnet'
): TokenCount[] {
  return texts.map(text => countTokens(text, model));
}

/**
 * Count tokens with caching consideration
 * Some content may be cached, reducing effective token count
 */
export interface CachedTokenCount extends TokenCount {
  cachedTokens: number;
  effectiveTokens: number;
}

export function countTokensWithCache(
  text: string,
  cachedPrefixLength: number = 0,
  model: string = 'claude-3-5-sonnet'
): CachedTokenCount {
  const total = countTokens(text, model);

  let cachedTokens = 0;
  if (cachedPrefixLength > 0) {
    const prefix = text.substring(0, cachedPrefixLength);
    cachedTokens = countTokens(prefix, model).tokens;
  }

  return {
    ...total,
    cachedTokens,
    effectiveTokens: total.tokens - cachedTokens,
  };
}
