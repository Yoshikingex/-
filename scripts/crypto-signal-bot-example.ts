import { CryptoSignalBot, type TradeExecutor } from "../server/crypto-signal-bot";
import { updateTrailingStop } from "../shared/crypto-trading";

const executor: TradeExecutor = {
  async executeMarketBuy(input) {
    // NOTE: 実運用時はDEX/ブローカーSDKに置き換えてください。
    console.log("[EXECUTOR] placing order", input);
    return { orderId: `paper-${Date.now()}` };
  },
};

const bot = new CryptoSignalBot(executor, {
  grokApiKey: process.env.GROK_API_KEY ?? "",
  dryRun: process.env.DRY_RUN !== "false",
  minFollowers: 30_000,
  risk: {
    maxRiskPercent: 2,
    stopLossPercent: 15,
    targetProfitPercent: 300,
    trailingStopPercent: 12,
  },
});

async function main() {
  const result = await bot.processTweetSignal({
    tweet: {
      id: "tweet-1",
      username: "crypto_alpha",
      followerCount: 45_000,
      text: "new gem launched CA: 0x1234567890abcdef1234567890ABCDEF12345678",
      postedAt: new Date().toISOString(),
    },
    entryPrice: 0.00012,
    walletUsdBalance: 10_000,
  });

  console.log("[RESULT]", result);

  const highestPrice = 0.0003;
  const stop = updateTrailingStop({
    highestPrice,
    trailingStopPercent: 12,
  });
  console.log("[TRAILING_STOP]", stop);
}

void main();
