# onepage-lead-db

関東の事業者について、公開情報だけから「HP制作の営業リード」を作るツールです。仕様は `_tasks/spec_v2.json` にあります。

## 守っているルール（抜粋）
- instagram.com と Google 検索には一切アクセスしません（どちらも robots.txt で自動収集が禁止されています）。Instagram は、事業者の公式サイトに貼られたリンクだけを記録します。
- robots.txt を守り、同じサイトへのアクセスは最短3秒間隔・同時1本です。一度取得したページはキャッシュから読み、再取得しません。
- 有料APIは使いません。
- このリポジトリは public です。`data/` と `logs/` はコミットしません（`.gitignore` で除外）。

## 使い方
```
cd /c/dev/onepage-lead-db          # Windows の場合は C:\dev\onepage-lead-db
pip install -r requirements.txt
python -m unittest discover -s tests -t .   # 単体テスト
python -m leaddb stage --n 100              # 段階テスト（取り込み → 巡回 → 統合 → 採点 → 出力）
python -m leaddb crawl                      # 途中で止まった巡回の続きを実行
python -m leaddb finalize                   # 統合・採点・CSV・ダッシュボードを作り直す
python -m leaddb stats                      # 進捗・件数を表示
```
途中で止めても、次に起動したときに実行中（RUNNING）だったジョブを未処理（PENDING）に戻し、続きから再開します。

## 出力
- `data/output/*.csv`（UTF-8 BOM付き。Excel でそのまま開けます）
- `data/output/dashboard.html`
- `data/leads.db`
- `logs/crawl.log`, `logs/error.log`, `logs/score.log`

## 取得元
| コード | 取得元 | ライセンス |
|---|---|---|
| S1 | 介護サービス情報公表システム オープンデータ（厚労省） | 厚労省利用規約 / CC BY 互換。出典の表示が必要 |
| S2 | 医療情報ネット オープンデータ（厚労省） | 二次利用可。出典の表示が必要 |
| S4 | 国交省 建設業者・宅建業者等企業情報検索システム | 国交省サイトは PDL1.0。検索システム独自の利用条件は未確認 |
| S8 | 各事業者の公式サイト（上記で得たURLのみ） | ― |
