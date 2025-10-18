/**
 * Example: Basic MCP Client Usage
 * This example demonstrates how to connect to an MCP server and call tools directly
 */

import { MCPClient } from '../src/mcp-client';

async function basicMCPExample() {
  // Create an MCP client
  const client = new MCPClient('https://gitmcp.io/cloudflare/agents');
  
  try {
    // Initialize the connection
    console.log('Initializing MCP connection...');
    const initResult = await client.initialize();
    console.log('Connected to:', initResult.serverInfo.name);
    
    // List available tools
    console.log('\nFetching available tools...');
    const tools = await client.listTools();
    console.log(`Found ${tools.length} tools:`);
    
    tools.forEach((tool, index) => {
      console.log(`${index + 1}. ${tool.name}: ${tool.description || 'No description'}`);
    });
    
    // Generate TypeScript API
    console.log('\nGenerating TypeScript API...');
    const api = await client.generateTypeScriptAPI();
    console.log('Generated API functions:', Object.keys(api));
    
    // Generate type definitions
    console.log('\nGenerating TypeScript definitions...');
    const typeDefs = await client.generateTypeDefinitions();
    console.log('Type definitions generated (truncated):');
    console.log(typeDefs.substring(0, 500) + '...');
    
    // Example tool call (if available)
    if (tools.length > 0) {
      console.log('\nTrying to call a tool...');
      try {
        const result = await client.callTool(tools[0].name, {});
        console.log('Tool result:', JSON.stringify(result, null, 2));
      } catch (error) {
        console.log('Tool call failed (expected for demo):', error instanceof Error ? error.message : error);
      }
    }
    
  } catch (error) {
    console.error('Error:', error instanceof Error ? error.message : error);
  } finally {
    await client.close();
  }
}

// Run the example
if (typeof module !== 'undefined' && require.main === module) {
  basicMCPExample().catch(console.error);
}

export { basicMCPExample };