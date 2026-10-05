# زندگی‌نامه‌ی من — سیدحسن جعفری

The memoir of Seyed Hasan Jafari, published as a small book site:
<https://daei-hassan.github.io/bio/>

The book is in three languages, each in its own folder of the site:

| Address | Language |
|---|---|
| `/fa/` | Persian, the original. The site's front address opens this one. |
| `/en/` | English translation |
| `/pt/` | Portuguese translation (European Portuguese) |

Each language has a **reading version**: one page per chapter, laid out for
phones and computers, with links to the same chapter in the other languages.

Persian also has a **page-turning version** (`/fa/flip/`), the printed pages as
images turned like a book, and the PDF. The translations link to these as the
original Persian edition.

## Where things are

| Path | What it is |
|---|---|
| `docs/text/fa/zendegi-nameh-final.md` | The Persian text. Source for the Persian reading version and the EPUB. |
| `docs/text/fa/zendegi-nameh-final.pdf` | The printed book. Source for the page-turning version and the download. |
| `docs/text/en/book.md` | The English translation. |
| `docs/text/pt/book.md` | The Portuguese translation. |
| `docs/text/translation-notes.md` | Rules both translations follow, and questions for the author. Not published. |
| `docs/text/translation-names.md` | The fixed spelling of every name, place and term, and every date, in both languages. Not published. |
| `src/` | Stylesheet, scripts, typefaces and the page images. |
| `build.py` | Builds the site into `_site/` and the EPUB into `dist/` (neither is committed). |
| `epub.py` | Writes the EPUB file. Called by `build.py`. |
| `src/epub/` | Stylesheet and cover image of the EPUB. |
| `tools/render_pages.sh` | Re-creates the page images from the PDF. |
| `.github/workflows/pages.yml` | Builds and publishes the site on every push to `main`. |

## Fixing the text

Edit the file for that language and push to `main`. The site rebuilds itself in
about a minute. You can do this from the GitHub website without any tools.

The build understands only what the files use today:

- `## فصل اول: تولد` or `## Chapter One: Birth` starts a chapter, `### …` starts
  a section inside it.
- A blank line separates paragraphs.
- Lines of verse are written as `*…*<br>`, one per line.
- `**bold**` and `*italic*`.

Anything else (tables, links, lists inside a chapter) stops the build with an error
naming the file and line, so a mistake cannot be published silently.

The page-turning version and the PDF download do not change when the Markdown
changes. They come from the PDF.

## Translations

A translation follows the Persian paragraph for paragraph: the same chapters,
the same sections, one paragraph for each Persian paragraph. The build checks
this and stops, naming the file and line, if a paragraph or heading was
dropped, added, merged or split.

So two things need care:

- **A change to the Persian text needs the same change in both translations.**
  Rewording a paragraph does not stop the build, so nothing will remind you.
  Adding or removing a paragraph does stop it until the translations match.
- **Do not split or join paragraphs in a translation**, even where it would
  read better.

Spellings of names and places are fixed in `docs/text/translation-names.md`
(chapter 1 in `translation-notes.md`). Check there before changing one, and
change it everywhere.

A translation is published only when all its chapters are in. Until then
`python3 build.py` skips it and says so. To look at an unfinished one on your
own computer, run `python3 build.py --drafts`.

To add a language, add its file under `docs/text/` and an entry for it in
`LANGS` at the top of `build.py`.

## The EPUB file

`python3 build.py` also writes `dist/zendegi-nameh-final.epub`, the Persian
book as a single file to send to readers. It opens in Apple Books, Google Play
Books and other e-book apps, where the reader chooses the text size.

It is built from the same Markdown file as the Persian reading version, so it
follows every fix to the text. It is not published on the site.

Its cover is a picture of the first page of the PDF. To re-create it after
replacing the PDF:

```sh
pdftoppm -jpeg -jpegopt quality=85 -r 150 -f 1 -l 1 -singlefile \
  docs/text/fa/zendegi-nameh-final.pdf src/epub/cover
```

## Replacing the PDF

1. Replace `docs/text/fa/zendegi-nameh-final.pdf`.
2. Run `tools/render_pages.sh` (needs `brew install poppler webp`).
3. If the page count or the pages chapters start on have changed, update
   `PAGE_COUNT` and `CHAPTER_PAGES` at the top of `build.py`.
4. If the wording changed, make the same changes in
   `docs/text/fa/zendegi-nameh-final.md`, and then in both translations. The
   reading versions are built from those files, not from the PDF.
5. Commit and push.

## Previewing on your own computer

```sh
python3 build.py
python3 -m http.server --directory _site 8000
```

Then open <http://localhost:8000/>. `build.py` needs Python 3 and nothing else.
To preview the EPUB, open `dist/zendegi-nameh-final.epub` in Apple Books.

## Old addresses

Before the translations, the Persian book sat at the front address
(`/fasl-1.html`, `/flip/`). Those addresses still work: the build leaves a small
page at each one that sends the reader to the same place under `/fa/`.

## Search engines

Every page carries a `noindex` tag, so search engines are asked not to list the
book. To allow listing, empty the `ROBOTS` line near the top of `build.py`.

## Licences of bundled files

- Persian typeface: Noto Naskh Arabic, SIL Open Font License (`src/fonts/OFL.txt`).
- Latin typeface: Source Serif 4, SIL Open Font License (`src/fonts/OFL-source-serif-4.txt`).
- Page-turning: StPageFlip 2.0.7, MIT (`src/flip/page-flip.LICENSE`).
