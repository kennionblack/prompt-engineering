import {
  MCPRequest,
  MCPResponse,
  MCPError,
  MCPTool,
  MCPToolCall,
  MCPToolResult,
  MCPInitializeParams,
  MCPInitializeResult,
  GeneratedToolAPI,
} from "./types";

/**
 * MCP Client implementation for Cloudflare Workers
 * Handles communication with MCP servers and converts tools to TypeScript APIs
 */
export class MCPClient {
  private serverUrl: string;
  private requestId = 0;
  private tools: Map<string, MCPTool> = new Map();
  private isInitialized = false;

  constructor(serverUrl: string) {
    this.serverUrl = serverUrl;
  }

  /**
   * Generate a unique request ID
   */
  private getNextRequestId(): string {
    return (++this.requestId).toString();
  }

  /**
   * Send an MCP request to the server
   */
  protected async sendRequest(method: string, params?: any): Promise<any> {
    const request: MCPRequest = {
      jsonrpc: "2.0",
      id: this.getNextRequestId(),
      method,
      params,
    };

    const response = await fetch(this.serverUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const mcpResponse: MCPResponse = await response.json();

    if (mcpResponse.error) {
      throw new Error(`MCP Error: ${mcpResponse.error.message}`);
    }

    return mcpResponse.result;
  }

  /**
   * Initialize the MCP connection
   */
  async initialize(): Promise<MCPInitializeResult> {
    const params: MCPInitializeParams = {
      protocolVersion: "2024-11-05",
      capabilities: {
        sampling: {},
      },
      clientInfo: {
        name: "cloudflare-mcp-client",
        version: "1.0.0",
      },
    };

    const result = await this.sendRequest("initialize", params);

    // Send initialized notification
    await this.sendNotification("notifications/initialized");

    this.isInitialized = true;
    return result;
  }

  /**
   * Send a notification (no response expected)
   */
  protected async sendNotification(method: string, params?: any): Promise<void> {
    const notification = {
      jsonrpc: "2.0",
      method,
      params,
    };

    await fetch(this.serverUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(notification),
    });
  }

  /**
   * List available tools from the MCP server
   */
  async listTools(): Promise<MCPTool[]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const result = await this.sendRequest("tools/list");
    const tools: MCPTool[] = result.tools || [];

    // Cache tools for later use
    tools.forEach((tool) => {
      this.tools.set(tool.name, tool);
    });

    return tools;
  }

  /**
   * Call a specific tool
   */
  async callTool(name: string, arguments_: Record<string, any>): Promise<MCPToolResult> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const result = await this.sendRequest("tools/call", {
      name,
      arguments: arguments_,
    });

    return result;
  }

  /**
   * Generate TypeScript API from MCP tools
   * This converts MCP tools into a more natural programming interface
   */
  async generateTypeScriptAPI(): Promise<GeneratedToolAPI> {
    const tools = await this.listTools();
    const api: GeneratedToolAPI = {};

    for (const tool of tools) {
      // Convert tool name to camelCase function name
      const functionName = this.toCamelCase(tool.name);

      // Create a typed function that calls the MCP tool
      api[functionName] = async (input: any) => {
        try {
          const result = await this.callTool(tool.name, input);

          // Return the content as a more natural format
          if (result.content && result.content.length > 0) {
            if (result.content.length === 1 && result.content[0].type === "text") {
              // If single text result, return just the text
              return result.content[0].text;
            }
            // Otherwise return the full content array
            return result.content;
          }

          return result;
        } catch (error) {
          throw new Error(
            `Tool '${tool.name}' failed: ${error instanceof Error ? error.message : String(error)}`
          );
        }
      };
    }

    return api;
  }

  /**
   * Generate TypeScript type definitions for the tools
   */
  async generateTypeDefinitions(): Promise<string> {
    const tools = await this.listTools();
    let definitions = "// Generated TypeScript definitions for MCP tools\n\n";

    for (const tool of tools) {
      const functionName = this.toCamelCase(tool.name);
      const inputType = this.generateInputType(tool);

      definitions += `/**\n * ${tool.description || `Call ${tool.name} tool`}\n */\n`;
      definitions += `${functionName}: (input: ${inputType}) => Promise<any>;\n\n`;
    }

    return `declare const codemode: {\n${definitions}};`;
  }

  /**
   * Convert snake_case or kebab-case to camelCase
   */
  private toCamelCase(str: string): string {
    return str.replace(/[-_]([a-z])/g, (match, letter) => letter.toUpperCase());
  }

  /**
   * Generate TypeScript input type from MCP tool schema
   */
  private generateInputType(tool: MCPTool): string {
    if (!tool.inputSchema || tool.inputSchema.type !== "object") {
      return "any";
    }

    const properties = tool.inputSchema.properties || {};
    const required = tool.inputSchema.required || [];

    const typeProps: string[] = [];

    for (const [propName, propSchema] of Object.entries(properties)) {
      const isOptional = !required.includes(propName);
      const propType = this.schemaToTypeScript(propSchema);
      const description = propSchema.description ? `\n  /** ${propSchema.description} */\n  ` : "";

      typeProps.push(`${description}${propName}${isOptional ? "?" : ""}: ${propType}`);
    }

    if (typeProps.length === 0) {
      return "{}";
    }

    return `{\n  ${typeProps.join(";\n  ")}\n}`;
  }

  /**
   * Convert JSON Schema type to TypeScript type
   */
  private schemaToTypeScript(schema: any): string {
    if (!schema || typeof schema !== "object") {
      return "any";
    }

    switch (schema.type) {
      case "string":
        return "string";
      case "number":
      case "integer":
        return "number";
      case "boolean":
        return "boolean";
      case "array":
        const itemType = schema.items ? this.schemaToTypeScript(schema.items) : "any";
        return `${itemType}[]`;
      case "object":
        if (schema.properties) {
          return this.generateInputType({ inputSchema: schema } as MCPTool);
        }
        return "Record<string, any>";
      default:
        return "any";
    }
  }

  /**
   * Get cached tool information
   */
  getTool(name: string): MCPTool | undefined {
    return this.tools.get(name);
  }

  /**
   * Close the MCP connection
   */
  async close(): Promise<void> {
    // MCP doesn't have a formal close method, but we can clean up
    this.tools.clear();
    this.isInitialized = false;
  }
}
