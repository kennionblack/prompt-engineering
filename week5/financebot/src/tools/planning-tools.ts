import { tool } from 'ai';
import { z } from 'zod';

export const planningTools = {
  calculateRetirementNeeds: tool({
    description: 'Calculate retirement savings needs based on desired income and lifestyle',
    inputSchema: z.object({
      currentAge: z.number().describe('Current age'),
      retirementAge: z.number().describe('Target retirement age'),
      currentIncome: z.number().describe('Current annual income'),
      desiredRetirementIncome: z.number().describe('Desired annual retirement income'),
      currentSavings: z.number().describe('Current retirement savings'),
      socialSecurityBenefit: z
        .number()
        .optional()
        .describe('Expected annual Social Security benefit'),
      inflationRate: z.number().optional().describe('Expected inflation rate (default: 0.03)'),
      returnRate: z.number().optional().describe('Expected investment return rate (default: 0.07)'),
    }),
    execute: async ({
      currentAge,
      retirementAge,
      currentIncome,
      desiredRetirementIncome,
      currentSavings,
      socialSecurityBenefit = 0,
      inflationRate = 0.03,
      returnRate = 0.07,
    }) => {
      const yearsToRetirement = retirementAge - currentAge;
      const futureRetirementIncome =
        desiredRetirementIncome * Math.pow(1 + inflationRate, yearsToRetirement);

      const netIncomeNeeded = futureRetirementIncome - socialSecurityBenefit;
      const withdrawalRate = 0.04;
      const requiredSavings = netIncomeNeeded / withdrawalRate;

      const futureValueCurrentSavings =
        currentSavings * Math.pow(1 + returnRate, yearsToRetirement);

      const additionalSavingsNeeded = Math.max(0, requiredSavings - futureValueCurrentSavings);

      const monthlyReturnRate = returnRate / 12;
      const monthsToRetirement = yearsToRetirement * 12;
      const requiredMonthlySavings =
        additionalSavingsNeeded > 0
          ? (additionalSavingsNeeded * monthlyReturnRate) /
            (Math.pow(1 + monthlyReturnRate, monthsToRetirement) - 1)
          : 0;

      const monthlySavingsRate = (requiredMonthlySavings * 12) / currentIncome;

      return JSON.stringify(
        {
          yearsToRetirement: yearsToRetirement,
          requiredRetirementSavings: Math.round(requiredSavings),
          currentSavings: currentSavings,
          futureValueCurrentSavings: Math.round(futureValueCurrentSavings),
          additionalSavingsNeeded: Math.round(additionalSavingsNeeded),
          requiredMonthlySavings: Math.round(requiredMonthlySavings),
          savingsRateNeeded: Math.round(monthlySavingsRate * 10000) / 100,
          projectedRetirementIncome: Math.round(futureRetirementIncome),
          analysis: `To maintain $${desiredRetirementIncome.toLocaleString()}/year in today's dollars during retirement, you need to save $${Math.round(requiredMonthlySavings).toLocaleString()}/month (${Math.round(monthlySavingsRate * 100)}% of current income).`,
        },
        null,
        2
      );
    },
  }),

  createBudgetAnalysis: tool({
    description: 'Analyze budget and provide spending recommendations',
    inputSchema: z.object({
      monthlyIncome: z.number().describe('Monthly after-tax income'),
      expenses: z
        .object({
          housing: z.number().describe('Housing costs (rent/mortgage, utilities)'),
          transportation: z.number().describe('Transportation costs'),
          food: z.number().describe('Food and dining expenses'),
          healthcare: z.number().describe('Healthcare and insurance'),
          entertainment: z.number().describe('Entertainment and recreation'),
          savings: z.number().describe('Current monthly savings'),
          other: z.number().describe('Other miscellaneous expenses'),
        })
        .describe('Monthly expense categories'),
    }),
    execute: async ({ monthlyIncome, expenses }) => {
      const totalExpenses = Object.values(expenses).reduce((sum, expense) => sum + expense, 0);
      const remainingIncome = monthlyIncome - totalExpenses;

      const percentages = Object.entries(expenses).reduce(
        (acc, [category, amount]) => {
          acc[category] = Math.round((amount / monthlyIncome) * 100);
          return acc;
        },
        {} as { [key: string]: number }
      );

      const recommendations = [];

      if (percentages.housing > 30) {
        recommendations.push(
          `Housing costs (${percentages.housing}%) exceed the recommended 30% of income.`
        );
      }

      if (percentages.savings < 20) {
        recommendations.push(
          `Increase savings to 20% of income (currently ${percentages.savings}%).`
        );
      }

      if (remainingIncome < 0) {
        recommendations.push(
          `Monthly expenses exceed income by $${Math.abs(remainingIncome)}. Immediate action needed.`
        );
      }

      const monthlyExpensesWithoutSavings = totalExpenses - expenses.savings;
      const emergencyFundTarget = monthlyExpensesWithoutSavings * 6;

      return JSON.stringify(
        {
          monthlyIncome: monthlyIncome,
          totalExpenses: totalExpenses,
          remainingIncome: remainingIncome,
          expensePercentages: percentages,
          budgetHealth:
            remainingIncome >= 0
              ? percentages.savings >= 15
                ? 'Excellent'
                : 'Good'
              : 'Needs Attention',
          emergencyFundTarget: Math.round(emergencyFundTarget),
          recommendations: recommendations,
          analysis: `Budget status: ${remainingIncome >= 0 ? 'Balanced' : 'Deficit'}. Savings rate: ${percentages.savings}% (target: 20%). ${recommendations.length > 0 ? 'Priority action needed.' : 'Well-managed budget!'}`,
        },
        null,
        2
      );
    },
  }),

  calculateEmergencyFund: tool({
    description: 'Calculate emergency fund needs and savings plan',
    inputSchema: z.object({
      monthlyExpenses: z.number().describe('Monthly essential expenses'),
      currentEmergencyFund: z.number().describe('Current emergency fund balance'),
      targetMonths: z
        .number()
        .optional()
        .describe('Target months of expenses to save (default: 6)'),
      monthlyContribution: z
        .number()
        .optional()
        .describe('Monthly amount to add to emergency fund'),
    }),
    execute: async ({
      monthlyExpenses,
      currentEmergencyFund,
      targetMonths = 6,
      monthlyContribution = 0,
    }) => {
      const targetAmount = monthlyExpenses * targetMonths;
      const shortfall = Math.max(0, targetAmount - currentEmergencyFund);
      const currentMonthsCovered = currentEmergencyFund / monthlyExpenses;

      let monthsToTarget = 0;
      if (shortfall > 0 && monthlyContribution > 0) {
        monthsToTarget = Math.ceil(shortfall / monthlyContribution);
      }

      let urgencyLevel = 'Low';
      if (currentMonthsCovered < 1) urgencyLevel = 'Critical';
      else if (currentMonthsCovered < 3) urgencyLevel = 'High';
      else if (currentMonthsCovered < 6) urgencyLevel = 'Moderate';

      const recommendations = [];

      if (currentMonthsCovered < 1) {
        recommendations.push('URGENT: Build $1,000 starter emergency fund immediately.');
      } else if (currentMonthsCovered < 3) {
        recommendations.push(
          'Priority: Increase emergency fund to 3 months of expenses before other investments.'
        );
      } else if (currentMonthsCovered < 6) {
        recommendations.push(
          'Continue building emergency fund to 6 months of expenses for full security.'
        );
      } else {
        recommendations.push('Emergency fund is adequate. Consider high-yield savings account.');
      }

      return JSON.stringify(
        {
          currentEmergencyFund: currentEmergencyFund,
          targetEmergencyFund: targetAmount,
          shortfall: shortfall,
          currentMonthsCovered: Math.round(currentMonthsCovered * 10) / 10,
          targetMonthsCovered: targetMonths,
          monthsToTarget: monthsToTarget,
          urgencyLevel: urgencyLevel,
          recommendations: recommendations,
          analysis: `Emergency fund status: ${Math.round(currentMonthsCovered * 10) / 10} months covered (target: ${targetMonths} months). ${urgencyLevel} priority. ${shortfall > 0 ? `Need $${shortfall.toLocaleString()} more.` : 'Target achieved!'}`,
        },
        null,
        2
      );
    },
  }),
};
