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
from leaddb.fetch import Fetcher, GuardViolation, RobotsUnreachable, check_guard
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


class UrlTest(unittest.TestCase):
    def test_clean_url(self):
        self.assertEqual(N.clean_url("http://www.shibuya‐dsc.jp"), "http://www.shibuya-dsc.jp")
        self.assertEqual(N.clean_url("ｗｗｗ.abc.jp"), "http://www.abc.jp")
        self.assertIsNone(N.clean_url("なし"))
        self.assertEqual(N.domain_of("https://www.ABC.co.jp/x"), "abc.co.jp")


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

    def _ig(self, lid, user="same_user"):
        self.con.execute("INSERT INTO social_accounts (lead_id, platform, username, confidence) VALUES (?,?,?,?)",
                         (lid, "instagram", user, "HIGH"))

    def test_instagram_chain_branches_not_merged(self):
        a = self.biz("S1:1", "ツクイ練馬春日町", "東京都練馬区春日町2-9-33")
        b = self.biz("S1:2", "ツクイ恋ヶ窪", "東京都国分寺市西恋ヶ窪3-6-10")
        self._ig(a); self._ig(b)
        self.assertEqual(dedup.run(self.con), 0)

    def test_instagram_same_entity_merged_without_moving_rows(self):
        a = self.biz("S1:1", "みどり苑", "埼玉県川越市1-1", "049-111-2222", "S1")
        b = self.biz("S2:1", "みどり苑", "埼玉県川越市9-9", None, "S2")
        self._ig(a); self._ig(b)
        db.add_contact(self.con, b, "email", "info@midori.jp", source_code="S8")
        self.assertEqual(dedup.run(self.con), 1)
        # 子の行はそのまま（取り消し可能）で、出力ではまとめて見える
        self.assertEqual(self.con.execute("SELECT lead_id FROM contacts WHERE kind='email'").fetchone()[0], b)
        self.assertEqual(dedup.group_ids(self.con, a), [a, b])
        rows = [r for r in export.build_rows(self.con) if r["lead_id"] == a]
        self.assertEqual(rows[0]["email"], "info@midori.jp")
        self.assertEqual(rows[0]["phone"], "049-111-2222")

    def test_merge_depth_one(self):
        a = self.biz("S1:1", "A", "埼玉県1")
        b = self.biz("S1:2", "B", "埼玉県2")
        c = self.biz("S1:3", "C", "埼玉県3")
        dedup._merge(self.con, b, c)
        dedup._merge(self.con, a, b)
        self.assertEqual({r[0] for r in self.con.execute("SELECT merged_into FROM businesses WHERE merged_into IS NOT NULL")}, {a})

    def test_instagram_shared_by_5_is_chain(self):
        ids = [self.biz(f"S1:{i}", f"店{i}", f"埼玉県{i}", f"049-111-{2220 + i}") for i in range(5)]
        for i in ids:
            self._ig(i, "chain_hq")
            self.con.execute("INSERT INTO websites (lead_id, status, quality_score, https_enabled, mobile_friendly) "
                             "VALUES (?, 'OLD', 10, 0, 0)", (i,))
        score.score_all(self.con)
        got = {r[0] for r in self.con.execute("SELECT web_need_score FROM scores")}
        # OLD20+スマホ15+SSL15+極端に古い10+導線なし10+IG&OLD10-チェーン15 = 65（care は非ビジュアル業種）
        self.assertEqual(got, {65})


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

    def test_robots_connection_error_is_unreachable(self):
        class Boom(FakeSession):
            def request(self, method, url, **kw):
                self.calls.append(url)
                raise __import__("requests").ConnectionError("x")
        f = Fetcher(self.con, interval=0, backoff=[0, 0, 0], session=Boom({}))
        with self.assertRaises(RobotsUnreachable):
            f.get("https://down.jp/")

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


class StageTest(unittest.TestCase):
    def test_targets_sum(self):
        from leaddb.__main__ import stage_targets
        for n in (100, 1000, 10000, 7):
            t = stage_targets(n)
            self.assertEqual(sum(t.values()), n)
        self.assertEqual(stage_targets(1000), {"real_estate": 300, "dental": 250, "clinic": 250, "care": 200})

    def test_spread_pages(self):
        self.assertEqual(takken.spread_pages(127, 4), [1, 32, 64, 96])
        self.assertEqual(takken.spread_pages(2, 5), [1, 2])
        self.assertEqual(takken.spread_pages(0, 3), [])


class TakkenPagingTest(DbTestBase):
    def test_select_page_sends_search_fields(self):
        hidden = ('<input id="resultCount" name="resultCount" type="hidden" value="500"/>'
                  '<input id="pageCount" name="pageCount" type="hidden" value="10"/>')

        def row(k):
            return (f"<tr><td>1</td><td>x</td><td>n</td><td><a onclick=\"js_ShowDetail('{k}')\">A{k}</a></td>"
                    f"<td>r</td><td>本店</td><td>群馬県前橋市1-1</td></tr>")

        class FakeFetcher:
            def __init__(self):
                self.posts = []

            def post(self, url, data, **kw):
                self.posts.append(dict(data))
                if url == takken.DETAIL:
                    body = TakkenParseTest.DETAIL.replace("049-257-4888", "027-111-" + data["sv_licenseNo"][-4:])
                elif data["CMD"] == "search":
                    body = hidden + row("10000001")
                else:  # 検索条件がなければ実サイト同様 0 件
                    body = hidden + (row("1000" + data["pageListNo1"].zfill(4)) if data.get("kenCode") == "10" else "")
                return Page(url, url, 200, "", body.encode("cp932", "replace"))

        from leaddb.fetch import Page
        ff = FakeFetcher()
        got = takken.ingest_takken(self.con, ff, pref="群馬県", target=3, per_page=1)
        self.assertEqual(got, 3)
        sel = [d for d in ff.posts if d.get("CMD") == "selectPage"]
        self.assertTrue(sel and all(d["kenCode"] == "10" for d in sel))


class PickNewTest(DbTestBase):
    def test_counts_existing_toward_target(self):
        from leaddb.sources import opendata
        rows = [{"ID": str(i), "_pref": "東京都"} for i in range(100)]
        self.biz("S2:dental:5", "x", "a")
        self.biz("S2:dental:7", "y", "b")
        got = opendata.pick_new(self.con, rows, 10, lambda r: f"S2:dental:{r['ID']}")
        self.assertEqual(len(got), 8)
        self.assertFalse({"5", "7"} & {r["ID"] for r in got})


class ConnRetryTest(DbTestBase):
    def test_connection_error_tries_twice(self):
        class Boom(FakeSession):
            def request(self, method, url, **kw):
                self.calls.append(url)
                raise __import__("requests").ConnectionError("x")
        s = Boom({})
        f = Fetcher(self.con, interval=0, backoff=[0, 0, 0], session=s)
        with self.assertRaises(Exception):
            f._request("GET", "https://x.jp/", None, use_robots=False)
        self.assertEqual(len(s.calls), 2)


class IgConfTest(unittest.TestCase):
    def test_classify(self):
        from leaddb import igconf as I
        cases = [
            ("ito.ryunoshin", "soleado.jp", ("ソレアード久喜",), "LOW"),         # 職員個人らしい
            ("kuonen.abiko", "kuonen-abiko.jp", ("くおん苑",), "HIGH"),          # ドメインと一致
            ("jalakaigo", "jala.co.jp", ("福寿",), "HIGH"),
            ("tokorozawa_kitano_dental", "dental-kitano.com", (), "HIGH"),
            ("hana_salon_official", "abc.jp", (), "MEDIUM"),                    # 事業用の語
            ("hanako_1990", "abc.jp", (), "MEDIUM"),                            # 判断材料なし
            ("taro.yamada", "yamada-koumuten.jp", ("山田工務店",), "HIGH"),     # 屋号と一致すれば個人名形でも可
            ("SHOP.Tanaka", None, (), "MEDIUM"),
            ("dr_oshige", "seaclinic-beauty.com", (), "MEDIUM"),                 # 院長本人らしい
            ("sugo.seikei", "north-oak-ortho-clinic.com", (), "MEDIUM"),
        ]
        for u, d, names, exp in cases:
            with self.subTest(u=u):
                self.assertEqual(I.classify(u, d, names), exp)


class ChainTest(DbTestBase):
    def setUp(self):
        super().setUp()
        from leaddb import config as C
        self.raw = Path(self.tmp.name) / "raw"
        self.raw.mkdir()
        self.p = mock.patch.object(C, "RAW", self.raw)
        self.p.start()
        with open(self.raw / "jigyosho_150_all_1.csv", "w", encoding="utf-8-sig") as f:
            f.write("都道府県名,法人番号\n" + "東京都,111\n" * 5 + "東京都,222\n" * 4 + "大阪府,222\n" * 3)

    def tearDown(self):
        self.p.stop()
        super().tearDown()

    def add(self, key, **kw):
        rec = {"source_key": key, "business_name": kw.pop("name", key), "industry": "care"}
        rec.update(kw)
        return db.upsert_business(self.con, rec)

    def reasons(self):
        return {r[0]: r[1] for r in self.con.execute("SELECT source_key, exclude_reason FROM businesses")}

    def test_rules(self):
        from leaddb import chains
        self.add("S1:a", corporate_number="111")
        self.add("S1:b", corporate_number="222")          # 関東では4施設 → 対象のまま
        self.add("S4:takken:1", staff_count=30)
        self.add("S4:takken:2", staff_count=29)
        self.con.commit()
        self.assertEqual(chains.compute(self.con), 2)
        r = self.reasons()
        self.assertIn("5施設", r["S1:a"])
        self.assertIsNone(r["S1:b"])
        self.assertIn("30人", r["S4:takken:1"])
        self.assertIsNone(r["S4:takken:2"])

    def test_corp_key(self):
        from leaddb import chains
        self.assertEqual(chains.corp_key("医療法人社団　善仁会 ○○クリニック"), "医療法人社団善仁会")
        self.assertIsNone(chains.corp_key("やまだ歯科医院"))

    def test_excluded_rows_leave_main_outputs(self):
        from leaddb import chains, config as C
        a = self.add("S1:a", corporate_number="111")
        b = self.add("S1:b", corporate_number="999")
        for i in (a, b):
            db.add_contact(self.con, i, "phone", "0312345678" if i == a else "0312345679", source_code="S1")
        self.con.commit()
        chains.compute(self.con)
        with mock.patch.object(C, "OUT", Path(self.tmp.name) / "out"):
            rows, counts = export.export_all(self.con)
            st = export.stats(self.con, rows)
        self.assertEqual((counts["all_leads.csv"], counts["excluded_chain_large.csv"]), (1, 1))
        self.assertEqual(st["candidates_total"], st["excluded_chain_large"] + st["leads_with_phone"] + st["missing_phone"])


class ReviewTest(DbTestBase):
    def lead(self, key, user, score_status="OLD"):
        lid = db.upsert_business(self.con, {"source_key": key, "business_name": key, "industry": "construction",
                                            "prefecture": "埼玉県"})
        db.add_contact(self.con, lid, "phone", "049" + str(abs(hash(key)))[:7], source_code="S1")
        self.con.execute("INSERT INTO social_accounts (lead_id, platform, url, username, confidence, source) "
                         "VALUES (?, 'instagram', ?, ?, 'MEDIUM', 'opendata_url')", (lid, f"https://www.instagram.com/{user}/", user))
        self.con.execute("INSERT INTO websites (lead_id, status, quality_score, https_enabled, mobile_friendly, "
                         "domain) VALUES (?, ?, 10, 0, 0, 'x.jp')", (lid, score_status))
        self.con.commit()
        return lid

    def write_csv(self, rows, enc="cp932"):
        from leaddb import review
        path = Path(self.tmp.name) / "filled.csv"
        cols = ["lead_id", "instagram_username"] + list(review.COLS.values())
        with open(path, "w", encoding=enc, newline="") as f:
            w = __import__("csv").writer(f)
            w.writerow(cols)
            w.writerows(rows)
        return path

    def test_yn_and_verdict(self):
        from leaddb import review as R
        self.assertEqual([R.yn(x) for x in ("Y", "はい", "○", "n", "×", "", "たぶん")], ["Y", "Y", "Y", "N", "N", None, None])
        self.assertEqual(R.verdict({"dm_ok": "Y", "is_business": "N", "is_owner": "Y"}), "CONFIRMED")
        self.assertEqual(R.verdict({"dm_ok": "N", "is_business": "Y", "is_owner": "Y"}), "REJECTED")
        self.assertEqual(R.verdict({"dm_ok": None, "is_business": "N", "is_owner": None}), "REJECTED")
        self.assertIsNone(R.verdict({"dm_ok": None, "is_business": "Y", "is_owner": None}))

    def test_import_apply_export_roundtrip(self):
        from leaddb import review, config as C
        a = self.lead("S9:a", "koumuten_a")
        b = self.lead("S9:b", "koumuten_b")
        c = self.lead("S9:c", "koumuten_c")
        path = self.write_csv([[a, "koumuten_a", "Y", "Y", "Y", "2026/8", "Y", "社長本人"],
                               [b, "koumuten_b", "N", "", "", "", "", ""],
                               [c, "koumuten_c", "", "", "", "", "", ""],
                               ["L9999999", "nobody", "Y", "", "", "", "Y", ""]])
        st = review.import_file(self.con, path)
        self.assertEqual(st, {"rows": 4, "imported": 2, "skipped_blank": 1, "unknown_lead": 1})
        self.assertEqual(review.apply(self.con), {"CONFIRMED": 1, "REJECTED": 1})
        score.score_all(self.con)
        with mock.patch.object(C, "OUT", Path(self.tmp.name) / "out"):
            rows, counts = export.export_all(self.con)
            dm = list(__import__("csv").DictReader(open(Path(self.tmp.name) / "out" / "instagram_dm_targets.csv",
                                                        encoding="utf-8-sig")))
            rv = list(__import__("csv").DictReader(open(Path(self.tmp.name) / "out" / "instagram_review.csv",
                                                        encoding="utf-8-sig")))
        self.assertEqual([r["instagram_username"] for r in dm][0], "koumuten_a")   # 確認済みが先頭
        self.assertNotIn("koumuten_b", [r["instagram_username"] for r in dm])     # 却下は除外
        got = {r["instagram_username"]: r for r in rv}
        self.assertEqual(got["koumuten_a"]["確認_最終投稿年月"], "2026-08")       # 記入内容を引き継ぐ
        self.assertEqual(got["koumuten_a"]["メモ"], "社長本人")
        self.assertEqual(got["koumuten_b"]["instagram_confidence"], "REJECTED")


class ZehTest(DbTestBase):
    def test_select_and_ingest(self):
        from leaddb.sources import zeh
        csvtext = ("\ufeff事業者名,ZEHビルダー登録番号,登録名称（屋号）,対応可能エリア,ホームページ,電話番号\n"
                   "株式会社山田工務店,B1,山田工務店,埼玉県;東京都,https://yamada-k.jp/results.html,049-111-2222\n"
                   "全国ハウス株式会社,B2,全国ハウス,北海道;青森県;東京都;大阪府,https://zenkoku.jp/,03-1111-2222\n"
                   "大阪工務店,B3,大阪工務店,大阪府,https://osaka.jp/,06-1111-2222\n")

        class F:
            def get(self, url):
                return Page(url, url, 200, "text/html", csvtext.encode("utf-8"))
        from leaddb.fetch import Page
        self.assertEqual(zeh.ingest_zeh(self.con, F()), 1)
        b = self.con.execute("SELECT * FROM businesses").fetchone()
        self.assertEqual((b["business_name"], b["industry"], b["prefecture"], b["service_area"], b["seed_website_url"]),
                         ("山田工務店", "construction", None, "埼玉県;東京都", "https://yamada-k.jp/"))
        self.assertEqual(self.con.execute("SELECT display FROM contacts").fetchone()[0], "049-111-2222")


class MigrationTest(unittest.TestCase):
    def test_adds_columns_to_old_db(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "old.db"
            con = sqlite3.connect(path)
            con.execute("CREATE TABLE businesses (lead_id TEXT PRIMARY KEY, source_key TEXT UNIQUE NOT NULL)")
            con.execute("INSERT INTO businesses VALUES ('L1','S1:1')")
            con.commit(); con.close()
            con = db.connect(path)
            cols = {r[1] for r in con.execute("PRAGMA table_info(businesses)")}
            self.assertTrue({"chain_size", "exclude_reason", "service_area"} <= cols)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM businesses").fetchone()[0], 1)
            con.close()


class ExportTest(DbTestBase):
    def test_dm_sort(self):
        rows = [{"website_status": "OLD", "web_need_score": 90, "lead_id": "L2"},
                {"website_status": "NONE", "web_need_score": 50, "lead_id": "L3"},
                {"website_status": "NONE", "web_need_score": 60, "lead_id": "L1"}]
        self.assertEqual([r["lead_id"] for r in sorted(rows, key=export.dm_sort_key)], ["L1", "L3", "L2"])


if __name__ == "__main__":
    unittest.main()
