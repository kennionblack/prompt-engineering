# FinanceBot 🏦

An intelligent MCP-powered personal finance advisor that provides comprehensive financial guidance, real-time market data, and personalized investment recommendations.

## Features 🚀

### Core Capabilities

- **Personalized Financial Advice**: Tailored recommendations based on your risk tolerance, investment horizon, and financial goals
- **Real-Time Market Data**: Integration with Yahoo Finance MCP server for live stock prices, financial statements, and market news
- **Advanced Financial Calculations**: Built-in tools for compound interest, loan payments, retirement planning, and more
- **Portfolio Analysis**: Comprehensive diversification analysis and optimization recommendations
- **Budget Planning**: Smart budgeting tools with the 50/30/20 rule and expense tracking
- **Risk Assessment**: Sharpe ratio calculations, volatility analysis, and risk-adjusted returns

### Built-in Financial Tools

- 📈 **Compound Interest Calculator**: Project investment growth with regular contributions
- 💰 **Loan Payment Analyzer**: Calculate payments, interest savings, and payoff strategies
- 🎯 **Retirement Planning**: Determine savings needs and monthly contribution requirements
- 📊 **Portfolio Diversification**: Analyze sector allocation and concentration risk
- ⚖️ **Risk-Adjusted Returns**: Calculate Sharpe ratios and volatility metrics
- 💳 **Budget Analysis**: Apply the 50/30/20 rule and identify spending optimizations
- 🆘 **Emergency Fund Calculator**: Plan for financial emergencies
- 📋 **Tax Strategy Analysis**: Optimize retirement contributions and tax efficiency
- 💵 **Inflation Impact**: Understand purchasing power erosion over time
- 🎲 **Investment Evaluation**: Multi-metric investment opportunity assessment

### MCP Server Integrations

- **Yahoo Finance MCP**: Live stock data, financial statements, options chains, and market news
- **Future Integrations**: Portfolio management, trading APIs, and financial modeling tools

## Installation & Setup 📦

### Prerequisites

- Node.js 18+ with npm
- Python 3.11+ (for Yahoo Finance MCP server)
- OpenAI API key

### Quick Start

1. **Clone and Install**

   ```bash
   cd week5/financebot
   npm install
   ```

2. **Environment Setup**

   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Optional: Set Up Yahoo Finance MCP Server**

   ```bash
   # Create MCP servers directory
   mkdir -p mcp-servers

   # Clone Yahoo Finance MCP
   git clone https://github.com/Alex2Yang97/yahoo-finance-mcp.git mcp-servers/yahoo-finance

   # Install Python dependencies
   cd mcp-servers/yahoo-finance
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   cd ../..

   # Update .env with the path
   echo "YAHOO_FINANCE_MCP_PATH=./mcp-servers/yahoo-finance" >> .env
   echo "ENABLE_STOCK_ANALYSIS=true" >> .env
   ```

4. **Build and Run**
   ```bash
   npm run build
   npm start
   ```

## Usage Guide 💡

### Getting Started

When you start FinanceBot, you'll see a personalized welcome screen. The bot maintains your financial profile including risk tolerance, investment horizon, and financial goals.

### Basic Commands

- `help` - Show available commands and example questions
- `profile` - View/edit your financial profile
- `status` - Check system status and portfolio summary
- `clear` - Clear conversation history
- `exit` - Exit FinanceBot

### Example Interactions

#### Stock Analysis

```
💰 > What's the current price and performance of Apple stock?
💰 > Analyze Tesla's financial statements for the last quarter
💰 > Get the latest news about Microsoft
```

#### Portfolio Management

```
💰 > My portfolio has 60% stocks and 40% bonds. How's my diversification?
💰 > I have $50k in tech stocks. Should I rebalance for a moderate risk profile?
💰 > Calculate the risk-adjusted returns for my investment returns: [0.08, 0.12, -0.03, 0.15, 0.09]
```

#### Financial Planning

```
💰 > I'm 30 years old, want to retire at 65 with $80k/year income. How much should I save monthly?
💰 > Calculate compound interest on $10,000 invested for 20 years at 7% with $500 monthly contributions
💰 > Help me create a budget with $6,000 monthly income
```

#### Investment Analysis

```
💰 > Should I invest in QQQ ETF given my moderate risk tolerance?
💰 > Compare the risk-return profile of VTI vs SPY
💰 > What's the impact of 3% inflation on $100,000 over 10 years?
```

## Configuration ⚙️

### Environment Variables

| Variable                     | Description                       | Default                       |
| ---------------------------- | --------------------------------- | ----------------------------- |
| `OPENAI_API_KEY`             | Your OpenAI API key               | Required                      |
| `YAHOO_FINANCE_MCP_PATH`     | Path to Yahoo Finance MCP server  | `./mcp-servers/yahoo-finance` |
| `DEFAULT_CURRENCY`           | Default currency for calculations | `USD`                         |
| `DEFAULT_RISK_TOLERANCE`     | Initial risk tolerance setting    | `moderate`                    |
| `DEFAULT_INVESTMENT_HORIZON` | Initial investment horizon        | `long_term`                   |
| `ENABLE_STOCK_ANALYSIS`      | Enable Yahoo Finance integration  | `true`                        |
| `ENABLE_PORTFOLIO_TRACKING`  | Enable portfolio features         | `true`                        |
| `ENABLE_NEWS_ALERTS`         | Enable market news features       | `true`                        |
| `ENABLE_BUDGET_ADVICE`       | Enable budgeting tools            | `true`                        |

### User Profile

The bot automatically learns and updates your financial profile based on your conversations:

- **Risk Tolerance**: Conservative, Moderate, or Aggressive
- **Investment Horizon**: Short-term, Medium-term, or Long-term
- **Currency**: Primary currency for calculations
- **Financial Goals**: Retirement, house purchase, emergency fund, etc.
- **Portfolio Holdings**: Track your current investments

## Architecture 🏗️

### Core Components

1. **FinanceBotAgent**: Main AI agent with advanced prompting strategies
2. **FinanceTools**: Comprehensive financial calculation toolkit
3. **MCP Client Integration**: Connects to external financial data sources
4. **User Profile Management**: Maintains personalized financial context
5. **Conversational Memory**: Tracks discussion topics and preferences

### Agentic AI Principles

FinanceBot implements advanced agentic AI patterns:

- **Contextual Awareness**: Maintains user profile and conversation history
- **Tool Integration**: Seamlessly combines multiple data sources and calculations
- **Proactive Analysis**: Suggests relevant analyses and improvements
- **Personalized Recommendations**: Tailors advice to individual circumstances
- **Risk Assessment**: Considers multiple risk factors in recommendations
- **Continuous Learning**: Updates understanding based on user preferences

### MCP Server Architecture

The bot uses the Model Context Protocol (MCP) to connect with external financial data sources:

```
FinanceBot Client ←→ MCP Protocol ←→ Yahoo Finance Server
                                  ←→ Future: Alpaca Trading API
                                  ←→ Future: Portfolio Management Server
                                  ←→ Future: Economic Data Server
```

## Development 🛠️

### Project Structure

```
financebot/
├── src/
│   ├── index.ts          # Main application entry point
│   ├── finance-tools.ts  # Built-in financial calculation tools
├── mcp-servers/          # External MCP server installations
│   └── yahoo-finance/    # Yahoo Finance MCP server
├── package.json          # Node.js dependencies and scripts
├── tsconfig.json         # TypeScript configuration
├── .env.example          # Environment variables template
└── README.md            # This file
```

### Building from Source

```bash
# Install dependencies
npm install

# Development mode (watch for changes)
npm run dev

# Production build
npm run build
npm start

# Format code
npm run format

# Type checking
npm run check
```

### Adding New MCP Servers

1. Install the MCP server in the `mcp-servers/` directory
2. Add configuration to the `mcpServers` array in `index.ts`
3. Update environment variables as needed
4. Test the integration with the new tools

### Extending Financial Tools

Add new tools to `finance-tools.ts`:

```typescript
private createNewFinanceTool() {
  return tool({
    description: 'Description of your new financial tool',
    inputSchema: z.object({
      parameter: z.number().describe('Parameter description'),
    }),
    execute: async ({ parameter }) => {
      // Your calculation logic
      return JSON.stringify(result, null, 2);
    },
  });
}
```

## Troubleshooting 🔧

### Common Issues

**Error: "Yahoo Finance MCP server not available"**

- Ensure Python 3.11+ is installed
- Verify the Yahoo Finance MCP server is properly installed
- Check the `YAHOO_FINANCE_MCP_PATH` environment variable

**Error: "No OpenAI API key provided"**

- Add your OpenAI API key to the `.env` file
- Ensure the `.env` file is in the project root directory

**Tool execution errors**

- Check network connectivity for external data sources
- Verify API rate limits aren't exceeded
- Review console logs for detailed error messages

### Performance Tips

- Use `status` command to check system resources
- Clear conversation history periodically with `clear`
- Restart the bot if MCP connections become unstable

## Security & Privacy 🔒

- All financial calculations are performed locally
- External APIs are only used for market data (Yahoo Finance)
- Your personal financial information is not transmitted to external services
- OpenAI API is used only for natural language processing

## Contributing 🤝

This project is part of a prompt engineering coursework. Contributions should focus on:

1. Additional MCP server integrations
2. Enhanced financial calculation tools
3. Improved agentic AI prompting strategies
4. Better user experience and interface design
5. Additional risk assessment metrics

## License 📄

MIT License - see the `package.json` file for details.

## Acknowledgments 🙏

- [Yahoo Finance MCP Server](https://github.com/Alex2Yang97/yahoo-finance-mcp) by Alex2Yang97
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [AI SDK](https://sdk.vercel.ai/) by Vercel
- Course materials and template from the prompt engineering curriculum

---

**Disclaimer**: FinanceBot is for educational and informational purposes only. It does not provide professional financial advice. Always consult with qualified financial advisors for investment decisions.
