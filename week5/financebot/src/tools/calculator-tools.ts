import { tool } from 'ai';
import { z } from 'zod';

export const calculatorTools = {
  calculateCompoundInterest: tool({
    description: 'Calculate compound interest for investments with various compounding frequencies',
    inputSchema: z.object({
      principal: z.number().describe('Initial investment amount'),
      annualRate: z.number().describe('Annual interest rate as decimal (e.g., 0.07 for 7%)'),
      years: z.number().describe('Number of years to compound'),
      compoundingFrequency: z
        .number()
        .optional()
        .describe('Times per year interest compounds (default: 12 for monthly)'),
      monthlyContribution: z.number().optional().describe('Additional monthly contribution'),
    }),
    execute: async ({
      principal,
      annualRate,
      years,
      compoundingFrequency = 12,
      monthlyContribution = 0,
    }) => {
      const r = annualRate / compoundingFrequency;
      const n = compoundingFrequency * years;

      // Future value of initial principal
      const futureValuePrincipal = principal * Math.pow(1 + r, n);

      // Future value of monthly contributions (annuity)
      let futureValueContributions = 0;
      if (monthlyContribution > 0) {
        const monthlyRate = annualRate / 12;
        const monthsTotal = years * 12;
        futureValueContributions =
          monthlyContribution * ((Math.pow(1 + monthlyRate, monthsTotal) - 1) / monthlyRate);
      }

      const totalFutureValue = futureValuePrincipal + futureValueContributions;
      const totalContributions = principal + monthlyContribution * years * 12;
      const totalGain = totalFutureValue - totalContributions;
      const effectiveAnnualReturn = Math.pow(totalFutureValue / principal, 1 / years) - 1;

      return JSON.stringify(
        {
          initialInvestment: principal,
          monthlyContribution: monthlyContribution,
          totalContributions: totalContributions,
          futureValue: Math.round(totalFutureValue * 100) / 100,
          totalGain: Math.round(totalGain * 100) / 100,
          effectiveAnnualReturn: Math.round(effectiveAnnualReturn * 10000) / 100,
          analysis: `After ${years} years with ${(annualRate * 100).toFixed(1)}% annual return, your $${principal.toLocaleString()} initial investment${monthlyContribution > 0 ? ` plus $${monthlyContribution}/month contributions` : ''} will grow to $${Math.round(totalFutureValue).toLocaleString()}, earning $${Math.round(totalGain).toLocaleString()} in returns.`,
        },
        null,
        2
      );
    },
  }),

  calculateLoanPayment: tool({
    description: 'Calculate loan payments, total interest, and amortization schedules',
    inputSchema: z.object({
      loanAmount: z.number().describe('Principal loan amount'),
      annualRate: z.number().describe('Annual interest rate as decimal (e.g., 0.045 for 4.5%)'),
      termYears: z.number().describe('Loan term in years'),
      extraPayment: z.number().optional().describe('Extra monthly payment amount'),
    }),
    execute: async ({ loanAmount, annualRate, termYears, extraPayment = 0 }) => {
      const monthlyRate = annualRate / 12;
      const numPayments = termYears * 12;

      const monthlyPayment =
        (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, numPayments)) /
        (Math.pow(1 + monthlyRate, numPayments) - 1);

      const totalPayment = monthlyPayment + extraPayment;

      let balance = loanAmount;
      let totalInterest = 0;
      let monthsPaid = 0;

      while (balance > 0.01 && monthsPaid < numPayments * 2) {
        const interestPayment = balance * monthlyRate;
        const principalPayment = Math.min(totalPayment - interestPayment, balance);

        balance -= principalPayment;
        totalInterest += interestPayment;
        monthsPaid++;
      }

      const yearsToPayoff = monthsPaid / 12;
      const standardTotalInterest = monthlyPayment * numPayments - loanAmount;
      const interestSaved = standardTotalInterest - totalInterest;
      const timeSaved = termYears * 12 - monthsPaid;

      return JSON.stringify(
        {
          loanAmount: loanAmount,
          monthlyPayment: Math.round(monthlyPayment * 100) / 100,
          extraPayment: extraPayment,
          totalMonthlyPayment: Math.round(totalPayment * 100) / 100,
          actualPayoffTime: Math.round(yearsToPayoff * 100) / 100,
          totalInterestPaid: Math.round(totalInterest * 100) / 100,
          interestSaved: Math.round(interestSaved * 100) / 100,
          monthsSaved: timeSaved,
          analysis: `With $${extraPayment > 0 ? `${Math.round(totalPayment)}` : `${Math.round(monthlyPayment)}`}/month payments, you'll pay off the $${loanAmount.toLocaleString()} loan in ${Math.round(yearsToPayoff * 10) / 10} years${extraPayment > 0 ? `, saving $${Math.round(interestSaved).toLocaleString()} in interest and ${Math.round(timeSaved)} months` : ''}.`,
        },
        null,
        2
      );
    },
  }),

  calculateInflationImpact: tool({
    description: 'Calculate the impact of inflation on purchasing power and investment returns',
    inputSchema: z.object({
      currentValue: z.number().describe('Current dollar amount'),
      years: z.number().describe('Number of years to project'),
      inflationRate: z.number().optional().describe('Annual inflation rate (default: 0.03 for 3%)'),
      investmentReturn: z.number().optional().describe('Annual investment return rate to compare'),
    }),
    execute: async ({ currentValue, years, inflationRate = 0.03, investmentReturn }) => {
      const futurePurchasingPower = currentValue / Math.pow(1 + inflationRate, years);
      const purchasingPowerLoss = currentValue - futurePurchasingPower;
      const percentageLoss = (purchasingPowerLoss / currentValue) * 100;

      let realReturn = null;
      let futureValueNominal = null;
      let futureValueReal = null;

      if (investmentReturn !== undefined) {
        realReturn = (1 + investmentReturn) / (1 + inflationRate) - 1;
        futureValueNominal = currentValue * Math.pow(1 + investmentReturn, years);
        futureValueReal = futureValueNominal / Math.pow(1 + inflationRate, years);
      }

      const requiredReturn = inflationRate;

      return JSON.stringify(
        {
          currentValue: currentValue,
          yearsProjected: years,
          inflationRate: Math.round(inflationRate * 10000) / 100,
          futurePurchasingPower: Math.round(futurePurchasingPower),
          purchasingPowerLoss: Math.round(purchasingPowerLoss),
          percentageLoss: Math.round(percentageLoss * 100) / 100,
          requiredReturnToMaintainPower: Math.round(requiredReturn * 10000) / 100,
          investmentAnalysis:
            investmentReturn !== undefined
              ? {
                  nominalReturn: Math.round(investmentReturn * 10000) / 100,
                  realReturn: Math.round(realReturn! * 10000) / 100,
                  futureValueNominal: Math.round(futureValueNominal!),
                  futureValueReal: Math.round(futureValueReal!),
                  beatsInflation: realReturn! > 0,
                }
              : null,
          analysis: `In ${years} years, $${currentValue.toLocaleString()} will have the purchasing power of $${Math.round(futurePurchasingPower).toLocaleString()} today (${Math.round(percentageLoss)}% loss). ${investmentReturn !== undefined ? `Your ${Math.round(investmentReturn * 100)}% investment return provides ${Math.round(realReturn! * 100)}% real return after inflation.` : `Investments need ${Math.round(requiredReturn * 100)}%+ returns to maintain purchasing power.`}`,
        },
        null,
        2
      );
    },
  }),
};
