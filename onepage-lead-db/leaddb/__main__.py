"""CLI:  python -m leaddb <command>

  stage --n 100      段階テスト（宅建:歯科:介護 ≒ 1/3ずつ）を取り込み→巡回→統合→採点→出力まで実行
  crawl              未巡回の公式サイトを巡回（途中再開可）
  finalize           統合→採点→CSV出力→集計→ダッシュボード
  stats              集計をJSONで表示
"""
import argparse
import json
import logging

from . import config, crawl, db, dedup, export, score
from .fetch import Fetcher
from .sources import opendata, takken

log = logging.getLogger("leaddb")


def finalize(con):
    merged = dedup.run(con)
    scored = score.score_all(con)
    rows, counts = export.export_all(con)
    st = export.stats(con, rows)
    export.dashboard(st)
    return {"merged": merged, "scored": scored, "files": counts, "stats": st}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="leaddb")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("stage")
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--takken-pref", default="埼玉県")
    sub.add_parser("crawl")
    sub.add_parser("finalize")
    sub.add_parser("stats")
    a = ap.parse_args(argv)

    config.setup_logging()
    con = db.connect(config.DB_PATH)
    reset = db.reset_running(con)
    if reset:
        log.warning("resume: %d RUNNING jobs reset to PENDING", reset)
    f = Fetcher(con)
    if a.cmd == "stage":
        n_re = a.n // 3 + a.n % 3
        n_dn = a.n // 3
        n_cr = a.n // 3
        got = {"real_estate": takken.ingest_takken(con, f, pref=a.takken_pref, limit=n_re),
               "dental": opendata.ingest_iryou(con, f, "dental", limit=n_dn),
               "care": opendata.ingest_kaigo(con, f, limit=n_cr)}
        log.info("ingested %s", got)
        crawled = crawl.crawl_all(con, f)
        res = finalize(con)
        res.update({"ingested": got, "crawled": crawled, "fetch": f.stats})
        print(json.dumps(res, ensure_ascii=False, indent=1))
    elif a.cmd == "crawl":
        print(json.dumps({"crawled": crawl.crawl_all(con, f), "fetch": f.stats}, ensure_ascii=False))
    elif a.cmd == "finalize":
        print(json.dumps(finalize(con), ensure_ascii=False, indent=1))
    elif a.cmd == "stats":
        print(json.dumps(export.stats(con), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
