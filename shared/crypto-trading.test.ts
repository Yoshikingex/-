import { describe, expect, it } from "vitest";
import {
  buildTradePlan,
  extractEvmContractAddress,
  shouldExecuteTrade,
  updateTrailingStop,
} from "./crypto-trading";

describe("crypto-trading", () => {
  it("extracts EVM contract address from tweet text", () => {
    const text = "CA: 0x1234567890abcdef1234567890ABCDEF12345678 now";
    expect(extractEvmContractAddress(text)).toBe("0x1234567890abcdef1234567890ABCDEF12345678");
  });

  it("builds plan with positive risk reward", () => {
    const plan = buildTradePlan({
      contractAddress: "0x1234567890abcdef1234567890ABCDEF12345678",
      entryPrice: 1,
      walletUsdBalance: 1000,
      config: {
        maxRiskPercent: 2,
        stopLossPercent: 10,
        targetProfitPercent: 300,
        trailingStopPercent: 12,
      },
    });

    expect(plan.positionSizeUsd).toBe(20);
    expect(plan.riskRewardRatio).toBeGreaterThan(1);
  });

  it("uses trailing stop based on highest price", () => {
    expect(updateTrailingStop({ highestPrice: 100, trailingStopPercent: 10 })).toBe(90);
  });

  it("does not execute in dry run", () => {
    const result = shouldExecuteTrade({
      dryRun: true,
      tweet: {
        id: "1",
        username: "alpha",
        postedAt: new Date().toISOString(),
        followerCount: 50000,
        text: "0x1234567890abcdef1234567890ABCDEF12345678",
      },
    });

    expect(result.shouldExecute).toBe(false);
    expect(result.reason).toContain("Dry-run");
  });
});
