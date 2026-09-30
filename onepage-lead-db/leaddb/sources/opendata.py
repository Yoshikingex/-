"""S1 介護サービス情報公表システム / S2 医療情報ネット のオープンデータ取り込み。"""
import csv
import io
import logging
import re
import zipfile

from .. import config, db
from .. import normalize as N

log = logging.getLogger("leaddb.ingest")

KAIGO_PAGE = "https://www.mhlw.go.jp/stf/kaigo-kouhyou_opendata.html"
IRYOU_PAGE = "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryou/newpage_43373.html"
IRYOU_FILES = {
    "dental": "https://www.mhlw.go.jp/content/11121000/03-1_dental_facility_info_20260601.csv.zip",
    "clinic": "https://www.mhlw.go.jp/content/11121000/02-1_clinic_facility_info_20260601.csv.zip",
}


def spread_sample(rows, n):
    """都道府県の優先順に並べ、全体から等間隔に n 件取る（地域の偏りを避ける）。"""
    order = {p: i for i, p in enumerate(config.PREF_ORDER)}
    rows = sorted(rows, key=lambda r: order.get(r["_pref"], 99))
    if n is None or n >= len(rows):
        return rows
    step = len(rows) / n
    return [rows[int(i * step)] for i in range(n)]


def resolve_kaigo_url(fetcher, code):
    """掲載ページから最新ファイル名を引く（名前に作成日時が入るため推測で組み立てない）。"""
    html = fetcher.get(KAIGO_PAGE).text
    m = re.findall(r'href="(/content/12300000/jigyosho_%s_all_\d+\.csv)"' % code, html)
    if not m:
        raise RuntimeError(f"kaigo csv link not found for service code {code}")
    return "https://www.mhlw.go.jp" + sorted(m)[-1]


def ingest_kaigo(con, fetcher, limit=None, code="150"):
    url = resolve_kaigo_url(fetcher, code)
    dest = config.RAW / url.rsplit("/", 1)[-1]
    fetcher.download(url, dest)
    rows = []
    with open(dest, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("都道府県名") in config.PREF_ORDER:
                r["_pref"] = r["都道府県名"]
                rows.append(r)
    picked = spread_sample(rows, limit)
    n = 0
    for r in picked:
        addr = (r.get("住所") or "") + (r.get("方書（ビル名等）") or "")
        postal, pref, city, address = N.split_address(addr)
        lead_id = db.upsert_business(con, {
            "source_key": f"S1:{r.get('事業所番号')}",
            "business_name": N.nfkc(r.get("事業所名")), "company_name": N.nfkc(r.get("法人の名称")) or None,
            "industry": "care", "sub_industry": N.nfkc(r.get("サービスの種類")) or "介護施設",
            "postal_code": postal, "prefecture": r["_pref"], "city": N.nfkc(r.get("市区町村名")) or city,
            "address": address, "corporate_number": (r.get("法人番号") or "").strip() or None,
            "seed_website_url": N.clean_url(r.get("URL")),
        })
        d, disp = N.format_phone(r.get("電話番号"))
        if d:
            db.add_contact(con, lead_id, "phone", d, disp, N.phone_type(d), source_code="S1", source_url=url)
        db.add_source(con, lead_id, "S1", url)
        n += 1
    con.commit()
    log.info("S1 kaigo(%s): kanto rows=%d picked=%d", code, len(rows), n)
    return n


def ingest_iryou(con, fetcher, kind="dental", limit=None):
    url = IRYOU_FILES[kind]
    dest = config.RAW / url.rsplit("/", 1)[-1]
    fetcher.download(url, dest)
    rows = []
    with zipfile.ZipFile(dest) as z:
        with z.open(z.namelist()[0]) as fh:
            for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig", newline="")):
                pref = N.pref_from_code(r.get("都道府県コード", ""))
                if pref:
                    r["_pref"] = pref
                    rows.append(r)
    picked = spread_sample(rows, limit)
    n = 0
    for r in picked:
        postal, pref, city, address = N.split_address(r.get("所在地"))
        lead_id = db.upsert_business(con, {
            "source_key": f"S2:{kind}:{r.get('ID')}",
            "business_name": N.nfkc(r.get("正式名称")), "company_name": None,
            "industry": kind, "sub_industry": "歯科医院" if kind == "dental" else "クリニック",
            "postal_code": postal, "prefecture": r["_pref"], "city": city, "address": address,
            "seed_website_url": N.clean_url(r.get("案内用ホームページアドレス")),
        })
        db.add_source(con, lead_id, "S2", url)
        n += 1
    con.commit()
    log.info("S2 iryou(%s): kanto rows=%d picked=%d", kind, len(rows), n)
    return n
