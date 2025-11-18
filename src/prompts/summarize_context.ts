/**
 * Prompt: summarize_context
 * Generate a prompt for summarizing conversation context
 */

import { getDatabase } from '../storage/database.js';
import { countMessageTokens } from '../utils/tokenizer.js';

export interface SummarizeContextParams {
  conversation_id?: string;
  focus?: string;
  max_summary_tokens?: number;
}

/**
 * Generate summarization prompt
 */
export async function generateSummarizePrompt(
  params: SummarizeContextParams = {}
): Promise<string> {
  const db = getDatabase();

  if (!params.conversation_id) {
    return `# Context Summarization Prompt

You are an expert at summarizing conversations while preserving key information.

## Task
Summarize the provided conversation context, focusing on:
- Main topics discussed
- Key decisions made
- Important facts or data points
- Action items or next steps

## Guidelines
- Be concise but comprehensive
- Preserve critical details
- Use bullet points for clarity
- Highlight any unresolved questions
${params.focus ? `\n## Specific Focus\n${params.focus}` : ''}
${params.max_summary_tokens ? `\n## Token Limit\nKeep summary under ${params.max_summary_tokens} tokens` : ''}

## Output Format
Provide the summary in this format:

**Main Topics:**
- [topic 1]
- [topic 2]

**Key Points:**
- [point 1]
- [point 2]

**Decisions/Conclusions:**
- [decision 1]

**Open Questions:**
- [question 1]

Now summarize the conversation above.`;
  }

  // Get conversation
  const conversation = db.getConversation(params.conversation_id);
  if (!conversation) {
    throw new Error('Conversation not found');
  }

  const messages = db.getMessages(params.conversation_id);
  if (messages.length === 0) {
    throw new Error('No messages to summarize');
  }

  // Calculate token count
  const tokenCount = countMessageTokens(
    messages.map(m => ({ role: m.role, content: m.content })),
    conversation.model
  ).tokens;

  // Format conversation
  const formattedMessages = messages.map(m =>
    `[${m.role.toUpperCase()}]: ${m.content}`
  ).join('\n\n');

  return `# Conversation Summarization Request

**Conversation:** ${conversation.title}
**Model:** ${conversation.model}
**Messages:** ${messages.length}
**Total Tokens:** ${tokenCount}
**Created:** ${new Date(conversation.created_at).toISOString()}

## Conversation History

${formattedMessages}

---

## Summarization Instructions

Please summarize the above conversation, focusing on:
- Main topics and themes discussed
- Key technical details or code snippets
- Important decisions or conclusions
- Questions asked and answers provided
- Any action items or next steps

${params.focus ? `\n**Special Focus:** ${params.focus}\n` : ''}

**Format Requirements:**
- Use clear section headers
- Bullet points for lists
- Preserve critical technical details
- Be concise but comprehensive
${params.max_summary_tokens ? `- Keep summary under ${params.max_summary_tokens} tokens` : '- Aim for 20-30% of original token count'}

**Summary Structure:**

**Overview:**
[1-2 sentence high-level summary]

**Main Topics:**
- [topic 1 with brief context]
- [topic 2 with brief context]

**Technical Details:**
- [key technical points, code patterns, etc.]

**Key Takeaways:**
- [important conclusions or decisions]

**Unresolved Items:**
- [open questions or pending tasks]

Now provide the summary:`;
}

/**
 * Get summarize context prompt name
 */
export function getSummarizeContextPromptName(): string {
  return 'summarize_context';
}
