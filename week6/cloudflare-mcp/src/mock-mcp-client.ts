import { MCPClient } from './mcp-client';
import { MCPRequest, MCPResponse, MCPTool } from './types';

/**
 * Mock MCP Client for testing and demonstrations
 * Simulates MCP protocol responses without needing a real server
 */
export class MockMCPClient extends MCPClient {
  private mockTools: MCPTool[] = [
    {
      name: 'fetch_agents_documentation',
      description: 'Fetch entire documentation file from GitHub repository: cloudflare/agents',
      inputSchema: {
        type: 'object',
        properties: {},
        required: []
      }
    },
    {
      name: 'search_agents_documentation', 
      description: 'Semantically search within the fetched documentation',
      inputSchema: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The search query to find relevant documentation'
          }
        },
        required: ['query']
      }
    },
    {
      name: 'search_agents_code',
      description: 'Search for code within the GitHub repository',
      inputSchema: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The search query to find relevant code files'
          },
          page: {
            type: 'number',
            description: 'Page number to retrieve (starting from 1)'
          }
        },
        required: ['query']
      }
    },
    {
      name: 'fetch_generic_url_content',
      description: 'Generic tool to fetch content from any absolute URL',
      inputSchema: {
        type: 'object',
        properties: {
          url: {
            type: 'string',
            description: 'The URL of the document or page to fetch'
          }
        },
        required: ['url']
      }
    }
  ];

  constructor(serverUrl: string = 'mock://localhost') {
    super(serverUrl);
  }

  /**
   * Override sendRequest to return mock responses
   */
  protected async sendRequest(method: string, params?: any): Promise<any> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 100 + Math.random() * 200));

    switch (method) {
      case 'initialize':
        return {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: { listChanged: false },
            logging: {}
          },
          serverInfo: {
            name: 'Mock MCP Server',
            version: '1.0.0'
          }
        };

      case 'tools/list':
        return {
          tools: this.mockTools
        };

      case 'tools/call':
        return this.mockToolCall(params.name, params.arguments);

      default:
        throw new Error(`Mock MCP Server: Unknown method ${method}`);
    }
  }

  private mockToolCall(toolName: string, args: any) {
    const responses = {
      'fetch_agents_documentation': {
        content: [{
          type: 'text',
          text: JSON.stringify({
            title: 'Cloudflare Agents Documentation',
            content: 'This is mock documentation content about Cloudflare Agents, Worker Loader API, and Code Mode features...',
            length: 15420,
            sections: ['Introduction', 'Code Mode', 'Worker Loader API', 'Examples']
          }, null, 2)
        }]
      },
      
      'search_agents_documentation': {
        content: [{
          type: 'text', 
          text: JSON.stringify({
            query: args.query || 'default search',
            results: [
              {
                title: 'Code Mode Documentation',
                excerpt: 'Code Mode is a better way to use MCP by generating TypeScript code...',
                score: 0.95,
                url: 'https://github.com/cloudflare/agents/blob/main/docs/codemode.md'
              },
              {
                title: 'Worker Loader API',
                excerpt: 'The Worker Loader API allows dynamic loading of Workers...',
                score: 0.87,
                url: 'https://developers.cloudflare.com/workers/runtime-apis/bindings/worker-loader/'
              }
            ],
            total: 2
          }, null, 2)
        }]
      },

      'search_agents_code': {
        content: [{
          type: 'text',
          text: JSON.stringify({
            query: args.query || 'typescript',
            page: args.page || 1,
            results: [
              {
                file: 'src/codemode.ts',
                path: 'packages/agents/src/codemode.ts', 
                matches: 3,
                preview: 'export class CodeMode { ... }'
              },
              {
                file: 'examples/basic.ts',
                path: 'packages/agents/examples/basic.ts',
                matches: 1,
                preview: 'import { codemode } from "agents/codemode";'
              }
            ],
            totalResults: 28,
            hasMore: true
          }, null, 2)
        }]
      },

      'fetch_generic_url_content': {
        content: [{
          type: 'text',
          text: JSON.stringify({
            url: args.url || 'https://example.com',
            title: 'Mock Web Page',
            content: 'This is mock content fetched from a URL. In a real implementation, this would contain the actual web page content.',
            contentType: 'text/html',
            length: 2048,
            timestamp: new Date().toISOString()
          }, null, 2)
        }]
      }
    };

    const response = responses[toolName as keyof typeof responses];
    if (!response) {
      throw new Error(`Mock MCP Server: Tool '${toolName}' not found`);
    }

    return response;
  }

  /**
   * Override sendNotification for mock
   */
  protected async sendNotification(method: string, params?: any): Promise<void> {
    // Mock notifications - just log them
    console.log(`Mock notification: ${method}`, params ? JSON.stringify(params) : '');
  }
}