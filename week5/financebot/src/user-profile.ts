import { UserProfile } from './types.js';

export class UserProfileManager {
  private userProfile: UserProfile;

  constructor() {
    this.userProfile = this.getDefaultProfile();
  }

  private getDefaultProfile(): UserProfile {
    return {
      riskTolerance: (process.env.DEFAULT_RISK_TOLERANCE as any) || 'moderate',
      investmentHorizon: (process.env.DEFAULT_INVESTMENT_HORIZON as any) || 'long_term',
      currency: process.env.DEFAULT_CURRENCY || 'USD',
      financialGoals: [],
      portfolio: [],
    };
  }

  getProfile(): UserProfile {
    return { ...this.userProfile };
  }

  updateProfile(updates: Partial<UserProfile>): void {
    this.userProfile = { ...this.userProfile, ...updates };
    console.log('📊 Updated user profile');
  }

  calculatePortfolioValue(): number {
    return this.userProfile.portfolio.reduce((total, holding) => {
      return total + holding.shares * holding.avgCost;
    }, 0);
  }

  handleProfileUpdatesFromText(input: string): void {
    const lowerInput = input.toLowerCase();

    // Risk tolerance updates
    if (lowerInput.includes('risk tolerance')) {
      if (lowerInput.includes('conservative')) {
        this.updateProfile({ riskTolerance: 'conservative' });
      } else if (lowerInput.includes('aggressive')) {
        this.updateProfile({ riskTolerance: 'aggressive' });
      } else if (lowerInput.includes('moderate')) {
        this.updateProfile({ riskTolerance: 'moderate' });
      }
    }

    // Investment horizon updates
    if (lowerInput.includes('investment horizon') || lowerInput.includes('time horizon')) {
      if (lowerInput.includes('short')) {
        this.updateProfile({ investmentHorizon: 'short_term' });
      } else if (lowerInput.includes('long')) {
        this.updateProfile({ investmentHorizon: 'long_term' });
      } else if (lowerInput.includes('medium')) {
        this.updateProfile({ investmentHorizon: 'medium_term' });
      }
    }

    // Goal updates
    const goalKeywords = [
      'retirement',
      'house',
      'emergency fund',
      'education',
      'vacation',
      'debt payoff',
    ];
    goalKeywords.forEach(goal => {
      if (
        lowerInput.includes(goal) &&
        (lowerInput.includes('goal') || lowerInput.includes('planning'))
      ) {
        const currentGoals = this.userProfile.financialGoals;
        if (!currentGoals.includes(goal)) {
          this.updateProfile({
            financialGoals: [...currentGoals, goal],
          });
        }
      }
    });
  }
}
