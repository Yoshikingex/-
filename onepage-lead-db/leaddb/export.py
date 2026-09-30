"""P8: CSV出力・集計・静的ダッシュボード。"""
import csv
import html
import json
from collections import Counter

from . import config
from . import normalize as N

COLUMNS = ["lead_id", "business_name", "company_name", "industry", "sub_industry", "postal_code", "prefecture",
           "city", "address", "phone", "phone_found", "email", "email_found", "website_url", "website_found",
           "website_status", "website_quality_score", "mobile_friendly", "https_enabled", "contact_form_found",
           "reservation_found", "line_found", "instagram_link_found", "facebook_link_found", "instagram_url",
           "instagram_username", "instagram_found", "instagram_confidence", "instagram_source",
           "instagram_last_checked_at", "facebook_url", "line_url", "google_maps_url", "review_count", "rating",
           "web_need_score", "web_need_level", "reason_1", "reason_2", "reason_3", "lead_priority",
           "data_confidence", "data_source", "source_url_1", "source_url_2", "source_url_3", "last_checked_at",
           "website_evidence", "staff_count", "recommended_dm_angle", "recommended_sample"]
DM_COLUMNS = ["business_name", "industry", "prefecture", "city", "phone", "email", "website_url", "instagram_url",
              "instagram_username", "web_need_score", "web_need_level", "website_status", "recommended_dm_angle",
              "recommended_sample"]
CALL_COLUMNS = ["business_name", "industry", "sub_industry", "prefecture", "city", "address", "phone", "staff_count",
                "website_status", "recommended_dm_angle", "recommended_sample", "data_source", "source_url_1"]
PHONE_SOURCE_RANK = {"S4": 0, "S1": 0, "S2": 1, "S3": 2, "S8": 3}
CONF_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
TF = {True: "TRUE", False: "FALSE"}


def _flag(v):
    return "" if v is None else TF[bool(v)]


def build_rows(con):
    rows = []
    for b in con.execute("SELECT * FROM businesses WHERE merged_into IS NULL ORDER BY lead_id").fetchall():
        lid = b["lead_id"]
        phones = sorted(con.execute("SELECT * FROM contacts WHERE lead_id=? AND kind='phone'", (lid,)).fetchall(),
                        key=lambda c: PHONE_SOURCE_RANK.get(c["source_code"], 9))
        w = con.execute("SELECT * FROM websites WHERE lead_id=?", (lid,)).fetchone()
        dom = w["domain"] if w else None
        emails = sorted((c["value"] for c in con.execute(
            "SELECT value FROM contacts WHERE lead_id=? AND kind='email' AND email_personal_suspect=0", (lid,))),
            key=lambda e: N.email_rank(e, dom))
        socials = con.execute("SELECT * FROM social_accounts WHERE lead_id=?", (lid,)).fetchall()
        igs = sorted((s for s in socials if s["platform"] == "instagram"), key=lambda s: CONF_RANK.get(s["confidence"], 9))
        ig = igs[0] if igs else None
        ig_ok = bool(ig) and ig["confidence"] in ("HIGH", "MEDIUM")
        fb = next((s["url"] for s in socials if s["platform"] == "facebook"), None)
        ln = next((s["url"] for s in socials if s["platform"] == "line"), None)
        sc = con.execute("SELECT * FROM scores WHERE lead_id=?", (lid,)).fetchone()
        srcs = con.execute("SELECT source_code, source_url FROM sources WHERE lead_id=? ORDER BY id", (lid,)).fetchall()
        status = w["status"] if w else "UNKNOWN"
        website_found = {"NONE": False, "UNKNOWN": None}.get(status, True)
        rows.append({
            "lead_id": lid, "business_name": b["business_name"], "company_name": b["company_name"],
            "industry": b["industry"], "sub_industry": b["sub_industry"], "postal_code": b["postal_code"],
            "prefecture": b["prefecture"], "city": b["city"], "address": b["address"],
            "phone": phones[0]["display"] if phones else None, "phone_found": TF[bool(phones)],
            "email": emails[0] if emails else None, "email_found": TF[bool(emails)],
            "website_url": (w["final_url"] or w["url"]) if w else None, "website_found": _flag(website_found),
            "website_status": status, "website_quality_score": w["quality_score"] if w else None,
            "mobile_friendly": _flag(w["mobile_friendly"]) if w else "", "https_enabled": _flag(w["https_enabled"]) if w else "",
            "contact_form_found": _flag(w["contact_form_found"]) if w else "",
            "reservation_found": _flag(w["reservation_found"]) if w else "",
            "line_found": _flag(w["line_found"]) if w else "", "instagram_link_found": _flag(w["instagram_link_found"]) if w else "",
            "facebook_link_found": _flag(w["facebook_link_found"]) if w else "",
            "instagram_url": ig["url"] if ig else None, "instagram_username": ig["username"] if ig else None,
            "instagram_found": TF[ig_ok], "instagram_confidence": ig["confidence"] if ig else None,
            "instagram_source": ig["source"] if ig else None, "instagram_last_checked_at": ig["last_checked_at"] if ig else None,
            "facebook_url": fb, "line_url": ln, "google_maps_url": None, "review_count": None, "rating": None,
            "web_need_score": sc["web_need_score"] if sc else None, "web_need_level": sc["web_need_level"] if sc else None,
            "reason_1": sc["reason_1"] if sc else None, "reason_2": sc["reason_2"] if sc else None,
            "reason_3": sc["reason_3"] if sc else None, "lead_priority": sc["lead_priority"] if sc else None,
            "data_confidence": b["data_confidence"],
            "data_source": ",".join(dict.fromkeys(s["source_code"] for s in srcs)),
            "source_url_1": srcs[0]["source_url"] if len(srcs) > 0 else None,
            "source_url_2": srcs[1]["source_url"] if len(srcs) > 1 else None,
            "source_url_3": srcs[2]["source_url"] if len(srcs) > 2 else None,
            "last_checked_at": (w["fetched_at"] if w else None) or b["updated_at"],
            "website_evidence": w["evidence"] if w else None, "staff_count": b["staff_count"],
            "recommended_dm_angle": sc["recommended_dm_angle"] if sc else None,
            "recommended_sample": sc["recommended_sample"] if sc else None,
        })
    return rows


def _write(path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})
    return len(rows)


def dm_sort_key(r):
    order = {"NONE": 0, "OLD": 1, "BASIC": 2}
    return (order.get(r["website_status"], 3), -(r["web_need_score"] or 0), r["lead_id"])


def export_all(con):
    rows = build_rows(con)
    out = config.OUT
    leads = [r for r in rows if r["phone_found"] == "TRUE"]
    counts = {
        "all_leads.csv": _write(out / "all_leads.csv", leads, COLUMNS),
        "high_priority.csv": _write(out / "high_priority.csv", [r for r in leads if (r["web_need_score"] or 0) >= 70], COLUMNS),
        "medium_priority.csv": _write(out / "medium_priority.csv",
                                      [r for r in leads if 50 <= (r["web_need_score"] or 0) < 70], COLUMNS),
        "with_instagram.csv": _write(out / "with_instagram.csv", [r for r in leads if r["instagram_found"] == "TRUE"], COLUMNS),
        "without_instagram.csv": _write(out / "without_instagram.csv",
                                        [r for r in leads if r["instagram_found"] != "TRUE"], COLUMNS),
        "with_email.csv": _write(out / "with_email.csv", [r for r in leads if r["email_found"] == "TRUE"], COLUMNS),
        "without_email.csv": _write(out / "without_email.csv", [r for r in leads if r["email_found"] != "TRUE"], COLUMNS),
        "missing_phone.csv": _write(out / "missing_phone.csv", [r for r in rows if r["phone_found"] != "TRUE"], COLUMNS),
    }
    dm = sorted((r for r in leads if r["instagram_found"] == "TRUE" and r["instagram_confidence"] != "LOW"
                 and (r["web_need_score"] or 0) >= 50), key=dm_sort_key)
    counts["instagram_dm_targets.csv"] = _write(out / "instagram_dm_targets.csv", dm, DM_COLUMNS)
    # Q1裁定: HP状態が確認できない宅建業者は、スコアとは別枠の電話営業リストにする（小規模順）
    calls = sorted((r for r in leads if r["industry"] == "real_estate" and r["website_status"] == "UNKNOWN"),
                   key=lambda r: (r["staff_count"] if r["staff_count"] is not None else 10 ** 6, r["lead_id"]))
    counts["phone_call_targets.csv"] = _write(out / "phone_call_targets.csv", calls, CALL_COLUMNS)
    for ind in sorted({r["industry"] for r in leads}):
        counts[f"by_industry/{ind}.csv"] = _write(out / "by_industry" / f"{ind}.csv",
                                                  [r for r in leads if r["industry"] == ind], COLUMNS)
    return rows, counts


def stats(con, rows=None):
    rows = rows if rows is not None else build_rows(con)
    leads = [r for r in rows if r["phone_found"] == "TRUE"]
    n = len(leads)

    def pct(k):
        return round(100.0 * k / n, 1) if n else 0.0
    ig = sum(r["instagram_found"] == "TRUE" for r in leads)
    em = sum(r["email_found"] == "TRUE" for r in leads)
    nohp = sum(r["website_status"] == "NONE" for r in leads)
    hp = sum(r["website_found"] == "TRUE" for r in leads)
    unknown = sum(r["website_found"] == "" for r in leads)
    lv = Counter(r["web_need_level"] for r in leads)
    jobs = {f"{k}:{s}": c for k, s, c in con.execute(
        "SELECT kind, status, COUNT(*) FROM crawl_jobs GROUP BY kind, status").fetchall()}
    cur = con.execute("SELECT kind, key FROM crawl_jobs WHERE status='RUNNING' ORDER BY updated_at DESC LIMIT 1").fetchone()
    scores = [r["web_need_score"] for r in leads if r["web_need_score"] is not None]
    return {
        "candidates_total": len(rows),
        "merged_duplicates": con.execute("SELECT COUNT(*) FROM businesses WHERE merged_into IS NOT NULL").fetchone()[0],
        "leads_with_phone": n, "missing_phone": len(rows) - n,
        "email_found": em, "email_rate_pct": pct(em),
        "instagram_found": ig, "instagram_rate_pct": pct(ig),
        "website_found": hp, "website_none": nohp, "website_unknown": unknown, "website_none_rate_pct": pct(nohp),
        "HIGH": lv.get("HIGH", 0), "MEDIUM": lv.get("MEDIUM", 0), "LOW": lv.get("LOW", 0),
        "avg_web_need_score": round(sum(scores) / len(scores), 1) if scores else None,
        "by_industry": dict(Counter(r["industry"] for r in leads).most_common()),
        "by_prefecture": {p: c for p in config.PREF_ORDER
                          for c in [sum(r["prefecture"] == p for r in leads)] if c},
        "by_website_status": dict(Counter(r["website_status"] for r in leads).most_common()),
        "by_priority": dict(sorted(Counter(r["lead_priority"] for r in leads).items())),
        "phone_call_targets": sum(r["industry"] == "real_estate" and r["website_status"] == "UNKNOWN" for r in leads),
        "jobs": jobs, "current_job": f"{cur['kind']}:{cur['key']}" if cur else None,
    }


def dashboard(st, path=None):
    """外部CDNなしの静的HTML。数値は表としても読める（棒はすべて単一色＝量の比較だけ）。"""
    path = path or (config.OUT / "dashboard.html")
    e = html.escape

    def tile(label, value, sub=""):
        return f'<div class="tile"><div class="lab">{e(label)}</div><div class="val">{e(str(value))}</div><div class="sub">{e(sub)}</div></div>'

    def bars(title, d):
        if not d:
            return ""
        mx = max(d.values()) or 1
        rows = "".join(f'<tr><th scope="row">{e(str(k))}</th><td class="barcell"><div class="bar" style="width:{100 * v / mx:.1f}%" '
                       f'title="{e(str(k))}: {v}件"></div></td><td class="num">{v}</td></tr>' for k, v in d.items())
        return f'<section><h2>{e(title)}</h2><table class="bars">{rows}</table></section>'
    n = st["leads_with_phone"]
    body = "".join([
        '<div class="tiles">',
        tile("総リード数（電話あり）", n, f"候補 {st['candidates_total']} / 重複統合 {st['merged_duplicates']}"),
        tile("電話取得率", f"{round(100 * n / st['candidates_total'], 1) if st['candidates_total'] else 0}%", f"電話なし {st['missing_phone']}"),
        tile("メール取得率", f"{st['email_rate_pct']}%", f"{st['email_found']}件"),
        tile("Instagram取得率", f"{st['instagram_rate_pct']}%", f"{st['instagram_found']}件"),
        tile("HPなし率", f"{st['website_none_rate_pct']}%", f"HPなし {st['website_none']} / 不明 {st['website_unknown']}"),
        tile("Web Need 平均", st["avg_web_need_score"] if st["avg_web_need_score"] is not None else "-", "0〜100"),
        '</div>',
        bars("Web Need レベル", {"HIGH": st["HIGH"], "MEDIUM": st["MEDIUM"], "LOW": st["LOW"]}),
        bars("業種別件数", st["by_industry"]),
        bars("都道府県別件数", st["by_prefecture"]),
        bars("サイト状態", st["by_website_status"]),
        bars("Instagram", {"あり": st["instagram_found"], "なし": n - st["instagram_found"]}),
        bars("メール", {"あり": st["email_found"], "なし": n - st["email_found"]}),
        bars("検索進捗（ジョブ）", st["jobs"]),
        f'<p class="sub">処理中ジョブ: {e(str(st["current_job"] or "なし"))}</p>',
        f'<details><summary>生データ（JSON）</summary><pre>{e(json.dumps(st, ensure_ascii=False, indent=1))}</pre></details>',
    ])
    page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lead Dashboard</title><style>
:root{{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3de;--bar:#2a78d6;}}
@media (prefers-color-scheme: dark){{:root{{--bg:#1a1a19;--ink:#ffffff;--ink2:#c3c2b7;--line:#383835;--bar:#3987e5;}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,sans-serif}}
h1{{font-size:20px;margin:0 0 12px}} h2{{font-size:15px;margin:20px 0 6px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}}
.tile{{border:1px solid var(--line);border-radius:8px;padding:10px}} .lab,.sub{{color:var(--ink2);font-size:12px}}
.val{{font-size:24px;font-weight:600}} table.bars{{width:100%;border-collapse:collapse;max-width:720px}}
.bars th{{text-align:left;font-weight:400;color:var(--ink2);padding:3px 8px 3px 0;white-space:nowrap;width:1%}}
.barcell{{width:100%;padding:3px 0}} .bar{{height:12px;background:var(--bar);border-radius:0 4px 4px 0;min-width:2px}}
.num{{text-align:right;padding-left:8px;font-variant-numeric:tabular-nums}} pre{{overflow:auto;font-size:12px}}
</style></head><body><h1>営業リード ダッシュボード</h1>{body}</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path
