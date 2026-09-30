"""P3: 重複統合。電話 → Instagram → ドメイン → 住所+社名 の順。削除はせず merged_into で印を付ける。"""
import logging
from collections import defaultdict

from . import normalize as N

log = logging.getLogger("leaddb.dedup")
SHARED_PHONE_MIN = 5  # 代表番号の共有とみなす件数


def _root(con, lead_id):
    seen = set()
    while lead_id and lead_id not in seen:
        seen.add(lead_id)
        r = con.execute("SELECT merged_into FROM businesses WHERE lead_id=?", (lead_id,)).fetchone()
        if not r or not r["merged_into"]:
            return lead_id
        lead_id = r["merged_into"]
    return lead_id


def _merge(con, keep, other):
    keep, other = _root(con, keep), _root(con, other)
    if keep == other:
        return 0
    con.execute("UPDATE businesses SET merged_into=? WHERE lead_id=? AND merged_into IS NULL", (keep, other))
    for t in ("contacts", "social_accounts", "sources"):
        con.execute(f"UPDATE OR IGNORE {t} SET lead_id=? WHERE lead_id=?", (keep, other))
    con.execute("UPDATE businesses SET data_confidence='HIGH' WHERE lead_id=?", (keep,))
    return 1


def _family(con, lead_id):
    r = con.execute("SELECT source_key FROM businesses WHERE lead_id=?", (lead_id,)).fetchone()
    return r["source_key"].split(":")[0] if r else None


def _same_entity(a, b):
    return (N.norm_name(a["business_name"] or "") == N.norm_name(b["business_name"] or "")
            or (a["address"] and N.norm_address(a["address"]) == N.norm_address(b["address"] or "")))


def _groups(con, sql):
    g = defaultdict(list)
    for r in con.execute(sql).fetchall():
        g[r[0]].append(r[1])
    return {k: sorted(set(v)) for k, v in g.items() if k and len(set(v)) > 1}


def run(con) -> int:
    merged = 0
    info = {r["lead_id"]: r for r in con.execute(
        "SELECT lead_id, business_name, address FROM businesses WHERE merged_into IS NULL")}
    # 1) 電話（最優先）。ただし同じ公的名簿内の別ID同士は、社名か住所も一致したときだけ統合する
    #    （同一法人の別施設が本部番号を共有するため）。5件以上の共有は住所一致が必須。
    for phone, ids in _groups(con, "SELECT c.value, c.lead_id FROM contacts c JOIN businesses b ON b.lead_id=c.lead_id "
                                   "WHERE c.kind='phone' AND b.merged_into IS NULL").items():
        keep = ids[0]
        for o in ids[1:]:
            a, b = info[keep], info[o]
            if len(ids) >= SHARED_PHONE_MIN:
                ok = bool(a["address"]) and N.norm_address(a["address"]) == N.norm_address(b["address"] or "")
            else:
                ok = _family(con, keep) != _family(con, o) or _same_entity(a, b)
            if ok:
                merged += _merge(con, keep, o)
    # 2) Instagram ユーザー名
    for _u, ids in _groups(con, "SELECT s.username, s.lead_id FROM social_accounts s JOIN businesses b ON "
                                "b.lead_id=s.lead_id WHERE s.platform='instagram' AND b.merged_into IS NULL").items():
        for o in ids[1:]:
            merged += _merge(con, ids[0], o)
    # 3) ドメイン：チェーンの支店を潰さないよう、社名か住所も一致したときだけ
    for dom, ids in _groups(con, "SELECT w.domain, w.lead_id FROM websites w JOIN businesses b ON b.lead_id=w.lead_id "
                                 "WHERE w.domain IS NOT NULL AND b.merged_into IS NULL").items():
        if N.is_portal(dom) or N.is_free_site(dom):
            continue
        for o in ids[1:]:
            if _same_entity(info[ids[0]], info[o]):
                merged += _merge(con, ids[0], o)
    # 4) 住所+社名
    g = defaultdict(list)
    for i, r in info.items():
        if r["address"] and r["business_name"]:
            g[(N.norm_address(r["address"]), N.norm_name(r["business_name"]))].append(i)
    for ids in g.values():
        ids = sorted(ids)
        for o in ids[1:]:
            merged += _merge(con, ids[0], o)
    # data_confidence（統合されなかったもの）: 同じ電話が2ソースで一致 → HIGH、公式ソース1件 → MEDIUM
    con.execute("UPDATE businesses SET data_confidence = CASE WHEN data_confidence='HIGH' OR EXISTS ("
                "SELECT 1 FROM contacts c WHERE c.lead_id=businesses.lead_id AND c.kind='phone' "
                "GROUP BY c.value HAVING COUNT(DISTINCT c.source_code) >= 2) THEN 'HIGH' ELSE 'MEDIUM' END "
                "WHERE merged_into IS NULL")
    con.commit()
    log.info("dedup merged=%d", merged)
    return merged
