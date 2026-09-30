"""S4 国交省 建設業者・宅建業者等企業情報検索システム（宅建業者）。
3秒間隔・同時1本（G6）。代表者の氏名は取得・保存しない（個人情報を持たない方針）。
"""
import logging
import re
import html as H

from .. import config, db
from .. import normalize as N

log = logging.getLogger("leaddb.ingest")

BASE = "https://etsuran2.mlit.go.jp/TAKKEN/"
SEARCH = BASE + "takkenKensaku.do"
DETAIL = BASE + "tkGaiyo.do"
PREF_CODE = {v: k for k, v in config.KANTO.items()}


def _decode(page):
    return page.body.decode("cp932", errors="replace")


def _hidden(html):
    return {m.group(1): H.unescape(m.group(2)) for m in
            re.finditer(r'<input[^>]*name="([^"]+)"[^>]*type="hidden"[^>]*value="([^"]*)"', html)}


def _clean(s):
    return H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


def parse_list(html):
    """一覧ページ → [(license_key, 商号, 所在地)]"""
    out = []
    for tr in re.findall(r"<tr.*?</tr>", html, flags=re.S):
        m = re.search(r"js_ShowDetail\('(\d+)'\)", tr)
        if not m:
            continue
        cells = [_clean(c) for c in re.findall(r"<td.*?</td>", tr, flags=re.S)]
        # No, 免許行政庁, 免許証番号, 商号, 代表者名, 事務所名, 所在地
        if len(cells) >= 7:
            out.append((m.group(1), cells[3], cells[6]))
    return out


def parse_detail(html):
    """詳細ページ → dict（ラベル→値）。代表者欄は捨てる。"""
    text = _clean(re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S))
    out = {}
    m = re.search(r"商号又は名称\s+(\S+)\s+(.+?)\s+代表者の氏名", text)
    if m:
        out["name"] = m.group(2).strip()
    m = re.search(r"主たる事務所の\s*所在地\s+(.+?)\s+総従事者数", text)
    if m:
        out["address"] = m.group(1).strip()
    m = re.search(r"電話番号\s+([0-9０-９\-‐－ー()（）]+)", text)
    if m:
        out["phone"] = m.group(1)
    m = re.search(r"総従事者数\s+(\d+)\s*人", text)
    if m:
        out["staff"] = int(m.group(1))
    out["kengyo"] = re.findall(r"兼業\s+(?:\d+\s+)?(\S+業)", text)
    out["license"] = (re.search(r"免許証番号\s+(.+?)\s+免許の有効期間", text) or [None, None])[1]
    return out


def ingest_takken(con, fetcher, pref="埼玉県", limit=50, disp=50):
    """都道府県の本店を一覧→詳細の順に取得。一覧はページ単位、詳細は業者単位でジョブ化（再開可）。"""
    ken = PREF_CODE[pref]
    form = {"CMD": "search", "caller": "TK", "rdoSelect": "1", "comNameKanaOnly": "", "comNameKanjiOnly": "",
            "rdoSelectJoken": "1", "licenseNoKbn": "", "licenseNoFrom": "", "licenseNoTo": "", "choice": "1",
            "kenCode": ken, "sortValue": "1", "rdoSelectSort": "1", "dispCount": str(disp), "dispPage": "1",
            "sv_dispCount": "0", "sv_dispPage": "0", "resultCount": "0", "pageCount": "0"}
    page = fetcher.post(SEARCH, form, use_cache=False)  # セッションを張るため毎回取得
    html = _decode(page)
    hidden = _hidden(html)
    total = int(hidden.get("resultCount", "0") or 0)
    pages = int(hidden.get("pageCount", "0") or 0)
    log.info("S4 takken %s: resultCount=%d pageCount=%d", pref, total, pages)
    n, pno = 0, 1
    while n < limit and pno <= max(pages, 1):
        jkey = f"{ken}:list:{disp}:{pno}"
        if pno > 1:
            f2 = dict(hidden, CMD="selectPage", pageListNo1=str(pno), pageListNo2=str(pno), dispPage=str(pno))
            html = _decode(fetcher.post(SEARCH, f2, use_cache=False))
            hidden = _hidden(html)
        rows = parse_list(html)
        db.set_job(con, "takken_list", jkey, "COMPLETE")
        for key, _name, _addr in rows:
            if n >= limit:
                break
            if db.job_status(con, "takken_detail", key) == "COMPLETE":
                n += 1
                continue
            db.set_job(con, "takken_detail", key, "RUNNING")
            try:
                d = parse_detail(_decode(fetcher.post(DETAIL, dict(hidden, sv_licenseNo=key))))
                postal, p2, city, address = N.split_address(d.get("address") or _addr)
                sub = "不動産管理会社" if any("管理" in k for k in d.get("kengyo", [])) else "不動産会社"
                lead_id = db.upsert_business(con, {
                    "source_key": f"S4:takken:{key}", "business_name": d.get("name") or _name,
                    "company_name": d.get("name") or _name, "industry": "real_estate", "sub_industry": sub,
                    "postal_code": postal, "prefecture": pref, "city": city, "address": address,
                    "staff_count": d.get("staff"),
                })
                dg, disp_ph = N.format_phone(d.get("phone"))
                if dg:
                    db.add_contact(con, lead_id, "phone", dg, disp_ph, N.phone_type(dg),
                                   source_code="S4", source_url=DETAIL + "#" + key)
                db.add_source(con, lead_id, "S4", DETAIL + "#" + key)
                db.set_job(con, "takken_detail", key, "COMPLETE")
                n += 1
            except Exception as e:  # noqa: BLE001 - 1件の失敗で全体を止めない
                log.warning("takken detail %s failed: %s", key, e)
                db.set_job(con, "takken_detail", key, "FAILED", str(e)[:200])
        pno += 1
    con.commit()
    return n
