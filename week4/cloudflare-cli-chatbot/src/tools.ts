/**
 * Tool definitions for the CLI chatbot
 * Add your custom tools here following the same pattern
 */
import { tool } from 'ai';
import { z } from 'zod';

/**
 * Get current time
 */
const getCurrentTime = tool({
  description: 'Get the current date and time',
  inputSchema: z.object({}),
  execute: async () => {
    return new Date().toLocaleString();
  },
});

/**
 * Simple calculator
 */
const calculate = tool({
  description: 'Perform basic mathematical calculations',
  inputSchema: z.object({
    expression: z
      .string()
      .describe(
        'Mathematical expression to evaluate (e.g., "2 + 2", "10 * 5")'
      ),
  }),
  execute: async ({ expression }) => {
    try {
      // Basic safety check - only allow numbers, operators, parentheses, and spaces
      if (!/^[0-9+\-*/().\s]+$/.test(expression)) {
        throw new Error('Invalid characters in expression');
      }

      // Use Function constructor instead of eval for slightly better security
      const result = new Function(`return ${expression}`)();
      return `${expression} = ${result}`;
    } catch (error) {
      return `Error calculating "${expression}": ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  },
});

/**
 * System information
 */
const getSystemInfo = tool({
  description: 'Get basic system information',
  inputSchema: z.object({}),
  execute: async () => {
    const os = await import('node:os');
    return JSON.stringify(
      {
        platform: os.platform(),
        architecture: os.arch(),
        nodeVersion: process.version,
        uptime: `${Math.floor(os.uptime() / 3600)} hours`,
        freeMemory: `${Math.round(os.freemem() / 1024 / 1024)} MB`,
        totalMemory: `${Math.round(os.totalmem() / 1024 / 1024)} MB`,
      },
      null,
      2
    );
  },
});

/**
 * Weather tool - placeholder for API integration
 */
const getWeather = tool({
  description: 'Get weather information for a city',
  inputSchema: z.object({
    city: z.string().describe('The city to get weather for'),
  }),
  execute: async ({ city }) => {
    // TODO: Replace with actual weather API call
    return `Weather information for ${city} is not implemented yet. You would need to integrate with a weather API like OpenWeatherMap.`;
  },
});

/**
 * File operations - read-only for safety
 */
const listFiles = tool({
  description: 'List files in a directory',
  inputSchema: z.object({
    path: z.string().describe('Directory path to list files from').optional(),
  }),
  execute: async ({ path = '.' }) => {
    try {
      const fs = await import('node:fs/promises');
      const files = await fs.readdir(path);
      return `Files in ${path}:\n${files.map((f: string) => `  - ${f}`).join('\n')}`;
    } catch (error) {
      return `Error listing files in "${path}": ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  },
});

/**
 * Export all available tools
 * Add your custom tools to this object
 */
export const tools = {
  getCurrentTime,
  calculate,
  getSystemInfo,
  getWeather,
  listFiles,
};

/**
 * Tool types for TypeScript
 */
export type ToolName = keyof typeof tools;
