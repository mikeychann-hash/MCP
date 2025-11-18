/**
 * Tool: count_tokens
 * Count tokens for text, messages, or conversations with multi-LLM support
 */

import { z } from 'zod';
import {
  countTokens,
  countMessageTokens,
  countStructuredTokens,
  calculateTokenPercentage,
  getTokenRecommendation,
  estimateCompressionSavings,
} from '../utils/tokenizer.js';
import { getDatabase } from '../storage/database.js';

const MessageSchema = z.object({
  role: z.string(),
  content: z.string(),
});

export const CountTokensInputSchema = z.object({
  input: z.union([
    z.string(), // Plain text
    z.array(MessageSchema), // Array of messages
    z.record(z.any()), // Structured data
  ]),
  model: z.string().default('claude-3-5-sonnet'),
  include_recommendations: z.boolean().default(true),
  conversation_id: z.string().uuid().optional(),
});

export type CountTokensInput = z.infer<typeof CountTokensInputSchema>;

/**
 * Count tokens with detailed analysis
 */
export async function countTokensTool(input: CountTokensInput): Promise<any> {
  const db = getDatabase();
  let tokenCount: number;
  let inputType: string;
  let details: any = {};

  // Determine input type and count tokens
  if (typeof input.input === 'string') {
    inputType = 'text';
    const result = countTokens(input.input, input.model);
    tokenCount = result.tokens;
    details = {
      characters: input.input.length,
      family: result.family,
    };
  } else if (Array.isArray(input.input)) {
    inputType = 'messages';
    const result = countMessageTokens(input.input, input.model);
    tokenCount = result.tokens;
    details = {
      message_count: input.input.length,
      family: result.family,
      average_tokens_per_message: Math.round(tokenCount / input.input.length),
    };
  } else {
    inputType = 'structured';
    const result = countStructuredTokens(input.input, input.model);
    tokenCount = result.tokens;
    details = {
      keys: Object.keys(input.input).length,
      family: result.family,
    };
  }

  // Calculate percentage of model limit
  const percentage = calculateTokenPercentage(tokenCount, input.model);

  // Build response
  const response: any = {
    success: true,
    tokens: tokenCount,
    model: input.model,
    input_type: inputType,
    percentage_of_limit: Math.round(percentage * 100) / 100,
    details,
  };

  // Add recommendations if requested
  if (input.include_recommendations) {
    const recommendation = getTokenRecommendation(tokenCount, input.model);
    response.recommendation = recommendation;

    // If should compress, estimate savings
    if (recommendation.shouldCompress) {
      const inputStr = typeof input.input === 'string'
        ? input.input
        : JSON.stringify(input.input);
      const savings = estimateCompressionSavings(inputStr, 0.5);
      response.compression_estimate = {
        potential_savings: savings.saved,
        estimated_tokens_after: savings.estimated,
        compression_ratio: 0.5,
      };
    }
  }

  // If conversation_id provided, get context
  if (input.conversation_id) {
    const conversation = db.getConversation(input.conversation_id);
    if (conversation) {
      const messages = db.getMessages(input.conversation_id);
      const conversationTokens = countMessageTokens(
        messages.map(m => ({ role: m.role, content: m.content })),
        conversation.model
      ).tokens;

      response.conversation_context = {
        total_tokens: conversationTokens,
        message_count: messages.length,
        percentage_of_limit: Math.round(
          calculateTokenPercentage(conversationTokens, conversation.model) * 100
        ) / 100,
      };
    }
  }

  return response;
}
