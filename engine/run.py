# -*- coding: utf-8 -*-
"""
CLI for the Code Beneath article engine. LOCAL only, nothing deploys.

  python run.py --count 2          generate+publish the next 2 queued topics
  python run.py --count 1 --dry    generate+QA only, do NOT publish (preview cost)
  python run.py --list             show the queue
"""
import argparse, io, sys, json, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import engine as E

# Autonomous queue: keep it full forever with zero human input.
MIN_QUEUED = 8        # when queued drops below this, brainstorm more
TARGET_QUEUED = 24    # top the queue back up to this (~2 months runway at 3/week)
MAX_TOPICS = 400      # hard safety cap on the plan size (runaway guard)

def load_plan():
    return json.loads(E.PLAN.read_text(encoding="utf-8"))
def save_plan(plan):
    E.PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

def attach_folders(plan):
    for t in plan["topics"]:
        t["_folder"] = plan["clusters"].get(t["cluster"], {}).get("folder", "articles")

def cmd_list(plan):
    for t in plan["topics"]:
        print(f'  [{t["status"]:<9}] p{t.get("priority","-")} {t["cluster"]:<10} {t["title"]}')

def process_one(topic, plan):
    slug = topic["slug"]
    total = 0.0
    print(f'\n=== {topic["title"]}  ({slug}) ===')
    inner, meta, u = E.generate(topic, plan); total += E.cost(u)
    topic["meta_description"] = E.strip_dashes(meta).strip()[:180]
    if not (140 <= len(topic["meta_description"]) <= 165):        # SEO length guard: fix once
        m2, u = E.regen_meta(topic, inner); total += E.cost(u)
        m2 = E.strip_dashes(m2).strip()
        if 130 <= len(m2) <= 170:
            topic["meta_description"] = m2[:165]
        print(f'   meta length fixed -> {len(topic["meta_description"])} chars')
    inner = E.strip_dashes(inner)                      # deterministic dash guard
    verdict, u = E.qa(topic, inner); total += E.cost(u)
    print(f'   QA: {verdict.get("verdict")} | issues: {verdict.get("issues")}')
    if verdict.get("verdict") != "PASS" or E.has_dash(inner):
        print('   -> repairing once...')
        inner, u = E.repair(topic, inner, verdict.get("issues", []) + (["remove em/en dashes"] if E.has_dash(inner) else []))
        total += E.cost(u)
        inner = E.strip_dashes(inner)
        verdict, u = E.qa(topic, inner); total += E.cost(u)
        print(f'   QA(2): {verdict.get("verdict")} | issues: {verdict.get("issues")}')
    passed = verdict.get("verdict") == "PASS" and not E.has_dash(inner)
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "slug": slug,
           "passed": passed, "cost_usd": round(total, 4), "verdict": verdict}
    if passed and not ARGS.dry:
        out = E.publish(topic, inner, plan)
        topic["status"] = "published"
        rec["file"] = str(out)
        print(f'   PUBLISHED -> {out}  (cost ${total:.4f})')
    elif passed and ARGS.dry:
        print(f'   DRY RUN: would publish  (cost ${total:.4f})')
    else:
        E.quarantine(topic, inner, verdict)
        topic["status"] = "needs_review"
        print(f'   QUARANTINED -> _needs-review/{slug}.html  (cost ${total:.4f})')
    E.log(rec)
    return total, (passed and not ARGS.dry)

def replenish_queue(plan):
    """Refill the topic queue automatically when it runs low. No human input needed."""
    queued = sum(1 for t in plan["topics"] if t["status"] == "queued")
    if queued >= MIN_QUEUED:
        return
    if len(plan["topics"]) >= MAX_TOPICS:
        print(f"   topic cap reached ({MAX_TOPICS}); not adding more."); return
    need = min(TARGET_QUEUED - queued, MAX_TOPICS - len(plan["topics"]))
    print(f"   queue low ({queued} queued) -> brainstorming {need} new topics...")
    try:
        new_topics, u = E.brainstorm_topics(plan, need)
    except Exception as e:
        print(f"   topic brainstorm failed, will retry next run: {e}"); return
    if not new_topics:
        print("   brainstorm produced no usable topics this time."); return
    plan["topics"].extend(new_topics)
    save_plan(plan)
    c = E.cost(u)
    E.log({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "event": "replenish",
           "added": len(new_topics), "slugs": [t["slug"] for t in new_topics], "cost_usd": round(c, 4)})
    now_q = sum(1 for t in plan["topics"] if t["status"] == "queued")
    print(f"   + added {len(new_topics)} topics (cost ${c:.4f}); queue now {now_q}")

def main():
    plan = load_plan()
    if ARGS.list:
        attach_folders(plan); cmd_list(plan); return
    # keep the pipeline self-feeding: top up the queue before we publish
    if not ARGS.dry:
        replenish_queue(plan)
    attach_folders(plan)
    queued = [t for t in plan["topics"] if t["status"] == "queued"]
    queued.sort(key=lambda t: t.get("priority", 99))
    batch = queued[:ARGS.count]
    if not batch:
        print("nothing queued."); return
    # Boris's rule: always keep an old backup before touching the site.
    if not ARGS.dry:
        import backup as B
        B.make()
    grand = 0.0; published = 0
    for t in batch:
        c, ok = process_one(t, plan)
        grand += c; published += (1 if ok else 0)
        save_plan(plan)          # persist status after each (folders stripped below)
    # strip runtime-only _folder before final save
    for t in plan["topics"]:
        t.pop("_folder", None)
    save_plan(plan)
    print(f'\nTOTAL cost this run: ${grand:.4f} for {len(batch)} article(s), {published} published')
    # exit code: 0 = something published (deploy should run), 3 = nothing new (skip deploy)
    sys.exit(0 if published > 0 else 3)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--list", action="store_true")
    ARGS = ap.parse_args()
    main()
