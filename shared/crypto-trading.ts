export interface InfluencerTweet {
  id: string;
  username: string;
  text: string;
  followerCount: number;
  postedAt: string;
}

export interface RiskConfig {
  maxRiskPercent: number;
  stopLossPercent: number;
  targetProfitPercent: number;
  trailingStopPercent: number;
}

export interface TradePlan {
  contractAddress: string;
  entryPrice: number;
  positionSizeUsd: number;
  stopLossPrice: number;
  takeProfitPrice: number;
  trailingStopPercent: number;
  riskRewardRatio: number;
}

export function extractEvmContractAddress(text: string): string | null {
  const match = text.match(/0x[a-fA-F0-9]{40}/);
  return match?.[0] ?? null;
}

export function isQualifiedInfluencer(tweet: InfluencerTweet, minFollowers = 30_000): boolean {
  return tweet.followerCount >= minFollowers;
}

/**
 * ROI 300% target = 価格が4倍（+300%）
 */
export function buildTradePlan(params: {
  contractAddress: string;
  entryPrice: number;
  walletUsdBalance: number;
  config: RiskConfig;
}): TradePlan {
  const { contractAddress, entryPrice, walletUsdBalance, config } = params;

  if (entryPrice <= 0) {
    throw new Error("entryPrice must be greater than 0");
  }

  const positionSizeUsd = walletUsdBalance * (config.maxRiskPercent / 100);
  const stopLossPrice = entryPrice * (1 - config.stopLossPercent / 100);
  const takeProfitPrice = entryPrice * (1 + config.targetProfitPercent / 100);

  const riskPerUnit = entryPrice - stopLossPrice;
  const rewardPerUnit = takeProfitPrice - entryPrice;
  const riskRewardRatio = rewardPerUnit / riskPerUnit;

  return {
    contractAddress,
    entryPrice,
    positionSizeUsd,
    stopLossPrice,
    takeProfitPrice,
    trailingStopPercent: config.trailingStopPercent,
    riskRewardRatio,
  };
}

export function updateTrailingStop(params: {
  highestPrice: number;
  trailingStopPercent: number;
}): number {
  const { highestPrice, trailingStopPercent } = params;
  if (highestPrice <= 0) {
    throw new Error("highestPrice must be greater than 0");
  }

  return highestPrice * (1 - trailingStopPercent / 100);
}

export function shouldExecuteTrade(params: {
  tweet: InfluencerTweet;
  minFollowers?: number;
  dryRun?: boolean;
}): { shouldExecute: boolean; reason: string; contractAddress: string | null } {
  const { tweet, minFollowers = 30_000, dryRun = true } = params;

  if (!isQualifiedInfluencer(tweet, minFollowers)) {
    return {
      shouldExecute: false,
      reason: `Follower count is below ${minFollowers}`,
      contractAddress: null,
    };
  }

  const contractAddress = extractEvmContractAddress(tweet.text);
  if (!contractAddress) {
    return {
      shouldExecute: false,
      reason: "No contract address found in tweet",
      contractAddress: null,
    };
  }

  if (dryRun) {
    return {
      shouldExecute: false,
      reason: "Dry-run mode enabled",
      contractAddress,
    };
  }

  return {
    shouldExecute: true,
    reason: "Signal matched",
    contractAddress,
  };
}
