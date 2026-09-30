"""公式サイトから見つけた Instagram の信頼度を、アカウント名と事業者の手がかりで見直す（instagram.com にはアクセスしない）。

HIGH   : アカウント名がサイトのドメインや社名の英字部分と重なる（事業者本人のアカウントと判断できる）
MEDIUM : 事業用らしい語（official/shop/clinic など）を含む、または判断材料がない
LOW    : 個人名らしい形（taro.yamada 等）で事業者の手がかりと重ならない → DM対象外・候補として保存
         （1,000件テストで、職員個人のアカウントが公式サイトからリンクされていた例があったため）
"""
import re

from . import normalize as N

STOP_TOKENS = {"www", "co", "jp", "com", "net", "or", "ne", "ac", "go", "info", "biz", "org", "tokyo", "html",
               "http", "https", "index", "web", "site", "home", "page", "official"}
BUSINESS_WORDS = ("official", "shop", "store", "salon", "clinic", "dental", "dc", "cafe", "care", "kaigo", "fudosan",
                  "estate", "home", "reform", "studio", "hair", "nail", "beauty", "gym", "hotel", "ryokan", "_jp",
                  "shika", "iin", "hospital", "kango", "day", "center", "house", "koumuten", "kensetsu", "design",
                  "group", "inc", "corp", "company", "farm", "bakery", "kitchen", "photo", "wedding", "garden",
                  # 院長・経営者本人らしい語（user 要望: 経営者に届くアカウントを残す）
                  "dr_", "dr.", "doctor", "incho", "ceo", "owner", "daihyo", "seikei", "ortho", "kyousei", "shinryo")
PERSONAL_RE = re.compile(r"^[a-z]{2,15}[._][a-z]{2,15}$")


def _tokens(domain, names):
    toks = set()
    if domain:
        for t in re.split(r"[.\-_]", domain.lower()):
            if len(t) >= 3 and t not in STOP_TOKENS:
                toks.add(t)
    for name in names:
        for t in re.findall(r"[a-z0-9]{3,}", N.nfkc(name or "").lower()):
            if t not in STOP_TOKENS:
                toks.add(t)
    return toks


def _overlap(core, toks):
    for t in toks:
        if (len(t) >= 4 and t in core) or (len(core) >= 4 and core in t):
            return True
        # 4文字以上の共通部分（例: kuonen ⊂ kuonenabiko, jala ⊂ jalakaigo）
        for i in range(len(t) - 3):
            if t[i:i + 4] in core:
                return True
    return False


def classify(username: str, domain: str = None, names=()) -> str:
    u = (username or "").lower()
    core = re.sub(r"[._]", "", u)
    if _overlap(core, _tokens(domain, names)):
        return "HIGH"
    if any(w in u for w in BUSINESS_WORDS):
        return "MEDIUM"
    if PERSONAL_RE.fullmatch(u):
        return "LOW"
    return "MEDIUM"


def reclassify(con) -> dict:
    """source='official_site' の Instagram 信頼度を見直す（冪等）。"""
    out = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    rows = con.execute("SELECT s.id, s.username, w.domain, b.business_name, b.company_name FROM social_accounts s "
                       "JOIN businesses b ON b.lead_id=s.lead_id LEFT JOIN websites w ON w.lead_id=s.lead_id "
                       "WHERE s.platform='instagram' AND s.source='official_site'").fetchall()
    for r in rows:
        c = classify(r["username"], r["domain"], (r["business_name"], r["company_name"]))
        con.execute("UPDATE social_accounts SET confidence=? WHERE id=?", (c, r["id"]))
        out[c] += 1
    con.commit()
    return out
