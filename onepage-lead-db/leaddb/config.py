"""パス・通信設定・対象地域などの定数。"""
import logging
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"
OUT = DATA / "output"
LOGS = ROOT / "logs"
DB_PATH = Path(os.environ.get("LEADDB_PATH", DATA / "leads.db"))

USER_AGENT = "onepage-lead-db/0.1 (public business info research; low-rate; respects robots.txt)"
PER_HOST_INTERVAL = float(os.environ.get("LEADDB_INTERVAL", "3.0"))  # G6: 同一ホスト最短3秒
TIMEOUT = 20
MAX_RETRIES = 3
BACKOFF = [30, 60, 120]  # G6: 429/503/接続エラー時
MAX_PAGES_PER_SITE = 3

# G2/G3: 自動アクセス禁止ホスト（robots.txt で実測済み）
FORBIDDEN_HOST_SUFFIXES = ("instagram.com",)
FORBIDDEN_URL_PREFIXES = ("https://www.google.com/search", "https://google.com/search",
                          "http://www.google.com/search", "https://www.google.co.jp/search")

# 都道府県コード → 名称（優先順）
KANTO = {"13": "東京都", "11": "埼玉県", "14": "神奈川県", "12": "千葉県",
         "08": "茨城県", "09": "栃木県", "10": "群馬県"}
PREF_ORDER = list(KANTO.values())

VISUAL_INDUSTRIES = {"construction", "real_estate", "beauty", "restaurant", "lodging", "gym"}


def setup_logging() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger()
    if getattr(root, "_leaddb_ready", False):
        return
    root.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.setLevel(logging.WARNING)
    root.addHandler(sh)
    for name, level, logger_name in (("crawl.log", logging.INFO, "leaddb"),
                                     ("error.log", logging.WARNING, ""),
                                     ("score.log", logging.INFO, "leaddb.score")):
        h = logging.FileHandler(LOGS / name, encoding="utf-8")
        h.setFormatter(fmt)
        h.setLevel(level)
        logging.getLogger(logger_name).addHandler(h)
    logging.getLogger("leaddb.score").propagate = False
    root._leaddb_ready = True
