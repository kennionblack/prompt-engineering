import { tool } from 'ai';
import { z } from 'zod';

export class FinanceTools {
  private tools: any = {};

  initialize() {
    this.tools = {
      calculateCompoundInterest: this.createCompoundInterestTool(),
      calculateLoanPayment: this.createLoanPaymentTool(),
      createBudgetAnalysis: this.createBudgetAnalysisTool(),
    };
  }

  getTools() {
    return this.tools;
  }

  private createCompoundInterestTool() {
    return tool({
      description: 'Calculate compound interest for investments',
      inputSchema: z.object({
        principal: z.number().describe('Initial investment amount'),
        annualRate: z.number().describe('Annual interest rate as decimal (e.g., 0.07 for 7%)'),
        years: z.number().describe('Number of years to compound'),
        monthlyContribution: z.number().optional().describe('Additional monthly contribution'),
      }),
      execute: async ({ principal, annualRate, years, monthlyContribution = 0 }) => {
        const monthlyRate = annualRate / 12;
        const months = years * 12;

        // Future value of principal
        const futureValuePrincipal = principal * Math.pow(1 + monthlyRate, months);

        // Future value of contributions
        let futureValueContributions = 0;
        if (monthlyContribution > 0) {
          futureValueContributions =
            monthlyContribution * ((Math.pow(1 + monthlyRate, months) - 1) / monthlyRate);
        }

        const totalFutureValue = futureValuePrincipal + futureValueContributions;
        const totalContributions = principal + monthlyContribution * months;
        const totalGain = totalFutureValue - totalContributions;

        return JSON.stringify(
          {
            initialInvestment: principal,
            monthlyContribution: monthlyContribution,
            futureValue: Math.round(totalFutureValue),
            totalGain: Math.round(totalGain),
            analysis: `After ${years} years, your investment will grow to $${Math.round(totalFutureValue).toLocaleString()}.`,
          },
          null,
          2
        );
      },
    });
  }

  private createLoanPaymentTool() {
    return tool({
      description: 'Calculate loan payments and total interest',
      inputSchema: z.object({
        loanAmount: z.number().describe('Principal loan amount'),
        annualRate: z.number().describe('Annual interest rate as decimal'),
        termYears: z.number().describe('Loan term in years'),
      }),
      execute: async ({ loanAmount, annualRate, termYears }) => {
        const monthlyRate = annualRate / 12;
        const numPayments = termYears * 12;

        const monthlyPayment =
          (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, numPayments)) /
          (Math.pow(1 + monthlyRate, numPayments) - 1);

        const totalPaid = monthlyPayment * numPayments;
        const totalInterest = totalPaid - loanAmount;

        return JSON.stringify(
          {
            loanAmount: loanAmount,
            monthlyPayment: Math.round(monthlyPayment),
            totalInterest: Math.round(totalInterest),
            analysis: `Monthly payment: $${Math.round(monthlyPayment)}, Total interest: $${Math.round(totalInterest).toLocaleString()}`,
          },
          null,
          2
        );
      },
    });
  }

  private createBudgetAnalysisTool() {
    return tool({
      description: 'Analyze budget and provide recommendations',
      inputSchema: z.object({
        monthlyIncome: z.number().describe('Monthly after-tax income'),
        expenses: z.object({
          housing: z.number().describe('Housing costs'),
          transportation: z.number().describe('Transportation costs'),
          food: z.number().describe('Food expenses'),
          savings: z.number().describe('Current monthly savings'),
          other: z.number().describe('Other expenses'),
        }),
      }),
      execute: async ({ monthlyIncome, expenses }) => {
        const totalExpenses = Object.values(expenses).reduce((sum, expense) => sum + expense, 0);
        const remainingIncome = monthlyIncome - totalExpenses;
        const savingsRate = (expenses.savings / monthlyIncome) * 100;
        const housingRate = (expenses.housing / monthlyIncome) * 100;

        const recommendations = [];
        if (housingRate > 30) {
          recommendations.push(
            `Housing costs (${Math.round(housingRate)}%) exceed recommended 30%.`
          );
        }
        if (savingsRate < 20) {
          recommendations.push(
            `Increase savings rate to 20% (currently ${Math.round(savingsRate)}%).`
          );
        }

        return JSON.stringify(
          {
            monthlyIncome: monthlyIncome,
            totalExpenses: totalExpenses,
            remainingIncome: remainingIncome,
            savingsRate: Math.round(savingsRate),
            recommendations: recommendations,
            analysis: `Budget status: ${remainingIncome >= 0 ? 'Balanced' : 'Deficit'}. Savings rate: ${Math.round(savingsRate)}%`,
          },
          null,
          2
        );
      },
    });
  }
}
