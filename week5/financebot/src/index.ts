import dotenv from 'dotenv';
import { FinanceBotCLI } from './cli.js';

dotenv.config();

// Start FinanceBot
const financeBot = new FinanceBotCLI();
financeBot.start().catch(console.error);
