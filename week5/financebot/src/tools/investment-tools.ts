import { tool } from 'ai';
import { z } from 'zod';

function calculateMaxDrawdown(returns: number[]): number {
  let peak = 1;
  let maxDrawdown = 0;
  let value = 1;

  for (const r of returns) {
    value *= 1 + r;
    if (value > peak) {
      peak = value;
    }
    const drawdown = (peak - value) / peak;
    if (drawdown > maxDrawdown) {
      maxDrawdown = drawdown;
    }
  }

  return maxDrawdown;
}

function erf(x: number): number {
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;

  const sign = x < 0 ? -1 : 1;
  x = Math.abs(x);

  const t = 1.0 / (1.0 + p * x);
  const y = 1.0 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);

  return sign * y;
}

export const investmentTools = {
  analyzePortfolioDiversification: tool({
    description: 'Analyze portfolio diversification and suggest improvements',
    inputSchema: z.object({
      holdings: z
        .array(
          z.object({
            symbol: z.string().describe('Stock symbol or asset name'),
            value: z.number().describe('Current value in portfolio'),
            sector: z.string().describe('Sector (e.g., Technology, Healthcare, Finance)'),
            assetType: z.string().describe('Asset type (stock, bond, ETF, crypto, etc.)'),
          })
        )
        .describe('Array of current portfolio holdings'),
      riskTolerance: z
        .enum(['conservative', 'moderate', 'aggressive'])
        .describe('Risk tolerance level'),
    }),
    execute: async ({ holdings, riskTolerance }) => {
      const totalValue = holdings.reduce((sum, holding) => sum + holding.value, 0);

      const sectorAllocations: { [key: string]: number } = {};
      holdings.forEach(holding => {
        sectorAllocations[holding.sector] =
          (sectorAllocations[holding.sector] || 0) + holding.value;
      });

      const assetAllocations: { [key: string]: number } = {};
      holdings.forEach(holding => {
        assetAllocations[holding.assetType] =
          (assetAllocations[holding.assetType] || 0) + holding.value;
      });

      const largestHolding = Math.max(...holdings.map(h => h.value));
      const concentrationRisk = largestHolding / totalValue;

      const idealAllocations = {
        conservative: { stocks: 0.4, bonds: 0.5, cash: 0.1 },
        moderate: { stocks: 0.6, bonds: 0.3, cash: 0.1 },
        aggressive: { stocks: 0.8, bonds: 0.15, cash: 0.05 },
      };

      const ideal = idealAllocations[riskTolerance];
      const sectorCount = Object.keys(sectorAllocations).length;
      const maxSectorAllocation = Math.max(...Object.values(sectorAllocations)) / totalValue;
      const diversificationScore = Math.max(
        0,
        100 - maxSectorAllocation * 100 - Math.max(0, (concentrationRisk - 0.1) * 200)
      );

      const recommendations = [];

      if (concentrationRisk > 0.2) {
        recommendations.push(
          `Reduce concentration risk: Your largest holding represents ${Math.round(concentrationRisk * 100)}% of portfolio.`
        );
      }

      if (sectorCount < 5) {
        recommendations.push(
          `Increase sector diversification: Currently invested in ${sectorCount} sectors.`
        );
      }

      return JSON.stringify(
        {
          portfolioValue: totalValue,
          diversificationScore: Math.round(diversificationScore),
          concentrationRisk: Math.round(concentrationRisk * 100),
          sectorCount: sectorCount,
          recommendations: recommendations,
          analysis: `Portfolio diversification score: ${Math.round(diversificationScore)}/100. ${recommendations.length > 0 ? 'Key improvements needed.' : 'Well-diversified portfolio.'}`,
        },
        null,
        2
      );
    },
  }),

  calculateRiskAdjustedReturn: tool({
    description: 'Calculate risk-adjusted returns (Sharpe ratio) and volatility metrics',
    inputSchema: z.object({
      returns: z.array(z.number()).describe('Array of periodic returns (as decimals)'),
      riskFreeRate: z.number().optional().describe('Risk-free rate (default: 0.02 for 2%)'),
    }),
    execute: async ({ returns, riskFreeRate = 0.02 }) => {
      if (returns.length === 0) {
        return JSON.stringify({ error: 'No returns data provided' });
      }

      const averageReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
      const variance =
        returns.reduce((sum, r) => sum + Math.pow(r - averageReturn, 2), 0) / (returns.length - 1);
      const volatility = Math.sqrt(variance);

      const excessReturn = averageReturn - riskFreeRate / 12;
      const sharpeRatio = volatility > 0 ? excessReturn / volatility : 0;

      const maxReturn = Math.max(...returns);
      const minReturn = Math.min(...returns);
      const maxDrawdown = calculateMaxDrawdown(returns);

      const annualizedReturn = Math.pow(1 + averageReturn, 12) - 1;
      const annualizedVolatility = volatility * Math.sqrt(12);
      const annualizedSharpe = (annualizedReturn - riskFreeRate) / annualizedVolatility;

      let riskLevel = 'Low';
      if (annualizedVolatility > 0.15) riskLevel = 'Moderate';
      if (annualizedVolatility > 0.25) riskLevel = 'High';
      if (annualizedVolatility > 0.35) riskLevel = 'Very High';

      return JSON.stringify(
        {
          averageMonthlyReturn: Math.round(averageReturn * 10000) / 100,
          annualizedReturn: Math.round(annualizedReturn * 10000) / 100,
          volatility: Math.round(annualizedVolatility * 10000) / 100,
          sharpeRatio: Math.round(annualizedSharpe * 100) / 100,
          maxReturn: Math.round(maxReturn * 10000) / 100,
          minReturn: Math.round(minReturn * 10000) / 100,
          maxDrawdown: Math.round(maxDrawdown * 10000) / 100,
          riskLevel: riskLevel,
          analysis: `Annualized return: ${Math.round(annualizedReturn * 100)}%, Volatility: ${Math.round(annualizedVolatility * 100)}%, Sharpe Ratio: ${Math.round(annualizedSharpe * 100) / 100}. ${sharpeRatio > 1 ? 'Excellent' : sharpeRatio > 0.5 ? 'Good' : 'Poor'} risk-adjusted performance.`,
        },
        null,
        2
      );
    },
  }),

  evaluateInvestmentOption: tool({
    description: 'Evaluate investment opportunities using multiple financial metrics',
    inputSchema: z.object({
      investmentName: z.string().describe('Name of the investment'),
      initialInvestment: z.number().describe('Initial investment amount'),
      expectedAnnualReturn: z.number().describe('Expected annual return rate'),
      expectedVolatility: z.number().describe('Expected annual volatility (standard deviation)'),
      investmentHorizon: z.number().describe('Investment time horizon in years'),
      fees: z.number().optional().describe('Annual fees as percentage (default: 0)'),
      riskFreeRate: z.number().optional().describe('Risk-free rate for comparison (default: 0.02)'),
      userRiskTolerance: z
        .enum(['conservative', 'moderate', 'aggressive'])
        .optional()
        .describe('User risk tolerance'),
    }),
    execute: async ({
      investmentName,
      initialInvestment,
      expectedAnnualReturn,
      expectedVolatility,
      investmentHorizon,
      fees = 0,
      riskFreeRate = 0.02,
      userRiskTolerance = 'moderate',
    }) => {
      const netExpectedReturn = expectedAnnualReturn - fees;
      const futureValue = initialInvestment * Math.pow(1 + netExpectedReturn, investmentHorizon);
      const totalReturn = futureValue - initialInvestment;
      const totalReturnPercentage = (totalReturn / initialInvestment) * 100;

      const excessReturn = netExpectedReturn - riskFreeRate;
      const sharpeRatio = expectedVolatility > 0 ? excessReturn / expectedVolatility : 0;

      const valueAtRisk =
        initialInvestment * (1 - Math.exp(netExpectedReturn - 1.645 * expectedVolatility));

      const probOfLoss =
        0.5 * (1 + erf(-netExpectedReturn / (expectedVolatility * Math.sqrt(2)))) * 100;

      const riskToleranceRanges = {
        conservative: { maxVolatility: 0.1, minSharpe: 0.5 },
        moderate: { maxVolatility: 0.2, minSharpe: 0.3 },
        aggressive: { maxVolatility: 0.35, minSharpe: 0.2 },
      };

      const toleranceMatch = riskToleranceRanges[userRiskTolerance];
      const riskMatch =
        expectedVolatility <= toleranceMatch.maxVolatility &&
        sharpeRatio >= toleranceMatch.minSharpe;

      let grade = 'D';
      if (sharpeRatio > 1.0 && expectedVolatility < 0.15) grade = 'A';
      else if (sharpeRatio > 0.7 && expectedVolatility < 0.2) grade = 'B';
      else if (sharpeRatio > 0.4 && expectedVolatility < 0.25) grade = 'C';

      const recommendations = [];
      if (!riskMatch) {
        recommendations.push('Risk level may not match your tolerance profile.');
      }
      if (fees > 0.01) {
        recommendations.push(
          `Consider lower-cost alternatives to reduce ${Math.round(fees * 100)}% fees.`
        );
      }

      return JSON.stringify(
        {
          investmentName: investmentName,
          initialInvestment: initialInvestment,
          projectedFutureValue: Math.round(futureValue),
          totalReturn: Math.round(totalReturn),
          totalReturnPercentage: Math.round(totalReturnPercentage * 100) / 100,
          annualizedReturn: Math.round(netExpectedReturn * 10000) / 100,
          volatility: Math.round(expectedVolatility * 10000) / 100,
          sharpeRatio: Math.round(sharpeRatio * 100) / 100,
          valueAtRisk95: Math.round(valueAtRisk),
          probabilityOfLoss: Math.round(probOfLoss * 10) / 10,
          investmentGrade: grade,
          riskToleranceMatch: riskMatch,
          recommendations: recommendations,
          analysis: `Grade ${grade} investment. Expected ${Math.round(totalReturnPercentage)}% total return over ${investmentHorizon} years with ${Math.round(probOfLoss)}% probability of loss.`,
        },
        null,
        2
      );
    },
  }),
};
