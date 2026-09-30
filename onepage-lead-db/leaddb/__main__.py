"""CLI:  python -m leaddb <command>

  stage --n 1000     段階テスト。累計 n 件になるまで取り込み→巡回→統合→採点→出力を実行
                     配分: 不動産30%（7都県に均等）/ 歯科25% / クリニック25% / 介護20%
  crawl              未巡回の公式サイトを巡回（途中再開可）
  retry-sites        到達不能/取得不可だったサイトを再巡回の対象に戻す
  repair-merges      旧方式の統合（行を移していた）を取り消す一回限りの修復
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


def stage_targets(n):
    """累計目標。端数は介護に寄せて合計を n に合わせる。"""
    t = {"real_estate": n * 30 // 100, "dental": n * 25 // 100, "clinic": n * 25 // 100}
    t["care"] = n - sum(t.values())
    return t


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
    sub.add_parser("crawl")
    sub.add_parser("retry-sites")
    sub.add_parser("repair-merges")
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
        t = stage_targets(a.n)
        got = {"real_estate": 0}
        for i, pref in enumerate(config.PREF_ORDER):
            per = t["real_estate"] // 7 + (1 if i < t["real_estate"] % 7 else 0)
            got["real_estate"] += takken.ingest_takken(con, f, pref=pref, target=per)
        got["dental"] = opendata.ingest_iryou(con, f, "dental", target=t["dental"])
        got["clinic"] = opendata.ingest_iryou(con, f, "clinic", target=t["clinic"])
        got["care"] = opendata.ingest_kaigo(con, f, target=t["care"])
        log.info("ingested %s", got)
        crawled = crawl.crawl_all(con, f)
        res = finalize(con)
        res.update({"ingested": got, "crawled": crawled, "fetch": f.stats})
        print(json.dumps(res, ensure_ascii=False, indent=1))
    elif a.cmd == "crawl":
        print(json.dumps({"crawled": crawl.crawl_all(con, f), "fetch": f.stats}, ensure_ascii=False))
    elif a.cmd == "retry-sites":
        print(json.dumps({"reset": crawl.retry_sites(con)}, ensure_ascii=False))
    elif a.cmd == "repair-merges":
        from . import repair
        print(json.dumps(repair.unmerge_all(con), ensure_ascii=False))
    elif a.cmd == "finalize":
        print(json.dumps(finalize(con), ensure_ascii=False, indent=1))
    elif a.cmd == "stats":
        print(json.dumps(export.stats(con), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
