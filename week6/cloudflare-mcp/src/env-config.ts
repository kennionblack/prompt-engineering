/**
 * Load environment variables for both local development and Cloudflare Workers
 * In development: Uses Node.js process.env (populated by dotenv elsewhere)
 * In production: Uses Cloudflare Workers environment bindings
 */
export function loadEnvironment(env?: any) {
  // If running in Cloudflare Workers, use the env parameter
  if (env) {
    return {
      openaiApiKey: env.OPENAI_API_KEY,
      mcpServerUrl: env.MCP_SERVER_URL || "https://gitmcp.io/cloudflare/agents",
    };
  }

  // For local development, use process.env (loaded by dotenv in demo files)
  return {
    openaiApiKey: process.env.OPENAI_API_KEY,
    mcpServerUrl: process.env.MCP_SERVER_URL || "https://gitmcp.io/cloudflare/agents",
  };
}
