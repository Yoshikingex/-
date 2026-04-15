import axios from "axios";
import {
  buildTradePlan,
  type InfluencerTweet,
  type RiskConfig,
  shouldExecuteTrade,
} from "../shared/crypto-trading";

interface GrokSignalResult {
  confidence: number;
  summary: string;
}

interface ExecuteOrderInput {
  contractAddress: string;
  amountUsd: number;
  stopLossPrice: number;
  takeProfitPrice: number;
}

export interface TradeExecutor {
  executeMarketBuy(input: ExecuteOrderInput): Promise<{ orderId: string }>;
}

export class CryptoSignalBot {
  constructor(
    private readonly executor: TradeExecutor,
    private readonly config: {
      grokApiKey: string;
      dryRun: boolean;
      minFollowers: number;
      risk: RiskConfig;
    },
  ) {}

  async processTweetSignal(params: {
    tweet: InfluencerTweet;
    entryPrice: number;
    walletUsdBalance: number;
  }): Promise<{ status: "ignored" | "executed"; reason: string; orderId?: string }> {
    const decision = shouldExecuteTrade({
      tweet: params.tweet,
      minFollowers: this.config.minFollowers,
      dryRun: this.config.dryRun,
    });

    if (!decision.contractAddress) {
      return { status: "ignored", reason: decision.reason };
    }

    const grokSignal = await this.analyzeWithGrok(params.tweet);
    if (grokSignal.confidence < 0.7) {
      return { status: "ignored", reason: `Low confidence (${grokSignal.confidence})` };
    }

    if (!decision.shouldExecute) {
      return { status: "ignored", reason: decision.reason };
    }

    const tradePlan = buildTradePlan({
      contractAddress: decision.contractAddress,
      entryPrice: params.entryPrice,
      walletUsdBalance: params.walletUsdBalance,
      config: this.config.risk,
    });

    if (tradePlan.riskRewardRatio <= 1) {
      return {
        status: "ignored",
        reason: `Risk reward too low (${tradePlan.riskRewardRatio.toFixed(2)})`,
      };
    }

    const order = await this.executor.executeMarketBuy({
      contractAddress: tradePlan.contractAddress,
      amountUsd: tradePlan.positionSizeUsd,
      stopLossPrice: tradePlan.stopLossPrice,
      takeProfitPrice: tradePlan.takeProfitPrice,
    });

    return {
      status: "executed",
      reason: `Order executed with RR ${tradePlan.riskRewardRatio.toFixed(2)}`,
      orderId: order.orderId,
    };
  }

  private async analyzeWithGrok(tweet: InfluencerTweet): Promise<GrokSignalResult> {
    const prompt = [
      "You evaluate crypto tweet signals for short-term momentum trading.",
      "Return strict JSON with keys: confidence (0 to 1), summary.",
      `tweet: ${tweet.text}`,
      `followerCount: ${tweet.followerCount}`,
      `username: ${tweet.username}`,
    ].join("\n");

    const response = await axios.post(
      "https://api.x.ai/v1/chat/completions",
      {
        model: "grok-3-mini",
        messages: [{ role: "user", content: prompt }],
        temperature: 0.2,
      },
      {
        headers: {
          Authorization: `Bearer ${this.config.grokApiKey}`,
          "Content-Type": "application/json",
        },
      },
    );

    const content = response.data?.choices?.[0]?.message?.content;
    if (typeof content !== "string") {
      return { confidence: 0, summary: "No model output" };
    }

    try {
      const parsed = JSON.parse(content) as GrokSignalResult;
      return {
        confidence: Number(parsed.confidence ?? 0),
        summary: String(parsed.summary ?? ""),
      };
    } catch {
      return { confidence: 0, summary: "Invalid JSON response from Grok" };
    }
  }
}
