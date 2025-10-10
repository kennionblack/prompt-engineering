import * as readline from 'node:readline';
import { FinanceBotAgent } from './finance-agent.js';

export class FinanceBotCLI {
  private rl: readline.Interface;
  private agent: FinanceBotAgent;

  constructor() {
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      prompt: '💰 > ',
    });

    this.agent = new FinanceBotAgent();
  }

  async start() {
    console.log('🏦 Starting FinanceBot - Your Personal Finance Advisor...');

    try {
      await this.agent.initialize();
    } catch (error) {
      console.error('Failed to initialize FinanceBot:', error);
      process.exit(1);
    }

    this.showWelcomeMessage();
    this.rl.prompt();

    this.rl.on('line', async (input: string) => {
      const trimmed = input.trim();

      if (trimmed === 'exit' || trimmed === 'quit') {
        await this.cleanup();
        return;
      }

      if (trimmed === 'clear') {
        this.agent.clearHistory();
        this.rl.prompt();
        return;
      }

      if (trimmed === 'status') {
        this.showStatus();
        this.rl.prompt();
        return;
      }

      if (trimmed === 'help') {
        this.showHelp();
        this.rl.prompt();
        return;
      }

      if (trimmed === 'profile') {
        this.showProfile();
        this.rl.prompt();
        return;
      }

      if (trimmed === '') {
        this.rl.prompt();
        return;
      }

      await this.handleUserInput(trimmed);
      this.rl.prompt();
    });

    this.rl.on('close', async () => {
      await this.cleanup();
    });

    process.on('SIGINT', async () => {
      await this.cleanup();
    });
  }

  private showWelcomeMessage() {
    console.log(`
╔══════════════════════════════════════════════════════════════╗
║                   🏦 Welcome to FinanceBot! 🏦                ║
║                                                              ║
║  Your AI-powered personal finance advisor with access to     ║
║  real-time market data, financial analysis tools, and       ║
║  personalized investment recommendations.                    ║
║                                                              ║
║  Commands:                                                   ║
║  • help     - Show available commands                        ║
║  • profile  - View/edit your financial profile              ║
║  • status   - Check system status                            ║
║  • clear    - Clear conversation history                     ║
║  • exit     - Exit FinanceBot                                ║
╚══════════════════════════════════════════════════════════════╝

Ask me anything about:
💹 Stock analysis and market trends
📊 Portfolio optimization and diversification
💰 Budgeting and expense tracking
🎯 Financial goal setting and planning
📈 Investment strategies and risk management
📰 Market news and economic insights

Let's start building your financial future! What would you like to know?
`);
  }

  private showHelp() {
    console.log(`
📚 FinanceBot Commands & Examples:

🔧 System Commands:
  help     - Show this help message
  profile  - View/edit your financial profile  
  status   - Check system and connection status
  clear    - Clear conversation history
  exit     - Exit FinanceBot

💡 Example Questions:
  "What's the current price of Apple stock?"
  "Should I invest in tech stocks given my moderate risk tolerance?"
  "Help me create a budget for saving $10,000 this year"
  "Calculate compound interest on $1000 invested for 10 years at 7%"
  "Analyze my portfolio diversification"

🎯 Tip: Be specific about your financial situation and goals for personalized advice!
`);
  }

  private showStatus() {
    const state = this.agent.getState();
    console.log(`
📊 FinanceBot Status:
  💬 Messages in conversation: ${state.messageCount}
  🛠️  Available tools: ${state.availableTools}
  🔗 MCP servers connected: ${state.mcpServers}
  💼 Portfolio holdings: ${state.userProfile.portfolio.length}
  💰 Estimated portfolio value: $${state.portfolioValue.toFixed(2)}
  ⚖️  Risk tolerance: ${state.userProfile.riskTolerance}
  📅 Investment horizon: ${state.userProfile.investmentHorizon}
`);
  }

  private showProfile() {
    const profile = this.agent.getState().userProfile;
    console.log(`
👤 Your Financial Profile:
  ⚖️  Risk Tolerance: ${profile.riskTolerance}
  📅 Investment Horizon: ${profile.investmentHorizon}
  💱 Currency: ${profile.currency}
  🎯 Financial Goals: ${profile.financialGoals.length > 0 ? profile.financialGoals.join(', ') : 'None set'}
  📈 Portfolio Holdings: ${profile.portfolio.length} positions
  
💡 To update your profile, tell me about changes like:
   "My risk tolerance is aggressive" or "Add retirement planning to my goals"
`);
  }

  private async handleUserInput(input: string) {
    try {
      // Check for profile updates in natural language
      this.agent.handleProfileUpdatesFromText(input);

      this.agent.addMessage({
        role: 'user',
        content: input,
      });

      const result = await this.agent.generateResponse();

      if (
        result.toolCalls &&
        result.toolCalls.length > 0 &&
        (!result.text || result.text.trim() === '')
      ) {
        this.agent.addMessage({
          role: 'assistant',
          content: result.text || '',
        });

        const toolResults = result.toolCalls
          .map(call => {
            const toolResult = result.toolResults?.find(r => r.toolCallId === call.toolCallId);
            return `${call.toolName} returned: ${toolResult?.output || 'No result'}`;
          })
          .join('\n');

        this.agent.addMessage({
          role: 'user',
          content: `Based on the tool results:\n${toolResults}\n\nPlease provide a comprehensive financial analysis and personalized recommendations based on my profile.`,
        });

        const interpretResult = await this.agent.generateResponse();
        this.agent.addMessage({
          role: 'assistant',
          content: interpretResult.text,
        });

        console.log(`\n💡 ${interpretResult.text || 'No response generated'}\n`);
      } else {
        this.agent.addMessage({
          role: 'assistant',
          content: result.text || '',
        });

        console.log(`\n💡 ${result.text || 'No response generated'}\n`);
      }

      if (result.toolCalls && result.toolCalls.length > 0) {
        console.log('🔧 Tools used:');
        for (const toolCall of result.toolCalls) {
          console.log(`  📊 ${toolCall.toolName}`);
        }
        console.log('');
      }
    } catch (error: any) {
      console.error(`❌ Error: ${error.message}\n`);
      if (this.agent.messages.length > 0) {
        this.agent.messages.pop();
      }
    }
  }

  private async cleanup() {
    console.log('\n🧹 Cleaning up connections...');
    await this.agent.cleanup();
    console.log('💰 Thank you for using FinanceBot! Keep building your financial future! 🚀');
    this.rl.close();
    process.exit(0);
  }

  getAgent(): FinanceBotAgent {
    return this.agent;
  }
}
