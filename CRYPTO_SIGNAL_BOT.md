# Crypto Signal Bot（Grok + X投稿監視 + 自動売買）

この実装は以下を満たすための**実運用向けベース**です。

- Grok APIで投稿内容を評価
- フォロワー3万人以上の投稿者のみ監視対象
- 投稿内のコントラクトアドレス検出
- 検出直後に自動でエントリー（`dryRun=false`時）
- 目標利益率300%（+300%）
- トレーリングストップ対応
- リスクリワードがプラス（>1）でない場合は発注しない

## 実装ファイル

- `shared/crypto-trading.ts`
  - コントラクトアドレス抽出
  - インフルエンサー判定
  - 利確/損切り/リスクリワード計算
  - トレーリングストップ価格計算
- `server/crypto-signal-bot.ts`
  - Grok API呼び出し
  - シグナル判定
  - リスクリワードチェック
  - 売買実行インターフェース
- `scripts/crypto-signal-bot-example.ts`
  - 動作サンプル（ペーパートレード）

## 必須環境変数

```bash
export GROK_API_KEY="your_xai_key"
export DRY_RUN="true" # false で実売買
```

## 実行例

```bash
pnpm tsx scripts/crypto-signal-bot-example.ts
```

## 注意点

- 300%固定目標は高リスクです。相場状況に応じて `targetProfitPercent` を調整してください。
- 実運用では `TradeExecutor` を DEX / ブローカー API 実装に差し替えてください。
- X（Twitter）監視はWebhookまたは定期ポーリングで `processTweetSignal` に渡す構成を推奨します。
