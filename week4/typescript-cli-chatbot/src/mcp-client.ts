import * as readline from 'node:readline';
import { openai } from '@ai-sdk/openai';
import { generateText, streamText, type CoreMessage, tool } from 'ai';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { z } from 'zod';
import dotenv from 'dotenv';

dotenv.config();

interface MCPServer {
  name: string;
  command: string;
  args?: string[];
  client?: Client;
}

class MCPCLIAgent {
  public messages: CoreMessage[] = [];
  private mcpServers: MCPServer[] = [];
  private availableTools: any[] = [];

  constructor() {
    this.mcpServers = [
      {
        name: 'chatbot-tools',
        command: 'node',
        args: ['dist/mcp-server.js'],
      },
    ];
  }

  async initialize() {
    console.log('Initializing MCP connections...');

    for (const serverConfig of this.mcpServers) {
      try {
        await this.connectToMCPServer(serverConfig);
      } catch (error) {
        console.error(`Failed to connect to ${serverConfig.name}:`, error);
      }
    }

    await this.loadAvailableTools();
    console.log(`Loaded ${this.availableTools.length} tools from MCP servers`);
  }

  private async connectToMCPServer(serverConfig: MCPServer) {
    const transport = new StdioClientTransport({
      command: serverConfig.command,
      args: serverConfig.args || [],
      stderr: 'pipe', // Capture stderr for error handling
    });

    const client = new Client(
      {
        name: 'typescript-cli-chatbot-client',
        version: '1.0.0',
      },
      {
        capabilities: {},
      }
    );

    try {
      await client.connect(transport);
      serverConfig.client = client;
      console.log(`Connected to MCP server: ${serverConfig.name}`);

      // Handle stderr from the server process when needed
      const stderrStream = transport.stderr;
      if (stderrStream) {
        stderrStream.on('data', (data) => {
          const message = data.toString().trim();
          if (message && !message.includes('MCP Server running')) {
            console.error(`${serverConfig.name} stderr:`, message);
          }
        });
      }
    } catch (error) {
      console.error(`Failed to connect to ${serverConfig.name}:`, error);
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
          console.error(
            `Error loading tools from ${serverConfig.name}:`,
            error
          );
        }
      }
    }
  }

  async onChatMessage(onFinish?: (result: any) => void) {
    const tools = this.createAISDKTools();
    const systemPrompt = this.generateSystemPrompt();

    const result = streamText({
      model: openai('gpt-4o-mini'),
      messages: this.messages,
      tools,
      system: systemPrompt,
      onFinish: onFinish || (() => {}),
    });

    return result;
  }

  async generateResponse() {
    const tools = this.createAISDKTools();
    const systemPrompt = this.generateSystemPrompt();

    return await generateText({
      model: openai('gpt-4o-mini'),
      messages: this.messages,
      tools,
      system: systemPrompt,
    });
  }

  private createAISDKTools() {
    const tools: any = {};

    for (const mcpTool of this.availableTools) {
      const zodSchema = this.createZodSchemaFromMCP(mcpTool.inputSchema);

      tools[mcpTool.name] = tool({
        description: mcpTool.description,
        inputSchema: zodSchema,
        execute: async (params: any) => {
          try {
            console.log(`Executing tool: ${mcpTool.name}`, params);

            const response = await mcpTool.client.callTool({
              name: mcpTool.name,
              arguments: params,
            });

            if (response.content && response.content.length > 0) {
              const result = response.content
                .filter((item: any) => item.type === 'text')
                .map((item: any) => item.text)
                .join('\n');

              console.log(
                `Tool result: ${result.substring(0, 100)}${result.length > 100 ? '...' : ''}`
              );
              return result;
            }

            return 'Tool executed successfully but returned no content.';
          } catch (error) {
            const errorMsg = `Error executing ${mcpTool.name}: ${error instanceof Error ? error.message : 'Unknown error'}`;
            console.log(`${errorMsg}`);
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

        // Create appropriate Zod schema based on property type
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
            // Default to string for unknown types
            zodField = z.string();
        }

        // Add description if available
        if (property.description) {
          zodField = zodField.describe(property.description);
        }

        // Make field optional if it's not in the required array
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

  private generateSystemPrompt(): string {
    let systemPrompt =
      'You are a helpful AI assistant with access to various tools via MCP (Model Context Protocol) servers. Use the available tools when appropriate to help users.';

    if (this.availableTools.length > 0) {
      systemPrompt += '\n\nAvailable tools:';
      for (const tool of this.availableTools) {
        systemPrompt += `\n- ${tool.name}: ${tool.description}`;

        // Add parameter information if available
        if (tool.inputSchema?.properties) {
          const params = Object.keys(tool.inputSchema.properties);
          if (params.length > 0) {
            systemPrompt += ` (parameters: ${params.join(', ')})`;
          }
        }
      }

      systemPrompt +=
        "\n\nUse these tools proactively when they can help answer the user's questions or complete their requests. IMPORTANT: When you call a tool, you MUST provide a natural language response that interprets the tool's output in a user-friendly way. Never leave the user with just tool output - always explain what the result means and provide helpful context. For example, if you get time data, say 'The current time is [time]' rather than just showing raw output.";
    }

    return systemPrompt;
  }

  addMessage(message: CoreMessage) {
    this.messages.push(message);
  }

  clearHistory() {
    this.messages = [];
    console.log('Conversation history cleared');
  }

  getState() {
    return {
      messageCount: this.messages.length,
      lastMessageRole: this.messages[this.messages.length - 1]?.role || null,
      availableTools: this.availableTools.length,
      mcpServers: this.mcpServers.length,
    };
  }

  async cleanup() {
    for (const serverConfig of this.mcpServers) {
      if (serverConfig.client) {
        await serverConfig.client.close();
      }
    }
  }
}

class MCPCLIChatbot {
  private rl: readline.Interface;
  private agent: MCPCLIAgent;

  constructor() {
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      prompt: '> ',
    });

    this.agent = new MCPCLIAgent();
  }

  async start() {
    console.log('Starting MCP-enabled CLI Chatbot...');

    try {
      await this.agent.initialize();
    } catch (error) {
      console.error('Failed to initialize MCP connections:', error);
      process.exit(1);
    }

    console.log(
      'Type "exit", "quit", "clear", "status" or press Ctrl+C to exit\n'
    );

    this.rl.prompt();

    this.rl.on('line', async (input: string) => {
      const trimmed = input.trim();

      if (trimmed === 'exit' || trimmed === 'quit') {
        await this.cleanup();
        return;
      }

      if (trimmed === 'clear') {
        this.agent.clearHistory();
        this.rl.prompt();
        return;
      }

      if (trimmed === 'status') {
        const state = this.agent.getState();
        console.log('\nAgent Status:');
        console.log(`  Messages: ${state.messageCount}`);
        console.log(`  Available Tools: ${state.availableTools}`);
        console.log(`  MCP Servers: ${state.mcpServers}`);
        console.log('');
        this.rl.prompt();
        return;
      }

      if (trimmed === '') {
        this.rl.prompt();
        return;
      }

      await this.handleUserInput(trimmed);
      this.rl.prompt();
    });

    this.rl.on('close', async () => {
      await this.cleanup();
    });

    // Handle Ctrl+C
    process.on('SIGINT', async () => {
      await this.cleanup();
    });
  }

  private async handleUserInput(input: string) {
    try {
      this.agent.addMessage({
        role: 'user',
        content: input,
      });

      const result = await this.agent.generateResponse();

      // by default, when a tool is called the agent doesn't generate a response
      // so as a workaround we feed the tool result into the message log
      if (
        result.toolCalls &&
        result.toolCalls.length > 0 &&
        (!result.text || result.text.trim() === '')
      ) {
        this.agent.addMessage({
          role: 'assistant',
          content: result.text || '',
        });

        const toolResults = result.toolCalls
          .map((call) => {
            const toolResult = result.toolResults?.find(
              (r) => r.toolCallId === call.toolCallId
            );
            return `${call.toolName} returned: ${toolResult?.output || 'No result'}`;
          })
          .join('\n');

        this.agent.addMessage({
          role: 'user',
          content: `Based on the tool results:\n${toolResults}\n\nPlease provide a natural language response to my original question.`,
        });

        const interpretResult = await this.agent.generateResponse();

        this.agent.addMessage({
          role: 'assistant',
          content: interpretResult.text,
        });

        console.log(`\n${interpretResult.text || 'No response generated'}\n`);
      } else {
        this.agent.addMessage({
          role: 'assistant',
          content: result.text || '',
        });

        console.log(`\n${result.text || 'No response generated'}\n`);
      }

      if (result.toolCalls && result.toolCalls.length > 0) {
        console.log('Tools executed via MCP:');
        for (const toolCall of result.toolCalls) {
          console.log(`  - ${toolCall.toolName}`);
        }
        console.log('');
      }
    } catch (error: any) {
      console.error(`Error: ${error.message}\n`);
      // Remove the failed user message
      if (this.agent.messages.length > 0) {
        this.agent.messages.pop();
      }
    }
  }

  private async cleanup() {
    console.log('\nCleaning up MCP connections...');
    await this.agent.cleanup();
    console.log('Goodbye!');
    this.rl.close();
    process.exit(0);
  }

  getAgent(): MCPCLIAgent {
    return this.agent;
  }
}

// Start the MCP-enabled chatbot
const chatbot = new MCPCLIChatbot();
chatbot.start().catch(console.error);
