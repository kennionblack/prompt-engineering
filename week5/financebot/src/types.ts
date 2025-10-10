export interface MCPServer {
  name: string;
  command: string;
  args?: string[];
  client?: any;
  enabled: boolean;
}

export interface UserProfile {
  riskTolerance: 'conservative' | 'moderate' | 'aggressive';
  investmentHorizon: 'short_term' | 'medium_term' | 'long_term';
  currency: string;
  monthlyIncome?: number;
  monthlyExpenses?: number;
  financialGoals: string[];
  portfolio: Array<{ symbol: string; shares: number; avgCost: number }>;
}

export interface BotState {
  messageCount: number;
  lastMessageRole: string | null;
  availableTools: number;
  mcpServers: number;
  userProfile: UserProfile;
  portfolioValue: number;
}
