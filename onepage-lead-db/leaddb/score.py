"""P7: web_need_score・優先度・DM切り口・おすすめサンプル。閾値は spec のまま（70/50）。"""
import logging
from datetime import date

from . import config
from . import normalize as N

log = logging.getLogger("leaddb.score")

SAMPLES = {
    "MAISON": "https://maison-akari.vercel.app",
    "雫": "https://shizuku-hair-atelier.vercel.app/",
    "KEBAB": "https://kebab-taste-a-better-day.vercel.app",
    "朧": "https://oboro-nine.vercel.app",
    "VELARIN.": "https://velarin.vercel.app",
    "AURELION": "https://kairos-meridian-plum.vercel.app",
}
INDUSTRY_SAMPLE = {
    "construction": ("MAISON", ["施工写真訴求", "ビフォーアフター", "高級感", "問い合わせ訴求"]),
    "real_estate": ("MAISON", ["物件紹介", "高級物件", "売主獲得", "Instagram→HP導線"]),
    "beauty": ("雫", ["スタイル写真", "店舗世界観", "Instagram→予約導線", "ブランド訴求"]),
    "bodycare": ("雫", ["Instagram→予約導線", "スタッフ訴求"]),
    "restaurant": ("KEBAB", ["料理シズル", "店舗世界観", "Instagram→予約導線"]),
    "lodging": ("朧", ["宿泊体験", "客室", "料理シズル", "店舗世界観"]),
    "auto": ("VELARIN.", ["在庫車紹介", "ブランド訴求", "問い合わせ訴求"]),
    "gym": ("VELARIN.", ["ビフォーアフター", "設備", "スタッフ訴求", "体験予約"]),
    "dental": ("AURELION", ["ブランド訴求", "スタッフ訴求", "予約導線"]),
    "clinic": ("AURELION", ["ブランド訴求", "スタッフ訴求", "予約導線"]),
    "care": ("朧", ["施設世界観", "スタッフ訴求", "見学予約"]),
}


def level(score: int) -> str:
    return "HIGH" if score >= 70 else "MEDIUM" if score >= 50 else "LOW"


def compute(lead: dict, today: date = None) -> dict:
    """lead: industry, website_status, quality_score, https_enabled, mobile_friendly, contact_form_found,
    reservation_found, copyright_year, domain, instagram_found(非LOW), chain(bool), phone_found."""
    today = today or date.today()
    pts = []
    st = lead.get("website_status")
    has_site = st in ("OLD", "BASIC", "AVERAGE", "GOOD", "EXCELLENT")
    if st == "NONE":
        pts.append((25, "公式HPが見つからない"))
    if st == "OLD":
        pts.append((20, "公式HPが古いデザイン"))
    if has_site and lead.get("mobile_friendly") == 0:
        pts.append((15, "スマホ対応が弱い"))
    if has_site and lead.get("https_enabled") == 0:
        pts.append((15, "SSLなし"))
    q = lead.get("quality_score")
    if has_site and q is not None and q <= 20:
        pts.append((10, "デザインが極端に古い"))
    if lead.get("industry") in config.VISUAL_INDUSTRIES:
        pts.append((10, "ビジュアル訴求が重要な業種"))
    if has_site and not lead.get("contact_form_found") and not lead.get("reservation_found"):
        pts.append((10, "予約・問い合わせ導線が弱い"))
    if has_site and N.is_free_site(lead.get("domain")):
        pts.append((10, "無料ブログ・簡易サイトのみ"))
    if lead.get("instagram_found") and st in ("OLD", "BASIC", "NONE"):
        pts.append((10, "Instagramはあるが公式HPが弱い"))
    cy = lead.get("copyright_year")
    if has_site and cy and cy <= today.year - 5:
        pts.append((5, f"更新が止まっている可能性（©{cy}）"))
    if st == "EXCELLENT":
        pts.append((-20, "高品質な最新サイトあり"))
    if lead.get("chain"):
        pts.append((-15, "チェーン本部管理の可能性"))
    if st == "GOOD":
        pts.append((-10, "サイトが十分に整っている"))
    score = max(0, min(100, sum(p for p, _ in pts)))
    reasons = [r for p, r in sorted(pts, key=lambda x: -x[0]) if p > 0][:3]
    reasons += [None] * (3 - len(reasons))
    ig = bool(lead.get("instagram_found"))
    phone = bool(lead.get("phone_found"))
    if phone and ig and st == "NONE":
        prio = "P1"
    elif phone and ig and st == "OLD":
        prio = "P2"
    elif phone and ig and st == "BASIC":
        prio = "P3"
    elif phone and not ig and st == "NONE":
        prio = "P4"
    else:
        prio = "P5"
    sample, angles = INDUSTRY_SAMPLE.get(lead.get("industry"), ("AURELION", ["ブランド訴求"]))
    angle = angles[0]
    if ig and st in ("NONE", "OLD", "BASIC"):
        angle = next((a for a in angles if a.startswith("Instagram→")), angle)
    return {"web_need_score": score, "web_need_level": level(score), "reason_1": reasons[0],
            "reason_2": reasons[1], "reason_3": reasons[2], "lead_priority": prio,
            "recommended_dm_angle": angle, "recommended_sample": sample}


LEAD_SQL = """
SELECT b.lead_id, b.industry, w.status AS website_status, w.quality_score, w.https_enabled, w.mobile_friendly,
       w.contact_form_found, w.reservation_found, w.copyright_year, w.domain,
       EXISTS(SELECT 1 FROM social_accounts s WHERE s.lead_id=b.lead_id AND s.platform='instagram'
              AND s.confidence IN ('HIGH','MEDIUM')) AS instagram_found,
       EXISTS(SELECT 1 FROM contacts c WHERE c.lead_id=b.lead_id AND c.kind='phone') AS phone_found,
       (w.domain IS NOT NULL AND (SELECT COUNT(*) FROM websites w2 JOIN businesses b2 ON b2.lead_id=w2.lead_id
            WHERE w2.domain=w.domain AND b2.merged_into IS NULL) >= 10) AS chain
FROM businesses b LEFT JOIN websites w ON w.lead_id=b.lead_id
WHERE b.merged_into IS NULL
"""


def score_all(con) -> int:
    from .db import now
    n = 0
    for r in con.execute(LEAD_SQL).fetchall():
        lead = dict(r)
        if N.is_portal(lead.get("domain")) or N.is_free_site(lead.get("domain")):
            lead["chain"] = False  # 共有プラットフォームはチェーン扱いしない
        s = compute(lead)
        con.execute("INSERT OR REPLACE INTO scores VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (r["lead_id"], s["web_need_score"], s["web_need_level"], s["reason_1"], s["reason_2"],
                     s["reason_3"], s["lead_priority"], s["recommended_dm_angle"], s["recommended_sample"], now()))
        log.info("score %s %s=%d %s | %s", r["lead_id"], s["web_need_level"], s["web_need_score"],
                 s["lead_priority"], " / ".join(x for x in (s["reason_1"], s["reason_2"], s["reason_3"]) if x))
        n += 1
    con.commit()
    return n
