/**
 * Prompt: compress_conversation
 * Generate a prompt for compressing conversation while preserving essential info
 */

import { getDatabase } from '../storage/database.js';
import { countMessageTokens, calculateTokenPercentage } from '../utils/tokenizer.js';

export interface CompressConversationParams {
  conversation_id: string;
  target_reduction_percent?: number;
  preserve_recent_count?: number;
}

/**
 * Generate compression prompt
 */
export async function generateCompressPrompt(
  params: CompressConversationParams
): Promise<string> {
  const db = getDatabase();

  // Get conversation
  const conversation = db.getConversation(params.conversation_id);
  if (!conversation) {
    throw new Error('Conversation not found');
  }

  const messages = db.getMessages(params.conversation_id);
  if (messages.length === 0) {
    throw new Error('No messages to compress');
  }

  const targetReduction = params.target_reduction_percent || 50;
  const preserveRecent = params.preserve_recent_count || 5;

  // Calculate token metrics
  const currentTokens = countMessageTokens(
    messages.map(m => ({ role: m.role, content: m.content })),
    conversation.model
  ).tokens;

  const targetTokens = Math.ceil(currentTokens * (1 - targetReduction / 100));
  const tokenPercentage = calculateTokenPercentage(currentTokens, conversation.model);

  // Split messages into old and recent
  const splitPoint = Math.max(0, messages.length - preserveRecent);
  const oldMessages = messages.slice(0, splitPoint);

  // Format old messages for compression
  const formattedOldMessages = oldMessages.map((m, i) =>
    `[Message ${i + 1} - ${m.role.toUpperCase()}]:\n${m.content}`
  ).join('\n\n---\n\n');

  return `# Conversation Compression Task

**Conversation:** ${conversation.title}
**Model:** ${conversation.model}

## Current State
- Total messages: ${messages.length}
- Current tokens: ${currentTokens}
- Token usage: ${tokenPercentage.toFixed(1)}% of model limit
- Target tokens: ${targetTokens}
- Required reduction: ${targetReduction}%

## Strategy
Compress the older ${oldMessages.length} messages below while:
- Preserving all essential information
- Maintaining chronological flow
- Keeping key facts, decisions, and code snippets
- Removing redundancy and verbose explanations

The most recent ${preserveRecent} messages will be kept unmodified.

## Messages to Compress

${formattedOldMessages}

---

## Compression Guidelines

1. **Preserve:**
   - Technical details (code, commands, configurations)
   - Specific numbers, dates, and facts
   - Decisions and conclusions
   - Error messages and solutions

2. **Compress:**
   - Verbose explanations (keep core meaning)
   - Repetitive confirmations
   - Conversational filler
   - Examples (keep 1-2 most relevant)

3. **Remove:**
   - Pure pleasantries
   - Redundant information
   - Off-topic tangents
   - Excessive examples

## Output Format

Provide a compressed version that:
- Reduces token count by ~${targetReduction}%
- Uses clear, concise language
- Organizes information logically
- Maintains technical accuracy

**Suggested Structure:**

[COMPRESSED CONTEXT]

**Topics Covered:**
- [topic 1]
- [topic 2]

**Key Information:**
- [fact/decision 1]
- [fact/decision 2]

**Technical Details:**
\`\`\`
[code/commands if relevant]
\`\`\`

**Outcomes:**
- [result 1]
- [result 2]

Now provide the compressed version:`;
}

/**
 * Get compress conversation prompt name
 */
export function getCompressConversationPromptName(): string {
  return 'compress_conversation';
}
