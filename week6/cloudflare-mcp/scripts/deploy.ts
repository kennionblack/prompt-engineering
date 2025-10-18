/**
 * Deployment Script for Cloudflare MCP Client
 * Run this script to deploy the MCP client to Cloudflare Workers
 */

import { execSync } from "child_process";
import { existsSync, readFileSync } from "fs";
import { join } from "path";

interface DeployConfig {
  environment: "dev" | "production";
  skipBuild?: boolean;
  skipTests?: boolean;
  verbose?: boolean;
}

class Deployer {
  private config: DeployConfig;

  constructor(config: DeployConfig) {
    this.config = config;
  }

  private log(message: string) {
    console.log(`[DEPLOY] ${message}`);
  }

  private error(message: string, error?: any) {
    console.error(`[ERROR] ${message}`);
    if (error && this.config.verbose) {
      console.error(error);
    }
  }

  private exec(command: string, description: string) {
    this.log(description);
    try {
      const result = execSync(command, {
        stdio: this.config.verbose ? "inherit" : "pipe",
        encoding: "utf8",
      });
      if (!this.config.verbose && result) {
        console.log(result);
      }
    } catch (error) {
      this.error(`Failed: ${description}`, error);
      throw error;
    }
  }

  async checkPrerequisites() {
    this.log("Checking prerequisites...");

    // Check if wrangler is installed
    try {
      execSync("wrangler --version", { stdio: "pipe" });
    } catch {
      throw new Error("Wrangler CLI not found. Install with: npm install -g wrangler");
    }

    // Check if package.json exists
    if (!existsSync("package.json")) {
      throw new Error("package.json not found. Run from project root.");
    }

    // Check if wrangler.toml exists
    if (!existsSync("wrangler.toml")) {
      throw new Error("wrangler.toml not found. Configuration file required.");
    }

    // Check if .env file exists (for dev)
    if (this.config.environment === "dev" && !existsSync(".env")) {
      this.log("Warning: .env file not found. Some features may not work.");
    }

    this.log("Prerequisites check passed ✓");
  }

  async installDependencies() {
    if (existsSync("node_modules")) {
      this.log("Dependencies already installed, skipping...");
      return;
    }

    this.exec("npm install", "Installing dependencies");
  }

  async runTests() {
    if (this.config.skipTests) {
      this.log("Skipping tests (--skip-tests flag)");
      return;
    }

    try {
      this.exec("npm run test", "Running tests");
    } catch (error) {
      this.error("Tests failed. Use --skip-tests to deploy anyway.");
      throw error;
    }
  }

  async buildProject() {
    if (this.config.skipBuild) {
      this.log("Skipping build (--skip-build flag)");
      return;
    }

    this.exec("npm run type-check", "Type checking");
    this.log("Build completed ✓");
  }

  async deploy() {
    const command =
      this.config.environment === "production" ? "wrangler deploy" : "wrangler deploy --env dev";

    this.exec(command, `Deploying to ${this.config.environment}`);

    // Show deployment info
    this.showDeploymentInfo();
  }

  private showDeploymentInfo() {
    this.log("Deployment completed! 🚀");

    const wranglerConfig = this.readWranglerConfig();
    const workerName =
      this.config.environment === "production" ? wranglerConfig.name : `${wranglerConfig.name}-dev`;

    console.log("\n📋 Deployment Information:");
    console.log(`   Worker Name: ${workerName}`);
    console.log(`   Environment: ${this.config.environment}`);
    console.log(`   URL: https://${workerName}.your-subdomain.workers.dev`);

    console.log("\n🔧 API Endpoints:");
    console.log("   POST /chat - AI chat with code mode");
    console.log("   GET  /mcp/tools - List MCP tools");
    console.log("   POST /mcp/call - Call MCP tools directly");
    console.log("   POST /codemode/execute - Execute code in sandbox");
    console.log("   GET  /health - Health check");

    console.log("\n📚 Next Steps:");
    console.log("1. Test the deployment with: curl https://your-worker.workers.dev/health");
    console.log("2. Set up environment variables in Cloudflare dashboard");
    console.log("3. Configure MCP server URLs");
    console.log("4. Test MCP integration");
  }

  private readWranglerConfig(): any {
    try {
      const content = readFileSync("wrangler.toml", "utf8");
      // Simple TOML parser for name field
      const nameMatch = content.match(/^name\s*=\s*["']([^"']+)["']/m);
      return {
        name: nameMatch ? nameMatch[1] : "cloudflare-mcp-client",
      };
    } catch {
      return { name: "cloudflare-mcp-client" };
    }
  }

  async run() {
    try {
      await this.checkPrerequisites();
      await this.installDependencies();
      await this.runTests();
      await this.buildProject();
      await this.deploy();
    } catch (error) {
      this.error("Deployment failed", error);
      process.exit(1);
    }
  }
}

// Parse command line arguments
function parseArgs(): DeployConfig {
  const args = process.argv.slice(2);

  const config: DeployConfig = {
    environment: "dev",
    skipBuild: false,
    skipTests: false,
    verbose: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    switch (arg) {
      case "--prod":
      case "--production":
        config.environment = "production";
        break;
      case "--dev":
      case "--development":
        config.environment = "dev";
        break;
      case "--skip-build":
        config.skipBuild = true;
        break;
      case "--skip-tests":
        config.skipTests = true;
        break;
      case "--verbose":
      case "-v":
        config.verbose = true;
        break;
      case "--help":
      case "-h":
        console.log(`
Cloudflare MCP Client Deployment Script

Usage: npm run deploy [options]

Options:
  --dev, --development    Deploy to development environment (default)
  --prod, --production    Deploy to production environment
  --skip-build           Skip the build step
  --skip-tests           Skip running tests
  --verbose, -v          Show verbose output
  --help, -h             Show this help message

Examples:
  npm run deploy                    # Deploy to dev
  npm run deploy --prod            # Deploy to production
  npm run deploy --skip-tests      # Deploy without running tests
        `);
        process.exit(0);
        break;
      default:
        console.error(`Unknown argument: ${arg}`);
        console.error("Use --help for usage information");
        process.exit(1);
    }
  }

  return config;
}

// Main execution
if (require.main === module) {
  const config = parseArgs();
  const deployer = new Deployer(config);
  deployer.run();
}

export { Deployer, DeployConfig };
