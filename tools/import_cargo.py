"""One-time importer: pulls page content + media from the live Cargo site into src/ and static/.

Run:  py tools/import_cargo.py
Re-running overwrites src/pages/*.html with fresh copies from Cargo, so only do it
before you start hand-editing the src files.
"""
import json, re, subprocess, urllib.request
from pathlib import Path

SITE = "https://seungki.net"
ROOT = Path(__file__).resolve().parent.parent
SRC, MEDIA = ROOT / "src", ROOT / "static" / "media"
PAGES = ["", "information", "project-2018-atc", "project-aespa-xr-show", "project-ailee",
         "project-aomg", "project-being-faust", "project-dpr-ian", "project-galaxy-unpacked-july-2023",
         "project-jtbc-lectures", "project-lamborghini-revuelto-korea", "project-local-election",
         "project-love-and-money", "project-nab-show-2023", "project-our-season",
         "project-virtual-camera-animation-demo"]
UA = {"User-Agent": "Mozilla/5.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r:
        return r.read()


def state(path):
    html = get(f"{SITE}/{path}").decode("utf8")
    i = html.index("window.__PRELOADED_STATE__=") + len("window.__PRELOADED_STATE__=")
    return json.JSONDecoder().raw_decode(html[i:])[0]


def attrs(s):
    return dict(re.findall(r'([a-z-]+)="([^"]*)"', s))


saved = {}  # remote url -> local filename


def download(url, name):
    if url in saved:
        return saved[url]
    name = re.sub(r"[^A-Za-z0-9._-]", "-", name)
    if (MEDIA / name).exists() and name in saved.values():  # name clash between different files
        name = f"{len(saved)}-{name}"
    dest = MEDIA / name
    if not dest.exists():
        print("  downloading", name)
        dest.write_bytes(get(url))
        if dest.suffix == ".mp4" and dest.stat().st_size > 40e6:  # GitHub rejects files over 100MB
            print("  shrinking", name)
            tmp = dest.with_suffix(".tmp.mp4")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", dest, "-vf", "scale=-2:'min(1080,ih)'",
                            "-c:v", "libx264", "-crf", "26", "-preset", "slow", "-c:a", "aac", "-b:a", "128k",
                            "-movflags", "+faststart", tmp], check=True)
            tmp.replace(dest)
    saved[url] = name
    return name


def media_item(tag_attrs, media):
    a = attrs(tag_attrs)
    keep = {k: a[k] for k in ("class", "scale", "limit-by") if a.get(k)}
    m = media.get(a.get("hash"), {})
    w, h = a.get("width") or m.get("width") or 16, a.get("height") or m.get("height") or 9
    auto = a.get("autoplay") == "true"
    controls = a.get("browser-default", "true") == "true"

    if m.get("is_url"):  # YouTube / Vimeo
        w, h = (16, 9) if m["url_type"] == "youtube" else (w, h)
        if m["url_type"] == "youtube":
            vid = m["url_id"]
            q = f"autoplay=1&mute=1&loop=1&playlist={vid}&controls=0&playsinline=1" if auto else "rel=0"
            src = f"https://www.youtube-nocookie.com/embed/{vid}?{q}"
        else:
            vid, _, hsh = m["url_id"].partition("/")
            q = ("background=1" if auto else "dnt=1") + (f"&h={hsh}" if hsh else "")
            src = f"https://player.vimeo.com/video/{vid}?{q}"
        inner = (f'<iframe src="{src}" loading="lazy" allow="autoplay; fullscreen; picture-in-picture" '
                 f'allowfullscreen title="{m.get("display_name") or "Video"}"></iframe>')
    elif a.get("src") or m.get("is_video"):  # self-hosted video
        url = a.get("src") or f"https://freight.cargo.site/original/i/{m['hash']}/{m['name']}"
        url = url.replace("cargo.site/original/", "cargo.site/t/original/")
        f = download(url, url.rsplit("/", 1)[1])
        poster = ""
        if a.get("poster") and a["poster"] in media:
            p = media[a["poster"]]
            poster = f' poster="/media/{download(f"https://freight.cargo.site/w/2000/i/{p["hash"]}/{p["name"]}", p["name"])}"'
        flags = " autoplay muted loop playsinline" if auto else ""
        flags += " controls" if controls and not auto else ""
        inner = f'<video src="/media/{f}"{poster}{flags} preload="metadata"></video>'
        keep["class"] = keep.get("class", "").replace("zoomable", "").strip()
    else:  # image
        f = download(f"https://freight.cargo.site/w/2000/i/{m['hash']}/{m['name']}", m["name"])
        inner = f'<img src="/media/{f}" width="{w}" height="{h}" alt="" loading="lazy">'

    if a.get("href"):
        tgt = ' target="_blank" rel="noopener"' if a.get("target") == "_blank" else ""
        inner = f'<a href="{link(a["href"])}"{tgt}>{inner}</a>'
        keep.pop("class", None)
    keep = {k: v for k, v in keep.items() if v}
    out = "".join(f' {k}="{v}"' for k, v in keep.items())
    return f'<media-item{out} style="--w:{w};--h:{h}">{inner}</media-item>'


def link(href):
    if href.startswith(("http", "#", "/")):
        return href
    return {"nav": "#nav", "contact-form": "#contact"}.get(href, f"/{href}/")


def convert(html, media):
    html = re.sub(r"<media-item([^>]*)></media-item>", lambda m: media_item(m.group(1), media), html)
    # dead links on the live site (reading-N pages no longer exist): keep the text, drop the link
    html = re.sub(r'<a[^>]*href="reading-\d"[^>]*>(.*?)</a>', r"\1", html)
    html = re.sub(r'href="([^"]+)"', lambda m: f'href="{link(m.group(1))}"', html)
    html = re.sub(r' rel="history"| class=""| draggable="true"', "", html)
    html = re.sub(r'<text-icon icon="([^"]+)"></text-icon>', r'<svg class="icon"><use href="/icons.svg#\1"></use></svg>', html)
    # hide the old public email address; site.js turns #contact links into a mailto on click
    html = html.replace("t.chung(at)nyu.edu", "Email me")
    html = html.replace('href="https://seungki.net/" target="_blank"', 'href="/"')
    return html.strip() + "\n"


def main():
    MEDIA.mkdir(parents=True, exist_ok=True)
    (SRC / "pages").mkdir(parents=True, exist_ok=True)
    pins = {"header": "header", "header---mobile": "header-mobile", "nav": "nav"}
    for path in PAGES:
        print("page", path or "/")
        st = state(path)
        for p in st["pages"]["byId"].values():
            media = {m["hash"]: m for m in p["media"]}
            body = convert(p["content"] or "", media)
            if p["purl"] in pins:
                out = SRC / f"{pins[p['purl']]}.html"
            else:
                slug = "index" if p["purl"] == "front-page" else p["purl"]
                title = "Tom Chung" if slug == "index" else p["title"].replace("Project - ", "") + " — Tom Chung"
                out = SRC / "pages" / f"{slug}.html"
                body = f"<!-- title: {title} -->\n{body}"
            out.write_text(body, encoding="utf8")
    # body font (SIL Open Font License) — Repro/Favorit are Cargo-only licenses, replaced by free fonts in site.css
    fonts = ROOT / "static" / "fonts"
    fonts.mkdir(exist_ok=True)
    for f in ("RoutedGothic.woff",):
        if not (fonts / f).exists():
            (fonts / f).write_bytes(get(f"https://type.cargo.site/files/{f}"))
    print("done")


if __name__ == "__main__":
    main()
