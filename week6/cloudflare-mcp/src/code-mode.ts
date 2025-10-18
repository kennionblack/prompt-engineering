import { MCPClient } from "./mcp-client";
import { Env, GeneratedToolAPI } from "./types";

/**
 * Code Mode implementation for Cloudflare Workers
 * Converts MCP tools into TypeScript APIs that can be executed in sandboxed workers
 */
export class CodeMode {
  private mcpClient: MCPClient;
  private env: Env;
  private generatedAPI?: GeneratedToolAPI;

  constructor(serverUrl: string, env: Env) {
    this.mcpClient = new MCPClient(serverUrl);
    this.env = env;
  }

  /**
   * Initialize the code mode environment
   */
  async initialize(): Promise<void> {
    await this.mcpClient.initialize();
    this.generatedAPI = await this.mcpClient.generateTypeScriptAPI();
  }

  /**
   * Generate TypeScript code that can be executed in a worker
   */
  async generateWorkerCode(userCode: string): Promise<string> {
    if (!this.generatedAPI) {
      await this.initialize();
    }

    const typeDefinitions = await this.mcpClient.generateTypeDefinitions();

    const workerCode = `
${typeDefinitions}

// User's generated code
async function executeUserCode() {
  ${userCode}
}

// Export default handler for Worker
export default {
  async fetch(request, env, ctx) {
    try {
      const result = await executeUserCode();
      
      // Log the result for the agent to see
      console.log(JSON.stringify(result, null, 2));
      
      return new Response(JSON.stringify({
        success: true,
        result
      }), {
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('Execution error:', errorMessage);
      
      return new Response(JSON.stringify({
        success: false,
        error: errorMessage
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};
`;

    return workerCode;
  }

  /**
   * Execute user code in a sandboxed worker
   */
  async executeInWorker(userCode: string, workerId?: string): Promise<any> {
    const workerCode = await this.generateWorkerCode(userCode);
    const id = workerId || `codemode-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Create a worker with the generated code
    const worker = await this.env.LOADER.get(id, async () => {
      return {
        compatibilityDate: "2024-10-21",
        mainModule: "index.js",
        modules: {
          "index.js": workerCode,
        },
        env: {
          // Pass through any necessary environment variables
          // but don't expose sensitive keys directly
        },
        // Block internet access - tools can only access MCP servers through bindings
        globalOutbound: null,
      };
    });

    // Execute the code by sending a request to the worker
    const entrypoint = (worker as any).getEntrypoint();
    const response = await entrypoint.fetch(new Request("http://localhost/"));

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error);
    }

    return result.result;
  }

  /**
   * Create a codemode tool that can be used with AI SDK
   */
  createCodemodeTool() {
    return {
      name: "codemode",
      description: "Execute TypeScript code that can call MCP tools",
      parameters: {
        type: "object",
        properties: {
          code: {
            type: "string",
            description: "TypeScript code to execute",
          },
          explanation: {
            type: "string",
            description: "Brief explanation of what the code does",
          },
        },
        required: ["code"],
      },
      execute: async ({ code, explanation }: { code: string; explanation?: string }) => {
        try {
          console.log(`Executing code: ${explanation || "No description"}`);
          const result = await this.executeInWorker(code);
          return result;
        } catch (error) {
          return {
            error: error instanceof Error ? error.message : String(error),
            success: false,
          };
        }
      },
    };
  }

  /**
   * Get the generated TypeScript API for direct use
   */
  getGeneratedAPI(): GeneratedToolAPI | undefined {
    return this.generatedAPI;
  }

  /**
   * Get type definitions for the generated API
   */
  async getTypeDefinitions(): Promise<string> {
    return await this.mcpClient.generateTypeDefinitions();
  }

  /**
   * Close the code mode instance
   */
  async close(): Promise<void> {
    await this.mcpClient.close();
  }
}

/**
 * Helper function to create a code mode instance with proper configuration
 */
export function createCodeMode(serverUrl: string, env: Env): CodeMode {
  return new CodeMode(serverUrl, env);
}

/**
 * Experimental codemode wrapper compatible with AI SDK
 * Based on the Cloudflare Agents SDK pattern
 */
export async function experimental_codemode(config: {
  prompt: string;
  tools?: Record<string, any>;
  serverUrl: string;
  env: Env;
  useMock?: boolean;
}) {
  const codeMode = createCodeMode(config.serverUrl, config.env);

  try {
    await codeMode.initialize();
  } catch (error) {
    console.warn("Failed to initialize MCP server, falling back to mock mode:", error);
    // If MCP server fails, we could fall back to mock mode here
    throw error;
  }

  // Create the codemode tool
  const codemodetool = codeMode.createCodemodeTool();

  // Combine with existing tools
  const wrappedTools = {
    ...config.tools,
    codemode: codemodetool,
  };

  // Enhanced prompt to encourage code generation
  const enhancedPrompt = `${config.prompt}

You have access to a powerful codemode tool that lets you write and execute TypeScript code. 
When you need to perform complex operations or chain multiple tool calls, generate TypeScript code using the codemode tool instead of calling tools directly.

The codemode environment provides access to MCP tools through a TypeScript API. You can write code that:
- Makes multiple tool calls in sequence
- Implements complex logic and control flow
- Handles errors and retries
- Processes and transforms data between tool calls

Always explain what your code does when using the codemode tool.`;

  return {
    prompt: enhancedPrompt,
    tools: wrappedTools,
    codeMode,
  };
}
