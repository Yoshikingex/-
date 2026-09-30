"""電話・メール・住所・社名・ドメインの正規化。"""
import re
import unicodedata
from urllib.parse import urlsplit

from .config import KANTO

HYPHENS = "-‐‑‒–—―−ーｰ－"
_HY = re.compile("[" + re.escape(HYPHENS) + "]")

BUSINESS_EMAIL_PREFIXES = {
    "info", "contact", "shop", "office", "support", "sales", "mail", "reserve", "reservation",
    "yoyaku", "recruit", "saiyo", "inquiry", "otoiawase", "toiawase", "customer", "hello",
    "estate", "fudosan", "reform", "home", "salon", "clinic", "dental", "kaigo", "care", "web",
    "admin", "service", "store", "hotel", "front", "booking", "staff", "jimu", "soumu", "honbu",
}
FREEMAIL_DOMAINS = {"gmail.com", "yahoo.co.jp", "ymail.ne.jp", "icloud.com", "me.com", "hotmail.com",
                    "outlook.com", "outlook.jp", "live.jp", "docomo.ne.jp", "ezweb.ne.jp",
                    "softbank.ne.jp", "i.softbank.jp", "au.com", "nifty.com", "biglobe.ne.jp"}
EMAIL_JUNK = re.compile(r"(\.(png|jpe?g|gif|webp|svg|css|js)$)|(example\.(com|jp))|(sentry)|(wixpress)|(domain\.com)")
FREE_SITE_DOMAINS = ("ameblo.jp", "jimdo.com", "jimdofree.com", "jimdosite.com", "wixsite.com", "fc2.com",
                     "blogspot.com", "hatenablog.com", "goo.ne.jp", "livedoor.jp", "seesaa.net",
                     "crayonsite.net", "peraichi.com", "strikingly.com", "weebly.com", "hp.peraichi.com",
                     "on.fc2.com", "shopinfo.jp", "wix.com", "note.com")
PORTAL_DOMAINS = ("hotpepper.jp", "tabelog.com", "epark.jp", "linktr.ee", "lit.link", "facebook.com",
                  "instagram.com", "twitter.com", "x.com", "line.me", "lin.ee", "youtube.com",
                  "suumo.jp", "homes.co.jp", "athome.co.jp", "wam.go.jp", "mhlw.go.jp", "google.com")


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


# ---------------- 電話 ----------------
def phone_digits(raw: str):
    """数字だけにする。日本の番号として妥当（0始まり10〜11桁）でなければ None。"""
    if not raw:
        return None
    s = nfkc(raw)
    s = re.sub(r"^\+?81[\s-]?", "0", s)
    d = re.sub(r"\D", "", s)
    if not d.startswith("0") or len(d) not in (10, 11):
        return None
    if len(d) == 11 and not re.match(r"^0(?:[5789]0|800)", d):  # 11桁は携帯・IP・0800だけ
        return None
    if len(d) == 10 and re.match(r"^0(?:[789]0|800)", d):      # 携帯/0800 は10桁にならない
        return None
    return d


def phone_type(d: str) -> str:
    if re.match(r"^0[789]0", d):
        return "mobile"
    if d.startswith("050"):
        return "ip"
    if d.startswith("0120") or d.startswith("0800"):
        return "freedial"
    return "fixed"


def format_phone(raw: str):
    """(digits, display) を返す。元の区切りがあればそれを尊重し、なければ規則で区切る。"""
    d = phone_digits(raw)
    if not d:
        return None, None
    s = nfkc(raw)
    s = re.sub(r"^\+?81[\s-]?", "0", s)
    s = re.sub(r"[()（）\s]+", "-", _HY.sub("-", s)).strip("-")
    groups = [g for g in re.split(r"-+", s) if g]
    if len(groups) == 3 and all(g.isdigit() for g in groups) and "".join(groups) == d:
        return d, "-".join(groups)
    if re.match(r"^0[789]0|^050", d):
        return d, f"{d[:3]}-{d[3:7]}-{d[7:]}"
    if d.startswith("0120") or d.startswith("0800"):
        return d, f"{d[:4]}-{d[4:7]}-{d[7:]}"
    if re.match(r"^0[36]", d):
        return d, f"{d[:2]}-{d[2:6]}-{d[6:]}"
    return d, f"{d[:3]}-{d[3:6]}-{d[6:]}"  # 市外局番の桁が不明なときの既定（通話には支障なし）


PHONE_RE = re.compile(
    r"(?<![\d０-９])(?:\+81[\s-]?|0)[\d０-９]{1,4}\s*[" + re.escape(HYPHENS) + r"(（)）\s]\s*[\d０-９]{1,4}\s*["
    + re.escape(HYPHENS) + r"(（)）\s]\s*[\d０-９]{3,4}(?![\d０-９])")


def find_phones(text: str):
    out = []
    for m in PHONE_RE.finditer(text or ""):
        d, disp = format_phone(m.group(0))
        if d and d not in [x[0] for x in out]:
            out.append((d, disp))
    return out


# ---------------- メール ----------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def classify_email(email: str):
    """(normalized, is_business, personal_suspect) を返す。無効なら (None, False, False)。"""
    e = nfkc(email).lower().strip(".")
    if not EMAIL_RE.fullmatch(e) or EMAIL_JUNK.search(e):
        return None, False, False
    local, dom = e.split("@", 1)
    base = re.split(r"[._\-+0-9]", local)[0]
    is_biz_prefix = local in BUSINESS_EMAIL_PREFIXES or base in BUSINESS_EMAIL_PREFIXES
    # 個人名らしい形（taro.yamada / t.yamada）で業務用接頭辞でもないものは除外対象。
    # 公式サイトに連絡先として掲載されたフリーメール（例: xxsalon@gmail.com）は業務用として扱う。
    looks_personal = bool(re.fullmatch(r"[a-z]{1,12}[._][a-z]{2,12}", local)) and not is_biz_prefix
    return e, not looks_personal, looks_personal


def email_rank(email: str, site_domain: str = None) -> int:
    """小さいほど優先：サイトと同じドメイン → 業務用接頭辞 → その他。"""
    local, dom = email.split("@", 1)
    same = bool(site_domain) and (dom == site_domain or dom.endswith("." + site_domain))
    biz = local in BUSINESS_EMAIL_PREFIXES or re.split(r"[._\-+0-9]", local)[0] in BUSINESS_EMAIL_PREFIXES
    return (0 if same else 2) + (0 if biz else 1)


# ---------------- URL / ドメイン ----------------
def domain_of(url: str):
    if not url:
        return None
    u = nfkc(url)
    if not re.match(r"^https?://", u, re.I):
        u = "http://" + u
    host = (urlsplit(u).hostname or "").lower()
    return host[4:] if host.startswith("www.") else (host or None)


def clean_url(url: str):
    u = _HY.sub("-", nfkc(url or "")).strip()
    if not u or u in ("-", "なし", "無"):
        return None
    if not re.match(r"^https?://", u, re.I):
        if re.match(r"^[\w.-]+\.[a-z]{2,}(/.*)?$", u, re.I):
            u = "http://" + u
        else:
            return None
    return u


def is_free_site(domain: str) -> bool:
    return bool(domain) and any(domain == d or domain.endswith("." + d) for d in FREE_SITE_DOMAINS)


def is_portal(domain: str) -> bool:
    return bool(domain) and any(domain == d or domain.endswith("." + d) for d in PORTAL_DOMAINS)


# ---------------- 社名・住所 ----------------
CORP_WORDS = r"(株式会社|有限会社|合同会社|合資会社|合名会社|一般社団法人|一般財団法人|公益社団法人|公益財団法人|" \
             r"社会福祉法人|医療法人社団|医療法人財団|医療法人|特定非営利活動法人|NPO法人|\(株\)|\(有\)|\(同\)|㈱|㈲)"


def norm_name(name: str) -> str:
    s = nfkc(name)
    s = re.sub(CORP_WORDS, "", s)
    return re.sub(r"[\s・･\-‐ー　]", "", s).lower()


PREFS_ALL = "北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|" \
            "石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|" \
            "岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県"
CITY_RE = re.compile(r"^(" + PREFS_ALL + r")?\s*((?:[^\s0-9]+?郡)?[^\s0-9]+?(?:市[^\s0-9]+?区|市|区|町|村))")


def split_address(addr: str):
    """(postal_code, prefecture, city, address) を返す。"""
    s = nfkc(addr)
    postal = None
    m = re.search(r"〒?\s*(\d{3})-?(\d{4})", s)
    if m and s.find(m.group(0)) < 3:
        postal = f"{m.group(1)}-{m.group(2)}"
        s = s.replace(m.group(0), "", 1).strip()
    m = CITY_RE.match(s)
    pref = m.group(1) if m else None
    city = m.group(2) if m else None
    return postal, pref, city, s or None


def norm_address(addr: str) -> str:
    s = nfkc(addr)
    s = re.sub(r"(\d+)丁目", r"\1-", s)
    s = re.sub(r"(\d+)番地?", r"\1-", s)
    s = re.sub(r"(\d+)号", r"\1", s)
    s = _HY.sub("-", s)
    s = re.sub(r"\s+", "", s)
    return re.sub(r"-+$", "", re.sub(r"-{2,}", "-", s))


def pref_from_code(code: str):
    return KANTO.get(str(code).zfill(2)[:2])
