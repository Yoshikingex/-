"""HTTP取得。robots.txt 順守・ホスト単位のレート制限・キャッシュ・指数バックオフ。"""
import gzip
import hashlib
import logging
import re
import time
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urlsplit

import requests

from . import config
from .db import now

log = logging.getLogger("leaddb.fetch")


class GuardViolation(Exception):
    """G2/G3/G5 に触れるアクセスを試みた。"""


class RobotsUnreachable(GuardViolation):
    """robots.txt が接続エラー/5xxで取れず、安全側で取得を見送った（サイト到達不能の可能性）。"""


@dataclass
class Page:
    url: str
    final_url: str
    status: int
    content_type: str
    body: bytes
    from_cache: bool = False

    @property
    def text(self) -> str:
        return decode_html(self.body, self.content_type)


def decode_html(body: bytes, content_type: str = "") -> str:
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    enc = m.group(1) if m else None
    if not enc:
        m = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
        enc = m.group(1).decode("ascii", "ignore") if m else None
    enc = (enc or "utf-8").lower()
    if enc in ("shift_jis", "sjis", "x-sjis", "shift-jis"):
        enc = "cp932"
    try:
        return body.decode(enc, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def check_guard(url: str) -> None:
    host = (urlsplit(url).hostname or "").lower()
    if any(host == s or host.endswith("." + s) for s in config.FORBIDDEN_HOST_SUFFIXES):
        raise GuardViolation(f"forbidden host: {host}")
    if any(url.startswith(p) for p in config.FORBIDDEN_URL_PREFIXES):
        raise GuardViolation(f"forbidden url: {url}")


class Fetcher:
    def __init__(self, con, interval=None, backoff=None, session=None):
        self.con = con
        self.interval = config.PER_HOST_INTERVAL if interval is None else interval
        self.backoff = config.BACKOFF if backoff is None else backoff
        self.s = session or requests.Session()
        self.s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ja,en;q=0.5"})
        self._last = {}
        self._robots = {}
        self._robots_unreachable = set()
        self.stats = {"network": 0, "cache": 0, "robots_block": 0, "errors": 0}
        config.CACHE.mkdir(parents=True, exist_ok=True)

    # ---- robots.txt ----
    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            rp = robotparser.RobotFileParser()
            rp.allow_all = True
            self._robots[base] = rp  # robots.txt 自身のリダイレクトで再帰しないよう仮登録
            try:
                page = self._request("GET", base + "/robots.txt", None, use_robots=False)
                if page.status >= 500:
                    rp.allow_all, rp.disallow_all = False, True  # RFC 9309: サーバーエラーは全拒否
                    self._robots_unreachable.add(base)
                elif page.status >= 400:
                    pass                                          # 404 等は制限なし
                else:
                    rp.allow_all = False
                    rp.parse(page.body.decode("utf-8", "replace").splitlines())
            except (requests.RequestException, GuardViolation):
                rp.allow_all, rp.disallow_all = False, True      # 取れないときは安全側
                self._robots_unreachable.add(base)
        ok = rp.can_fetch(config.USER_AGENT, url)
        if not ok:
            self.stats["robots_block"] += 1
        return ok

    # ---- 取得 ----
    def get(self, url, **kw) -> Page:
        return self._request("GET", url, None, **kw)

    def post(self, url, data: dict, **kw) -> Page:
        return self._request("POST", url, data, **kw)

    def _cache_key(self, method, url, data):
        body = "&".join(f"{k}={v}" for k, v in sorted((data or {}).items()))
        return hashlib.sha1(f"{method} {url} {body}".encode()).hexdigest()

    def _request(self, method, url, data, use_robots=True, use_cache=True) -> Page:
        check_guard(url)
        key = self._cache_key(method, url, data)
        if use_cache:
            row = self.con.execute("SELECT * FROM http_cache WHERE cache_key=?", (key,)).fetchone()
            if row:
                self.stats["cache"] += 1
                body = gzip.decompress((config.CACHE / row["body_path"]).read_bytes())
                return Page(url, row["final_url"], row["status"], row["content_type"] or "", body, True)
        if use_robots and not self.allowed(url):
            p = urlsplit(url)
            if f"{p.scheme}://{p.netloc}" in self._robots_unreachable:
                raise RobotsUnreachable(f"robots.txt unreachable: {url}")
            raise GuardViolation(f"robots.txt disallow: {url}")
        host = urlsplit(url).netloc
        last_err = None
        for attempt in range(config.MAX_RETRIES):
            wait = self.interval - (time.monotonic() - self._last.get(host, -1e9))
            if wait > 0:
                time.sleep(wait)
            self._last[host] = time.monotonic()
            try:
                self.stats["network"] += 1
                r = self._follow(method, url, data)
                if r.status_code in (429, 503) and attempt < config.MAX_RETRIES - 1:
                    log.warning("HTTP %s %s -> backoff %ss", r.status_code, url, self.backoff[attempt])
                    time.sleep(self.backoff[attempt])
                    continue
                page = Page(url, r.url, r.status_code, r.headers.get("Content-Type", ""), r.content)
                if use_cache and r.status_code < 500:
                    self._store(key, page)
                log.info("%s %s %s %dB", method, r.status_code, url, len(r.content))
                return page
            except requests.RequestException as e:
                last_err = e
                self.stats["errors"] += 1
                log.warning("request error %s (%s) attempt %d", url, type(e).__name__, attempt + 1)
                if attempt >= config.CONN_RETRIES - 1:
                    break  # 接続エラー（DNS/SSL/切断）は長く待っても直らないことが多い → 早めに打ち切る
                time.sleep(min(self.backoff[attempt], config.CONN_RETRY_WAIT))
        raise last_err or requests.RequestException(f"failed: {url}")

    def _follow(self, method, url, data, hops=5):
        """リダイレクトを自前で辿り、遷移先ごとに G2/G3 と robots.txt を先に検査する。"""
        r = self.s.request(method, url, data=data, timeout=config.TIMEOUT, allow_redirects=False)
        for _ in range(hops):
            if r.status_code not in (301, 302, 303, 307, 308) or "Location" not in r.headers:
                return r
            nxt = requests.compat.urljoin(r.url, r.headers["Location"])
            check_guard(nxt)
            if not self.allowed(nxt):
                raise GuardViolation(f"robots.txt disallow (redirect): {nxt}")
            host = urlsplit(nxt).netloc
            wait = self.interval - (time.monotonic() - self._last.get(host, -1e9))
            if wait > 0:
                time.sleep(wait)
            self._last[host] = time.monotonic()
            if r.status_code in (307, 308):
                r = self.s.request(method, nxt, data=data, timeout=config.TIMEOUT, allow_redirects=False)
            else:
                r = self.s.get(nxt, timeout=config.TIMEOUT, allow_redirects=False)
        return r

    def _store(self, key, page: Page):
        path = f"{key[:2]}/{key}.gz"
        (config.CACHE / key[:2]).mkdir(parents=True, exist_ok=True)
        (config.CACHE / path).write_bytes(gzip.compress(page.body))
        self.con.execute("INSERT OR REPLACE INTO http_cache VALUES (?,?,?,?,?,?,?)",
                         (key, page.url, page.final_url, page.status, page.content_type, path, now()))
        self.con.commit()

    def download(self, url, dest) -> None:
        """大きな公開データファイルの取得（既にあれば再取得しない）。"""
        check_guard(url)
        if dest.exists() and dest.stat().st_size > 0:
            return
        if not self.allowed(url):
            raise GuardViolation(f"robots.txt disallow: {url}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.stats["network"] += 1
        with self.s.get(url, timeout=120, stream=True) as r:
            r.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
            tmp.replace(dest)
        log.info("downloaded %s -> %s (%d B)", url, dest.name, dest.stat().st_size)
