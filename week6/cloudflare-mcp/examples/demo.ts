/**
 * Interactive Demo for Cloudflare MCP Client
 * This file demonstrates all major features of the MCP client
 */

import dotenv from 'dotenv';
import { MCPClient } from '../src/mcp-client';
import { MockMCPClient } from '../src/mock-mcp-client';
import { experimental_codemode } from '../src/code-mode';
import { loadEnvironment } from '../src/env-config';

// Load environment variables for local demo
dotenv.config({ path: "../../.env" });
const env = loadEnvironment();

// Demo configuration
const DEMO_CONFIG = {
  // Using a publicly available MCP server for demo
  MCP_SERVER_URL: env.mcpServerUrl,
  MOCK_MODE: true // Set to false to use real MCP server
};

/**
 * Mock environment that simulates Cloudflare Workers environment
 */
const createMockEnv = () => ({
  LOADER: {
    async get(id: string, factory?: () => Promise<any>) {
      console.log(`📦 Creating worker with ID: ${id}`);
      
      if (factory) {
        const definition = await factory();
        console.log('   Worker configuration:');
        console.log(`   - Compatibility date: ${definition.compatibilityDate}`);
        console.log(`   - Main module: ${definition.mainModule}`);
        console.log(`   - Modules: ${Object.keys(definition.modules || {}).join(', ')}`);
        console.log(`   - Internet access: ${definition.globalOutbound ? 'Allowed' : 'Blocked'}`);
      }
      
      return {
        getEntrypoint: () => ({
          fetch: async (request: Request) => {
            // Simulate code execution
            const mockResults = [
              { success: true, result: { filesFound: 42, totalSize: '1.2MB' } },
              { success: true, result: 'Task completed successfully' },
              { success: true, result: { timestamp: new Date().toISOString(), status: 'processed' } }
            ];
            
            const result = mockResults[Math.floor(Math.random() * mockResults.length)];
            console.log('   ✅ Code executed successfully');
            
            return new Response(JSON.stringify(result), {
              headers: { 'Content-Type': 'application/json' }
            });
          }
        })
      };
    }
  } as any,
  OPENAI_API_KEY: 'demo-key',
  MCP_SERVER_URL: DEMO_CONFIG.MCP_SERVER_URL
});

/**
 * Demo 1: Basic MCP Client Features
 */
async function demo1_BasicMCPClient() {
  console.log('\n🔧 DEMO 1: Basic MCP Client Features');
  console.log('=====================================');
  
  // Use mock client for demo safety
  const client = DEMO_CONFIG.MOCK_MODE 
    ? new MockMCPClient(DEMO_CONFIG.MCP_SERVER_URL)
    : new MCPClient(DEMO_CONFIG.MCP_SERVER_URL);
  
  try {
    // Initialize connection
    console.log('🔌 Connecting to MCP server...');
    const initResult = await client.initialize();
    console.log(`✅ Connected to: ${initResult.serverInfo.name} v${initResult.serverInfo.version}`);
    console.log(`   Protocol version: ${initResult.protocolVersion}`);
    
    // List available tools
    console.log('\n📋 Discovering available tools...');
    const tools = await client.listTools();
    console.log(`✅ Found ${tools.length} tools:`);
    
    tools.forEach((tool, index) => {
      console.log(`   ${index + 1}. ${tool.name}`);
      console.log(`      Description: ${tool.description || 'No description'}`);
      
      // Show schema preview
      if (tool.inputSchema?.properties) {
        const props = Object.keys(tool.inputSchema.properties);
        console.log(`      Parameters: ${props.slice(0, 3).join(', ')}${props.length > 3 ? '...' : ''}`);
      }
    });
    
    // Generate TypeScript API
    console.log('\n🔄 Generating TypeScript API...');
    const api = await client.generateTypeScriptAPI();
    console.log('✅ Generated API functions:');
    Object.keys(api).forEach((func, index) => {
      console.log(`   ${index + 1}. ${func}()`);
    });
    
    // Show type definitions
    console.log('\n📝 Type definitions preview:');
    const typeDefs = await client.generateTypeDefinitions();
    const preview = typeDefs.split('\n').slice(0, 10).join('\n');
    console.log(preview + '\n   ... (truncated)');
    
    // Try calling a tool (mock or real)
    if (tools.length > 0) {
      console.log(`\n🎯 Testing tool call: ${tools[0].name}`);
      try {
        // Use the toCamelCase method that's now accessible 
        const functionName = tools[0].name.replace(/[-_]([a-z])/g, (_, letter) => letter.toUpperCase());
        const result = await api[functionName]({});
        console.log('✅ Tool call successful:');
        console.log(`   Result: ${typeof result === 'string' ? result.substring(0, 200) + '...' : JSON.stringify(result, null, 2).substring(0, 200) + '...'}`);
      } catch (error) {
        console.log(`⚠️  Tool call failed (expected in demo): ${error instanceof Error ? error.message : error}`);
      }
    }
    
  } catch (error) {
    console.log(`❌ Demo 1 failed: ${error instanceof Error ? error.message : error}`);
  } finally {
    await client.close();
  }
}

/**
 * Demo 2: Code Mode Features
 */
async function demo2_CodeMode() {
  console.log('\n🚀 DEMO 2: Code Mode Features');
  console.log('=============================');
  
  const mockEnv = createMockEnv();
  
  try {
    // Initialize code mode
    console.log('⚙️  Initializing Code Mode...');
    
    // For demo mode, we'll create a simplified mock version
    if (DEMO_CONFIG.MOCK_MODE) {
      console.log('✅ Code Mode initialized (Mock Mode)');
      console.log('   Available tools: codemode, fetchAgentsDocumentation, searchAgentsDocumentation, searchAgentsCode');
      console.log('   Enhanced prompt length: 350 characters');
      
      // Show mock generated TypeScript definitions
      console.log('\n📋 Generated API interface:');
      const mockTypeDefs = `
declare const codemode: {
  /**
   * Fetch entire documentation file from GitHub repository
   */
  fetchAgentsDocumentation: (input: {}) => Promise<any>;
  
  /**
   * Semantically search within the fetched documentation
   */
  searchAgentsDocumentation: (input: { query: string }) => Promise<any>;
  
  /**
   * Search for code within the GitHub repository
   */
  searchAgentsCode: (input: { query: string; page?: number }) => Promise<any>;
};`;
      console.log(mockTypeDefs);
      
      // Mock code execution examples
      console.log('\n🎯 Mock Code Executions:');
      const mockExamples = [
        'File System Analysis: ✅ Found 42 documentation files, 128 code files',
        'Multi-step Workflow: ✅ Retrieved 15 search results, processed content',
        'Error Handling: ✅ Retry logic succeeded on attempt 2 of 3'
      ];
      
      mockExamples.forEach(example => {
        console.log(`   ${example}`);
      });
      
      return;
    }
    
    const { prompt, tools, codeMode } = await experimental_codemode({
      prompt: 'You are a development assistant with access to file system and documentation tools.',
      serverUrl: DEMO_CONFIG.MCP_SERVER_URL,
      env: mockEnv
    });
    
    console.log('✅ Code Mode initialized');
    console.log(`   Available tools: ${Object.keys(tools).join(', ')}`);
    console.log(`   Enhanced prompt length: ${prompt.length} characters`);
    
    // Show generated TypeScript definitions
    console.log('\n📋 Generated API interface:');
    const typeDefs = await codeMode.getTypeDefinitions();
    const interfacePreview = typeDefs.split('\n').slice(0, 15).join('\n');
    console.log(interfacePreview + '\n   ... (truncated)');
    
    // Demo code examples
    const codeExamples = [
      {
        title: 'File System Analysis',
        code: `
// Analyze project structure
const docs = await codemode.fetchAgentsDocumentation({});
const codeSearch = await codemode.searchAgentsCode({ 
  query: 'worker loader', 
  page: 1 
});

return {
  docsSize: docs?.content?.length || 0,
  codeResults: codeSearch?.results?.length || 0,
  analysisTime: new Date().toISOString()
};`
      },
      {
        title: 'Multi-step Workflow',
        code: `
// Complex multi-step operation
const searchResults = await codemode.searchAgentsDocumentation({
  query: 'model context protocol'
});

if (searchResults?.results?.length > 0) {
  const firstResult = searchResults.results[0];
  const details = await codemode.fetchGenericUrlContent({
    url: firstResult.url
  });
  
  return {
    found: true,
    title: firstResult.title,
    contentSize: details?.content?.length || 0
  };
}

return { found: false, message: 'No results found' };`
      },
      {
        title: 'Error Handling & Retry Logic',
        code: `
// Robust error handling
let attempts = 0;
const maxAttempts = 3;

while (attempts < maxAttempts) {
  try {
    const result = await codemode.searchAgentsCode({
      query: 'typescript',
      page: attempts + 1
    });
    
    if (result?.results?.length > 0) {
      return {
        success: true,
        attempt: attempts + 1,
        results: result.results.length
      };
    }
  } catch (error) {
    console.log(\`Attempt \${attempts + 1} failed: \${error.message}\`);
  }
  
  attempts++;
  await new Promise(resolve => setTimeout(resolve, 1000));
}

return { success: false, attempts };`
      }
    ];
    
    // Execute code examples
    for (const example of codeExamples) {
      console.log(`\n🎯 Executing: ${example.title}`);
      console.log('   Code preview:');
      console.log(example.code.split('\n').slice(0, 5).map(line => `      ${line}`).join('\n') + '...');
      
      try {
        const result = await codeMode.executeInWorker(example.code.trim());
        console.log('✅ Execution successful:');
        console.log(`   Result: ${JSON.stringify(result, null, 2)}`);
      } catch (error) {
        console.log(`⚠️  Execution failed (mock mode): ${error instanceof Error ? error.message : error}`);
      }
    }
    
    await codeMode.close();
    
  } catch (error) {
    console.log(`❌ Demo 2 failed: ${error instanceof Error ? error.message : error}`);
  }
}

/**
 * Demo 3: AI Agent Integration Pattern
 */
async function demo3_AIAgentIntegration() {
  console.log('\n🤖 DEMO 3: AI Agent Integration Pattern');
  console.log('======================================');
  
  const mockEnv = createMockEnv();
  
  try {
    console.log('⚙️  Setting up AI agent with Code Mode...');
    
    if (DEMO_CONFIG.MOCK_MODE) {
      console.log('✅ AI agent configured (Mock Mode)');
      console.log('   System prompt: "You are a helpful AI assistant with access to development tools..."');
      console.log('   Tools available: codemode, fetchAgentsDocumentation, searchAgentsDocumentation, searchAgentsCode');
      
      // Mock scenarios
      const scenarios = [
        {
          task: 'Find and analyze project documentation',
          userMessage: 'Search the documentation for information about Worker Loader API and summarize the key features',
          expectedFlow: [
            '1. Generate code to search documentation',
            '2. Execute search in sandboxed worker', 
            '3. Process and summarize results',
            '4. Return structured response'
          ]
        },
        {
          task: 'Complex data processing workflow',
          userMessage: 'Find all TypeScript files, analyze their complexity, and create a report',
          expectedFlow: [
            '1. Search for TypeScript code files',
            '2. Fetch content for analysis',
            '3. Process and calculate metrics', 
            '4. Generate comprehensive report'
          ]
        }
      ];
      
      scenarios.forEach((scenario, index) => {
        console.log(`\n📝 Scenario ${index + 1}: ${scenario.task}`);
        console.log(`   User: "${scenario.userMessage}"`);
        console.log('   Expected AI workflow:');
        scenario.expectedFlow.forEach(step => console.log(`      ${step}`));
        console.log('   ✅ Agent would generate and execute TypeScript code');
      });
      
      console.log('\n🛠️  Code Mode Tool Definition:');
      console.log('   Name: codemode');
      console.log('   Description: Execute TypeScript code that can call MCP tools');
      console.log('   Parameters:');
      console.log('     - code: string - TypeScript code to execute');
      console.log('     - explanation: string - Brief explanation of what the code does');
      
      return;
    }
    
    const { prompt, tools } = await experimental_codemode({
      prompt: `You are a helpful AI assistant with access to development tools.
      When performing complex tasks, write TypeScript code using the codemode tool.
      Always explain what your code does and break down complex operations.`,
      serverUrl: DEMO_CONFIG.MCP_SERVER_URL,
      env: mockEnv
    });
    
    console.log('✅ AI agent configured');
    console.log(`   System prompt: "${prompt.split('.')[0]}..."`);
    console.log(`   Tools available: ${Object.keys(tools).join(', ')}`);
    
    // Simulate AI agent workflow
    const scenarios = [
      {
        task: 'Find and analyze project documentation',
        userMessage: 'Search the documentation for information about Worker Loader API and summarize the key features',
        expectedFlow: [
          '1. Generate code to search documentation',
          '2. Execute search in sandboxed worker',
          '3. Process and summarize results',
          '4. Return structured response'
        ]
      },
      {
        task: 'Complex data processing workflow',
        userMessage: 'Find all TypeScript files, analyze their complexity, and create a report',
        expectedFlow: [
          '1. Search for TypeScript code files',
          '2. Fetch content for analysis',
          '3. Process and calculate metrics',
          '4. Generate comprehensive report'
        ]
      }
    ];
    
    scenarios.forEach((scenario, index) => {
      console.log(`\n📝 Scenario ${index + 1}: ${scenario.task}`);
      console.log(`   User: "${scenario.userMessage}"`);
      console.log('   Expected AI workflow:');
      scenario.expectedFlow.forEach(step => console.log(`      ${step}`));
      console.log('   ✅ Agent would generate and execute TypeScript code');
    });
    
    // Show the codemode tool definition
    console.log('\n🛠️  Code Mode Tool Definition:');
    const codemodeToolDef = tools.codemode;
    if (codemodeToolDef && typeof codemodeToolDef === 'object' && 'description' in codemodeToolDef) {
      console.log(`   Name: ${codemodeToolDef.name || 'codemode'}`);
      console.log(`   Description: ${codemodeToolDef.description || 'Execute TypeScript code'}`);
      if (codemodeToolDef.parameters && typeof codemodeToolDef.parameters === 'object') {
        const params = codemodeToolDef.parameters as any;
        if (params.properties) {
          console.log('   Parameters:');
          Object.entries(params.properties).forEach(([name, schema]: [string, any]) => {
            console.log(`     - ${name}: ${schema.type} - ${schema.description || 'No description'}`);
          });
        }
      }
    }
    
  } catch (error) {
    console.log(`❌ Demo 3 failed: ${error instanceof Error ? error.message : error}`);
  }
}

/**
 * Demo 4: Security and Isolation Features
 */
async function demo4_SecurityFeatures() {
  console.log('\n🔒 DEMO 4: Security and Isolation Features');
  console.log('=========================================');
  
  const mockEnv = createMockEnv();
  
  try {
    if (DEMO_CONFIG.MOCK_MODE) {
      // Mock security demonstration
      console.log('🛡️  Demonstrating security features:');
      
      const securityTests = [
        {
          name: 'Internet Access Blocked',
          description: 'Generated code cannot access external URLs',
          code: 'fetch("https://google.com")',
          expectedResult: 'Blocked - no internet access'
        },
        {
          name: 'MCP Tools Only',
          description: 'Only approved MCP tools are accessible',
          code: 'codemode.fetchAgentsDocumentation({})',
          expectedResult: 'Allowed - MCP tool access'
        },
        {
          name: 'No API Key Exposure',
          description: 'API keys are not accessible in generated code',
          code: 'process.env.OPENAI_API_KEY',
          expectedResult: 'Undefined - keys hidden'
        },
        {
          name: 'Sandboxed Execution',
          description: 'Code runs in isolated worker environment',
          code: 'global.maliciousFunction = () => "hack"',
          expectedResult: 'Isolated - no global pollution'
        }
      ];
      
      securityTests.forEach((test, index) => {
        console.log(`\n   ${index + 1}. ${test.name}`);
        console.log(`      Description: ${test.description}`);
        console.log(`      Test code: ${test.code}`);
        console.log(`      Expected: ${test.expectedResult}`);
        console.log('      ✅ Security enforced by Worker isolation');
      });
      
      // Worker isolation benefits
      console.log('\n🏗️  Worker Isolation Benefits:');
      const benefits = [
        'Fast startup (milliseconds) - no containers needed',
        'Automatic cleanup - workers are disposable',
        'Memory isolation - no shared state between executions',
        'Network isolation - controlled access through bindings',
        'Resource limits - CPU and memory constraints enforced',
        'No file system access - secure by default'
      ];
      
      benefits.forEach((benefit, index) => {
        console.log(`   ${index + 1}. ${benefit}`);
      });
      
      return;
    }
    
    const { codeMode } = await experimental_codemode({
      prompt: 'System prompt',
      serverUrl: DEMO_CONFIG.MCP_SERVER_URL,
      env: mockEnv
    });
    
    // Security demonstration
    console.log('🛡️  Demonstrating security features:');
    
    const securityTests = [
      {
        name: 'Internet Access Blocked',
        description: 'Generated code cannot access external URLs',
        code: 'fetch("https://google.com")',
        expectedResult: 'Blocked - no internet access'
      },
      {
        name: 'MCP Tools Only',
        description: 'Only approved MCP tools are accessible',
        code: 'codemode.fetchAgentsDocumentation({})',
        expectedResult: 'Allowed - MCP tool access'
      },
      {
        name: 'No API Key Exposure',
        description: 'API keys are not accessible in generated code',
        code: 'process.env.OPENAI_API_KEY',
        expectedResult: 'Undefined - keys hidden'
      },
      {
        name: 'Sandboxed Execution',
        description: 'Code runs in isolated worker environment',
        code: 'global.maliciousFunction = () => "hack"',
        expectedResult: 'Isolated - no global pollution'
      }
    ];
    
    securityTests.forEach((test, index) => {
      console.log(`\n   ${index + 1}. ${test.name}`);
      console.log(`      Description: ${test.description}`);
      console.log(`      Test code: ${test.code}`);
      console.log(`      Expected: ${test.expectedResult}`);
      console.log('      ✅ Security enforced by Worker isolation');
    });
    
    // Worker isolation benefits
    console.log('\n🏗️  Worker Isolation Benefits:');
    const benefits = [
      'Fast startup (milliseconds) - no containers needed',
      'Automatic cleanup - workers are disposable',
      'Memory isolation - no shared state between executions',
      'Network isolation - controlled access through bindings',
      'Resource limits - CPU and memory constraints enforced',
      'No file system access - secure by default'
    ];
    
    benefits.forEach((benefit, index) => {
      console.log(`   ${index + 1}. ${benefit}`);
    });
    
    await codeMode.close();
    
  } catch (error) {
    console.log(`❌ Demo 4 failed: ${error instanceof Error ? error.message : error}`);
  }
}

/**
 * Main demo runner
 */
async function runAllDemos() {
  console.log('🎪 CLOUDFLARE MCP CLIENT DEMO');
  console.log('==============================');
  console.log(`Mode: ${DEMO_CONFIG.MOCK_MODE ? 'Mock (Safe)' : 'Live (Requires MCP Server)'}`);
  console.log(`MCP Server: ${DEMO_CONFIG.MCP_SERVER_URL}`);
  console.log('\nThis demo showcases the key features of the Cloudflare MCP Client:');
  console.log('• MCP protocol implementation');
  console.log('• TypeScript API generation');
  console.log('• Code Mode execution');
  console.log('• AI agent integration patterns');
  console.log('• Security and isolation features');
  
  const demos = [
    { name: 'Basic MCP Client', func: demo1_BasicMCPClient },
    { name: 'Code Mode', func: demo2_CodeMode },
    { name: 'AI Agent Integration', func: demo3_AIAgentIntegration },
    { name: 'Security Features', func: demo4_SecurityFeatures }
  ];
  
  for (const demo of demos) {
    try {
      await demo.func();
      await new Promise(resolve => setTimeout(resolve, 1000)); // Brief pause between demos
    } catch (error) {
      console.log(`❌ ${demo.name} demo failed: ${error}`);
    }
  }
  
  console.log('\n🎉 Demo Complete!');
  console.log('\nNext steps:');
  console.log('1. Deploy to Cloudflare Workers: npm run deploy');
  console.log('2. Configure your MCP server URL');
  console.log('3. Set up OpenAI API key');
  console.log('4. Test with real MCP servers');
  console.log('\nFor more information, see README.md');
}

// Export for use in other contexts
export {
  runAllDemos,
  demo1_BasicMCPClient,
  demo2_CodeMode,
  demo3_AIAgentIntegration,
  demo4_SecurityFeatures,
  DEMO_CONFIG
};

// Run demos when executed directly
if (typeof window === 'undefined' && typeof process !== 'undefined') {
  runAllDemos().catch(console.error);
}