"""Instagram 目視確認（人がブラウザで見て記入した結果）の取り込みと反映。

  1. data/output/instagram_review.csv を Excel 等で開き、確認列に Y/N を記入する
  2. 別名で保存（例: data/input/instagram_review_filled.csv）。出力側は再生成で上書きされるため
  3. python -m leaddb import-review --file data/input/instagram_review_filled.csv
  4. python -m leaddb finalize  → DM対象・優先度に反映

反映ルール:
  CONFIRMED : DM可=Y かつ（事業用=Y または 経営者本人=Y）→ DM対象の最優先
  REJECTED  : DM可=N、または 事業用=N かつ 経営者本人≠Y → DM対象から外す
  それ以外（空欄が多い等）は自動判定（HIGH/MEDIUM/LOW）のまま
"""
import csv
import re

from .db import now

COLS = {
    "is_business": "確認_事業用アカウント(Y/N)",
    "is_owner": "確認_経営者本人(Y/N)",
    "has_products": "確認_商品サービス投稿(Y/N)",
    "last_post_ym": "確認_最終投稿年月",
    "dm_ok": "確認_DM可(Y/N)",
    "memo": "メモ",
}
YES = {"y", "yes", "はい", "○", "〇", "1", "true", "t", "ｙ"}
NO = {"n", "no", "いいえ", "×", "✕", "0", "false", "f", "ｎ"}


def yn(v):
    s = (v or "").strip().lower()
    if s in YES:
        return "Y"
    if s in NO:
        return "N"
    return None


def verdict(r) -> str:
    if r["dm_ok"] == "N" or (r["is_business"] == "N" and r["is_owner"] != "Y"):
        return "REJECTED"
    if r["dm_ok"] == "Y" and (r["is_business"] == "Y" or r["is_owner"] == "Y"):
        return "CONFIRMED"
    return None


def _read(path):
    for enc in ("utf-8-sig", "cp932"):  # Windows の Excel 保存は cp932 になることが多い
        try:
            with open(path, encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"文字コードを判定できません: {path}")


def import_file(con, path) -> dict:
    stats = {"rows": 0, "imported": 0, "skipped_blank": 0, "unknown_lead": 0}
    for row in _read(path):
        stats["rows"] += 1
        lead, user = (row.get("lead_id") or "").strip(), (row.get("instagram_username") or "").strip().lower()
        if not lead or not user:
            stats["unknown_lead"] += 1
            continue
        if not con.execute("SELECT 1 FROM businesses WHERE lead_id=?", (lead,)).fetchone():
            stats["unknown_lead"] += 1
            continue
        vals = {k: yn(row.get(c)) for k, c in COLS.items() if k not in ("last_post_ym", "memo")}
        ym = (row.get(COLS["last_post_ym"]) or "").strip()
        m = re.match(r"^(\d{4})[/\-.年]?(\d{1,2})", ym)
        vals["last_post_ym"] = f"{m.group(1)}-{int(m.group(2)):02d}" if m else (ym or None)
        vals["memo"] = (row.get(COLS["memo"]) or "").strip() or None
        if not any(vals.values()):
            stats["skipped_blank"] += 1
            continue
        con.execute("INSERT OR REPLACE INTO ig_reviews (lead_id, username, is_business, is_owner, has_products, "
                    "last_post_ym, dm_ok, memo, imported_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (lead, user, vals["is_business"], vals["is_owner"], vals["has_products"], vals["last_post_ym"],
                     vals["dm_ok"], vals["memo"], now()))
        stats["imported"] += 1
    con.commit()
    return stats


def apply(con) -> dict:
    """ig_reviews を social_accounts.confidence に反映（自動判定の後に実行する）。"""
    out = {"CONFIRMED": 0, "REJECTED": 0}
    for r in con.execute("SELECT * FROM ig_reviews").fetchall():
        v = verdict(r)
        if v:
            n = con.execute("UPDATE social_accounts SET confidence=? WHERE lead_id=? AND platform='instagram' "
                            "AND username=?", (v, r["lead_id"], r["username"])).rowcount
            out[v] += bool(n)
    con.commit()
    return out


def lookup(con):
    return {(r["lead_id"], r["username"]): r for r in con.execute("SELECT * FROM ig_reviews")}
