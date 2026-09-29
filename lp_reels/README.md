# LP ビフォーアフター縦型リール（1素材＝1本）

| ファイル | テーマ | 曲（Mixkit） | 雰囲気 |
|---|---|---|---|
| `output/01_car.mp4` | 高級車ブランド VELARIN | Autofahren（Deep House） | 黒×シャンパンゴールド / Cinzel＋しっぽり明朝 |
| `output/02_kebab.mp4` | ケバブ専門店 | Gimme that Groove!（Funk） | 炭黒×オレンジ / Playfair Display＋Zen角ゴシック |
| `output/03_salon.mp4` | ヘアサロン SHIZUKU | Hazy After Hours（Electronica） | アイボリー×ローズゴールド / Cormorant＋しっぽり明朝 |
| `output/04_ryokan.mp4` | 高級旅館 朧 | Relax（Ambient）＋琴・鈴を自作合成 | 墨×金 / Zen Old Mincho＋しっぽり明朝 |
| `output/05_gym.mp4` | パーソナルジム BEYOND | Trap Electro Vibes | 黒×イエロー / Bebas Neue＋Zen角ゴシック |

仕様: 1080x1920 / 30fps / H.264 + AAC 192kbps / 約26秒 / 音量 -14 LUFS（Instagram・TikTok 推奨付近）

## 構成（全5本共通）
| 秒 | 内容 |
|---|---|
| 0–2 | BEFOREだけ再生、AFTER枠に問いかけテロップ。曲はこもった音（ローパス） |
| 2 | 曲のドロップと同時にAFTER登場（フラッシュ＋光のスイープ＋効果音） |
| 2–約19 | 上AFTER／下BEFOREを同期再生。下段に見どころ解説を4回切り替え |
| 約19–23 | AFTERを単独で大きく（ページのクライマックス）＋コピー |
| 最後3秒 | エンドカード（相談導線＋保存促し） |

## 画質処理
- 斜めに撮影された画面を台形補正（`edges.json` に画面の上下辺の直線を保存）
- 色補正（`levels.json` の実測値で黒レベル・白レベル・色かぶりを補正、AFTERは中間調を締めてコントラスト強め）
- シャープ処理＋角丸カード＋影＋フィルムグレイン

## 再生成
```
pip install numpy scipy pillow librosa imageio-ffmpeg   # ffmpeg は libass 入りが必要
python3 build.py <素材mp4フォルダ> [car kebab salon ryokan gym]
```
テロップ・色・曲・切替秒数は `themes.py` で変更する。曲と効果音は初回実行時に Mixkit から `_cache/` へ自動ダウンロード（リポジトリには含めない）。

## 素材ライセンス
- 曲・効果音: Mixkit（Stock Music Free License / Sound Effects Free License）。利用前に https://mixkit.co/license/ で最新条件を確認すること
- 旅館の琴・鈴: `build.py` 内で合成（第三者素材なし）
- フォント: すべて SIL Open Font License 1.1（Google Fonts 由来、npm `@expo-google-fonts/*` から取得）
