import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import * as os from 'node:os';
import * as fs from 'node:fs/promises';

class ChatbotMCPServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: 'typescript-cli-chatbot',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupErrorHandling();
  }

  private setupToolHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'getCurrentTime',
            description: 'Get the current date and time',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
          {
            name: 'calculate',
            description: 'Perform basic mathematical calculations',
            inputSchema: {
              type: 'object',
              properties: {
                expression: {
                  type: 'string',
                  description:
                    'Mathematical expression to evaluate (e.g., "2 + 2", "10 * 5")',
                },
              },
              required: ['expression'],
            },
          },
          {
            name: 'getSystemInfo',
            description: 'Get basic system information',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
          {
            name: 'getWeather',
            description: 'Get weather information for a city',
            inputSchema: {
              type: 'object',
              properties: {
                city: {
                  type: 'string',
                  description: 'The city to get weather for',
                },
              },
              required: ['city'],
            },
          },
          {
            name: 'listFiles',
            description: 'List files in a directory',
            inputSchema: {
              type: 'object',
              properties: {
                path: {
                  type: 'string',
                  description: 'Directory path to list files from',
                  default: '.',
                },
              },
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'getCurrentTime':
            return {
              content: [
                {
                  type: 'text',
                  text: new Date().toLocaleString(),
                },
              ],
            };

          case 'calculate':
            return {
              content: [
                {
                  type: 'text',
                  text: await this.handleCalculate(args?.expression as string),
                },
              ],
            };

          case 'getSystemInfo':
            return {
              content: [
                {
                  type: 'text',
                  text: await this.handleGetSystemInfo(),
                },
              ],
            };

          case 'getWeather':
            return {
              content: [
                {
                  type: 'text',
                  text: await this.handleGetWeather(args?.city as string),
                },
              ],
            };

          case 'listFiles':
            return {
              content: [
                {
                  type: 'text',
                  text: await this.handleListFiles(args?.path as string),
                },
              ],
            };

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error executing ${name}: ${error instanceof Error ? error.message : 'Unknown error'}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  private async handleCalculate(expression: string): Promise<string> {
    try {
      if (!/^[0-9+\-*/().\s]+$/.test(expression)) {
        throw new Error('Invalid characters in expression');
      }

      const result = new Function(`return ${expression}`)();
      return `${expression} = ${result}`;
    } catch (error) {
      return `Error calculating "${expression}": ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  }

  private async handleGetSystemInfo(): Promise<string> {
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
  }

  private async handleGetWeather(city: string): Promise<string> {
    // TODO: Replace with actual weather API call
    return `Weather information for ${city} is not implemented yet. You would need to integrate with a weather API like OpenWeatherMap.`;
  }

  private async handleListFiles(path: string = '.'): Promise<string> {
    try {
      const files = await fs.readdir(path);
      return `Files in ${path}:\n${files.map((f: string) => `  - ${f}`).join('\n')}`;
    } catch (error) {
      return `Error listing files in "${path}": ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  }

  private setupErrorHandling() {
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('TypeScript CLI Chatbot MCP Server running on stdio');
  }
}

// Start the server
const server = new ChatbotMCPServer();
server.run().catch(console.error);
