/**
 * Tool: optimize_query
 * Analyze and optimize queries for better token efficiency
 */

import { z } from 'zod';
import { countTokens, getTokenRecommendation } from '../utils/tokenizer.js';

export const OptimizeQueryInputSchema = z.object({
  query: z.string().min(1),
  context: z.string().optional(),
  model: z.string().default('claude-3-5-sonnet'),
  optimization_goal: z.enum(['reduce_tokens', 'improve_clarity', 'both']).default('both'),
  max_tokens: z.number().positive().optional(),
});

export type OptimizeQueryInput = z.infer<typeof OptimizeQueryInputSchema>;

/**
 * Analyze query for optimization opportunities
 */
function analyzeQuery(query: string): {
  issues: string[];
  suggestions: string[];
  score: number;
} {
  const issues: string[] = [];
  const suggestions: string[] = [];
  let score = 100;

  // Check for excessive length
  if (query.length > 2000) {
    issues.push('Query is very long');
    suggestions.push('Consider breaking into smaller, focused queries');
    score -= 20;
  }

  // Check for repetition
  const words = query.toLowerCase().split(/\s+/);
  const wordCount = new Map<string, number>();
  words.forEach(word => {
    wordCount.set(word, (wordCount.get(word) || 0) + 1);
  });

  const repetitions = Array.from(wordCount.entries())
    .filter(([word, count]) => count > 3 && word.length > 4);

  if (repetitions.length > 0) {
    issues.push('Excessive word repetition detected');
    suggestions.push(`Repeated words: ${repetitions.map(([w]) => w).join(', ')}`);
    score -= 10;
  }

  // Check for excessive examples
  const exampleMatches = query.match(/\bfor example\b|\be\.g\.\b|\bsuch as\b/gi);
  if (exampleMatches && exampleMatches.length > 3) {
    issues.push('Too many examples provided');
    suggestions.push('Limit to 1-2 most relevant examples');
    score -= 10;
  }

  // Check for vague language
  const vagueWords = ['thing', 'stuff', 'something', 'somehow', 'whatever'];
  const hasVague = vagueWords.some(word =>
    query.toLowerCase().includes(word)
  );

  if (hasVague) {
    issues.push('Contains vague language');
    suggestions.push('Use specific, concrete terms');
    score -= 5;
  }

  // Check for unnecessary filler
  const fillers = [
    'basically',
    'actually',
    'literally',
    'just',
    'really',
    'very',
    'quite',
  ];

  const fillerCount = fillers.reduce((count, filler) =>
    count + (query.toLowerCase().match(new RegExp(`\\b${filler}\\b`, 'g'))?.length || 0), 0
  );

  if (fillerCount > 3) {
    issues.push('Contains filler words');
    suggestions.push('Remove unnecessary words like "basically", "actually", "just"');
    score -= 5;
  }

  return { issues, suggestions, score: Math.max(0, score) };
}

/**
 * Generate optimized version of query
 */
function optimizeQueryText(
  query: string,
  goal: 'reduce_tokens' | 'improve_clarity' | 'both'
): string {
  let optimized = query;

  // Remove filler words
  const fillers = ['basically', 'actually', 'literally', 'just', 'really', 'very', 'quite'];
  fillers.forEach(filler => {
    const regex = new RegExp(`\\b${filler}\\b`, 'gi');
    optimized = optimized.replace(regex, '');
  });

  // Clean up extra whitespace
  optimized = optimized.replace(/\s+/g, ' ').trim();

  // Remove redundant phrases
  optimized = optimized.replace(/\bI want to know\b/gi, '');
  optimized = optimized.replace(/\bCan you please\b/gi, '');
  optimized = optimized.replace(/\bI would like to\b/gi, '');

  // Trim to be more concise if goal is reduce_tokens
  if (goal === 'reduce_tokens' || goal === 'both') {
    // Simplify common verbose patterns
    optimized = optimized.replace(/\bin order to\b/gi, 'to');
    optimized = optimized.replace(/\bdue to the fact that\b/gi, 'because');
    optimized = optimized.replace(/\bat this point in time\b/gi, 'now');
  }

  return optimized.trim();
}

/**
 * Optimize query tool
 */
export async function optimizeQuery(input: OptimizeQueryInput): Promise<any> {
  // Analyze original query
  const analysis = analyzeQuery(input.query);
  const originalTokens = countTokens(input.query, input.model).tokens;

  // Generate optimized version
  const optimizedQuery = optimizeQueryText(input.query, input.optimization_goal);
  const optimizedTokens = countTokens(optimizedQuery, input.model).tokens;

  const tokensSaved = originalTokens - optimizedTokens;
  const savingsPercent = originalTokens > 0
    ? Math.round((tokensSaved / originalTokens) * 100)
    : 0;

  // If context is provided, analyze combined tokens
  let contextAnalysis;
  if (input.context) {
    const contextTokens = countTokens(input.context, input.model).tokens;
    const totalOriginal = originalTokens + contextTokens;
    const totalOptimized = optimizedTokens + contextTokens;

    const recommendation = getTokenRecommendation(totalOriginal, input.model);

    contextAnalysis = {
      context_tokens: contextTokens,
      total_tokens_original: totalOriginal,
      total_tokens_optimized: totalOptimized,
      recommendation,
    };
  }

  // Check if meets max_tokens constraint
  const meetsConstraint = !input.max_tokens || optimizedTokens <= input.max_tokens;

  return {
    success: true,
    original: {
      query: input.query,
      tokens: originalTokens,
      analysis_score: analysis.score,
      issues: analysis.issues,
    },
    optimized: {
      query: optimizedQuery,
      tokens: optimizedTokens,
      meets_constraint: meetsConstraint,
    },
    improvement: {
      tokens_saved: tokensSaved,
      savings_percent: savingsPercent,
      suggestions: analysis.suggestions,
    },
    context_analysis: contextAnalysis,
  };
}
