/**
 * Configuration Management
 * Handles all server configuration with Windows-compatible paths and validation
 */

import path from 'path';
import os from 'os';
import { z } from 'zod';

/**
 * Configuration schema with Zod validation
 */
const ConfigSchema = z.object({
  // Database configuration
  database: z.object({
    path: z.string(),
    maxConnections: z.number().default(5),
    busyTimeout: z.number().default(5000),
  }),

  // Token limits per model
  tokenLimits: z.object({
    'claude-3-5-sonnet': z.number().default(200000),
    'claude-3-5-haiku': z.number().default(200000),
    'claude-3-opus': z.number().default(200000),
    'gpt-4': z.number().default(128000),
    'gpt-4-turbo': z.number().default(128000),
    'gpt-3.5-turbo': z.number().default(16385),
  }),

  // Cache configuration
  cache: z.object({
    enabled: z.boolean().default(true),
    maxSize: z.number().default(100),
    ttl: z.number().default(3600000), // 1 hour in ms
  }),

  // Compression settings
  compression: z.object({
    minTokensForCompression: z.number().default(10000),
    targetCompressionRatio: z.number().default(0.5),
    aggressivenessLevel: z.enum(['low', 'medium', 'high']).default('medium'),
  }),

  // Server settings
  server: z.object({
    name: z.string().default('mcp-token-optimizer'),
    version: z.string().default('1.0.0'),
    logLevel: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  }),
});

export type Config = z.infer<typeof ConfigSchema>;

/**
 * Get Windows-compatible data directory path
 */
function getDataDirectory(): string {
  const platform = os.platform();

  if (platform === 'win32') {
    // Windows: Use APPDATA or fallback to USERPROFILE
    const appData = process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming');
    return path.join(appData, 'mcp-token-optimizer');
  } else if (platform === 'darwin') {
    // macOS: Use Application Support
    return path.join(os.homedir(), 'Library', 'Application Support', 'mcp-token-optimizer');
  } else {
    // Linux: Use .local/share
    return path.join(os.homedir(), '.local', 'share', 'mcp-token-optimizer');
  }
}

/**
 * Default configuration with platform-specific paths
 */
const defaultConfig: Config = {
  database: {
    path: path.join(getDataDirectory(), 'token-optimizer.db'),
    maxConnections: 5,
    busyTimeout: 5000,
  },
  tokenLimits: {
    'claude-3-5-sonnet': 200000,
    'claude-3-5-haiku': 200000,
    'claude-3-opus': 200000,
    'gpt-4': 128000,
    'gpt-4-turbo': 128000,
    'gpt-3.5-turbo': 16385,
  },
  cache: {
    enabled: true,
    maxSize: 100,
    ttl: 3600000,
  },
  compression: {
    minTokensForCompression: 10000,
    targetCompressionRatio: 0.5,
    aggressivenessLevel: 'medium',
  },
  server: {
    name: 'mcp-token-optimizer',
    version: '1.0.0',
    logLevel: 'info',
  },
};

/**
 * Load and validate configuration
 */
export function loadConfig(): Config {
  // For now, use default config
  // In production, you might load from environment variables or config file
  const config = ConfigSchema.parse(defaultConfig);
  return config;
}

/**
 * Get the current configuration
 */
let cachedConfig: Config | null = null;

export function getConfig(): Config {
  if (!cachedConfig) {
    cachedConfig = loadConfig();
  }
  return cachedConfig;
}

/**
 * Export default config for testing
 */
export { defaultConfig };
