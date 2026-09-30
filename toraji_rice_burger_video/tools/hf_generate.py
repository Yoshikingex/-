"""Higgsfield API で全シーンの動画クリップを生成する（クレジット上限つき）。

前提: 環境変数 HF_API_KEY_ID / HF_API_KEY_SECRET（Higgsfield Console で発行。チャットに貼らない）
使い方:
  python tools/hf_generate.py prepare               # 入力画像(16:9)を作る。無料・キー不要
  python tools/hf_generate.py estimate [--budget 200]  # 候補モデルごとに全クリップを見積もり→予算内で最も品質の高いモデルを選ぶ（生成はしない）
  python tools/hf_generate.py run [--budget 200]    # 選んだモデルで生成→ work/clips/<clip>.mp4 に保存
  python tools/hf_generate.py status                # 使ったクレジット（見積もりベース）と進み具合
安全装置:
  - 送信前に毎回見積もりを取り、「使用済み＋この1本」が予算を超えるなら送らずに止める
  - 同じクリップは Idempotency-Key を保存して再送（二重課金しない）。完成済みクリップはスキップ
  - failed / nsfw は課金されない（公式ドキュメント）ので使用額から外す
"""
import hashlib
import json
import os
import random
import sys
import time
import uuid
from pathlib import Path

import requests
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
WORK = ROOT / "work"
INPUTS = WORK / "clip_inputs"
CLIPS = WORK / "clips"
LEDGER = WORK / "hf_ledger.json"
PLAN = WORK / "hf_plan.json"
API = "https://api.higgsfield.ai"

# 候補モデル（上から品質優先【推測】）。body は image_url と prompt 以外の固定パラメータ。
# dur: クリップ秒数を決める関数の範囲（min, max）。enum のモデルは最小値を使う。
CANDIDATES = [
    {"name": "Kling 3.0 Turbo 720p", "path": "kling-video/v3.0-turbo/image-to-video",
     "body": {"resolution": "720p"}, "dur": (3, 5)},
    {"name": "Seedance 2.0 720p", "path": "bytedance/seedance-2.0/image-to-video",
     "body": {"resolution": "720p", "generate_audio": False}, "dur": (4, 5)},
    {"name": "Kling 2.5 Turbo Standard", "path": "kling-video/v2.5-turbo/standard/image-to-video",
     "body": {}, "dur": (5, 5)},
    {"name": "Hailuo 2.3 Standard", "path": "minimax/hailuo-2.3/standard/image-to-video",
     "body": {}, "dur": (6, 6)},
    {"name": "Wan 2.6 720p", "path": "wan/v2.6/image-to-video",
     "body": {"resolution": "720p"}, "dur": (5, 5)},
    {"name": "PixVerse V6 540p", "path": "pixverse/v6/image-to-video",
     "body": {"resolution": "540p", "generate_audio": False}, "dur": (3, 5)},
    {"name": "LTX 2.5 Fast 720p", "path": "lightricks/ltx-2.5/image-to-video/fast",
     "body": {"resolution": "720p", "generate_audio": False, "aspect_ratio": "16:9"}, "dur": (6, 6)},
]
RETRY_RESERVE = 0.15   # 撮り直し用に予算の15%を残してモデルを選ぶ

HOST_PROMPTS = {
    "S03": "The young woman in the red and black TORAJI uniform waves at the camera with her right hand and talks "
           "cheerfully, natural head movement and blinking, warm restaurant background with soft bokeh, static camera. "
           "Keep her face, glasses, braids and outfit identical.",
    "S28": "The young woman smiles excitedly, nods and gives a happy thumbs-up toward the rice burger beside her, "
           "natural blinking, warm restaurant background with bokeh, static camera. Keep her face and outfit identical.",
    "S30": "The young woman talks energetically to the camera and does a small fist pump at the end with a big smile, "
           "natural head movement, warm restaurant background with bokeh, static camera. Keep her face and outfit identical.",
}
NEG = "Realistic physics, natural food texture, no morphing, no extra hands, no text, no subtitles, no watermark."


# ---------------- クリップ一覧 ----------------
def clip_list():
    """scenes.json から生成するクリップを作る。同じ絵を使うシーン(S01/S29)は1本を共有。"""
    cfg = json.loads((ROOT / "tools" / "scenes.json").read_text(encoding="utf-8"))
    tim_path = ROOT / "output" / "timings.json"
    tim = {s["id"]: s["dur"] for s in json.loads(tim_path.read_text(encoding="utf-8"))["scenes"]} if tim_path.exists() else {}
    clips, seen = [], {}
    for sc in cfg["scenes"]:
        key = sc["id"] if sc["kind"] == "host" else sc["img"]
        need = tim.get(sc["id"], 4.0)
        if key in seen:
            seen[key]["scenes"].append(sc["id"])
            seen[key]["need"] = max(seen[key]["need"], need)
            continue
        if sc["kind"] == "host":
            prompt = HOST_PROMPTS[sc["id"]]
        else:
            m = sc["motion"]
            prompt = f"{m[0].upper() + m[1:]}. Scene: {sc['shot']}. {NEG}"
        c = {"clip": key, "scenes": [sc["id"]], "kind": sc["kind"], "prompt": prompt, "need": need}
        seen[key] = c
        clips.append(c)
    return clips


# ---------------- 入力画像（無料・ローカル） ----------------
def cover(im, size):
    r = max(size[0] / im.width, size[1] / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - size[0]) // 2, (im.height - size[1]) // 2
    return im.crop((x, y, x + size[0], y + size[1]))


def host_frame(scene_id, size=(1280, 720)):
    """ソアちゃんの切り抜きを暖色のボケ背景に合成した最初のフレーム（動画化の起点）。"""
    w, h = size
    bg = Image.open(A / "source" / "04_hero_burger.png").convert("RGB")
    bg = ImageEnhance.Brightness(cover(bg, size).filter(ImageFilter.GaussianBlur(28))).enhance(0.55)
    host = Image.open(A / "panels" / "host_cutout.png")
    host = host.crop((0, 0, host.width, int(host.height * 0.62)))   # 頭〜腰
    hh = int(h * 0.98)
    host = host.resize((int(host.width * hh / host.height), hh), Image.LANCZOS)
    canvas = bg.convert("RGBA")
    if scene_id in ("S28", "S30"):
        b = Image.open(A / "source" / "04_hero_burger.png").convert("RGBA").resize((int(h * 0.72),) * 2, Image.LANCZOS)
        m = Image.new("L", b.size, 0)
        from PIL import ImageDraw
        ImageDraw.Draw(m).ellipse((b.width * 0.06, b.height * 0.04, b.width * 0.94, b.height * 0.98), fill=255)
        b.putalpha(m.filter(ImageFilter.GaussianBlur(b.width * 0.05)))
        canvas.alpha_composite(b, (int(w * 0.52), int(h * 0.22)))
        canvas.alpha_composite(host, (int(w * 0.12), h - hh))
    else:
        canvas.alpha_composite(host, ((w - host.width) // 2, h - hh))
    return canvas.convert("RGB")


def prepare():
    INPUTS.mkdir(parents=True, exist_ok=True)
    for c in clip_list():
        dst = INPUTS / f"{c['clip']}.jpg"
        if c["kind"] == "host":
            im = host_frame(c["scenes"][0])
        else:
            im = cover(Image.open(A / "panels_hd" / f"{c['clip']}.png").convert("RGB"), (1280, 720))
        im.save(dst, quality=92)
    n = len(clip_list())
    print(f"prepared {n} input frames -> {INPUTS}")


# ---------------- API ----------------
def headers():
    kid, sec = os.environ.get("HF_API_KEY_ID"), os.environ.get("HF_API_KEY_SECRET")
    if not kid or not sec:
        sys.exit("HF_API_KEY_ID / HF_API_KEY_SECRET が設定されていません（環境の設定で登録→新しいセッションで実行）")
    return {"Authorization": f"Key {kid}:{sec}", "Content-Type": "application/json"}


def call(method, url, **kw):
    for attempt in range(5):
        try:
            r = requests.request(method, url, timeout=60, **kw)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        return r
    raise RuntimeError(f"network failure: {method} {url}")


def duration_for(cand, need):
    lo, hi = cand["dur"]
    return int(min(max(round(need), lo), hi))


def body_for(cand, clip, image_url="https://example.com/input.jpg"):
    b = dict(cand["body"])
    b.update({"prompt": clip["prompt"], "image_url": image_url, "duration": duration_for(cand, clip["need"])})
    return b


def estimate_one(cand, body):
    r = call("POST", f"{API}/estimate/{cand['path']}", headers=headers(), json=body)
    if r.status_code != 200:
        return None, f"{r.status_code} {r.text[:160]}"
    return float(r.json()["credits"]), None


def load(p, default):
    return json.loads(p.read_text()) if p.exists() else default


def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1))


def estimate(budget):
    clips = clip_list()
    rows = []
    for cand in CANDIDATES:
        total, err = 0.0, None
        for c in clips:
            cr, err = estimate_one(cand, body_for(cand, c))
            if cr is None:
                break
            total += cr
        rows.append({"model": cand["name"], "path": cand["path"], "total": None if err else round(total, 2), "error": err})
        print(f"{cand['name']:<28} {'ERROR ' + err if err else f'{total:8.2f} credits / {len(clips)} clips'}")
    usable = budget * (1 - RETRY_RESERVE)
    pick = next((r for r in rows if r["total"] is not None and r["total"] <= usable), None)
    save(PLAN, {"budget": budget, "clips": len(clips), "estimates": rows, "selected": pick})
    if pick:
        print(f"\n選択: {pick['model']}  合計 {pick['total']} クレジット（予算 {budget}、撮り直し用に {budget - pick['total']:.1f} 残す）")
    else:
        print(f"\n予算 {budget}（撮り直し分を除くと {usable:.0f}）に収まるモデルがありません。クリップ数を減らす必要があります。")


def upload(path):
    r = call("POST", f"{API}/files/generate-upload-url", headers=headers(), json={"content_type": "image/jpeg"})
    r.raise_for_status()
    u = r.json()
    put = call("PUT", u["upload_url"], headers=u["upload_headers"], data=path.read_bytes())  # 認証ヘッダは送らない
    put.raise_for_status()
    return u["public_url"]


def spent(ledger):
    return sum(v["credits"] for v in ledger.values() if v.get("status") not in ("failed", "nsfw", "canceled", "rejected"))


def run(budget):
    plan = load(PLAN, None)
    if not plan or not plan.get("selected"):
        sys.exit("先に `estimate` を実行してモデルを選んでください")
    cand = next(c for c in CANDIDATES if c["path"] == plan["selected"]["path"])
    ledger = load(LEDGER, {})
    CLIPS.mkdir(parents=True, exist_ok=True)
    for c in clip_list():
        out = CLIPS / f"{c['clip']}.mp4"
        if out.exists():
            continue
        rec = ledger.get(c["clip"], {})
        if rec.get("status") in ("failed", "nsfw", "canceled") and rec.get("retries", 0) >= 1:
            print(f"{c['clip']}: 2回失敗したのでスキップ（画像ズームで代用される）")
            continue
        if not rec.get("request_id") or rec.get("status") in ("failed", "nsfw", "canceled"):
            if not rec.get("image_url"):
                rec["image_url"] = upload(INPUTS / f"{c['clip']}.jpg")
            body = body_for(cand, c, rec["image_url"])
            cr, err = estimate_one(cand, body)
            if cr is None:
                print(f"{c['clip']}: 見積もり失敗 {err}")
                continue
            if spent(ledger) + cr > budget:
                print(f"予算上限: 使用済み {spent(ledger):.2f} + {cr:.2f} > {budget}。ここで停止します。")
                break
            retries = rec.get("retries", -1) + 1
            key = str(uuid.uuid4()) if rec.get("status") in ("failed", "nsfw", "canceled") or not rec.get("idem") else rec["idem"]
            rec.update({"model": cand["name"], "idem": key, "credits": cr, "status": "submitting", "retries": retries,
                        "body_hash": hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()})
            ledger[c["clip"]] = rec
            save(LEDGER, ledger)
            r = call("POST", f"{API}/{cand['path']}", headers={**headers(), "Idempotency-Key": key}, json=body)
            if r.status_code == 400 and "concurrent" in r.text:
                time.sleep(20)
                r = call("POST", f"{API}/{cand['path']}", headers={**headers(), "Idempotency-Key": key}, json=body)
            if r.status_code not in (200, 201, 202):
                rec["status"] = "rejected"   # 受付前の拒否は課金されない
                save(LEDGER, ledger)
                print(f"{c['clip']}: 送信エラー {r.status_code} {r.text[:200]}")
                continue
            j = r.json()
            rec.update({"request_id": j["request_id"], "status_url": j["status_url"], "status": j["status"]})
            save(LEDGER, ledger)
            print(f"{c['clip']}: 送信 {cr:.2f}cr（累計 {spent(ledger):.2f}/{budget}）")
        # 完了待ち
        delay = 2.0
        t0 = time.time()
        while True:
            s = call("GET", rec["status_url"], headers=headers())
            if s.status_code == 200:
                j = s.json()
                rec["status"] = j["status"]
                if j["status"] == "completed":
                    url = (j.get("video") or {}).get("url") or (j.get("videos") or [{}])[0].get("url")
                    data = call("GET", url).content
                    out.write_bytes(data)
                    print(f"{c['clip']}: 完了 {len(data) // 1024}KB")
                    break
                if j["status"] in ("failed", "nsfw", "canceled"):
                    print(f"{c['clip']}: {j['status']}（課金なし） {str(j.get('error', ''))[:120]}")
                    break
            if time.time() - t0 > 900:
                print(f"{c['clip']}: 15分待っても終わらないので次へ（再実行で続きから確認）")
                break
            time.sleep(delay + random.uniform(0, 0.5))
            delay = min(delay * 1.5, 10.0)
        save(LEDGER, ledger)
    status()


def status():
    ledger = load(LEDGER, {})
    clips = clip_list()
    done = sum((CLIPS / f"{c['clip']}.mp4").exists() for c in clips)
    print(f"完成 {done}/{len(clips)} クリップ ／ 使用クレジット（見積もりベース）{spent(ledger):.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    budget = float(sys.argv[sys.argv.index("--budget") + 1]) if "--budget" in sys.argv else 200.0
    {"prepare": prepare, "estimate": lambda: estimate(budget), "run": lambda: run(budget), "status": status}[cmd]()
