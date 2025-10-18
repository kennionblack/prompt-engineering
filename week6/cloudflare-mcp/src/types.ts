/**
 * MCP (Model Context Protocol) Types
 * Based on the MCP specification
 */

export interface MCPRequest {
  jsonrpc: '2.0';
  id: string | number;
  method: string;
  params?: any;
}

export interface MCPResponse {
  jsonrpc: '2.0';
  id: string | number;
  result?: any;
  error?: MCPError;
}

export interface MCPError {
  code: number;
  message: string;
  data?: any;
}

export interface MCPNotification {
  jsonrpc: '2.0';
  method: string;
  params?: any;
}

export interface MCPTool {
  name: string;
  description?: string;
  inputSchema: {
    type: 'object';
    properties: Record<string, any>;
    required?: string[];
  };
}

export interface MCPToolCall {
  name: string;
  arguments: Record<string, any>;
}

export interface MCPToolResult {
  content: Array<{
    type: 'text';
    text: string;
  }>;
  isError?: boolean;
}

export interface MCPServerCapabilities {
  tools?: {
    listChanged?: boolean;
  };
  logging?: {};
  prompts?: {
    listChanged?: boolean;
  };
  resources?: {
    subscribe?: boolean;
    listChanged?: boolean;
  };
}

export interface MCPClientCapabilities {
  experimental?: Record<string, any>;
  sampling?: {};
}

export interface MCPInitializeParams {
  protocolVersion: string;
  capabilities: MCPClientCapabilities;
  clientInfo: {
    name: string;
    version: string;
  };
}

export interface MCPInitializeResult {
  protocolVersion: string;
  capabilities: MCPServerCapabilities;
  serverInfo: {
    name: string;
    version: string;
  };
}

// Cloudflare Workers specific types
export interface Env {
  LOADER: WorkerLoader;
  OPENAI_API_KEY?: string;
  MCP_SERVER_URL?: string;
}

export interface WorkerLoader {
  get(id: string, factory?: () => Promise<WorkerDefinition>): Promise<Worker>;
}

export interface WorkerDefinition {
  compatibilityDate: string;
  mainModule: string;
  modules: Record<string, string>;
  env?: Record<string, any>;
  globalOutbound?: any;
}

export interface CodeModeConfig {
  prompt: string;
  tools: Record<string, any>;
  globalOutbound?: any;
  loader: WorkerLoader;
  proxy: any;
}

export interface GeneratedToolAPI {
  [toolName: string]: (input: any) => Promise<any>;
}