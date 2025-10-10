import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { tool } from 'ai';
import { z } from 'zod';
import { MCPServer } from './types.js';

export class MCPManager {
  private mcpServers: MCPServer[] = [];
  private availableTools: any[] = [];

  constructor() {
    this.initializeMCPServers();
  }

  private initializeMCPServers() {
    this.mcpServers = [
      {
        name: 'yahoo-finance',
        command: 'uv',
        args: ['run', 'server.py'],
        enabled: process.env.ENABLE_STOCK_ANALYSIS === 'true',
      },
    ];
  }

  async initialize(): Promise<void> {
    for (const serverConfig of this.mcpServers) {
      if (serverConfig.enabled) {
        try {
          await this.connectToMCPServer(serverConfig);
        } catch (error) {
          console.log(`⚠️  Optional MCP server ${serverConfig.name} not available: ${error}`);
        }
      }
    }

    await this.loadAvailableTools();
    console.log(`✅ Loaded ${this.availableTools.length} external MCP tools`);
  }

  private async connectToMCPServer(serverConfig: MCPServer) {
    const yahooPythonPath = process.env.YAHOO_FINANCE_MCP_PATH;
    if (!yahooPythonPath && serverConfig.name === 'yahoo-finance') {
      throw new Error('Yahoo Finance MCP path not configured');
    }

    const transport = new StdioClientTransport({
      command: serverConfig.command,
      args: serverConfig.args || [],
      cwd: yahooPythonPath || undefined,
      stderr: 'pipe',
    });

    const client = new Client(
      {
        name: 'financebot-client',
        version: '1.0.0',
      },
      {
        capabilities: {},
      }
    );

    try {
      await client.connect(transport);
      serverConfig.client = client;
      console.log(`📈 Connected to ${serverConfig.name} MCP server`);

      const stderrStream = transport.stderr;
      if (stderrStream) {
        stderrStream.on('data', data => {
          const message = data.toString().trim();
          if (message && !message.includes('Server running')) {
            console.error(`${serverConfig.name}:`, message);
          }
        });
      }
    } catch (error) {
      throw error;
    }
  }

  private async loadAvailableTools() {
    this.availableTools = [];

    for (const serverConfig of this.mcpServers) {
      if (serverConfig.client) {
        try {
          const response = await serverConfig.client.listTools();
          for (const tool of response.tools) {
            this.availableTools.push({
              ...tool,
              serverName: serverConfig.name,
              client: serverConfig.client,
            });
          }
        } catch (error) {
          console.error(`Error loading tools from ${serverConfig.name}:`, error);
        }
      }
    }
  }

  createMCPTools(): any {
    const tools: any = {};

    for (const mcpTool of this.availableTools) {
      const zodSchema = this.createZodSchemaFromMCP(mcpTool.inputSchema);

      tools[mcpTool.name] = tool({
        description: mcpTool.description,
        inputSchema: zodSchema,
        execute: async (params: any) => {
          try {
            const response = await mcpTool.client.callTool({
              name: mcpTool.name,
              arguments: params,
            });

            if (response.content && response.content.length > 0) {
              return response.content
                .filter((item: any) => item.type === 'text')
                .map((item: any) => item.text)
                .join('\n');
            }

            return 'Tool executed successfully but returned no content.';
          } catch (error) {
            const errorMsg = `Error executing ${mcpTool.name}: ${error instanceof Error ? error.message : 'Unknown error'}`;
            return errorMsg;
          }
        },
      });
    }

    return tools;
  }

  private createZodSchemaFromMCP(inputSchema: any): z.ZodSchema {
    if (!inputSchema || inputSchema.type !== 'object') {
      return z.object({});
    }

    const shape: Record<string, z.ZodSchema> = {};

    if (inputSchema.properties) {
      for (const [key, prop] of Object.entries(inputSchema.properties)) {
        const property = prop as any;
        let zodField: z.ZodSchema;

        switch (property.type) {
          case 'string':
            zodField = z.string();
            break;
          case 'number':
            zodField = z.number();
            break;
          case 'integer':
            zodField = z.number().int();
            break;
          case 'boolean':
            zodField = z.boolean();
            break;
          case 'array':
            zodField = z.array(z.any());
            break;
          default:
            zodField = z.string();
        }

        if (property.description) {
          zodField = zodField.describe(property.description);
        }

        const isRequired =
          inputSchema.required &&
          Array.isArray(inputSchema.required) &&
          inputSchema.required.includes(key);
        if (!isRequired) {
          zodField = zodField.optional();
        }

        shape[key] = zodField;
      }
    }

    return z.object(shape);
  }

  getAvailableTools(): any[] {
    return this.availableTools;
  }

  getConnectedServerCount(): number {
    return this.mcpServers.filter(s => s.enabled && s.client).length;
  }

  async cleanup(): Promise<void> {
    for (const serverConfig of this.mcpServers) {
      if (serverConfig.client) {
        await serverConfig.client.close();
      }
    }
  }
}
