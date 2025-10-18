/**
 * Example: Code Mode with AI Agent
 * This example shows how to use code mode with an AI agent to perform complex tasks
 */

import { experimental_codemode } from '../src/code-mode';
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

// Mock environment for example (in real use, this comes from Cloudflare Workers)
const mockEnv = {
  LOADER: {
    async get(id: string, factory?: () => Promise<any>) {
      // Mock implementation - in real Workers this would create actual isolates
      console.log(`Would create worker with ID: ${id}`);
      if (factory) {
        const definition = await factory();
        console.log('Worker definition:', {
          compatibilityDate: definition.compatibilityDate,
          mainModule: definition.mainModule,
          moduleCount: Object.keys(definition.modules || {}).length
        });
      }
      
      // Return mock worker
      return {
        getEntrypoint: () => ({
          fetch: async (request: Request) => {
            // Mock execution result
            return new Response(JSON.stringify({
              success: true,
              result: 'Mock execution result'
            }), {
              headers: { 'Content-Type': 'application/json' }
            });
          }
        })
      };
    }
  } as any,
  OPENAI_API_KEY: 'mock-key-for-demo',
  MCP_SERVER_URL: 'https://gitmcp.io/cloudflare/agents'
};

async function codeModeExample() {
  try {
    console.log('Setting up Code Mode...');
    
    // Initialize code mode with MCP server
    const { prompt, tools, codeMode } = await experimental_codemode({
      prompt: `You are a helpful AI assistant with access to development tools.
      When performing complex tasks, write TypeScript code using the codemode tool to chain operations together.
      Always explain what your code does.`,
      serverUrl: 'https://gitmcp.io/cloudflare/agents',
      env: mockEnv
    });
    
    console.log('Enhanced prompt:', prompt.substring(0, 200) + '...');
    console.log('Available tools:', Object.keys(tools));
    
    // Example: Direct code execution (mock)
    console.log('\nTesting direct code execution...');
    const sampleCode = `
      // Find documentation and search for specific topics
      const docs = await codemode.fetchAgentsDocumentation({});
      const searchResults = await codemode.searchAgentsDocumentation({
        query: "worker loader api"
      });
      
      return {
        docsLength: docs?.content?.length || 0,
        searchResults: searchResults?.results?.length || 0,
        timestamp: new Date().toISOString()
      };
    `;
    
    try {
      const result = await codeMode.executeInWorker(sampleCode);
      console.log('Code execution result:', result);
    } catch (error) {
      console.log('Code execution (mock):', error instanceof Error ? error.message : error);
    }
    
    // Example: Using with AI SDK (mock - requires real API key)
    console.log('\nExample AI SDK integration:');
    
    const exampleMessages = [
      {
        role: 'user' as const,
        content: 'Search the Cloudflare agents documentation for information about the Worker Loader API and summarize the key points'
      }
    ];
    
    console.log('Would create AI stream with:');
    console.log('- Model: gpt-4');
    console.log('- System prompt length:', prompt.length);
    console.log('- Tools available:', Object.keys(tools));
    console.log('- User message:', exampleMessages[0].content);
    
    // In a real implementation with API key:
    /*
    const stream = streamText({
      model: openai('gpt-4', { apiKey: mockEnv.OPENAI_API_KEY }),
      system: prompt,
      messages: exampleMessages,
      tools,
      maxTokens: 1500
    });
    
    for await (const chunk of stream.textStream) {
      process.stdout.write(chunk);
    }
    */
    
    // Show generated TypeScript definitions
    console.log('\nGenerated TypeScript definitions:');
    const typeDefs = await codeMode.getTypeDefinitions();
    console.log(typeDefs.substring(0, 800) + '...');
    
  } catch (error) {
    console.error('Error in code mode example:', error instanceof Error ? error.message : error);
  }
}

export { codeModeExample };

// Example usage
codeModeExample().catch(console.error);