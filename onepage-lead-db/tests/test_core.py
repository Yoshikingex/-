import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from leaddb import db, dedup, export, score
from leaddb import extract as X
from leaddb import normalize as N
from leaddb.fetch import Fetcher, GuardViolation, Page, check_guard
from leaddb.sources import takken


class PhoneTest(unittest.TestCase):
    CASES = [
        ("049-257-4888", ("0492574888", "049-257-4888")),
        ("０４９－２５７－４８８８", ("0492574888", "049-257-4888")),
        ("03(1234)5678", ("0312345678", "03-1234-5678")),
        ("0312345678", ("0312345678", "03-1234-5678")),
        ("090-1234-5678", ("09012345678", "090-1234-5678")),
        ("09012345678", ("09012345678", "090-1234-5678")),
        ("0120-123-456", ("0120123456", "0120-123-456")),
        ("0800-123-4567", ("08001234567", "0800-123-4567")),
        ("+81 3-1234-5678", ("0312345678", "03-1234-5678")),
        ("0495-22-1234", ("0495221234", "0495-22-1234")),
        ("050-1234-5678", ("05012345678", "050-1234-5678")),
        ("123-4567", (None, None)),
        ("03-1234-56789", (None, None)),
        ("", (None, None)),
    ]

    def test_format(self):
        for raw, exp in self.CASES:
            with self.subTest(raw=raw):
                self.assertEqual(N.format_phone(raw), exp)

    def test_type(self):
        self.assertEqual(N.phone_type("09012345678"), "mobile")
        self.assertEqual(N.phone_type("05012345678"), "ip")
        self.assertEqual(N.phone_type("0120123456"), "freedial")
        self.assertEqual(N.phone_type("0492574888"), "fixed")

    def test_find_in_text(self):
        got = N.find_phones("TEL：049-257-4888　FAX：049-257-4889 郵便番号 350-0001 年 2024-01-01")
        self.assertEqual([d for d, _ in got], ["0492574888", "0492574889"])


class EmailTest(unittest.TestCase):
    def test_classify(self):
        cases = [
            ("info@example-dental.jp", ("info@example-dental.jp", True, False)),
            ("INFO@Shop.CO.JP", ("info@shop.co.jp", True, False)),
            ("contact@abc.com", ("contact@abc.com", True, False)),
            ("salon.hana@gmail.com", ("salon.hana@gmail.com", True, False)),
            ("taro.yamada@abc.co.jp", ("taro.yamada@abc.co.jp", False, True)),
            ("logo@2x.png", (None, False, False)),
            ("user@example.com", (None, False, False)),
            ("abc@sentry.io", (None, False, False)),
            ("not-an-email", (None, False, False)),
        ]
        for raw, exp in cases:
            with self.subTest(raw=raw):
                self.assertEqual(N.classify_email(raw), exp)

    def test_rank(self):
        emails = ["hello@gmail.com", "info@abc.jp", "tanaka@abc.jp"]
        self.assertEqual(sorted(emails, key=lambda e: N.email_rank(e, "abc.jp"))[0], "info@abc.jp")


class AddressTest(unittest.TestCase):
    def test_split(self):
        self.assertEqual(N.split_address("〒350-0001 埼玉県川越市新宿町１－１１－５"),
                         ("350-0001", "埼玉県", "川越市", "埼玉県川越市新宿町1-11-5"))
        self.assertEqual(N.split_address("東京都千代田区丸の内1-1")[1:3], ("東京都", "千代田区"))
        self.assertEqual(N.split_address("神奈川県横浜市中区山下町1")[2], "横浜市中区")
        self.assertEqual(N.split_address("群馬県吾妻郡草津町草津1")[2], "吾妻郡草津町")

    def test_norm(self):
        self.assertEqual(N.norm_address("川越市新宿町1丁目11番5号"), N.norm_address("川越市新宿町１－１１－５"))
        self.assertEqual(N.norm_name("株式会社 武藏野土地"), N.norm_name("武藏野土地(株)"))


class ExtractTest(unittest.TestCase):
    HTML = """<html><head><meta name="viewport" content="width=device-width"><meta property="og:title" content="x">
    </head><body><a href="tel:049-257-4888">電話</a><a href="https://www.instagram.com/hana_salon/">IG</a>
    <a href="https://instagram.com/p/ABC123/">post</a><a href="https://www.facebook.com/hana">fb</a>
    <a href="https://lin.ee/abc">LINE</a><a href="/company/">会社概要</a><a href="https://other.com/about">外部</a>
    <a href="mailto:info@hana.jp">mail</a><a href="https://beauty.hotpepper.jp/slnH000/">ご予約はこちら</a>
    <form><textarea></textarea></form><footer>© 2014-2025 HANA</footer></body></html>"""

    def test_parse(self):
        r = X.parse_page(self.HTML, "https://hana.jp/")
        self.assertEqual(r["tel_links"], [("0492574888", "049-257-4888")])
        self.assertEqual(r["instagram"], [("hana_salon", "https://www.instagram.com/hana_salon/")])
        self.assertEqual(r["subpages"], ["https://hana.jp/company/"])
        self.assertTrue(r["has_form"] and r["reservation"])
        self.assertEqual(r["line"], ["https://lin.ee/abc"])
        self.assertIn("info@hana.jp", r["emails"])

    def test_instagram_username(self):
        self.assertEqual(X.instagram_username("https://www.instagram.com/Hana_Salon/?hl=ja"), "hana_salon")
        self.assertIsNone(X.instagram_username("https://www.instagram.com/explore/tags/x/"))
        self.assertIsNone(X.instagram_username("https://example.com/instagram.com/abc"))

    def test_quality(self):
        q = X.site_quality(self.HTML, "https://hana.jp/", today=date(2026, 9, 30))
        self.assertEqual(q["copyright_year"], 2025)
        self.assertGreaterEqual(q["quality_score"], 66)
        old = ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"><meta charset="shift_jis"><center><font>a</font>'
               '<center><table width=1><table width=2><table bgcolor=x>© 2009')
        q2 = X.site_quality(old, "http://old.jp/", today=date(2026, 9, 30))
        self.assertEqual(q2["status"], "OLD")
        self.assertEqual(q2["quality_score"], 0)

    def test_pick_phone_prefers_tel_and_skips_fax(self):
        pages = [{"tel_links": [], "phones": [("0492574889", "049-257-4889"), ("0492574888", "049-257-4888")],
                  "_text": "TEL 049-257-4888 FAX 049-257-4889"}]
        self.assertEqual(X.pick_phone(pages), ("0492574888", "049-257-4888"))


class ScoreTest(unittest.TestCase):
    T = date(2026, 9, 30)

    def s(self, **kw):
        base = {"industry": "beauty", "phone_found": True}
        base.update(kw)
        return score.compute(base, today=self.T)

    def test_none_visual_instagram(self):
        r = self.s(website_status="NONE", instagram_found=True)
        self.assertEqual((r["web_need_score"], r["web_need_level"], r["lead_priority"]), (45, "LOW", "P1"))
        self.assertEqual(r["recommended_dm_angle"], "Instagram→予約導線")

    def test_old_site_full(self):
        r = self.s(website_status="OLD", quality_score=10, mobile_friendly=0, https_enabled=0,
                   contact_form_found=0, reservation_found=0, copyright_year=2015, domain="x.jp")
        self.assertEqual(r["web_need_score"], 85)  # 20+15+15+10+10+10+5
        self.assertEqual(r["web_need_level"], "HIGH")

    def test_medium_boundary(self):
        r = self.s(website_status="BASIC", quality_score=40, mobile_friendly=0, https_enabled=0,
                   contact_form_found=0, reservation_found=0, domain="x.jp", industry="dental")
        self.assertEqual((r["web_need_score"], r["web_need_level"]), (40, "LOW"))
        r = self.s(website_status="BASIC", quality_score=40, mobile_friendly=0, https_enabled=0,
                   contact_form_found=0, reservation_found=0, domain="x.jp")
        self.assertEqual((r["web_need_score"], r["web_need_level"]), (50, "MEDIUM"))

    def test_excellent_clamped(self):
        r = self.s(website_status="EXCELLENT", quality_score=95, mobile_friendly=1, https_enabled=1,
                   contact_form_found=1, chain=True)
        self.assertEqual(r["web_need_score"], 0)

    def test_unknown_gets_no_site_points(self):
        r = self.s(website_status="UNKNOWN", industry="real_estate")
        self.assertEqual(r["web_need_score"], 10)
        self.assertEqual(r["lead_priority"], "P5")

    def test_p4_and_reasons(self):
        r = self.s(website_status="NONE", industry="care")
        self.assertEqual(r["lead_priority"], "P4")
        self.assertEqual(r["reason_1"], "公式HPが見つからない")
        self.assertIsNone(r["reason_2"])

    def test_free_site(self):
        r = self.s(website_status="BASIC", quality_score=30, mobile_friendly=1, https_enabled=1,
                   contact_form_found=1, domain="hana.ameblo.jp")
        self.assertIn("無料ブログ・簡易サイトのみ", [r["reason_1"], r["reason_2"], r["reason_3"]])

    def test_levels(self):
        self.assertEqual([score.level(x) for x in (0, 49, 50, 69, 70, 100)],
                         ["LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH", "HIGH"])

    def test_sample_mapping_all_industries(self):
        for ind, (sample, angles) in score.INDUSTRY_SAMPLE.items():
            with self.subTest(ind=ind):
                self.assertIn(sample, score.SAMPLES)
                self.assertTrue(angles)
                self.assertEqual(self.s(industry=ind, website_status="GOOD")["recommended_sample"], sample)


class DbTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.con = db.connect(Path(self.tmp.name) / "t.db")

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def biz(self, key, name, addr, phone=None, src="S1"):
        lid = db.upsert_business(self.con, {"source_key": key, "business_name": name, "address": addr,
                                            "industry": "care", "prefecture": "埼玉県"})
        if phone:
            d, disp = N.format_phone(phone)
            db.add_contact(self.con, lid, "phone", d, disp, source_code=src)
        db.add_source(self.con, lid, src, "u")
        self.con.commit()
        return lid


class DedupTest(DbTestBase):
    def alive(self):
        return self.con.execute("SELECT COUNT(*) FROM businesses WHERE merged_into IS NULL").fetchone()[0]

    def test_upsert_idempotent(self):
        a = self.biz("S1:1", "A", "埼玉県川越市1-1")
        b = self.biz("S1:1", "A", "埼玉県川越市1-1")
        self.assertEqual(a, b)
        self.assertEqual(self.alive(), 1)

    def test_phone_cross_source_merges(self):
        self.biz("S1:1", "ひかり苑", "埼玉県川越市1-1", "049-111-2222", "S1")
        self.biz("S4:1", "別名", "埼玉県川越市9-9", "049-111-2222", "S4")
        self.assertEqual(dedup.run(self.con), 1)
        self.assertEqual(self.alive(), 1)

    def test_phone_same_registry_different_entity_kept(self):
        self.biz("S1:1", "ひかり苑デイ", "埼玉県川越市1-1", "049-111-2222")
        self.biz("S1:2", "ひかり訪問介護", "埼玉県川越市5-5", "049-111-2222")
        self.assertEqual(dedup.run(self.con), 0)

    def test_phone_same_registry_same_address_merges(self):
        self.biz("S1:1", "ひかり苑デイ", "埼玉県川越市1丁目1番", "049-111-2222")
        self.biz("S1:2", "ひかり訪問介護", "埼玉県川越市1-1", "049-111-2222")
        self.assertEqual(dedup.run(self.con), 1)

    def test_shared_phone_needs_address(self):
        for i in range(5):
            self.biz(f"S4:{i}", f"支店{i}", f"埼玉県川越市{i}-1", "0120-111-222", "S4" if i else "S1")
        self.assertEqual(dedup.run(self.con), 0)

    def test_name_address_merge_and_confidence(self):
        a = self.biz("S1:1", "株式会社みどり", "埼玉県川越市1-1", "049-111-2222", "S1")
        self.biz("S2:1", "みどり", "埼玉県川越市1丁目1番", None, "S2")
        self.assertEqual(dedup.run(self.con), 1)
        conf = self.con.execute("SELECT data_confidence FROM businesses WHERE lead_id=?", (a,)).fetchone()[0]
        self.assertEqual(conf, "HIGH")

    def test_instagram_merge(self):
        a = self.biz("S1:1", "A", "埼玉県1")
        b = self.biz("S2:1", "B", "埼玉県2")
        for lid in (a, b):
            self.con.execute("INSERT INTO social_accounts (lead_id, platform, username, confidence) VALUES (?,?,?,?)",
                             (lid, "instagram", "same_user", "HIGH"))
        self.assertEqual(dedup.run(self.con), 1)


class JobResumeTest(DbTestBase):
    def test_reset_running(self):
        db.set_job(self.con, "site", "L1", "RUNNING")
        db.set_job(self.con, "site", "L2", "COMPLETE")
        self.assertEqual(db.reset_running(self.con), 1)
        self.assertEqual(db.job_status(self.con, "site", "L1"), "PENDING")
        self.assertEqual(db.job_status(self.con, "site", "L2"), "COMPLETE")

    def test_attempts_counted(self):
        db.set_job(self.con, "site", "L1", "RUNNING")
        db.set_job(self.con, "site", "L1", "FAILED", "x")
        db.set_job(self.con, "site", "L1", "RUNNING")
        n = self.con.execute("SELECT attempts FROM crawl_jobs WHERE key='L1'").fetchone()[0]
        self.assertEqual(n, 2)


class FakeResp:
    def __init__(self, url, status=200, body=b"", headers=None):
        self.url, self.status_code, self.content = url, status, body
        self.headers = headers or {}


class FakeSession:
    def __init__(self, routes):
        self.routes, self.calls, self.headers = routes, [], {}

    def request(self, method, url, **kw):
        self.calls.append(url)
        status, body, headers = self.routes.get(url, (404, b"", {}))
        return FakeResp(url, status, body, headers)

    def get(self, url, **kw):
        return self.request("GET", url)


class FetchGuardTest(DbTestBase):
    def f(self, routes):
        return Fetcher(self.con, interval=0, backoff=[0, 0, 0], session=FakeSession(routes))

    def test_forbidden_hosts(self):
        with self.assertRaises(GuardViolation):
            check_guard("https://www.instagram.com/abc/")
        with self.assertRaises(GuardViolation):
            check_guard("https://www.google.com/search?q=x")
        check_guard("https://example.jp/")

    def test_robots_disallow(self):
        f = self.f({"https://a.jp/robots.txt": (200, b"User-agent: *\nDisallow: /private", {}),
                    "https://a.jp/ok": (200, b"ok", {})})
        self.assertEqual(f.get("https://a.jp/ok").body, b"ok")
        with self.assertRaises(GuardViolation):
            f.get("https://a.jp/private/x")

    def test_robots_404_allows_and_5xx_blocks(self):
        f = self.f({"https://b.jp/x": (200, b"x", {}), "https://c.jp/robots.txt": (503, b"", {})})
        self.assertTrue(f.allowed("https://b.jp/x"))
        self.assertFalse(f.allowed("https://c.jp/x"))

    def test_redirect_to_instagram_blocked_before_request(self):
        s = FakeSession({"https://d.jp/": (302, b"", {"Location": "https://www.instagram.com/d/"})})
        f = Fetcher(self.con, interval=0, backoff=[0, 0, 0], session=s)
        with self.assertRaises(GuardViolation):
            f.get("https://d.jp/")
        self.assertFalse(any("instagram.com" in c for c in s.calls))

    def test_cache_hit_no_network(self):
        f = self.f({"https://e.jp/p": (200, b"hello", {})})
        f.get("https://e.jp/p")
        before = len(f.s.calls)
        self.assertTrue(f.get("https://e.jp/p").from_cache)
        self.assertEqual(len(f.s.calls), before)


class TakkenParseTest(unittest.TestCase):
    DETAIL = ("<table><tr><th>免許証番号</th><td>埼玉県知事免許 (17)第000001号</td></tr><tr><th>免許の有効期間</th><td>x</td></tr>"
              "<tr><th>商号又は名称</th><td>ﾑｻｼﾉﾄﾁｶﾌﾞｼｷｶﾞｲｼﾔ<br>武藏野土地株式会社</td></tr><tr><th>代表者の氏名</th><td>ｱﾗｲ 新井</td></tr>"
              "<tr><th>主たる事務所の<br>所在地</th><td>埼玉県川越市新宿町１－１１－５</td></tr><tr><th>総従事者数</th><td>5 人</td></tr>"
              "<tr><th>電話番号</th><td>049-257-4888</td></tr><tr><th>兼業</th><td>1 不動産管理業</td></tr></table>")

    def test_detail(self):
        d = takken.parse_detail(self.DETAIL)
        self.assertEqual(d["name"], "武藏野土地株式会社")
        self.assertEqual(d["phone"], "049-257-4888")
        self.assertEqual(d["staff"], 5)
        self.assertEqual(d["address"], "埼玉県川越市新宿町１－１１－５")
        self.assertEqual(d["kengyo"], ["不動産管理業"])
        self.assertNotIn("新井", str(d))  # 代表者名は保持しない

    def test_list(self):
        html = ("<tr><td>1</td><td>埼玉県</td><td>(17)第000001号</td><td><a onclick=\"js_ShowDetail('11000001')\">"
                "武藏野土地株式会社</a></td><td>新井</td><td>本店</td><td>埼玉県川越市新宿町１－１１－５</td></tr>")
        self.assertEqual(takken.parse_list(html), [("11000001", "武藏野土地株式会社", "埼玉県川越市新宿町１－１１－５")])


class ExportTest(DbTestBase):
    def test_dm_sort(self):
        rows = [{"website_status": "OLD", "web_need_score": 90, "lead_id": "L2"},
                {"website_status": "NONE", "web_need_score": 50, "lead_id": "L3"},
                {"website_status": "NONE", "web_need_score": 60, "lead_id": "L1"}]
        self.assertEqual([r["lead_id"] for r in sorted(rows, key=export.dm_sort_key)], ["L1", "L3", "L2"])


if __name__ == "__main__":
    unittest.main()
