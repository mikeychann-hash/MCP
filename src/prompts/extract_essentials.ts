/**
 * Prompt: extract_essentials
 * Generate a prompt for extracting only essential information from context
 */

import { getDatabase } from '../storage/database.js';
import { countTokens } from '../utils/tokenizer.js';

export interface ExtractEssentialsParams {
  conversation_id?: string;
  content?: string;
  extract_type?: 'facts' | 'code' | 'decisions' | 'questions' | 'all';
  model?: string;
}

/**
 * Generate extraction prompt
 */
export async function generateExtractPrompt(
  params: ExtractEssentialsParams
): Promise<string> {
  const db = getDatabase();
  const extractType = params.extract_type || 'all';

  // Build extraction instructions based on type
  const extractionInstructions = {
    facts: `## Extract: Facts and Data Points

Identify and extract:
- Specific numbers, dates, and metrics
- Named entities (people, places, tools, technologies)
- File paths, URLs, and references
- Version numbers and technical specifications
- Concrete statements of fact`,

    code: `## Extract: Code and Technical Content

Identify and extract:
- Code snippets and commands
- Configuration settings
- Function/class names and signatures
- API endpoints and parameters
- Error messages and stack traces
- Technical procedures and steps`,

    decisions: `## Extract: Decisions and Conclusions

Identify and extract:
- Explicit decisions made
- Chosen approaches or solutions
- Rejected alternatives (with reasons)
- Action items and next steps
- Agreements and commitments`,

    questions: `## Extract: Questions and Answers

Identify and extract:
- Questions asked (both answered and unanswered)
- Answers provided
- Clarifications requested
- Unresolved issues or uncertainties
- Knowledge gaps identified`,

    all: `## Extract: All Essential Information

Identify and extract:
1. **Facts:** Specific data, numbers, names, references
2. **Code/Technical:** Code snippets, commands, configurations
3. **Decisions:** Choices made, solutions selected
4. **Q&A:** Questions asked and answers provided
5. **Actions:** Next steps, tasks, commitments`,
  };

  if (params.content) {
    // Extract from provided content
    const tokens = countTokens(params.content, params.model).tokens;

    return `# Essential Information Extraction

**Task:** Extract essential information from the provided text
**Content Length:** ${params.content.length} characters (${tokens} tokens)
**Extraction Type:** ${extractType}

${extractionInstructions[extractType]}

## Source Content

${params.content}

---

## Output Format

Provide extracted information in this structured format:

${extractType === 'facts' || extractType === 'all' ? `
**Facts & Data:**
- [fact 1]
- [fact 2]
` : ''}

${extractType === 'code' || extractType === 'all' ? `
**Technical/Code:**
\`\`\`
[code snippet 1]
\`\`\`
- [technical detail]
` : ''}

${extractType === 'decisions' || extractType === 'all' ? `
**Decisions:**
- [decision 1]: [rationale]
- [decision 2]: [rationale]
` : ''}

${extractType === 'questions' || extractType === 'all' ? `
**Questions & Answers:**
- Q: [question]
  A: [answer]
- Q: [unanswered question]
  A: [pending]
` : ''}

**Summary:**
[One sentence summarizing the essentials]

Now extract the essential information:`;
  }

  if (params.conversation_id) {
    // Extract from conversation
    const conversation = db.getConversation(params.conversation_id);
    if (!conversation) {
      throw new Error('Conversation not found');
    }

    const messages = db.getMessages(params.conversation_id);
    if (messages.length === 0) {
      throw new Error('No messages to extract from');
    }

    // Format conversation
    const formattedMessages = messages.map((m, i) =>
      `[${i + 1}] ${m.role.toUpperCase()}:\n${m.content}`
    ).join('\n\n');

    return `# Extract Essential Information

**Conversation:** ${conversation.title}
**Messages:** ${messages.length}
**Extraction Type:** ${extractType}

${extractionInstructions[extractType]}

## Conversation

${formattedMessages}

---

## Extraction Guidelines

1. **Be Selective:** Only include truly essential information
2. **Be Precise:** Quote exact details (numbers, names, code)
3. **Be Organized:** Group related items together
4. **Be Concise:** Use bullet points and clear headers
5. **Preserve Context:** Include enough context to understand each item

## Output Format

${extractType === 'all' ? `
**Essential Facts:**
- [fact 1]
- [fact 2]

**Code & Commands:**
\`\`\`
[snippet 1]
\`\`\`
- Context: [when/why used]

**Key Decisions:**
- [decision 1]: [brief rationale]

**Important Q&A:**
- Q: [question]
  A: [answer]

**Action Items:**
- [ ] [task 1]
- [ ] [task 2]

**Summary:**
[2-3 sentences capturing the essence of the conversation]
` : `
[Format based on extraction type: ${extractType}]
`}

Now extract the essential information:`;
  }

  // Generic extraction prompt
  return `# Extract Essential Information

${extractionInstructions[extractType]}

## Guidelines

1. Focus on concrete, actionable information
2. Preserve exact technical details
3. Remove redundancy and filler
4. Maintain critical context
5. Use clear, structured output

## Output Format

Organize extracted information clearly with:
- Bullet points for lists
- Code blocks for snippets
- Headers for categories
- Brief explanations where needed

Provide the extracted essentials below:`;
}

/**
 * Get extract essentials prompt name
 */
export function getExtractEssentialsPromptName(): string {
  return 'extract_essentials';
}
