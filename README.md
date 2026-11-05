# seungki.net

Static rebuild of the Cargo site, hosted on GitHub Pages.

## Editing

| What | Where |
|---|---|
| Page content | `src/pages/*.html` (`index.html` = home; first line sets the browser tab title) |
| Top menu (desktop / mobile) | `src/header.html`, `src/header-mobile.html` |
| Project index + footer (bottom of every page) | `src/nav.html` |
| Styles | `static/site.css` |
| Images / videos | `static/media/` → referenced as `/media/name.jpg` |

Then rebuild and preview:

```
py build.py serve      # http://localhost:8000
```

`build.py` writes the finished site to `docs/`. Commit `docs/` along with your edits — GitHub Pages serves that folder.

Cargo-style tags still work in the source: `<column-set gutter="2rem"><column-unit span="8">…</column-unit><column-unit span="4">…</column-unit></column-set>`, and `<media-item style="--w:1920;--h:1080"><img src="/media/x.jpg"></media-item>` (add `class="zoomable"` for click-to-enlarge).

## Going live

1. Create a GitHub repo (e.g. `seungki.net`), then push:
   ```
   git remote add origin https://github.com/<you>/seungki.net.git
   git push -u origin main
   ```
2. Repo → **Settings → Pages** → Source: *Deploy from a branch*, Branch: `main`, folder: `/docs`.
3. Custom domain: `seungki.net` is already set (via `docs/CNAME`). At your domain registrar, replace the Cargo DNS records with:
   - `A` records for `@`: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - `CNAME` for `www` → `<you>.github.io`
4. Once DNS verifies (minutes to a few hours), tick **Enforce HTTPS** in Settings → Pages.
5. Only then cancel Cargo / the Cargo domain add-on. **Check first whether the domain itself is registered through Cargo** — if so, transfer it to a registrar (Cloudflare, Porkbun, Namecheap…) before cancelling, or you'll lose it.

## Notes

- Fonts: Routed Gothic is self-hosted (SIL Open Font License). Repro and Favorit were Cargo-licensed, so Inter and Space Grotesk stand in — change `--font-repro` / `--font-favorit` in `site.css` if you buy the originals.
- Contact: the email address is assembled in `static/site.js` on click and never appears in the HTML.
- `tools/import_cargo.py` was the one-time import from Cargo. Don't re-run it after editing `src/` — it overwrites the pages.
