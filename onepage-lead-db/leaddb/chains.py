"""チェーン・大手の判定（user 裁定: 除外）。ネットワークは使わず、取得済みの公開データとDBだけで判定する。

基準（初期値。1,000件テストの分布から設定した推測値で、調整可能）:
  - 同一法人が関東で CHAIN_MIN_FACILITIES 施設以上（S1=法人番号 / S2=正式名称の法人部分）
  - 宅建業者の総従事者数が LARGE_STAFF_MIN 人以上
  - サンプル内で同一ドメインを 10 件以上 / 同一Instagramを 5 件以上が共有
"""
import csv
import io
import re
import zipfile
from collections import Counter

from . import config
from . import normalize as N

CHAIN_MIN_FACILITIES = 5
LARGE_STAFF_MIN = 30
SHARED_DOMAIN_MIN = 10
SHARED_IG_MIN = 5
KANTO_CODES = {"08", "09", "10", "11", "12", "13", "14"}
CORP_RE = re.compile(r"^((?:医療法人社団|医療法人財団|社会医療法人|医療法人|一般社団法人|一般財団法人|社会福祉法人|株式会社|有限会社)"
                     r"\s*[^\s]+)")


def corp_key(official_name: str):
    """正式名称から法人部分（例: 医療法人社団善仁会）を取り出す。個人開設などは None。"""
    s = N.nfkc(official_name)
    m = CORP_RE.match(s)
    return re.sub(r"\s+", "", m.group(1)) if m else None


def _s1_counts():
    cnt = Counter()
    for path in sorted(config.RAW.glob("jigyosho_*_all_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("都道府県名") in config.PREF_ORDER and (r.get("法人番号") or "").strip():
                    cnt[r["法人番号"].strip()] += 1
    return cnt


def _s2_counts():
    cnt = Counter()
    for path in sorted(config.RAW.glob("0[23]-1_*_facility_info_*.csv.zip")):
        with zipfile.ZipFile(path) as z, z.open(z.namelist()[0]) as fh:
            for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig", newline="")):
                if str(r.get("都道府県コード", "")).zfill(2)[:2] in KANTO_CODES:
                    k = corp_key(r.get("正式名称"))
                    if k:
                        cnt[k] += 1
    return cnt


def compute(con) -> int:
    """businesses.chain_size / exclude_reason を更新。除外件数を返す。"""
    s1, s2 = _s1_counts(), _s2_counts()
    dom_cnt = Counter(r[0] for r in con.execute(
        "SELECT w.domain FROM websites w JOIN businesses b ON b.lead_id=w.lead_id "
        "WHERE b.merged_into IS NULL AND w.domain IS NOT NULL"))
    ig_cnt = Counter(r[0] for r in con.execute(
        "SELECT DISTINCT s.username, s.lead_id FROM social_accounts s JOIN businesses b ON b.lead_id=s.lead_id "
        "WHERE b.merged_into IS NULL AND s.platform='instagram'"))
    n = 0
    for b in con.execute("SELECT b.*, w.domain FROM businesses b LEFT JOIN websites w ON w.lead_id=b.lead_id "
                         "WHERE b.merged_into IS NULL").fetchall():
        size, reason = None, None
        fam = b["source_key"].split(":")[0]
        if fam == "S1" and b["corporate_number"]:
            size = s1.get(b["corporate_number"])
        elif fam == "S2":
            k = corp_key(b["business_name"])
            size = s2.get(k) if k else None
        if size and size >= CHAIN_MIN_FACILITIES:
            reason = f"チェーン（同一法人が関東で{size}施設）"
        elif fam == "S4" and (b["staff_count"] or 0) >= LARGE_STAFF_MIN:
            reason = f"大手（従事者{b['staff_count']}人）"
        elif b["domain"] and not (N.is_portal(b["domain"]) or N.is_free_site(b["domain"])) \
                and dom_cnt[b["domain"]] >= SHARED_DOMAIN_MIN:
            reason = f"チェーン（同一ドメインを{dom_cnt[b['domain']]}件が共有）"
        else:
            igs = [r[0] for r in con.execute("SELECT username FROM social_accounts WHERE lead_id=? AND "
                                              "platform='instagram'", (b["lead_id"],))]
            top = max((ig_cnt[u] for u in igs), default=0)
            if top >= SHARED_IG_MIN:
                reason = f"チェーン（同一Instagramを{top}件が共有）"
        con.execute("UPDATE businesses SET chain_size=?, exclude_reason=? WHERE lead_id=?", (size, reason, b["lead_id"]))
        n += bool(reason)
    con.commit()
    return n
