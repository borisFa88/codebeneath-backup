# -*- coding: utf-8 -*-
"""
Telegram notifications for the Code Beneath engine. Runs after each cron
pipeline (see run-pipeline.sh) and reports what happened since the last
notification: new article live, QA quarantine, topic refill, failed run.

  python3 notify.py --run-rc N --backup-rc N   called by run-pipeline.sh
  python3 notify.py --init                     mark everything already logged as notified
  python3 notify.py --setup <BOT_TOKEN>        save token + capture chat id (send /start to the bot first)
  python3 notify.py --test                     send a status message now

Config: ~/.config/claude-seo/telegram.json {"bot_token": ..., "chat_id": ...}
(env TG_BOT_TOKEN / TG_CHAT_ID also work). Not configured = silent skip; this
script never fails the pipeline and never touches the site.
"""
import argparse, datetime, json, os, pathlib, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

HERE = pathlib.Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.jsonl"
PLAN = HERE / "content-plan.json"
LOG = HERE / "pipeline.log"
STATE = HERE / ".notify-state.json"
CFG = pathlib.Path.home() / ".config" / "claude-seo" / "telegram.json"
SITE_ROOT = os.environ.get("CB_SITE_ROOT", "/var/www/html")
DOMAIN = "https://codebeneath.com"
DAYS_HE = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
CRON_DAYS = (0, 2, 4)   # Mon/Wed/Fri 09:00 server time, keep in sync with crontab
CRON_HOUR = 9


# ---------- telegram ----------
def load_cfg():
    tok, chat = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
    if CFG.exists():
        c = json.loads(CFG.read_text(encoding="utf-8-sig"))
        tok, chat = tok or c.get("bot_token"), chat or c.get("chat_id")
    return tok, chat

def tg(method, token, data=None):
    body = urllib.parse.urlencode(data).encode("utf-8") if data else None
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=body,
                                 headers={"User-Agent": "cb-engine-notify/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def send(text):
    """True = delivered. False = not configured or failed (caller keeps the backlog)."""
    tok, chat = load_cfg()
    if not (tok and chat):
        print("telegram: not configured, skip"); return False
    try:
        r = tg("sendMessage", tok, {"chat_id": chat, "text": text[:4000]})
        print("telegram:", "sent" if r.get("ok") else r)
        return bool(r.get("ok"))
    except Exception as e:
        print("telegram error:", e); return False


# ---------- engine state ----------
def read_manifest():
    out = []
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try: out.append(json.loads(line))
                except ValueError: pass
    return out

def plan_info():
    try:
        topics = json.loads(PLAN.read_text(encoding="utf-8-sig")).get("topics", [])
    except Exception:
        return {}, 0, 0
    titles = {t["slug"]: t["title"] for t in topics}
    pub = sum(1 for t in topics if t.get("status") == "published")
    queued = sum(1 for t in topics if t.get("status") == "queued")
    return titles, pub, queued

def load_state():
    try: return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: return {}

def mark_seen(n):
    STATE.write_text(json.dumps({"seen": n, "ts": datetime.datetime.now().isoformat(timespec="seconds")}),
                     encoding="utf-8")

def url_for(path):
    p = str(path)
    return DOMAIN + p[len(SITE_ROOT):] if p.startswith(SITE_ROOT) else p

def next_run():
    now = datetime.datetime.now()
    day = now
    for d in range(8):
        day = (now + datetime.timedelta(days=d)).replace(hour=CRON_HOUR, minute=0, second=0, microsecond=0)
        if day.weekday() in CRON_DAYS and day > now:
            break
    try:
        from zoneinfo import ZoneInfo
        day = day.astimezone().astimezone(ZoneInfo("Asia/Jerusalem"))   # Bar reads Israel time
    except Exception:
        pass
    return f"יום {DAYS_HE[day.weekday()]} {day:%d/%m} בשעה {day:%H:%M}"

def log_tail(n=12):
    try: return "\n".join(LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except Exception: return "(no log)"

_FX = None
def usd_ils():
    """Live USD->ILS rate, display only. None when offline (then only $ is shown)."""
    global _FX
    if _FX is None:
        try:
            req = urllib.request.Request("https://open.er-api.com/v6/latest/USD",
                                         headers={"User-Agent": "cb-engine-notify/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                _FX = float(json.loads(r.read().decode("utf-8"))["rates"]["ILS"])
        except Exception:
            _FX = 0.0
    return _FX or None

def money(usd, digits=2):
    rate = usd_ils()
    return f"${usd:.{digits}f} (≈₪{usd * rate:.2f})" if rate else f"${usd:.{digits}f}"

def spend_line():
    """Anthropic API is the engine's only running cost (server is Boris's, dev.to + Telegram are free)."""
    recs = read_manifest()
    if not recs:
        return "💰 עלות: אין עדיין הרצות"
    month = datetime.date.today().strftime("%Y-%m")
    total = sum(r.get("cost_usd", 0) for r in recs)
    this_month = sum(r.get("cost_usd", 0) for r in recs if str(r.get("ts", "")).startswith(month))
    arts = [r["cost_usd"] for r in recs if r.get("passed") and r.get("file")]
    proj = (sum(arts) / len(arts)) * 13 if arts else 0     # 3 runs/week ≈ 13 articles/month
    since = datetime.date.fromisoformat(str(recs[0]["ts"])[:10]).strftime("%d/%m")
    return (f"💰 עלות החודש: {money(this_month)} · מאז {since}: {money(total)}\n"
            f"   צפי לחודש מלא (13 מאמרים): {money(proj)}")

def footer():
    _, pub, queued = plan_info()
    return f"📊 באתר: {pub} מאמרים מהמנוע · {queued} בתור · הבא: {next_run()}\n{spend_line()}"


# ---------- message building ----------
def describe(rec, titles):
    if rec.get("event") == "replenish":
        return f"🔄 התור התמלא אוטומטית: נוספו {rec.get('added')} נושאים חדשים (עלות {money(rec.get('cost_usd', 0), 3)})"
    title = titles.get(rec.get("slug"), rec.get("slug"))
    if rec.get("passed") and rec.get("file"):
        lines = ["✅ מאמר חדש עלה ל-codebeneath.com", "", title, url_for(rec["file"])]
        dv = rec.get("devto")
        if dv and str(dv).startswith("http"):
            lines.append(f"🔗 קישור חוזר מ-dev.to: {dv}")
        elif dv:
            lines.append(f"dev.to: לא פורסם ({dv})")
        words = (rec.get("verdict") or {}).get("word_estimate") or "?"
        lines.append(f"QA עבר · כ-{words} מילים · עלות המאמר: {money(rec.get('cost_usd', 0), 3)}")
        return "\n".join(lines)
    if rec.get("passed") is False:
        issues = "; ".join(map(str, (rec.get("verdict") or {}).get("issues") or []))
        return f"⚠️ מאמר לא עבר QA, הועבר להסגר ולא פורסם\n\n{title}\nבעיות: {issues[:600]}"
    return None   # dry runs and anything unknown stay quiet


def pipeline(run_rc, backup_rc):
    recs = read_manifest()
    state = load_state()
    seen = state.get("seen", max(0, len(recs) - 1))   # no state: report only the latest record
    titles, _, _ = plan_info()
    parts = [p for p in (describe(r, titles) for r in recs[seen:]) if p]
    published_now = any(r.get("passed") and r.get("file") for r in recs[seen:])
    if run_rc not in (None, 0, 3):
        parts.append(f"❌ הרצת המנוע נכשלה (קוד {run_rc}). סוף הלוג:\n{log_tail()}")
    elif run_rc == 3 and not published_now and not parts:
        parts.append(f"ℹ️ המנוע רץ אבל לא פורסם מאמר הפעם. סוף הלוג:\n{log_tail(6)}")
    # git-backup.sh exits 0 even when the push fails, so also read its log line
    if backup_rc not in (None, 0) or "git-backup: push failed" in log_tail(3):
        parts.append(f"⚠️ הגיבוי ל-GitHub נכשל (קוד {backup_rc}). האתר עצמו תקין, הגיבוי המקומי נשמר.")
    if not parts:
        print("telegram: nothing new"); mark_seen(len(recs)); return
    if send("\n\n".join(parts + [footer()])):
        mark_seen(len(recs))


def status_message():
    titles, _, _ = plan_info()
    live = [r for r in read_manifest() if r.get("passed") and r.get("file")]
    lines = ["🔔 התראות Code Beneath מחוברות. מעכשיו תקבל הודעה על כל מאמר שעולה.", "",
             "אחרונים שעלו:"]
    for r in live[-3:]:
        lines.append(f"· {titles.get(r['slug'], r['slug'])}\n  {url_for(r['file'])}")
    return "\n".join(lines + ["", footer()])


def setup(token):
    r = tg("getUpdates", token)
    chats = [u["message"]["chat"]["id"] for u in r.get("result", []) if "message" in u]
    if not chats:
        print("no messages yet: open the bot in Telegram, press Start, then rerun --setup"); return
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps({"bot_token": token, "chat_id": chats[-1]}), encoding="utf-8")
    os.chmod(CFG, 0o600)
    print("saved", CFG, "chat_id", chats[-1])
    if send(status_message()):
        mark_seen(len(read_manifest()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-rc", type=int)
    ap.add_argument("--backup-rc", type=int)
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--setup")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    try:
        if a.init:
            mark_seen(len(read_manifest())); print("notify state initialised")
        elif a.setup:
            setup(a.setup)
        elif a.test:
            send(status_message())
        else:
            pipeline(a.run_rc, a.backup_rc)
    except Exception as e:          # never break the cron pipeline
        print("notify error:", e)
