import { Hono } from "hono";
import { streamText } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import { experimental_codemode } from "./code-mode";
import { MCPClient } from "./mcp-client";
import { Env } from "./types";
import { loadEnvironment } from "./env-config";

const app = new Hono<{ Bindings: Env }>();

/**
 * Root endpoint - serve HTML demo page
 */
app.get("/", (c) => {
  return c.html(`<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloudflare MCP Client Demo</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .status {
            background: #e8f5e8;
            border: 1px solid #4caf50;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .chat-container {
            border: 1px solid #ddd;
            border-radius: 8px;
            height: 300px;
            overflow-y: auto;
            padding: 15px;
            margin-bottom: 20px;
            background: #fafafa;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
        }
        .user {
            background: #007bff;
            color: white;
            text-align: right;
        }
        .assistant {
            background: #e9ecef;
            color: #333;
        }
        .input-container {
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        button {
            padding: 12px 24px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .endpoints {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .endpoint {
            font-family: monospace;
            background: white;
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            border: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Cloudflare MCP Client</h1>
        
        <div id="status" class="status">
            <strong>Status:</strong> <span id="statusText">Checking...</span>
        </div>

        <div class="chat-container" id="chatContainer">
            <div class="message assistant">
                <strong>Assistant:</strong> Hello! I'm an AI assistant running on Cloudflare Workers. Ask me anything!
            </div>
        </div>

        <div class="input-container">
            <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()" id="sendButton">Send</button>
        </div>

        <div class="endpoints">
            <h3>Available Endpoints:</h3>
            <div class="endpoint">GET /health - Health check</div>
            <div class="endpoint">GET /test - Configuration test</div>
            <div class="endpoint">POST /chat/simple - Simple chat (working)</div>
            <div class="endpoint">POST /chat - Full MCP chat (requires MCP server)</div>
            <div class="endpoint">GET /mcp/tools - List MCP tools</div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin;
        let messages = [];

        async function checkStatus() {
            try {
                const response = await fetch(\`\${API_BASE}/test\`);
                const data = await response.json();
                document.getElementById('statusText').innerHTML = \`
                    ✅ Connected | 
                    OpenAI: \${data.hasOpenAI ? '✅' : '❌'} | 
                    MCP Server: \${data.mcpServer}
                \`;
            } catch (error) {
                document.getElementById('statusText').textContent = '❌ Connection failed';
            }
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;

            const sendButton = document.getElementById('sendButton');
            sendButton.disabled = true;
            sendButton.textContent = 'Sending...';

            // Add user message to chat
            messages.push({ role: 'user', content: message });
            addMessageToChat('user', message);
            input.value = '';

            try {
                const response = await fetch(\`\${API_BASE}/chat/simple\`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ messages })
                });

                if (!response.ok) {
                    throw new Error(\`HTTP error! status: \${response.status}\`);
                }

                // Handle streaming response
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let assistantMessage = '';

                const assistantDiv = addMessageToChat('assistant', '');
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('0:"')) {
                            try {
                                const content = JSON.parse(line.substring(2));
                                assistantMessage += content;
                                assistantDiv.innerHTML = \`<strong>Assistant:</strong> \${assistantMessage}\`;
                            } catch (e) {
                                // Ignore parse errors for now
                            }
                        }
                    }
                }

                messages.push({ role: 'assistant', content: assistantMessage });

            } catch (error) {
                console.error('Chat error:', error);
                addMessageToChat('assistant', \`Error: \${error.message}\`);
            }

            sendButton.disabled = false;
            sendButton.textContent = 'Send';
        }

        function addMessageToChat(role, content) {
            const chatContainer = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = \`message \${role}\`;
            messageDiv.innerHTML = \`<strong>\${role === 'user' ? 'You' : 'Assistant'}:</strong> \${content}\`;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return messageDiv;
        }

        // Check status on load
        checkStatus();
    </script>
</body>
</html>`);
});

/**
 * Health check endpoint
 */
app.get("/health", (c) => {
  return c.json({ status: "healthy", timestamp: new Date().toISOString() });
});

/**
 * Simple test endpoint that doesn't require external MCP server
 */
app.get("/test", (c) => {
  const config = loadEnvironment(c.env);
  return c.json({
    status: "ok",
    hasOpenAI: !!config.openaiApiKey,
    mcpServer: config.mcpServerUrl,
    timestamp: new Date().toISOString(),
  });
});

/**
 * Simple chat endpoint without MCP (for testing)
 */
app.post("/chat/simple", async (c) => {
  try {
    const { messages } = await c.req.json();

    if (!messages || !Array.isArray(messages)) {
      return c.json({ error: "Messages array is required" }, 400);
    }

    const config = loadEnvironment(c.env);

    if (!config.openaiApiKey) {
      return c.json({ error: "OpenAI API key is required" }, 400);
    }

    // Create OpenAI client with API key
    const openaiProvider = createOpenAI({
      apiKey: config.openaiApiKey,
    });
    const model = openaiProvider("gpt-4o-mini");

    // Stream the response
    const result = await streamText({
      model,
      system: "You are a helpful AI assistant.",
      messages,
      maxTokens: 1000,
    });

    // Return streaming response
    return result.toDataStreamResponse({
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  } catch (error) {
    console.error("Simple chat error:", error);
    return c.json(
      {
        error: "Internal server error",
        details: error instanceof Error ? error.message : String(error),
      },
      500
    );
  }
});

/**
 * Main chat endpoint using code mode
 */
app.post("/chat", async (c) => {
  try {
    const { messages, mcpServerUrl } = await c.req.json();

    if (!messages || !Array.isArray(messages)) {
      return c.json({ error: "Messages array is required" }, 400);
    }

    const config = loadEnvironment(c.env);
    const serverUrl = mcpServerUrl || config.mcpServerUrl;

    if (!serverUrl) {
      return c.json({ error: "MCP server URL is required" }, 400);
    }

    if (!config.openaiApiKey) {
      return c.json({ error: "OpenAI API key is required" }, 400);
    }

    // Set up code mode with MCP integration
    const { prompt, tools, codeMode } = await experimental_codemode({
      prompt: `You are a helpful AI assistant with access to MCP tools through code mode. 
      When performing complex tasks, write TypeScript code using the codemode tool to chain operations together.`,
      serverUrl,
      env: c.env,
    });

    // Create OpenAI client with API key
    const openaiProvider = createOpenAI({
      apiKey: config.openaiApiKey,
    });
    const model = openaiProvider("gpt-4");

    // Stream the response
    const result = await streamText({
      model,
      system: prompt,
      messages,
      tools,
      maxTokens: 2000,
    });

    // Return streaming response
    return result.toDataStreamResponse({
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  } catch (error) {
    console.error("Chat error:", error);
    return c.json(
      {
        error: "Internal server error",
        details: error instanceof Error ? error.message : String(error),
      },
      500
    );
  }
});

/**
 * Direct MCP tool calling endpoint (for testing)
 */
app.post("/mcp/call", async (c) => {
  try {
    const { serverUrl, toolName, arguments: args } = await c.req.json();

    if (!serverUrl || !toolName) {
      return c.json({ error: "serverUrl and toolName are required" }, 400);
    }

    const mcpClient = new MCPClient(serverUrl);
    await mcpClient.initialize();

    const result = await mcpClient.callTool(toolName, args || {});

    return c.json({ result });
  } catch (error) {
    console.error("MCP call error:", error);
    return c.json(
      {
        error: "MCP call failed",
        details: error instanceof Error ? error.message : String(error),
      },
      500
    );
  }
});

/**
 * List available MCP tools
 */
app.get("/mcp/tools", async (c) => {
  try {
    const config = loadEnvironment(c.env);
    const serverUrl = c.req.query("serverUrl") || config.mcpServerUrl;

    if (!serverUrl) {
      return c.json({ error: "MCP server URL is required" }, 400);
    }

    const mcpClient = new MCPClient(serverUrl);
    await mcpClient.initialize();

    const tools = await mcpClient.listTools();
    const typeDefinitions = await mcpClient.generateTypeDefinitions();

    return c.json({ tools, typeDefinitions });
  } catch (error) {
    console.error("MCP tools error:", error);
    return c.json(
      {
        error: "Failed to fetch MCP tools",
        details: error instanceof Error ? error.message : String(error),
      },
      500
    );
  }
});

/**
 * Execute code in sandbox (for testing code mode)
 */
app.post("/codemode/execute", async (c) => {
  try {
    const { code, serverUrl } = await c.req.json();

    if (!code) {
      return c.json({ error: "Code is required" }, 400);
    }

    const config = loadEnvironment(c.env);
    const mcpServerUrl = serverUrl || config.mcpServerUrl;
    if (!mcpServerUrl) {
      return c.json({ error: "MCP server URL is required" }, 400);
    }

    const { codeMode } = await experimental_codemode({
      prompt: "System prompt",
      serverUrl: mcpServerUrl,
      env: c.env,
    });

    const result = await codeMode.executeInWorker(code);

    return c.json({ result });
  } catch (error) {
    console.error("Code execution error:", error);
    return c.json(
      {
        error: "Code execution failed",
        details: error instanceof Error ? error.message : String(error),
      },
      500
    );
  }
});

/**
 * CORS preflight
 */
app.options("*", (c) => {
  return c.text("OK", 200, {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  });
});

export default app;
