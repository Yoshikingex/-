"""P4/P5/P6: 公式サイトの巡回（最大3ページ）と抽出結果の保存。"""
import logging

import requests

from . import config, db
from . import extract as X
from . import normalize as N
from .fetch import GuardViolation

log = logging.getLogger("leaddb.crawl")


def _save_website(con, lead_id, **kw):
    cols = ["url", "final_url", "domain", "status", "quality_score", "https_enabled", "mobile_friendly",
            "contact_form_found", "reservation_found", "line_found", "instagram_link_found",
            "facebook_link_found", "copyright_year", "http_status", "evidence"]
    con.execute(f"INSERT OR REPLACE INTO websites (lead_id, {', '.join(cols)}, fetched_at) "
                f"VALUES (?, {', '.join('?' * len(cols))}, ?)", [lead_id] + [kw.get(c) for c in cols] + [db.now()])


def _add_social(con, lead_id, platform, url, username, confidence, source, source_url):
    con.execute("INSERT OR IGNORE INTO social_accounts (lead_id, platform, url, username, confidence, source, "
                "source_url, last_checked_at) VALUES (?,?,?,?,?,?,?,?)",
                (lead_id, platform, url, username, confidence, source, source_url, db.now()))


def crawl_one(con, fetcher, lead_id, seed_url):
    """1事業者分。サイトが無い/取れない場合も websites に状態を残す。"""
    url = N.clean_url(seed_url)
    dom = N.domain_of(url) if url else None
    if not url:
        _save_website(con, lead_id, status="NONE", evidence="公開データにURL記載なし")
        return "NONE"
    ig = X.instagram_username(url)
    if ig:  # 公開データのURL欄が Instagram（G2: instagram.com にはアクセスしない）
        _add_social(con, lead_id, "instagram", f"https://www.instagram.com/{ig}/", ig, "MEDIUM", "opendata_url", url)
        _save_website(con, lead_id, url=None, status="NONE", evidence="URL欄がInstagramのみ", instagram_link_found=1)
        return "NONE"
    try:
        top = fetcher.get(url)
    except GuardViolation as e:
        _save_website(con, lead_id, url=url, domain=dom, status="UNKNOWN", evidence=f"取得不可: {e}"[:200])
        return "UNKNOWN"
    except requests.RequestException as e:
        _save_website(con, lead_id, url=url, domain=dom, status="UNREACHABLE",
                      evidence=f"接続不可: {type(e).__name__}")
        return "UNREACHABLE"
    if top.status >= 400:
        _save_website(con, lead_id, url=url, domain=dom, status="UNREACHABLE", http_status=top.status,
                      evidence=f"HTTP {top.status}")
        return "UNREACHABLE"
    html = top.text
    pages = [X.parse_page(html, top.final_url)]
    for sub in list(dict.fromkeys(pages[0]["subpages"]))[: config.MAX_PAGES_PER_SITE - 1]:
        try:
            p = fetcher.get(sub)
            if p.status < 400:
                pages.append(X.parse_page(p.text, p.final_url))
        except (GuardViolation, requests.RequestException) as e:
            log.info("subpage skip %s: %s", sub, e)
    q = X.site_quality(html, top.final_url)
    final_dom = N.domain_of(top.final_url)
    src = top.final_url
    # 電話
    d, disp = X.pick_phone(pages)
    if d:
        db.add_contact(con, lead_id, "phone", d, disp, N.phone_type(d), source_code="S8", source_url=src)
    # メール（業務用のみ。個人名らしいものは除外フラグ）
    for raw in dict.fromkeys(e for p in pages for e in p["emails"]):
        e, biz, suspect = N.classify_email(raw)
        if e:
            db.add_contact(con, lead_id, "email", e, e, personal_suspect=suspect or not biz,
                           source_code="S8", source_url=src)
    # SNS
    igs = list(dict.fromkeys(x for p in pages for x in p["instagram"]))
    for u, iurl in igs[:2]:
        _add_social(con, lead_id, "instagram", iurl, u, "HIGH", "official_site", src)
    fbs = list(dict.fromkeys(x for p in pages for x in p["facebook"]))
    if fbs:
        _add_social(con, lead_id, "facebook", fbs[0], None, "HIGH", "official_site", src)
    lines = list(dict.fromkeys(x for p in pages for x in p["line"]))
    if lines:
        _add_social(con, lead_id, "line", lines[0], None, "HIGH", "official_site", src)
    _save_website(con, lead_id, url=url, final_url=top.final_url, domain=final_dom, status=q["status"],
                  quality_score=q["quality_score"], https_enabled=int(q["https"]), mobile_friendly=int(q["viewport"]),
                  contact_form_found=int(any(p["has_form"] for p in pages)),
                  reservation_found=int(any(p["reservation"] for p in pages)),
                  line_found=int(bool(lines)), instagram_link_found=int(bool(igs)),
                  facebook_link_found=int(bool(fbs)), copyright_year=q["copyright_year"],
                  http_status=top.status, evidence=" / ".join(q["evidence"]))
    return q["status"]


def crawl_all(con, fetcher, limit=None):
    """未巡回の事業者を巡回。ジョブ単位で状態を残すので途中停止しても続きから再開できる。"""
    rows = con.execute("SELECT b.lead_id, b.seed_website_url FROM businesses b "
                       "LEFT JOIN crawl_jobs j ON j.kind='site' AND j.key=b.lead_id "
                       "WHERE b.merged_into IS NULL AND b.industry != 'real_estate' "
                       "AND (j.status IS NULL OR j.status IN ('PENDING','RUNNING')) "
                       "ORDER BY b.lead_id").fetchall()
    done = 0
    for r in rows[:limit] if limit else rows:
        db.set_job(con, "site", r["lead_id"], "RUNNING")
        try:
            st = crawl_one(con, fetcher, r["lead_id"], r["seed_website_url"])
            db.set_job(con, "site", r["lead_id"], "COMPLETE", st)
        except Exception as e:  # noqa: BLE001
            log.exception("crawl failed %s", r["lead_id"])
            db.set_job(con, "site", r["lead_id"], "FAILED", str(e)[:200])
        done += 1
    # 宅建業者（S4）はURLを持たないため、サイト状態は UNKNOWN として記録（推測で NONE にしない）
    for r in con.execute("SELECT lead_id FROM businesses WHERE industry='real_estate' AND merged_into IS NULL "
                         "AND lead_id NOT IN (SELECT lead_id FROM websites)").fetchall():
        _save_website(con, r["lead_id"], status="UNKNOWN", evidence="取得元にURL項目なし（国交省データ）")
    con.commit()
    return done
