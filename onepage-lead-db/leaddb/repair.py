"""旧方式の統合（子の行を本体へ移していた）を取り消す一回限りの修復。DELETE は使わない。

1,000件テストで Instagram 一致による誤統合（チェーン支店）が 11/11 件あったため作成。
移された行は出典（source_url / CSV の事業所番号）をたどって子へ戻す。
"""
import csv
import logging

from . import config
from . import normalize as N

log = logging.getLogger("leaddb.repair")


def _s1_phones():
    """介護CSVの 事業所番号 → 電話番号(digits)。"""
    out = {}
    for path in sorted(config.RAW.glob("jigyosho_*_all_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                d = N.phone_digits(r.get("電話番号"))
                if d:
                    out[f"S1:{r.get('事業所番号')}"] = d
    return out


def _move_by_url(con, table, url_col, root, child, url, root_url):
    if not url:
        return 0
    if url != root_url:  # 子のサイト由来の行 → 子へ戻す
        return con.execute(f"UPDATE OR IGNORE {table} SET lead_id=? WHERE lead_id=? AND {url_col}=?",
                           (child, root, url)).rowcount
    # 本体と同じページ由来（同一サイト）→ 子にも同じ行を複製する
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})") if r[1] not in ("id", "lead_id")]
    return con.execute(f"INSERT OR IGNORE INTO {table} (lead_id, {', '.join(cols)}) "
                       f"SELECT ?, {', '.join(cols)} FROM {table} WHERE lead_id=? AND {url_col}=?",
                       (child, root, url)).rowcount


def unmerge_all(con) -> dict:
    phones = _s1_phones()
    stats = {"unmerged": 0, "rows_restored": 0}
    children = con.execute("SELECT b.lead_id, b.merged_into, b.source_key, b.seed_website_url FROM businesses b "
                           "WHERE b.merged_into IS NOT NULL").fetchall()
    for c in children:
        child, root = c["lead_id"], c["merged_into"]
        rk = con.execute("SELECT source_key FROM businesses WHERE lead_id=?", (root,)).fetchone()["source_key"]
        cw = con.execute("SELECT final_url FROM websites WHERE lead_id=?", (child,)).fetchone()
        rw = con.execute("SELECT final_url FROM websites WHERE lead_id=?", (root,)).fetchone()
        cu, ru = (cw["final_url"] if cw else None), (rw["final_url"] if rw else None)
        n = _move_by_url(con, "contacts", "source_url", root, child, cu, ru)
        n += _move_by_url(con, "social_accounts", "source_url", root, child, cu, ru)
        if c["seed_website_url"]:  # 公開データURL欄がInstagramだった場合の行
            n += _move_by_url(con, "social_accounts", "source_url", root, child, c["seed_website_url"], None)
        # 公的名簿の電話（S1）
        vc, vr = phones.get(c["source_key"]), phones.get(rk)
        if vc:
            if vc != vr:
                n += con.execute("UPDATE OR IGNORE contacts SET lead_id=? WHERE lead_id=? AND kind='phone' "
                                 "AND source_code='S1' AND value=?", (child, root, vc)).rowcount
            d, disp = vc, N.format_phone(vc)[1]
            n += con.execute("INSERT OR IGNORE INTO contacts (lead_id, kind, value, display, phone_type, source_code) "
                             "VALUES (?, 'phone', ?, ?, ?, 'S1')", (child, d, disp, N.phone_type(d))).rowcount
        # 出典（取得元コードは source_key の先頭）
        fam = c["source_key"].split(":")[0]
        if fam != rk.split(":")[0]:
            n += con.execute("UPDATE OR IGNORE sources SET lead_id=? WHERE lead_id=? AND source_code=?",
                             (child, root, fam)).rowcount
        n += con.execute("INSERT OR IGNORE INTO sources (lead_id, source_code, source_url, fetched_at) "
                         "SELECT ?, source_code, source_url, fetched_at FROM sources WHERE lead_id=? AND source_code=?",
                         (child, root, fam)).rowcount
        con.execute("UPDATE businesses SET merged_into=NULL, data_confidence=NULL WHERE lead_id=?", (child,))
        stats["unmerged"] += 1
        stats["rows_restored"] += n
        log.info("unmerge %s from %s restored=%d", child, root, n)
    con.execute("UPDATE businesses SET data_confidence=NULL WHERE merged_into IS NULL")
    con.commit()
    return stats
