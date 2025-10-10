import { openai } from '@ai-sdk/openai';
import { generateText, type CoreMessage } from 'ai';
import { FinanceTools } from './finance-tools.js';
import { MCPManager } from './mcp-manager.js';
import { UserProfileManager } from './user-profile.js';
import { BotState } from './types.js';

export class FinanceBotAgent {
  public messages: CoreMessage[] = [];
  private financeTools: FinanceTools;
  private mcpManager: MCPManager;
  private userProfileManager: UserProfileManager;
  private conversationContext: string = '';

  constructor() {
    this.financeTools = new FinanceTools();
    this.mcpManager = new MCPManager();
    this.userProfileManager = new UserProfileManager();
  }

  async initialize(): Promise<void> {
    console.log('🏦 Initializing FinanceBot...');

    // Initialize built-in finance tools
    this.financeTools.initialize();

    // Connect to MCP servers
    await this.mcpManager.initialize();

    console.log('💡 Ready to provide personalized financial advice!\n');
  }

  async generateResponse() {
    const tools = this.createAllTools();
    const systemPrompt = this.generateFinanceSystemPrompt();

    return await generateText({
      model: openai('gpt-4o-mini'),
      messages: this.messages,
      tools,
      system: systemPrompt,
      temperature: 0.7,
    });
  }

  private createAllTools() {
    const tools: any = {};

    // Add built-in finance tools
    const builtinTools = this.financeTools.getTools();
    Object.assign(tools, builtinTools);

    // Add MCP tools
    const mcpTools = this.mcpManager.createMCPTools();
    Object.assign(tools, mcpTools);

    return tools;
  }

  private generateFinanceSystemPrompt(): string {
    const profile = this.userProfileManager.getProfile();
    const availableTools = this.mcpManager.getAvailableTools();

    const basePrompt = `You are FinanceBot, an expert personal finance advisor with deep knowledge of investments, budgeting, financial planning, and market analysis.

## Core Principles:
- Provide personalized, actionable financial advice
- Always consider the user's risk tolerance, investment horizon, and financial goals
- Use data-driven insights from available tools
- Explain complex financial concepts in simple terms
- Prioritize financial security and responsible investing

## Current User Profile:
- Risk Tolerance: ${profile.riskTolerance}
- Investment Horizon: ${profile.investmentHorizon}
- Currency: ${profile.currency}
- Financial Goals: ${profile.financialGoals.length > 0 ? profile.financialGoals.join(', ') : 'Not specified'}
- Portfolio Size: ${profile.portfolio.length} holdings

## Communication Style:
- Be conversational and encouraging
- Use relevant financial metrics and data
- Provide specific, actionable recommendations
- Ask clarifying questions to better understand needs
- Avoid financial jargon without explanation`;

    if (availableTools.length > 0) {
      let toolsDescription = '\n\n## Available Tools:\n';
      availableTools.forEach(tool => {
        toolsDescription += `- ${tool.name}: ${tool.description}\n`;
      });

      toolsDescription += `
## Tool Usage Guidelines:
- Always use tools to get current, accurate financial data
- Combine multiple data sources for comprehensive analysis
- Interpret tool results in the context of the user's profile
- Provide clear explanations of what the data means for the user`;

      return basePrompt + toolsDescription;
    }

    return (
      basePrompt +
      '\n\nNote: External financial data tools are not currently available, but I can still provide general financial advice and calculations.'
    );
  }

  updateUserProfile(updates: any) {
    this.userProfileManager.updateProfile(updates);
  }

  handleProfileUpdatesFromText(input: string) {
    this.userProfileManager.handleProfileUpdatesFromText(input);
  }

  addMessage(message: CoreMessage) {
    this.messages.push(message);

    // Maintain conversation context for better continuity
    if (this.messages.length > 10) {
      this.conversationContext = this.summarizeOldMessages();
      this.messages = this.messages.slice(-8);
    }
  }

  private summarizeOldMessages(): string {
    const oldMessages = this.messages.slice(0, -8);
    const topics = new Set<string>();

    oldMessages.forEach(msg => {
      if (msg.content && typeof msg.content === 'string') {
        const content = msg.content.toLowerCase();
        if (content.includes('stock') || content.includes('investment')) topics.add('investments');
        if (content.includes('budget') || content.includes('expense')) topics.add('budgeting');
        if (content.includes('goal') || content.includes('plan')) topics.add('financial_planning');
        if (content.includes('risk') || content.includes('diversif')) topics.add('risk_management');
      }
    });

    return `Previous conversation covered: ${Array.from(topics).join(', ')}`;
  }

  clearHistory() {
    this.messages = [];
    this.conversationContext = '';
    console.log('🗑️ Conversation history cleared');
  }

  getState(): BotState {
    const profile = this.userProfileManager.getProfile();
    return {
      messageCount: this.messages.length,
      lastMessageRole: this.messages[this.messages.length - 1]?.role || null,
      availableTools: this.mcpManager.getAvailableTools().length,
      mcpServers: this.mcpManager.getConnectedServerCount(),
      userProfile: profile,
      portfolioValue: this.userProfileManager.calculatePortfolioValue(),
    };
  }

  async cleanup() {
    await this.mcpManager.cleanup();
  }
}
