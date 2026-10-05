# زندگی‌نامه‌ی من — سیدحسن جعفری

The memoir of Seyed Hasan Jafari, published as a small book site:
<https://daei-hassan.github.io/bio/>

The site has two versions of the book:

- **Reading version** — one page per chapter, laid out for phones and computers.
- **Page-turning version** (`/flip/`) — the printed pages as images, turned like a book.

## Where things are

| Path | What it is |
|---|---|
| `docs/text/zendegi-nameh-final.md` | The text. This is the source for the reading version. |
| `docs/text/zendegi-nameh-final.pdf` | The printed book. Source for the page-turning version and the download. |
| `src/` | Stylesheet, scripts, typeface and the page images. |
| `build.py` | Builds the site into `_site/` (not committed). |
| `tools/render_pages.sh` | Re-creates the page images from the PDF. |
| `.github/workflows/pages.yml` | Builds and publishes the site on every push to `main`. |

## Fixing the text

Edit `docs/text/zendegi-nameh-final.md` and push to `main`. The site rebuilds itself in
about a minute. You can do this from the GitHub website without any tools.

The build understands only what the file uses today:

- `## فصل اول: تولد` starts a chapter, `### …` starts a section inside it.
- A blank line separates paragraphs.
- Lines of verse are written as `*…*<br>`, one per line.
- `**bold**` and `*italic*`.

Anything else (tables, links, lists inside a chapter) stops the build with an error
naming the line, so a mistake cannot be published silently.

The page-turning version and the PDF download do not change when the Markdown
changes. They come from the PDF.

## Replacing the PDF

1. Replace `docs/text/zendegi-nameh-final.pdf`.
2. Run `tools/render_pages.sh` (needs `brew install poppler webp`).
3. If the page count or the pages chapters start on have changed, update
   `PAGE_COUNT` and `CHAPTER_PAGES` at the top of `build.py`.
4. Commit and push.

## Previewing on your own computer

```sh
python3 build.py
python3 -m http.server --directory _site 8000
```

Then open <http://localhost:8000/>. `build.py` needs Python 3 and nothing else.

## Search engines

Every page carries a `noindex` tag, so search engines are asked not to list the
book. To allow listing, empty the `ROBOTS` line near the top of `build.py`.

## Licences of bundled files

- Typeface: Noto Naskh Arabic, SIL Open Font License (`src/fonts/OFL.txt`).
- Page-turning: StPageFlip 2.0.7, MIT (`src/flip/page-flip.LICENSE`).
