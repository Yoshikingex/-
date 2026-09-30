"""S5 SII ZEHビルダー/プランナー一覧（工務店）。出典：SII公開データ（zehweb.jp/policy: 出典記載で自由利用可）。

- 関東7都県を営業エリアに含み、かつ営業エリアが MAX_AREAS 都道府県以内（地元の工務店）だけを取り込む（user 裁定 Q1=1）
- 本社住所の項目はないため prefecture は推測で埋めず、営業エリアを service_area に記録する
- ホームページ欄はZEH実績の下層ページが多いので、ドメイン直下（トップページ）を公式サイトとして巡回する
"""
import csv
import io
import logging
from urllib.parse import urlsplit

from .. import config, db
from .. import normalize as N

log = logging.getLogger("leaddb.ingest")

URL = "https://zehweb.jp/registration/builder/system/api.php"
MAX_AREAS = 3


def areas(s):
    return [a.strip() for a in (s or "").split(";") if a.strip()]


def site_root(url):
    u = N.clean_url(url)
    if not u:
        return None
    p = urlsplit(u)
    return f"{p.scheme}://{p.netloc}/" if p.netloc else None


def select(rows, scope="kanto", max_areas=MAX_AREAS):
    """scope='kanto': 関東7都県を含むもの / 'nationwide': 全国（user 裁定: Instagram 1,000件のため全国へ拡大）。"""
    out = []
    for r in rows:
        a = areas(r.get("対応可能エリア"))
        if not a or len(a) > max_areas:
            continue
        if scope == "kanto" and not any(p in config.PREF_ORDER for p in a):
            continue
        out.append(r)
    return out


def ingest_zeh(con, fetcher, target=None, scope="kanto", max_areas=MAX_AREAS):
    page = fetcher.get(URL)
    text = page.body.decode("utf-8-sig", errors="replace")
    rows = select(list(csv.DictReader(io.StringIO(text))), scope, max_areas)
    n = 0
    for r in rows[:target] if target else rows:
        reg = (r.get("ZEHビルダー登録番号") or "").strip()
        if not reg:
            continue
        a = areas(r.get("対応可能エリア"))
        lead_id = db.upsert_business(con, {
            "source_key": f"S5:zeh:{reg}",
            "business_name": N.nfkc(r.get("登録名称（屋号）")) or N.nfkc(r.get("事業者名")),
            "company_name": N.nfkc(r.get("事業者名")) or None,
            "industry": "construction", "sub_industry": "工務店（ZEHビルダー）",
            "prefecture": None, "service_area": ";".join(a),
            "seed_website_url": site_root(r.get("ホームページ")),
        })
        d, disp = N.format_phone(r.get("電話番号"))
        if d:
            db.add_contact(con, lead_id, "phone", d, disp, N.phone_type(d), source_code="S5", source_url=URL)
        db.add_source(con, lead_id, "S5", URL)
        n += 1
    con.commit()
    log.info("S5 zeh(%s, areas<=%d): rows=%d ingested=%d", scope, max_areas, len(rows), n)
    return n
