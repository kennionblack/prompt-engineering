import * as readline from 'node:readline';
import { openai } from '@ai-sdk/openai';
import { generateText, streamText, type CoreMessage } from 'ai';
import dotenv from 'dotenv';
import { tools } from './tools.js';

dotenv.config();

class CLIAgent {
  public messages: CoreMessage[] = [];

  async onChatMessage(onFinish?: (result: any) => void) {
    const result = streamText({
      model: openai('gpt-4o-mini'),
      messages: this.messages,
      tools,
      system:
        'You are a helpful AI assistant with access to various tools. Use the available tools when appropriate to help users.',
      onFinish: onFinish || (() => {}),
    });

    return result;
  }

  async generateResponse() {
    return await generateText({
      model: openai('gpt-4o-mini'),
      messages: this.messages,
      tools,
      system:
        'You are a helpful AI assistant with access to various tools. Use the available tools when appropriate to help users.',
    });
  }

  addMessage(message: CoreMessage) {
    this.messages.push(message);
  }

  clearHistory() {
    this.messages = [];
    console.log('Conversation history cleared');
  }

  getState() {
    return {
      messageCount: this.messages.length,
      lastMessageRole: this.messages[this.messages.length - 1]?.role || null,
    };
  }
}

class CLIChatbot {
  private rl: readline.Interface;
  private agent: CLIAgent;

  constructor() {
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      prompt: '> ',
    });

    this.agent = new CLIAgent();
  }

  async start() {
    console.log('Type "exit", "quit", "clear" or press Ctrl+C to exit\n');

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
      console.log('\nGoodbye!');
      process.exit(0);
    });

    // Handle Ctrl+C
    process.on('SIGINT', () => {
      console.log('\nGoodbye!');
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

      // Display response in either result.text or result of tool call
      console.log(
        `\n🤖 ${result.text ? result.text : result.toolResults[0].output}\n`
      );

      if (result.toolCalls && result.toolCalls.length > 0) {
        console.log('Tools executed:');
        for (const toolCall of result.toolCalls) {
          console.log(`  - ${toolCall.toolName}`);
        }
        console.log('');
      }
    } catch (error: any) {
      console.error(`Error: ${error.message}\n`);
      // Remove the failed user message
      if (this.agent.messages.length > 0) {
        this.agent.messages.pop();
      }
    }
  }

  getAgent(): CLIAgent {
    return this.agent;
  }
}

// Start the chatbot
const chatbot = new CLIChatbot();
chatbot.start().catch(console.error);
