"""SQLite スキーマとジョブ管理。DELETE/DROP は使わない（spec db.safety）。"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS businesses (
  lead_id TEXT PRIMARY KEY,
  source_key TEXT UNIQUE NOT NULL,
  business_name TEXT, company_name TEXT, industry TEXT, sub_industry TEXT,
  postal_code TEXT, prefecture TEXT, city TEXT, address TEXT,
  corporate_number TEXT, staff_count INTEGER,
  seed_website_url TEXT,
  data_confidence TEXT,
  merged_into TEXT,
  created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id TEXT NOT NULL, kind TEXT NOT NULL, value TEXT NOT NULL,
  display TEXT, phone_type TEXT, email_personal_suspect INTEGER DEFAULT 0,
  source_code TEXT, source_url TEXT,
  UNIQUE(lead_id, kind, value, source_code)
);
CREATE TABLE IF NOT EXISTS social_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id TEXT NOT NULL, platform TEXT NOT NULL, url TEXT, username TEXT,
  confidence TEXT, source TEXT, source_url TEXT, last_checked_at TEXT,
  UNIQUE(lead_id, platform, username)
);
CREATE TABLE IF NOT EXISTS websites (
  lead_id TEXT PRIMARY KEY, url TEXT, final_url TEXT, domain TEXT,
  status TEXT, quality_score INTEGER,
  https_enabled INTEGER, mobile_friendly INTEGER, contact_form_found INTEGER,
  reservation_found INTEGER, line_found INTEGER, instagram_link_found INTEGER,
  facebook_link_found INTEGER, copyright_year INTEGER, http_status INTEGER,
  evidence TEXT, fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS scores (
  lead_id TEXT PRIMARY KEY, web_need_score INTEGER, web_need_level TEXT,
  reason_1 TEXT, reason_2 TEXT, reason_3 TEXT, lead_priority TEXT,
  recommended_dm_angle TEXT, recommended_sample TEXT, scored_at TEXT
);
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id TEXT NOT NULL, source_code TEXT NOT NULL, source_url TEXT, fetched_at TEXT,
  UNIQUE(lead_id, source_code, source_url)
);
CREATE TABLE IF NOT EXISTS crawl_jobs (
  job_id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL, key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
  attempts INTEGER DEFAULT 0, last_error TEXT, updated_at TEXT,
  UNIQUE(kind, key)
);
CREATE TABLE IF NOT EXISTS http_cache (
  cache_key TEXT PRIMARY KEY, url TEXT, final_url TEXT, status INTEGER,
  content_type TEXT, body_path TEXT, fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_contacts_value ON contacts(kind, value);
CREATE INDEX IF NOT EXISTS ix_websites_domain ON websites(domain);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def next_lead_id(con) -> str:
    row = con.execute("SELECT MAX(CAST(SUBSTR(lead_id,2) AS INTEGER)) FROM businesses").fetchone()
    return "L%07d" % ((row[0] or 0) + 1)


def upsert_business(con, rec: dict) -> str:
    """source_key 単位で登録（同じ入力を2回取り込んでも増えない）。lead_id を返す。"""
    row = con.execute("SELECT lead_id FROM businesses WHERE source_key=?", (rec["source_key"],)).fetchone()
    cols = ["business_name", "company_name", "industry", "sub_industry", "postal_code", "prefecture",
            "city", "address", "corporate_number", "staff_count", "seed_website_url"]
    if row:
        lead_id = row["lead_id"]
        sets = ", ".join(f"{c}=COALESCE(?, {c})" for c in cols)
        con.execute(f"UPDATE businesses SET {sets}, updated_at=? WHERE lead_id=?",
                    [rec.get(c) for c in cols] + [now(), lead_id])
    else:
        lead_id = next_lead_id(con)
        con.execute(
            f"INSERT INTO businesses (lead_id, source_key, {', '.join(cols)}, created_at, updated_at) "
            f"VALUES (?, ?, {', '.join('?' * len(cols))}, ?, ?)",
            [lead_id, rec["source_key"]] + [rec.get(c) for c in cols] + [now(), now()])
    return lead_id


def add_contact(con, lead_id, kind, value, display=None, phone_type=None,
                personal_suspect=0, source_code=None, source_url=None):
    if not value:
        return
    con.execute("INSERT OR IGNORE INTO contacts (lead_id, kind, value, display, phone_type, "
                "email_personal_suspect, source_code, source_url) VALUES (?,?,?,?,?,?,?,?)",
                (lead_id, kind, value, display, phone_type, int(personal_suspect), source_code, source_url))


def add_source(con, lead_id, source_code, source_url):
    con.execute("INSERT OR IGNORE INTO sources (lead_id, source_code, source_url, fetched_at) VALUES (?,?,?,?)",
                (lead_id, source_code, source_url, now()))


# ---- ジョブ（再開機能） ----
def ensure_job(con, kind, key):
    con.execute("INSERT OR IGNORE INTO crawl_jobs (kind, key, updated_at) VALUES (?,?,?)", (kind, key, now()))


def job_status(con, kind, key):
    row = con.execute("SELECT status FROM crawl_jobs WHERE kind=? AND key=?", (kind, key)).fetchone()
    return row["status"] if row else None


def set_job(con, kind, key, status, error=None):
    ensure_job(con, kind, key)
    con.execute("UPDATE crawl_jobs SET status=?, last_error=?, updated_at=?, "
                "attempts = attempts + CASE WHEN ?='RUNNING' THEN 1 ELSE 0 END WHERE kind=? AND key=?",
                (status, error, now(), status, kind, key))
    con.commit()


def reset_running(con) -> int:
    """前回途中で止まった RUNNING を PENDING に戻す（起動時に呼ぶ）。"""
    cur = con.execute("UPDATE crawl_jobs SET status='PENDING', updated_at=? WHERE status='RUNNING'", (now(),))
    con.commit()
    return cur.rowcount
