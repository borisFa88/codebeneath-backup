# -*- coding: utf-8 -*-
"""
Code Beneath SEO article engine.
Generate -> AI self-QA gate -> deterministic no-em-dash filter -> publish (local).
Cheap by design: Claude Haiku 4.5 + prompt caching. ~3-5 cents per article.

Everything is LOCAL. Nothing here deploys to the server.
Run:  python run.py --count 2
"""
import os, re, io, sys, json, datetime, pathlib
from anthropic import Anthropic

# Site root: the web root. Local dev = parent of _automation; server = /var/www/html via CB_SITE_ROOT.
ROOT = pathlib.Path(os.environ.get("CB_SITE_ROOT") or str(pathlib.Path(__file__).resolve().parent.parent))
AUTO = pathlib.Path(__file__).resolve().parent  # where engine files + content-plan live
PLAN = AUTO / "content-plan.json"
QUARANTINE = AUTO / "_needs-review"
MANIFEST = AUTO / "manifest.jsonl"
DOMAIN = "https://codebeneath.com"
MODEL = "claude-haiku-4-5"          # cheapest capable model

def _cfg():
    cfg = pathlib.Path.home() / ".config" / "claude-seo" / "anthropic.json"  # cross-platform (Win + Linux)
    return json.loads(cfg.read_text(encoding="utf-8-sig"))

_c = _cfg()
# Org-scoped keys need a workspace id header; workspace-scoped keys do not.
_headers = {"anthropic-workspace-id": _c["workspace_id"]} if _c.get("workspace_id") else None
client = Anthropic(api_key=_c["api_key"], default_headers=_headers)

# ---------------------------------------------------------------- em dash guard
_DASH_MAP = {
    "—": ", ",   # em dash
    "–": "-",     # en dash
    "&mdash;": ", ", "&ndash;": "-", "&#8212;": ", ", "&#8211;": "-",
}
def strip_dashes(html: str) -> str:
    for k, v in _DASH_MAP.items():
        html = html.replace(k, v)
    return html
def has_dash(html: str) -> bool:
    return any(k in html for k in _DASH_MAP)

# ---------------------------------------------------------------- shared chrome
# Header + footer copied from the live site (styling classes preserved) with ALL
# links rewritten absolute so a page works from any folder depth.
HEADER = r'''<header class="site-block-template-part">
<div class="site-block-group alignfull is-layout-flow site-block-group-is-layout-flow">
<div class="site-block-group has-global-padding is-layout-constrained site-block-group-is-layout-constrained">
<div class="site-block-group alignwide is-content-justification-left is-layout-flex site-block-group-is-layout-flex" style="padding-top:var(--site--preset--spacing--30);padding-bottom:var(--site--preset--spacing--30)"><p class="site-block-site-title"><a href="/" rel="home">codebeneath.com</a></p></div>
<nav class="has-text-color has-contrast-color has-medium-font-size is-responsive alignwide site-block-navigation is-layout-flex site-block-navigation-is-layout-flex" aria-label="Navigation"><button aria-haspopup="dialog" aria-label="Open menu" class="site-block-navigation__responsive-container-open"><svg width="24" height="24" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 7.5h16v1.5H4z"></path><path d="M4 15h16v1.5H4z"></path></svg></button>
<div class="site-block-navigation__responsive-container" id="modal-1" tabindex="-1"><div class="site-block-navigation__responsive-close" tabindex="-1"><div class="site-block-navigation__responsive-dialog"><button aria-label="Close menu" class="site-block-navigation__responsive-container-close"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false"><path d="m13.06 12 6.47-6.47-1.06-1.06L12 10.94 5.53 4.47 4.47 5.53 10.94 12l-6.47 6.47 1.06 1.06L12 13.06l6.47 6.47 1.06-1.06L13.06 12Z"></path></svg></button>
<div class="site-block-navigation__responsive-container-content" id="modal-1-content">
<ul class="site-block-navigation__container has-text-color has-contrast-color has-medium-font-size is-responsive alignwide site-block-navigation">
<li class="site-block-navigation-item has-child site-block-navigation-submenu"><a class="site-block-navigation-item__content" href="/category/http/"><span class="site-block-navigation-item__label">HTTP Requests</span></a><ul class="site-block-navigation__submenu-container site-block-navigation-submenu"><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/handlingHttpRequest/how-to-read-dynamic-http-type.html">How to Read an Unknown HTTP Request Body Type</a></li><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/handlingHttpRequest/token-based-security-in-web-applications.html">Token-Based Security in Web Applications</a></li></ul></li>
<li class="site-block-navigation-item has-child site-block-navigation-submenu"><a class="site-block-navigation-item__content" href="/category/languages/"><span class="site-block-navigation-item__label">Programming Languages</span></a><ul class="site-block-navigation__submenu-container site-block-navigation-submenu"><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/nonJava/python-is-not-real-programming-language.html">Python vs Java and C++: A Developer Opinion</a></li><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/nonJava/go-lang.html">RAII in Go: Resource Cleanup With defer</a></li><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/nonJava/native-language.html">Native C and C++ for Modern Developers</a></li></ul></li>
<li class="site-block-navigation-item has-child site-block-navigation-submenu"><a class="site-block-navigation-item__content" href="/category/not-only-http/"><span class="site-block-navigation-item__label">Sockets and File Transfer</span></a><ul class="site-block-navigation__submenu-container site-block-navigation-submenu"><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/notOnlyHttp/tcp-udp-socket.html">TCP vs UDP in Go: runnable echo server examples</a></li><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/notOnlyHttp/web-socket.html">WebSocket vs HTTP: browser messages and persistent connections</a></li><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/notOnlyHttp/ftp-file-transfer-protocol.html">FTP File Transfers With Kotlin and Python</a></li></ul></li>
<li class="site-block-navigation-item has-child site-block-navigation-submenu"><a class="site-block-navigation-item__content" href="/articles.html#stories"><span class="site-block-navigation-item__label">Programming Stories</span></a><ul class="site-block-navigation__submenu-container site-block-navigation-submenu"><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/programmerStories/linux-how-to-manage-the-password-safety.html">Linux Password Security and Account Protection</a></li><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/programmerStories/go-land-never-replace-java.html">Go vs Java: Where Each Language Fits</a></li><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/programmerStories/funny-stories-in-my-programming-carrier.html">Funny Stories From a Programming Career</a></li><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/programmerStories/dont-speak-british-in-la.html">Consistent Coding Style: The No Mixed Principle</a></li></ul></li>
<li class="site-block-navigation-item has-child site-block-navigation-submenu"><a class="site-block-navigation-item__content" href="/category/tools/"><span class="site-block-navigation-item__label">Development Tools</span></a><ul class="site-block-navigation__submenu-container site-block-navigation-submenu"><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/recommendedTools/1-tools-which-i-like-and-recommend-to-use.html">Recommended Development and Server Tools</a></li></ul></li>
<li class="site-block-navigation-item has-child site-block-navigation-submenu"><a class="site-block-navigation-item__content" href="/category/spring-alternatives/"><span class="site-block-navigation-item__label">Spring Framework</span></a><ul class="site-block-navigation__submenu-container site-block-navigation-submenu"><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/springAlternatives/spring-cant-work-with-another-clients.html">How to Handle Multiple Content Types in Spring Boot</a></li><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/springAlternatives/spring-is-not-the-holly-framework.html">Spring Framework vs Spring Boot: understand the layers</a></li></ul></li>
<li class="site-block-navigation-item has-child site-block-navigation-submenu"><a class="site-block-navigation-item__content" href="/articles.html#ai"><span class="site-block-navigation-item__label">AI and Programming</span></a><ul class="site-block-navigation__submenu-container site-block-navigation-submenu"><li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/newEra/lifewithAI.html">Life With AI: A Short Programming Note</a></li></ul></li>
<li class="site-block-navigation-item"><a class="site-block-navigation-item__content" href="/articles.html"><span class="site-block-navigation-item__label">All Articles</span></a></li>
</ul></div></div></div></nav></div></div></header>'''

FOOTER = r'''<footer class="cb-footer"><nav aria-label="Footer"><a href="/articles.html">All articles</a><a href="/about.html">About the author</a><a href="/my-service.html">Services</a><a href="/contact-me.html">Contact</a><a href="/privacy-policy.html">Privacy</a><a href="/accessibility-statement.html">Accessibility</a></nav><p>Code Beneath . Programming beneath the frameworks.</p></footer>'''

HEAD_ASSETS = r'''<link rel="stylesheet" href="/assets/css/navigation.css" media="all" />
<link rel="stylesheet" href="/assets/vendor/cdnjs/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" media="all" />
<link rel="stylesheet" href="/assets/vendor/cdnjs/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css" media="all" />
<link rel="stylesheet" href="/assets/css/site.css" />
<link rel="stylesheet" href="/assets/css/article-discovery.css" />'''

FOOT_SCRIPTS = r'''<script src="/assets/js/static-navigation.js" defer></script>
<script src="/assets/vendor/cdnjs/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script>hljs.highlightAll();</script>'''

# Google Analytics 4 (codebeneath.com property, stream G-SCNSJWPRF1)
GA_TAG = r'''<script async src="https://www.googletagmanager.com/gtag/js?id=G-SCNSJWPRF1"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-SCNSJWPRF1');</script>'''

# ---------------------------------------------------------------- page assembly
def build_head(topic, url):
    t = topic["title"]; d = topic["meta_description"]; kw = topic.get("target_keyword", "")
    schema = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": t, "name": t, "description": d, "url": url, "inLanguage": "en-US",
        "dateModified": datetime.date.today().isoformat(),
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "author": {"@type": "Person", "name": "Boris Fain", "url": DOMAIN + "/about.html"},
        "publisher": {"@type": "Organization", "name": "Code Beneath", "url": DOMAIN + "/"},
        "isPartOf": {"@type": "WebSite", "name": "Code Beneath", "url": DOMAIN + "/"},
    }
    crumbs = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Articles", "item": DOMAIN + "/articles.html"},
            {"@type": "ListItem", "position": 3, "name": t, "item": url},
        ],
    }
    return f'''<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="robots" content="max-image-preview:large" />
<title>{t} | Code Beneath</title>
<meta name="description" content="{d}" />
<link rel="canonical" href="{url}" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="Code Beneath" />
<meta property="og:title" content="{t} | Code Beneath" />
<meta property="og:description" content="{d}" />
<meta property="og:url" content="{url}" />
<meta name="twitter:card" content="summary" />
<meta name="twitter:title" content="{t} | Code Beneath" />
<meta name="twitter:description" content="{d}" />
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(crumbs, ensure_ascii=False)}</script>
{HEAD_ASSETS}'''

def related_block(topic, plan):
    links = topic.get("internal_links", [])[:4]
    cluster = plan["clusters"].get(topic["cluster"], {})
    hub = cluster.get("hub", "/articles.html")
    items = "".join(f'<li><a href="{u}">{_title_for(u, plan)}</a></li>' for u in links)
    return (f'<section class="cb-related" aria-label="Further reading"><h2>Continue reading</h2>'
            f'<ul>{items}</ul><p><a href="{hub}">More in {cluster.get("label","Articles")}</a> . '
            f'<a href="/articles.html">Browse all programming articles</a></p></section>')

def _title_for(url, plan):
    for t in plan["topics"]:
        if _url_for(t) == DOMAIN + url or _rel_url(t) == url:
            return t["title"]
    # fall back to a readable slug
    base = url.rstrip("/").split("/")[-1].replace(".html", "").replace("-", " ")
    return base[:1].upper() + base[1:]

def _rel_url(topic):
    return f'/{_folder(topic)}/{topic["slug"]}.html'
def _url_for(topic):
    return DOMAIN + _rel_url(topic)
def _folder(topic):
    return topic.get("_folder")  # filled from cluster at runtime

def compose(topic, inner_html, plan):
    url = _url_for(topic)
    cluster = plan["clusters"].get(topic["cluster"], {})
    crumb_anchor = cluster.get("hub", "/articles.html")
    head = build_head(topic, url)
    byline_date = datetime.date.today().strftime("%B %-d, %Y") if os.name != "nt" else datetime.date.today().strftime("%B %d, %Y")
    return f'''<!DOCTYPE html>
<html lang="en-US">
<head>
{head}
{GA_TAG}
</head>
<body class="site-singular single single-post site-theme-twentytwentyfive">
<div class="site-site-blocks">
{HEADER}
<main id="content" class="site-block-group has-global-padding is-layout-constrained site-block-group-is-layout-constrained" style="margin-top:var(--site--preset--spacing--60)">
<nav class="cb-breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/articles.html">Articles</a> / <a href="{crumb_anchor}">{cluster.get("label","Articles")}</a></nav>
<h1 class="site-block-post-title">{topic["title"]}</h1>
<div class="site-block-group has-small-font-size" style="margin-bottom:var(--site--preset--spacing--60)"><p class="site-block-paragraph">By <a href="/about.html" rel="author">Boris Fain</a> · Updated <time datetime="{datetime.date.today().isoformat()}">{byline_date}</time></p></div>
<div class="entry-content site-block-post-content is-layout-constrained">
{inner_html}
</div>
{related_block(topic, plan)}
</main>
{FOOTER}
</div>
{FOOT_SCRIPTS}
</body>
</html>'''

# ---------------------------------------------------------------- Claude calls
GEN_SYSTEM = """You are the staff writer for Code Beneath (codebeneath.com), a site about low-level programming: HTTP, sockets, security, Java, Go, C, C++, Kotlin, Python. Author voice: opinionated, practical, direct, written by a working engineer (Boris Fain). You explain what happens beneath the frameworks with runnable code.

You write the INNER BODY of one article as clean semantic HTML only. Do NOT output <html>, <head>, <body>, the site header, the h1, the byline, or the footer. Those are added by the system. Start at the first paragraph.

Hard rules, all mandatory:
1. NEVER use an em dash or en dash anywhere (no . no .). Use a comma, a period, parentheses, or a colon instead. This is an absolute rule.
2. Every code block must be COMPLETE and RUNNABLE, not a fragment. Wrap code as <pre><code class="language-xxx"> with the correct language (go, java, cpp, c, python, kotlin, bash, sql). Escape < and & inside code as &lt; and &amp;.
3. Length 1200+ words of real technical substance.
4. Structure: an opening paragraph that states the problem and naturally contains the target keyword, then several <h2> sections, at least one runnable code example, a comparison <table> where it helps, a short 'Common mistakes' section, and a compact FAQ as <h2>FAQ</h2> followed by <h3> questions with <p> answers.
5. Be MORE complete than the top-ranking competitor: cover what they cover plus at least one thing they miss (an edge case, a measurement, a gotcha).
6. Accuracy over fluff. If you are not certain a code sample compiles and runs, do not include it. No invented benchmarks, no fake numbers.
7. Paragraphs as <p class="site-block-paragraph">. Do not include a conclusion that just repeats the intro.

Output the meta description first, then the inner HTML, using exactly these markers and nothing else:
<<<META>>>
a 150 to 160 character meta description that contains the target keyword, plain text, no em dash
<<<END META>>>
<<<ARTICLE>>>
...inner html...
<<<END>>>"""

def _extract(text, start="<<<ARTICLE>>>", end="<<<END>>>"):
    i = text.find(start); j = text.find(end)
    if i == -1 or j == -1:
        return text.strip()
    return text[i + len(start):j].strip()

def generate(topic, plan):
    sib = ", ".join(f'{t["title"]} ({_rel_url(t)})'
                    for t in plan["topics"] if t["id"] != topic["id"])[:1500]
    existing = ", ".join(topic.get("internal_links", []))
    user = f"""Write the article body.
Title: {topic['title']}
Target keyword (must appear in the first paragraph): {topic['target_keyword']}
Search intent: {topic.get('intent','')}
How to beat competitors: {topic.get('beat_strategy','')}
Link naturally, using <a href>, to 2 or 3 of these existing pages where relevant: {existing}
Keep it specific and code-first."""
    resp = client.messages.create(
        model=MODEL, max_tokens=8000,
        system=[{"type": "text", "text": GEN_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    meta = _extract(text, "<<<META>>>", "<<<END META>>>")
    inner = _extract(text, "<<<ARTICLE>>>", "<<<END>>>")
    return inner, meta, resp.usage

QA_SYSTEM = """You are a strict SEO and technical editor for Code Beneath. You receive one article body (inner HTML) and its target keyword. Judge it hard, as if it must outrank Baeldung and Cloudflare. Check:
- technical accuracy: is the code correct and runnable, are the claims true
- originality and depth: 1200+ words of substance, covers more than a shallow post
- SEO: target keyword present in the first paragraph and at least one H2, clear H2 structure, at least one runnable code block, a table or FAQ present
- style: matches an opinionated working-engineer voice, no filler
- ABSOLUTE: no em dash and no en dash anywhere
Return ONLY compact JSON between the markers:
<<<QA>>>
{"verdict":"PASS"|"FAIL","issues":["..."],"has_dash":true|false,"word_estimate":N}
<<<END>>>"""

def qa(topic, inner_html):
    user = f"Target keyword: {topic['target_keyword']}\n\nArticle body:\n{inner_html}"
    resp = client.messages.create(
        model=MODEL, max_tokens=1200,
        system=[{"type": "text", "text": QA_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    raw = _extract(text, "<<<QA>>>", "<<<END>>>")
    try:
        return json.loads(raw), resp.usage
    except Exception:
        return {"verdict": "FAIL", "issues": ["QA output unparseable"], "has_dash": has_dash(inner_html)}, resp.usage

def repair(topic, inner_html, issues):
    user = (f"Revise this article body to fix these issues, keep everything else. "
            f"Issues: {json.dumps(issues, ensure_ascii=False)}\n\nBody:\n{inner_html}")
    resp = client.messages.create(
        model=MODEL, max_tokens=8000,
        system=[{"type": "text", "text": GEN_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return _extract(text), resp.usage

# ---------------------------------------------------------------- topic autogen
# Keeps the queue full forever with zero human input: when run.py sees the queue
# run low it asks Claude for fresh long-tail topics, deduped and link-validated.
TOPIC_SYSTEM = """You are the SEO content strategist for Code Beneath (codebeneath.com), a site about low-level programming: HTTP, sockets, TLS, DNS, Java, Go, C, C++, Kotlin, Python, Spring, Linux, databases, and developer tools.

Your job: propose NEW article topics that a young, low-authority site can realistically rank for and pull traffic from. Follow this exact winning strategy:
- Target LONG-TAIL, code-first, runnable-example queries (for example "golang tcp server graceful shutdown example", "read x509 certificate in java example", "postgres index only scan not used"), NOT head terms owned by MDN, Cloudflare, Baeldung, or GeeksforGeeks.
- Each topic must be a concrete question or task a working developer types into Google, winnable because the best possible answer is a full runnable example plus edge cases and a gotcha, which the big sites rarely give.
- Spread the topics across the existing clusters so every hub keeps growing.
- Every topic must be DISTINCT from the existing titles and keywords you are given: no duplicates, no near duplicates, no rephrasings.

Hard rules, all mandatory:
1. No em dash and no en dash anywhere in any field. Use commas, periods, parentheses, or colons.
2. Plain text only in every field. No HTML, no markdown, no code fences.
3. slug is lowercase kebab-case, unique, with no file extension.
4. internal_links: pick 2 or 3 URLs ONLY from the provided list of existing pages. Never invent a URL.
5. cluster must be exactly one of the provided cluster keys.

Return ONLY a JSON array of topic objects between the markers, nothing before or after:
<<<TOPICS>>>
[{"cluster":"...","title":"...","slug":"...","target_keyword":"...","intent":"...","competitors":["...","..."],"beat_strategy":"...","internal_links":["/path.html","/path2.html"]}]
<<<END>>>"""

def _header_slugs():
    return {u.rstrip("/").split("/")[-1].replace(".html", "").lower()
            for u in re.findall(r'href="(/[^"]+\.html)"', HEADER)}

def _existing_signatures(plan):
    """Everything a new topic must NOT collide with: plan slugs/keywords/titles + real site file slugs."""
    sigs = set()
    for t in plan["topics"]:
        for k in ("slug", "target_keyword", "title", "id"):
            v = (t.get(k) or "").strip().lower()
            if v:
                sigs.add(v)
    sigs |= _header_slugs()      # do not overwrite existing hand-written articles
    return sigs

def _rel_url_static(topic, plan):
    """Folder from the cluster map (not the runtime _folder, which is unset during replenish)."""
    folder = plan["clusters"].get(topic["cluster"], {}).get("folder", "articles")
    return f'/{folder}/{topic["slug"]}.html'

def _valid_link_targets(plan):
    """Only link new articles to pages that ALREADY exist, so no 'Continue reading' 404s."""
    urls = set(re.findall(r'href="(/[^"]+\.html)"', HEADER))
    urls |= {"/articles.html", "/about.html", "/my-service.html", "/contact-me.html"}
    for c in plan["clusters"].values():
        if c.get("hub"):
            urls.add(c["hub"])
    for t in plan["topics"]:
        if t.get("status") == "published":
            urls.add(_rel_url_static(t, plan))
    return urls

def brainstorm_topics(plan, need):
    """Ask Claude for `need` NEW long-tail topics. Returns (clean_topics, usage)."""
    need = max(1, min(need, 12))    # cap per call so the JSON array never truncates
    existing = sorted({(t.get("title") or "") + "  ::  " + (t.get("target_keyword") or "")
                       for t in plan["topics"]})
    clusters = {k: v.get("label", k) for k, v in plan["clusters"].items()}
    valid = sorted(_valid_link_targets(plan))
    strat = plan.get("_meta", {}).get("strategy", {})
    user = f"""Propose {need} NEW topics as a JSON array.

Clusters (use these keys exactly): {json.dumps(clusters, ensure_ascii=False)}

Existing pages you may link to in internal_links (choose ONLY from this list): {json.dumps(valid, ensure_ascii=False)}

Core insight: {strat.get('core_insight','')}
How we beat competitors: {strat.get('how_we_beat_competitors','')}

Do NOT duplicate or rephrase any of these existing topics (title :: keyword):
{chr(10).join('- ' + e for e in existing)}

Return {need} distinct, winnable, code-first topics spread across the clusters."""
    resp = client.messages.create(
        model=MODEL, max_tokens=8000,
        system=[{"type": "text", "text": TOPIC_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    raw = _extract(text, "<<<TOPICS>>>", "<<<END>>>")
    a, b = raw.find("["), raw.rfind("]")          # tolerate stray fences/prose
    if a != -1 and b != -1:
        raw = raw[a:b + 1]
    try:
        proposed = json.loads(raw)
    except Exception:
        proposed = []
    return _sanitize_topics(proposed, plan), resp.usage

def _sanitize_topics(proposed, plan):
    sigs = _existing_signatures(plan)
    valid = _valid_link_targets(plan)
    clusters = set(plan["clusters"].keys())
    out = []
    for p in (proposed if isinstance(proposed, list) else []):
        if not isinstance(p, dict):
            continue
        cluster = str(p.get("cluster", "")).strip()
        title = strip_dashes(str(p.get("title", ""))).strip()
        slug = re.sub(r"[^a-z0-9-]", "", str(p.get("slug", "")).strip().lower().replace(" ", "-")).strip("-")
        kw = strip_dashes(str(p.get("target_keyword", ""))).strip()
        if cluster not in clusters or not title or not slug or not kw:
            continue
        if slug in sigs or kw.lower() in sigs or title.lower() in sigs:
            continue
        links = [u for u in (p.get("internal_links") or []) if u in valid]
        if len(links) < 2:
            hub = plan["clusters"][cluster].get("hub", "/articles.html")
            for fb in (hub, "/articles.html"):
                if fb not in links:
                    links.append(fb)
        comp = [strip_dashes(str(c)).strip() for c in (p.get("competitors") or []) if str(c).strip()][:4]
        out.append({
            "id": slug, "cluster": cluster, "title": title, "slug": slug,
            "target_keyword": kw,
            "intent": strip_dashes(str(p.get("intent", "informational, developers"))).strip()[:120],
            "competitors": comp or ["various blogs"],
            "beat_strategy": strip_dashes(str(p.get("beat_strategy", ""))).strip()[:400],
            "internal_links": links[:3], "priority": 5, "status": "queued", "auto": True,
        })
        sigs.update({slug, kw.lower(), title.lower()})   # block self-duplicates within the batch
    return out

# ---------------------------------------------------------------- cost meter
# Haiku 4.5: $1/MTok in, $5/MTok out, cache read ~$0.10/MTok, cache write ~$1.25/MTok
def cost(u):
    cin = getattr(u, "input_tokens", 0); cout = getattr(u, "output_tokens", 0)
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    return (cin/1e6*1.0) + (cout/1e6*5.0) + (cr/1e6*0.10) + (cw/1e6*1.25)

# ---------------------------------------------------------------- publish (local)
def publish(topic, inner_html, plan):
    folder = ROOT / _folder(topic)
    folder.mkdir(parents=True, exist_ok=True)
    page = compose(topic, inner_html, plan)
    out = folder / f'{topic["slug"]}.html'
    out.write_text(page, encoding="utf-8")
    _add_to_sitemap(_url_for(topic))
    add_to_articles_index(topic, plan)   # list on /articles.html (never orphan it)
    add_to_hub(topic, plan)              # list on the cluster hub
    return out

def _add_to_sitemap(url):
    sm = ROOT / "sitemap.xml"
    x = sm.read_text(encoding="utf-8")
    if url in x:
        return
    today = datetime.date.today().isoformat()
    entry = f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{today}</lastmod>\n  </url>\n"
    x = x.replace("</urlset>", entry + "</urlset>")
    sm.write_text(x, encoding="utf-8")

# ---------------------------------------------------------------- internal linking
# So a new article is never orphaned: list it on /articles.html AND on its cluster hub.
ARTICLES_SECTION = {"http": "http", "languages": "languages", "sockets": "networking",
                    "spring": "spring", "security": "security", "tools": "tools"}

def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _hub_file(topic, plan):
    hub = plan["clusters"].get(topic["cluster"], {}).get("hub", "")   # e.g. /category/http/
    seg = hub.strip("/").split("/")
    if len(seg) >= 2 and seg[0] == "category":
        return ROOT / "category" / seg[1] / "index.html"
    return None

def add_to_articles_index(topic, plan):
    """Insert the article into the matching <section> of /articles.html. Idempotent."""
    f = ROOT / "articles.html"
    if not f.exists():
        return False
    html = f.read_text(encoding="utf-8")
    url = _rel_url_static(topic, plan)
    if f'href="{url}"' in html:
        return False
    sid = ARTICLES_SECTION.get(topic["cluster"])
    if not sid:
        return False
    i = html.find(f'<section id="{sid}">')
    if i == -1:
        return False
    j = html.find("</ul>", i)            # end of that section's list
    if j == -1:
        return False
    li = f'<li><h3><a href="{url}">{_esc(topic["title"])}</a></h3><p>{_esc(topic.get("meta_description",""))}</p></li>'
    html = html[:j] + li + html[j:]
    html = _append_itemlist(html, DOMAIN + url, topic["title"])
    f.write_text(html, encoding="utf-8")
    return True

def _append_itemlist(html, full_url, title):
    k = html.find('"itemListElement": [')
    if k == -1:
        return html
    end = html.find("]}}", k)
    if end == -1:
        return html
    pos = html.count('"@type": "ListItem"', k, end) + 1
    item = ', {"@type": "ListItem", "position": %d, "url": %s, "name": %s}' % (
        pos, json.dumps(full_url, ensure_ascii=False), json.dumps(title, ensure_ascii=False))
    return html[:end] + item + html[end:]

def add_to_hub(topic, plan):
    """Insert the article into its category hub index.html. Idempotent."""
    f = _hub_file(topic, plan)
    if not f or not f.exists():
        return False
    html = f.read_text(encoding="utf-8")
    url = _rel_url_static(topic, plan)
    if f'href="{url}"' in html:
        return False
    j = html.find("</ul>")
    if j == -1:
        return False
    li = f'<li><a href="{url}">{_esc(topic["title"])}</a></li>'
    html = html[:j] + li + html[j:]
    html = _append_haspart(html, DOMAIN + url, topic["title"])
    f.write_text(html, encoding="utf-8")
    return True

def _append_haspart(html, full_url, title):
    k = html.find('"hasPart":[')
    if k == -1:
        return html
    end = html.find("]}", k)
    if end == -1:
        return html
    item = ',{"@type":"WebPage","name":%s,"url":%s}' % (
        json.dumps(title, ensure_ascii=False), json.dumps(full_url, ensure_ascii=False))
    return html[:end] + item + html[end:]

def quarantine(topic, inner_html, verdict):
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    (QUARANTINE / f'{topic["slug"]}.html').write_text(inner_html, encoding="utf-8")
    (QUARANTINE / f'{topic["slug"]}.qa.json').write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")

def log(rec):
    with open(MANIFEST, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
