"""CLI:  python -m leaddb <command>

  stage --n 1000     段階テスト。累計 n 件になるまで取り込み→巡回→統合→採点→出力を実行
                     配分: 不動産30%（7都県に均等）/ 歯科25% / クリニック25% / 介護20%
  ingest-zeh [--scope kanto|nationwide] [--max-areas 3] [--limit N]
                     SII ZEHビルダー一覧（地元工務店＝営業エリアが max-areas 都道府県以内）を取り込む
  ingest-opendata --kind dental|clinic|care [--scope kanto|nationwide] [--require-url] [--exclude-chain] [--limit N]
                     厚労省オープンデータ（歯科・クリニック・介護）を取り込む
  crawl [--workers 8] [--max-minutes 110] [--until-instagram N]
                     未巡回の公式サイトを巡回（途中再開可。別ホストを並列、同一ホストは1本・3秒間隔）
  retry-sites        到達不能/取得不可だったサイトを再巡回の対象に戻す
  repair-merges      旧方式の統合（行を移していた）を取り消す一回限りの修復
  import-review --file PATH   Instagram目視確認の記入済みCSVを取り込む（その後 finalize で反映）
  finalize           統合→採点→CSV出力→集計→ダッシュボード
  stats              集計をJSONで表示
"""
import argparse
import json
import logging

from . import chains, config, crawl, db, dedup, export, igconf, review, score
from .fetch import Fetcher
from .sources import opendata, takken, zeh

log = logging.getLogger("leaddb")


def stage_targets(n):
    """累計目標。端数は介護に寄せて合計を n に合わせる。"""
    t = {"real_estate": n * 30 // 100, "dental": n * 25 // 100, "clinic": n * 25 // 100}
    t["care"] = n - sum(t.values())
    return t


def finalize(con):
    merged = dedup.run(con)
    ig = igconf.reclassify(con)
    ig.update(review.apply(con))  # 人の確認結果は自動判定より優先
    excluded = chains.compute(con)
    scored = score.score_all(con)
    rows, counts = export.export_all(con)
    st = export.stats(con, rows)
    export.dashboard(st)
    return {"merged": merged, "instagram_confidence": ig, "excluded_chain_large": excluded, "scored": scored,
            "files": counts, "stats": st}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="leaddb")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("stage")
    p.add_argument("--n", type=int, default=100)
    pz = sub.add_parser("ingest-zeh")
    pz.add_argument("--limit", type=int, default=None)
    pz.add_argument("--scope", choices=["kanto", "nationwide"], default="kanto")
    pz.add_argument("--max-areas", type=int, default=zeh.MAX_AREAS)
    po = sub.add_parser("ingest-opendata")
    po.add_argument("--kind", choices=["dental", "clinic", "care"], required=True)
    po.add_argument("--scope", choices=["kanto", "nationwide"], default="kanto")
    po.add_argument("--require-url", action="store_true")
    po.add_argument("--exclude-chain", action="store_true")
    po.add_argument("--limit", type=int, default=None)
    pc = sub.add_parser("crawl")
    pc.add_argument("--workers", type=int, default=1)
    pc.add_argument("--max-minutes", type=float, default=None)
    pc.add_argument("--until-instagram", type=int, default=None)
    sub.add_parser("retry-sites")
    sub.add_parser("repair-merges")
    pr = sub.add_parser("import-review")
    pr.add_argument("--file", required=True)
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
    elif a.cmd == "ingest-zeh":
        print(json.dumps({"ingested": zeh.ingest_zeh(con, f, target=a.limit, scope=a.scope, max_areas=a.max_areas)},
                         ensure_ascii=False))
    elif a.cmd == "ingest-opendata":
        kw = dict(target=a.limit, scope=a.scope, require_url=a.require_url, exclude_chain=a.exclude_chain)
        n = (opendata.ingest_kaigo(con, f, **kw) if a.kind == "care" else opendata.ingest_iryou(con, f, a.kind, **kw))
        print(json.dumps({"ingested": n}, ensure_ascii=False))
    elif a.cmd == "crawl":
        n = crawl.crawl_all(con, f, workers=a.workers, max_minutes=a.max_minutes, until_instagram=a.until_instagram)
        print(json.dumps({"crawled": n, "remaining": len(crawl._pending(con)), "instagram_leads": crawl.instagram_leads(con),
                          "fetch": f.stats}, ensure_ascii=False))
    elif a.cmd == "retry-sites":
        print(json.dumps({"reset": crawl.retry_sites(con)}, ensure_ascii=False))
    elif a.cmd == "repair-merges":
        from . import repair
        print(json.dumps(repair.unmerge_all(con), ensure_ascii=False))
    elif a.cmd == "import-review":
        print(json.dumps(review.import_file(con, a.file), ensure_ascii=False))
    elif a.cmd == "finalize":
        print(json.dumps(finalize(con), ensure_ascii=False, indent=1))
    elif a.cmd == "stats":
        print(json.dumps(export.stats(con), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
