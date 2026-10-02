# -*- coding: utf-8 -*-
"""
Distribution layer: cross-post a published Code Beneath article to dev.to with a
canonical URL pointing BACK to codebeneath.com (so SEO stays on the original, and
the republish sends referral traffic + a backlink, never competes with us).

Called best-effort from run.py right after a successful publish. Also runnable
standalone to backfill an existing article:
    python distribute.py <folder>/<slug>          (draft)
    python distribute.py <folder>/<slug> --live    (published)

Key: env DEVTO_API_KEY, else ~/.config/claude-seo/devto.json {"api_key": "..."}.
No external deps (urllib only), so it runs on the server as-is.
"""
import os, re, io, sys, json, pathlib, urllib.request, urllib.error

DOMAIN = "https://codebeneath.com"

def _key():
    k = os.environ.get("DEVTO_API_KEY")
    if k:
        return k.strip()
    p = pathlib.Path.home() / ".config" / "claude-seo" / "devto.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8-sig")).get("api_key", "").strip()
    return None

# cluster -> dev.to tags (lowercase, <=4). "programming" is always safe.
CLUSTER_TAGS = {
    "sockets":   ["go", "networking", "programming"],
    "http":      ["webdev", "http", "programming"],
    "languages": ["go", "java", "programming"],
    "spring":    ["java", "springboot", "programming"],
    "security":  ["security", "linux", "programming"],
    "tools":     ["devops", "linux", "programming"],
}

def _abs_links(html):
    return re.sub(r'href="(/[^"]*)"', lambda m: f'href="{DOMAIN}{m.group(1)}"', html)

def _unescape(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
             .replace("&#39;", "'").replace("&amp;", "&"))

def _code_fences(html):
    # <pre><code class="language-go">...</code></pre> -> ```go fenced blocks (real syntax highlight on dev.to)
    html = re.sub(r'<pre><code class="language-([a-zA-Z0-9+#]+)">(.*?)</code></pre>',
                  lambda m: f"\n```{m.group(1).lower()}\n{_unescape(m.group(2)).strip()}\n```\n", html, flags=re.S)
    html = re.sub(r'<pre><code>(.*?)</code></pre>',
                  lambda m: f"\n```\n{_unescape(m.group(1)).strip()}\n```\n", html, flags=re.S)
    return html

def to_markdownish(inner_html):
    # dev.to body_markdown renders leftover HTML (p/h2/h3/ul/li/strong/table/a) fine,
    # so we only fix the two things markdown must own: code blocks + absolute links.
    h = _code_fences(_abs_links(inner_html))
    h = re.sub(r'<p class="site-block-paragraph">', "<p>", h)
    return h.strip()

def cross_post(title, url, inner_html, description="", cluster="", tags=None, live=True):
    key = _key()
    if not key:
        return {"ok": False, "error": "no dev.to key configured"}
    body = f"*Originally published on [Code Beneath]({url}).*\n\n" + to_markdownish(inner_html)
    article = {
        "title": (title or "").strip()[:128],
        "body_markdown": body,
        "published": bool(live),
        "canonical_url": url,
        "tags": (tags or CLUSTER_TAGS.get(cluster, ["programming"]))[:4],
    }
    if description:
        article["description"] = description.strip()[:140]
    data = json.dumps({"article": article}).encode("utf-8")
    req = urllib.request.Request(
        "https://dev.to/api/articles", data=data, method="POST",
        headers={"api-key": key, "Content-Type": "application/json",
                 "Accept": "application/vnd.forem.api-v1+json",
                 # dev.to is behind Cloudflare, which 403s the default Python UA.
                 "User-Agent": "Mozilla/5.0 (compatible; codebeneath-distributor/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            j = json.loads(r.read().decode("utf-8"))
            return {"ok": True, "url": j.get("url"), "id": j.get("id")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}", "detail": e.read()[:400].decode("utf-8", "replace")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ---- standalone: backfill an existing published article by <folder>/<slug> ----
def _from_file(rel):
    root = pathlib.Path(os.environ.get("CB_SITE_ROOT") or str(pathlib.Path(__file__).resolve().parent.parent))
    f = root / (rel if rel.endswith(".html") else rel + ".html")
    html = f.read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)(?: \| Code Beneath)?</title>", html, re.S).group(1).strip()
    desc = (re.search(r'<meta name="description" content="(.*?)"', html) or [None, ""])[1]
    url = (re.search(r'<link rel="canonical" href="(.*?)"', html) or [None, ""])[1]
    inner = re.search(r'<div class="entry-content[^"]*"[^>]*>(.*?)</div>\s*<section class="cb-related"', html, re.S)
    inner = inner.group(1).strip() if inner else re.search(r"<main[^>]*>(.*?)</main>", html, re.S).group(1)
    return title, url, inner, desc

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rel = sys.argv[1]
    live = "--live" in sys.argv[2:]
    title, url, inner, desc = _from_file(rel)
    print(f"cross-posting: {title}\n  canonical: {url}\n  live: {live}")
    r = cross_post(title, url, inner, desc, live=live)
    print(json.dumps(r, ensure_ascii=False, indent=2))
