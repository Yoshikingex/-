# ナレーション音声（ソアちゃん）

- エンジン：ElevenLabs（Higgsfield の text2speech_v2 経由）／声：Luna（voice_id 375a3398-e3b4-4f91-845d-42181e352899）
- 加工：1.08倍速（ffmpeg atempo・声の高さは変えない）→ 前後の無音カット → ピーク -1.5dB に正規化
- 選定理由：難しい12セリフのWhisper一致率: Luna×1.08=89.3% / Luna=88.7% / Chloe=85.6% / Kokoro=84.8%
- 使用クレジット：約10.8（試し録り・作り直し込み）
- ファイル：S01〜S31（本編）、V01〜V09（ショート）。書き出しは `work/voice_elevenlabs/` に展開して `render_video.py --voice elevenlabs`
