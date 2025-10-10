import { tool } from 'ai';
import { z } from 'zod';

export const taxTools = {
  analyzeTaxImplications: tool({
    description: 'Analyze tax implications of investment and retirement decisions',
    inputSchema: z.object({
      annualIncome: z.number().describe('Annual taxable income'),
      fillingStatus: z
        .enum(['single', 'married_joint', 'married_separate', 'head_of_household'])
        .describe('Tax filing status'),
      traditionalIRAContribution: z.number().optional().describe('Traditional IRA contribution'),
      rothIRAContribution: z.number().optional().describe('Roth IRA contribution'),
      k401Contribution: z.number().optional().describe('401(k) contribution'),
      capitalGains: z.number().optional().describe('Long-term capital gains'),
      state: z.string().optional().describe('State for state tax calculation'),
    }),
    execute: async ({
      annualIncome,
      fillingStatus,
      traditionalIRAContribution = 0,
      rothIRAContribution = 0,
      k401Contribution = 0,
      capitalGains = 0,
      state = 'N/A',
    }) => {
      const taxBrackets = {
        single: [
          { min: 0, max: 11000, rate: 0.1 },
          { min: 11000, max: 44725, rate: 0.12 },
          { min: 44725, max: 95375, rate: 0.22 },
          { min: 95375, max: 182050, rate: 0.24 },
          { min: 182050, max: 231250, rate: 0.32 },
          { min: 231250, max: 578125, rate: 0.35 },
          { min: 578125, max: Infinity, rate: 0.37 },
        ],
        married_joint: [
          { min: 0, max: 22000, rate: 0.1 },
          { min: 22000, max: 89450, rate: 0.12 },
          { min: 89450, max: 190750, rate: 0.22 },
          { min: 190750, max: 364200, rate: 0.24 },
          { min: 364200, max: 462500, rate: 0.32 },
          { min: 462500, max: 693750, rate: 0.35 },
          { min: 693750, max: Infinity, rate: 0.37 },
        ],
      };

      const brackets = taxBrackets[fillingStatus as keyof typeof taxBrackets] || taxBrackets.single;

      const preTaxContributions = traditionalIRAContribution + k401Contribution;
      const taxableIncome = Math.max(0, annualIncome - preTaxContributions);

      let federalTax = 0;
      for (const bracket of brackets) {
        const taxableAtBracket = Math.max(0, Math.min(taxableIncome, bracket.max) - bracket.min);
        federalTax += taxableAtBracket * bracket.rate;
        if (taxableIncome <= bracket.max) break;
      }

      const marginalTaxRate =
        brackets.find(b => taxableIncome > b.min && taxableIncome <= b.max)?.rate || 0.37;

      let capitalGainsTax = 0;
      if (capitalGains > 0) {
        const cgRate = taxableIncome < 44725 ? 0 : taxableIncome < 492300 ? 0.15 : 0.2;
        capitalGainsTax = capitalGains * cgRate;
      }

      const taxSavings = preTaxContributions * marginalTaxRate;
      const effectiveTaxRate = federalTax / annualIncome;

      const recommendations = [];

      const k401Max = 23000;
      const iraMax = 7000;

      if (k401Contribution < k401Max) {
        const additionalContribution = Math.min(k401Max - k401Contribution, annualIncome * 0.1);
        const additionalSavings = additionalContribution * marginalTaxRate;
        recommendations.push(
          `Consider increasing 401(k) contribution by $${Math.round(additionalContribution)} to save $${Math.round(additionalSavings)} in taxes.`
        );
      }

      if (traditionalIRAContribution + rothIRAContribution < iraMax) {
        const remaining = iraMax - traditionalIRAContribution - rothIRAContribution;
        if (marginalTaxRate >= 0.22) {
          recommendations.push(
            `Consider contributing $${remaining} to Traditional IRA for immediate tax deduction.`
          );
        } else {
          recommendations.push(
            `Consider contributing $${remaining} to Roth IRA for tax-free growth.`
          );
        }
      }

      return JSON.stringify(
        {
          annualIncome: annualIncome,
          taxableIncome: taxableIncome,
          federalTax: Math.round(federalTax),
          marginalTaxRate: Math.round(marginalTaxRate * 100),
          effectiveTaxRate: Math.round(effectiveTaxRate * 100),
          capitalGainsTax: Math.round(capitalGainsTax),
          taxSavingsFromContributions: Math.round(taxSavings),
          netIncome: Math.round(annualIncome - federalTax - capitalGainsTax),
          recommendations: recommendations,
          analysis: `Effective tax rate: ${Math.round(effectiveTaxRate * 100)}%. Pre-tax contributions saved $${Math.round(taxSavings)} in taxes. ${recommendations.length > 0 ? 'Key opportunity available.' : 'Tax-efficient strategy in place.'}`,
        },
        null,
        2
      );
    },
  }),
};
