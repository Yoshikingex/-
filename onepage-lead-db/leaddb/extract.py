"""公式サイトHTMLからの抽出とサイト品質の採点。ネットワークには触れない（純粋関数）。"""
import re
from datetime import date
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from . import normalize as N

IG_RESERVED = {"p", "reel", "reels", "explore", "accounts", "stories", "tv", "about", "developer",
               "legal", "direct", "share", "tags", "locations", "web", "static", "sharer"}
SUBPAGE_HINTS = re.compile(r"(会社概要|会社案内|企業情報|店舗情報|医院案内|クリニック案内|施設案内|アクセス|お問い?合わ?せ|"
                           r"contact|about|company|access|profile|info|gaiyo|outline)", re.I)
RESERVE_HINTS = re.compile(r"(予約|reserve|reservation|booking|yoyaku)", re.I)
RESERVE_DOMAINS = ("hotpepper.jp", "epark.jp", "airrsv.net", "coubic.com", "reserva.be", "stores.jp",
                   "select-type.com", "dentaltool", "apo-toolbox", "ssl.haisha-yoyaku.jp", "489.jp", "tol-app.jp")
MODERN_MARKERS = ("__NEXT_DATA__", "/_next/", "_nuxt", "data-v-", "wp-block-", "gatsby", "astro-", "framerusercontent",
                  "studio.design", "webflow", "wix-", "squarespace", "shopify")
COPYRIGHT_RE = re.compile(r"(?:©|&copy;|copyright|\(c\))[^0-9<]{0,20}((?:19|20)\d{2})"
                          r"(?:\s*[-–〜~]\s*((?:19|20)\d{2}))?")


def instagram_username(url: str):
    try:
        parts = urlsplit(url if "://" in url else "https://" + url)
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    if not (host == "instagram.com" or host.endswith(".instagram.com") or host == "instagr.am"):
        return None
    seg = [s for s in parts.path.split("/") if s]
    if not seg or seg[0].lower() in IG_RESERVED:
        return None
    u = seg[0].lower()
    return u if re.fullmatch(r"[a-z0-9._]{1,30}", u) else None


def parse_page(html: str, base_url: str) -> dict:
    """1ページ分の抽出結果。"""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    res = {"phones": [], "tel_links": [], "emails": [], "instagram": [], "facebook": [], "line": [],
           "subpages": [], "has_form": False, "reservation": False}
    site_host = (urlsplit(base_url).hostname or "").lower()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        low = href.lower()
        label = a.get_text(" ", strip=True)
        if low.startswith("tel:"):
            d, disp = N.format_phone(href[4:])
            if d:
                res["tel_links"].append((d, disp))
            continue
        if low.startswith("mailto:"):
            res["emails"].append(href[7:].split("?")[0])
            continue
        absu = urljoin(base_url, href)
        host = (urlsplit(absu).hostname or "").lower()
        u = instagram_username(absu)
        if u:
            res["instagram"].append((u, f"https://www.instagram.com/{u}/"))
        elif host.endswith("facebook.com") and "sharer" not in low:
            res["facebook"].append(absu.split("?")[0])
        elif host in ("line.me", "lin.ee", "page.line.me") or host.endswith(".line.me"):
            res["line"].append(absu)
        if RESERVE_HINTS.search(label) or RESERVE_HINTS.search(low) or any(d in host for d in RESERVE_DOMAINS):
            res["reservation"] = True
        same = host == site_host or host.endswith("." + site_host.removeprefix("www."))
        if same and (SUBPAGE_HINTS.search(label) or SUBPAGE_HINTS.search(low)) and absu.split("#")[0] != base_url:
            res["subpages"].append(absu.split("#")[0])
    for f in soup.find_all("form"):
        if f.find("textarea") or f.find("input", attrs={"type": "email"}):
            res["has_form"] = True
    if re.search(r"(WEB|ネット|オンライン|24時間)\s*予約", text):
        res["reservation"] = True
    res["phones"] = N.find_phones(text)
    res["emails"] += N.EMAIL_RE.findall(text)
    res["_text"] = text
    return res


def pick_phone(pages: list):
    """tel: リンク優先、なければ本文で最も多く出た番号。FAXらしい番号は避ける。"""
    counts = {}
    for p in pages:
        for d, disp in p["tel_links"]:
            counts.setdefault(d, [disp, 0])[1] += 10
        for d, disp in p["phones"]:
            counts.setdefault(d, [disp, 0])[1] += 1
    fax = set()
    for p in pages:
        for m in re.finditer(r"FAX[:：\s]*([0-9０-９\-‐－ー()（）\s]{10,16})", p.get("_text", ""), re.I):
            d, _ = N.format_phone(m.group(1))
            if d:
                fax.add(d)
    # FAXと判明した番号は後回し（TEL/FAX共通で他に候補がない場合だけ採用）
    ranked = sorted(((d not in fax, v[1], d, v[0]) for d, v in counts.items()), reverse=True)
    return (ranked[0][2], ranked[0][3]) if ranked else (None, None)


def site_quality(html: str, final_url: str, today: date = None) -> dict:
    """0〜100 の品質点と根拠。高いほど今風で整ったサイト。"""
    today = today or date.today()
    low = html.lower()
    ev = []
    score = 50
    https = final_url.lower().startswith("https://")
    score += 10 if https else -15
    ev.append("https" if https else "httpのみ")
    viewport = bool(re.search(r"<meta[^>]+name=[\"']?viewport", low))
    score += 10 if viewport else -20
    ev.append("viewportあり" if viewport else "viewportなし")
    if re.search(r"<frameset|<frame\s", low):
        score -= 15; ev.append("frame使用")
    if re.search(r"\.swf[\"'?]|shockwave-flash", low):
        score -= 15; ev.append("Flash痕跡")
    if len(re.findall(r"<font[\s>]", low)) + len(re.findall(r"<center[\s>]", low)) >= 2:
        score -= 10; ev.append("font/centerタグ")
    if len(re.findall(r"<table[^>]*(width|cellpadding|bgcolor)=", low)) >= 3:
        score -= 10; ev.append("テーブルレイアウト")
    if re.search(r"jquery[-.]?1\.\d", low):
        score -= 5; ev.append("jQuery1.x")
    if re.search(r"<!doctype html public|xhtml1", low):
        score -= 10; ev.append("旧DOCTYPE")
    if re.search(r"charset=[\"']?(shift_jis|euc-jp|x-sjis)", low):
        score -= 5; ev.append("SJIS/EUC")
    for marker, pts, label in (("og:", 5, "OGP"), ("application/ld+json", 5, "構造化データ"),
                               ('loading="lazy"', 5, "遅延読込"), ("srcset=", 5, "srcset")):
        if marker in low:
            score += pts; ev.append(label)
    if any(m.lower() in low for m in MODERN_MARKERS):
        score += 5; ev.append("モダン基盤")
    years = []
    for a, b in COPYRIGHT_RE.findall(low):
        years += [int(y) for y in (a, b) if y and int(y) <= today.year]
    cy = max(years) if years else None
    if cy:
        if cy >= today.year - 1:
            score += 5; ev.append(f"©{cy}")
        elif cy <= today.year - 5:
            score -= 10; ev.append(f"©{cy}(古い)")
    dom = N.domain_of(final_url)
    if N.is_free_site(dom):
        score = min(score, 30); ev.append("無料ブログ/簡易サイト")
    score = max(0, min(100, score))
    return {"quality_score": score, "status": status_from_quality(score), "https": https,
            "viewport": viewport, "copyright_year": cy, "free_site": N.is_free_site(dom), "evidence": ev}


def status_from_quality(q: int) -> str:
    if q <= 25:
        return "OLD"
    if q <= 45:
        return "BASIC"
    if q <= 65:
        return "AVERAGE"
    if q <= 85:
        return "GOOD"
    return "EXCELLENT"
