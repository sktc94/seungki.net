"""Builds the static site into docs/ (which GitHub Pages serves).

    py build.py            build once
    py build.py serve      build, then preview at http://localhost:8000

Edit content in src/ (pages/*.html, header.html, header-mobile.html, nav.html),
styles in static/site.css, then rebuild.
"""
import re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC, STATIC, OUT = ROOT / "src", ROOT / "static", ROOT / "docs"
DOMAIN = "seungki.net"

LAYOUT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="Tom (Seungki) Chung — virtual production pipeline specialist. Unreal Engine, ICVFX/XR, LED volume workflows.">
<link rel="icon" href="/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=Space+Grotesk:wght@300..700&display=swap">
<link rel="stylesheet" href="/site.css">
<script src="/site.js" defer></script>
</head>
<body>
<div class="content">
{header}
{header_mobile}
<div class="pages">
{page}
</div>
{nav}
</div>
</body>
</html>
"""


def page(id_, body, cls=""):
    return (f'<div id="{id_}" class="page {cls}"><div class="page-layout"><div class="page-content">'
            f"<bodycopy>\n{body}</bodycopy></div></div></div>")


def column_sets(html):
    """Give every column-unit an explicit span (Cargo splits unspecified ones evenly; last one fills the rest)."""
    def fix(m):
        attrs, inner = m.group(1), m.group(2)
        units = re.findall(r"<column-unit([^>]*)>", inner)
        spans = [re.search(r'span="(\d+)"', u) for u in units]
        given = sum(int(s.group(1)) for s in spans if s)
        free = [i for i, s in enumerate(spans) if not s]
        each = (12 - given) // len(free) if free else 0
        out = [int(s.group(1)) if s else each for s in spans]
        if out:
            out[-1] = 12 - sum(out[:-1])
        it = iter(out)
        inner = re.sub(r"<column-unit[^>]*>", lambda _: f'<column-unit style="--span:{next(it)}">', inner)
        g = re.search(r'gutter="([\d.]+)(\w*)"', attrs)
        style = f' style="--gutter:{g.group(1)}{g.group(2) or "rem"}"' if g else ""
        return f"<column-set{style}>{inner}</column-set>"
    return re.sub(r"<column-set([^>]*)>(.*?)</column-set>", fix, html, flags=re.S)  # (no nested sets)


def galleries(html):
    """Masonry layout for gallery-columnized: each item goes into the currently shortest column."""
    def fix(m):
        attrs, inner = m.group(1), m.group(2)
        n = int((re.search(r'columns="(\d+)"', attrs) or [0, 2])[1])
        g = (re.search(r'gutter="([^"]+)"', attrs) or [0, "1rem"])[1]
        items = re.findall(r"<media-item.*?</media-item>", inner, re.S)
        cols, heights = [[] for _ in range(n)], [0.0] * n
        for i, it in enumerate(items):
            w, h = re.search(r"--w:([\d.]+);--h:([\d.]+)", it).groups()
            c = heights.index(min(heights))
            cols[c].append(it.replace('style="', f'style="order:{i};', 1))  # order = original sequence on mobile
            heights[c] += float(h) / float(w)
        body = "".join(f'<div class="gc-col">{"".join(c)}</div>' for c in cols)
        return f'<gallery-columnized style="--gutter:{g}">{body}</gallery-columnized>'
    return re.sub(r"<gallery-columnized([^>]*)>(.*?)</gallery-columnized>", fix, html, flags=re.S)


def media_sizes(html):
    """Turn Cargo's scale / limit-by attributes into inline sizes."""
    def fix(m):
        tag = m.group(0)
        scale = re.search(r'scale="([^"]+)"', tag)
        if not scale:
            return tag
        w, h = re.search(r"--w:([\d.]+);--h:([\d.]+)", tag).groups()
        s = scale.group(1)
        size = f"width:min(100%, calc({s} * {w} / {h}))" if 'limit-by="height"' in tag else f"width:{s}"
        return re.sub(r'\s(scale|limit-by)="[^"]*"', "", tag).replace('style="', f'style="{size};', 1)
    return re.sub(r"<media-item[^>]*>", fix, html)


def render(html):
    return media_sizes(galleries(column_sets(html)))


def mark_active(html, url):
    return re.sub(rf'<a href="{re.escape(url)}"', f'<a class="active" href="{url}"', html)


def build():
    OUT.mkdir(exist_ok=True)
    for p in OUT.iterdir():  # empty docs/ but keep the folder (a preview server may be using it)
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.copytree(STATIC, OUT, dirs_exist_ok=True)
    (OUT / "CNAME").write_text(DOMAIN + "\n")
    (OUT / ".nojekyll").write_text("")
    parts = {k: render((SRC / f"{k}.html").read_text(encoding="utf8")) for k in ("header", "header-mobile", "nav")}
    pages = sorted((SRC / "pages").glob("*.html"))
    for f in pages + [None]:
        if f is None:  # 404 page
            slug, title, body = "404", "Page not found — Tom Chung", "<br><br><br><br><br><h2>Page not found.</h2>"
            dest, url = OUT / "404.html", None
        else:
            text = f.read_text(encoding="utf8")
            m = re.match(r"<!-- title: (.*?) -->\n", text)
            title, body = m.group(1), text[m.end():]
            slug = f.stem
            url = "/" if slug == "index" else f"/{slug}/"
            dest = OUT / "index.html" if slug == "index" else OUT / slug / "index.html"
        html = LAYOUT.format(
            title=title,
            header=page("header", parts["header"], "pinned-top overlay desktop-only"),
            header_mobile=page("header-mobile", parts["header-mobile"], "pinned-top overlay mobile-only"),
            page=page("front-page" if slug == "index" else slug, render(body)),
            nav=page("nav", parts["nav"], "pinned-bottom"),
        )
        if url and url != "/":  # Cargo setting: no active state for home links
            html = mark_active(html, url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf8")
    print(f"built {len(pages)} pages into {OUT}")


if __name__ == "__main__":
    build()
    if sys.argv[1:] == ["serve"]:
        import functools, http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=OUT)
        print("preview: http://localhost:8000")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()
