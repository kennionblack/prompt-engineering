import * as readline from 'node:readline';
import { openai } from '@ai-sdk/openai';
import { generateText, type CoreMessage } from 'ai';
import dotenv from 'dotenv';
import { FinanceTools } from './finance-tools.js';

dotenv.config();

class FinanceBotAgent {
  public messages: CoreMessage[] = [];
  private financeTools: FinanceTools;

  constructor() {
    this.financeTools = new FinanceTools();
    this.financeTools.initialize();
  }

  async generateResponse() {
    const tools = this.financeTools.getTools();
    const systemPrompt = `You are FinanceBot, a personal finance advisor. You have access to financial calculation tools. 
    Provide helpful, accurate financial advice and use the available tools when appropriate.
    
    Available tools:
    - calculateCompoundInterest: Calculate compound interest for investments
    - calculateLoanPayment: Calculate loan payments and interest
    - createBudgetAnalysis: Analyze budgets and provide recommendations`;

    return await generateText({
      model: openai('gpt-4o-mini'),
      messages: this.messages,
      tools,
      system: systemPrompt,
    });
  }

  addMessage(message: CoreMessage) {
    this.messages.push(message);
  }

  clearHistory() {
    this.messages = [];
    console.log('Conversation history cleared');
  }
}

class FinanceBotCLI {
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
    console.log('🏦 FinanceBot - Your Personal Finance Advisor');
    console.log('Type "exit", "quit", or "clear" for commands\n');

    this.rl.prompt();

    this.rl.on('line', async (input: string) => {
      const trimmed = input.trim();

      if (trimmed === 'exit' || trimmed === 'quit') {
        this.rl.close();
        return;
      }

      if (trimmed === 'clear') {
        this.agent.clearHistory();
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

    this.rl.on('close', () => {
      console.log('\nThank you for using FinanceBot!');
      process.exit(0);
    });

    process.on('SIGINT', () => {
      console.log('\nThank you for using FinanceBot!');
      process.exit(0);
    });
  }

  private async handleUserInput(input: string) {
    try {
      this.agent.addMessage({
        role: 'user',
        content: input,
      });

      const result = await this.agent.generateResponse();

      this.agent.addMessage({
        role: 'assistant',
        content: result.text,
      });

      console.log(`\n💡 ${result.text}\n`);

      if (result.toolCalls && result.toolCalls.length > 0) {
        console.log('Tools used:');
        for (const toolCall of result.toolCalls) {
          console.log(`  - ${toolCall.toolName}`);
        }
        console.log('');
      }
    } catch (error: any) {
      console.error(`Error: ${error.message}\n`);
      if (this.agent.messages.length > 0) {
        this.agent.messages.pop();
      }
    }
  }
}

const financeBot = new FinanceBotCLI();
financeBot.start().catch(console.error);
