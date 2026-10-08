#!/usr/bin/env python3
"""Build the book from docs/text/<language>/: the site into _site/ and the
Persian EPUB file into dist/.

Standard library only:  python3 build.py
Add --drafts to also build translations that are not finished yet.
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

import epub

ROOT = Path(__file__).resolve().parent
TEXT = ROOT / "docs" / "text"
PDF = TEXT / "fa" / "zendegi-nameh-final.pdf"
SRC = ROOT / "src"
OUT = ROOT / "_site"
EPUB = ROOT / "dist" / "zendegi-nameh-final.epub"

# Printed page each chapter starts on in the PDF, and the PDF's page count.
# Used for chapter lengths in the contents and for chapter jumps in the flipbook.
CHAPTER_PAGES = [4, 10, 23, 37, 40, 54, 57, 65]
PAGE_COUNT = 93

# Remove this line's content to let search engines list the site.
ROBOTS = '<meta name="robots" content="noindex">'

VERSE_LINE = re.compile(r"^\*[^*]+\*(<br>)?$")
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# One entry per language, published in its own folder. Persian is the original;
# a translation must match it chapter for chapter and paragraph for paragraph.
# "contents" is the "## " heading of the hand-written contents list, which is
# skipped because the contents are regenerated from the headings.
LANGS = {
    "fa": {
        "source": TEXT / "fa" / "zendegi-nameh-final.md",
        "name": "فارسی",
        "dir": "rtl",
        "prefix": "fasl",
        "font": "noto-naskh-arabic-arabic.woff2",
        "contents": "فهرست مطالب",
        "toc": "فهرست",
        "start": "آغاز مطالعه",
        "resume": "ادامه‌ی مطالعه",
        "flip": "نسخه‌ی ورق‌زدنی",
        "pdf": "دریافت PDF",
        "pages": "{n} صفحه",
        "menu": "فهرست ☰",
        "back": "→ بازگشت",
        "prev": "→ فصل قبل",
        "next": "فصل بعد ←",
        "end": "پایان ←",
        "folio": "فصل {n} از {total}",
        "note": "",
    },
    "en": {
        "source": TEXT / "en" / "book.md",
        "name": "English",
        "dir": "ltr",
        "prefix": "chapter",
        "font": "source-serif-4-latin.woff2",
        "contents": "Contents",
        "toc": "Contents",
        "start": "Start reading",
        "resume": "Continue reading",
        "flip": "Page-turning edition (Persian)",
        "pdf": "PDF (Persian)",
        "menu": "Contents ☰",
        "back": "← Back",
        "prev": "← Previous chapter",
        "next": "Next chapter →",
        "end": "The end →",
        "folio": "Chapter {n} of {total}",
        "note": "Translated from the Persian",
    },
    "pt": {
        "source": TEXT / "pt" / "book.md",
        "name": "Português",
        "dir": "ltr",
        "prefix": "capitulo",
        "font": "source-serif-4-latin.woff2",
        "contents": "Índice",
        "toc": "Índice",
        "start": "Começar a ler",
        "resume": "Continuar a ler",
        "flip": "Edição para folhear (em persa)",
        "pdf": "PDF (em persa)",
        "menu": "Índice ☰",
        "back": "← Voltar",
        "prev": "← Capítulo anterior",
        "next": "Capítulo seguinte →",
        "end": "Fim →",
        "folio": "Capítulo {n} de {total}",
        "note": "Traduzido do persa",
    },
}


class Problem(Exception):
    """A line of a source file that the build will not publish."""


def fail(line_no, message):
    raise Problem(f"{line_no}: {message}")


def num(book, n):
    return str(n).translate(FA_DIGITS) if book["code"] == "fa" else str(n)


def inline(text, line_no):
    """Escape text and convert **bold** and *italic*."""
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", out)
    if "*" in out or "`" in out or "](" in out:
        fail(line_no, "markup this build does not support (stray *, code or link)")
    return out


def blocks(lines):
    """Yield (first_line_no, [lines]) for each run of non-blank lines."""
    block, start = [], 0
    for no, line in lines:
        if line.strip():
            if not block:
                start = no
            block.append(line.rstrip())
        elif block:
            yield start, block
            block = []
    if block:
        yield start, block


def strip_br(line):
    return line[:-4].rstrip() if line.endswith("<br>") else line


def render_block(start, block):
    """Convert one block of chapter text to HTML."""
    first = block[0]
    if any("<" in strip_br(line) for line in block):
        fail(start, "HTML other than a line-ending <br> is not supported")
    if re.match(r"^(>|\||[-+*] |\d+\. |!\[|```|---\s*$)", first.lstrip()):
        fail(start, "only paragraphs, ### headings and verse are supported in chapters")
    if all(VERSE_LINE.match(line) for line in block):
        verse = "<br>\n".join(inline(strip_br(line)[1:-1], start) for line in block)
        return f'<p class="verse">{verse}</p>'
    parts = []
    for line in block:
        parts.append(inline(strip_br(line), start) + ("<br>" if line.endswith("<br>") else ""))
    return "<p>" + "\n".join(parts) + "</p>"


def parse(code):
    lang = LANGS[code]
    source = lang["source"].relative_to(ROOT)
    try:
        return dict(read_book(lang), code=code, lang=lang, source=source)
    except Problem as problem:
        sys.exit(f"{source}:{problem}")


def read_book(lang):
    lines = list(enumerate(lang["source"].read_text(encoding="utf-8").split("\n"), 1))

    # Split into the part before the first "## " and one section per "## ".
    sections, current = [], {"heading": None, "line": 1, "lines": []}
    for no, line in lines:
        if line.startswith("## "):
            sections.append(current)
            current = {"heading": line[3:].strip(), "line": no, "lines": []}
        else:
            current["lines"].append((no, line))
    sections.append(current)

    starts, front = zip(*blocks(sections[0]["lines"]))
    if len(front) != 5 or not front[0][0].startswith("# ") or len(front[1]) != 3:
        fail(1, "expected: # title, part<br> + subtitle<br> + years, **author**, *dedication*, *opening line*")
    book = {
        "title": front[0][0][2:].strip(),
        "part": inline(strip_br(front[1][0]), starts[1]),
        "subtitle": inline(strip_br(front[1][1]), starts[1] + 1),
        "years": inline(front[1][2], starts[1] + 2),
        "author": front[2][0].strip("*"),
        "dedication": "<br>\n      ".join(inline(strip_br(line), starts[3]) for line in front[3]),
        "opening": inline(front[4][0], starts[4]),
        "chapters": [],
    }

    for section in sections[1:]:
        heading = section["heading"]
        if heading == lang["contents"]:
            continue  # regenerated from the headings
        if ":" not in heading:
            fail(section["line"], 'chapter headings must look like "## فصل اول: تولد" or "## Chapter One: Birth"')
        label, title = (part.strip() for part in heading.split(":", 1))
        # "marks" records the line and kind of every block, to compare a translation with the original.
        chapter = {"label": label, "title": title, "line": section["line"], "sections": [], "body": [], "marks": []}
        for start, block in blocks(section["lines"]):
            if block[0].startswith("#"):
                if not block[0].startswith("### ") or len(block) != 1:
                    fail(start, "only ### sub-headings are supported inside a chapter")
                text = block[0][4:].strip()
                anchor = f"s{len(chapter['sections']) + 1}"
                chapter["sections"].append({"id": anchor, "title": text})
                chapter["body"].append(f'<h2 id="{anchor}">{inline(text, start)}</h2>')
                chapter["marks"].append((start, "section heading"))
            else:
                chapter["body"].append(render_block(start, block))
                verse = chapter["body"][-1].startswith('<p class="verse">')
                chapter["marks"].append((start, f"{len(block)}-line verse" if verse else "paragraph"))
        book["chapters"].append(chapter)

    for n, chapter in enumerate(book["chapters"], 1):
        chapter["n"] = n
        chapter["file"] = f"{lang['prefix']}-{n}.html"
    return book


def check_matches(original, book):
    """Stop unless a translation follows the original block for block."""
    if len(book["chapters"]) > len(original["chapters"]):
        extra = book["chapters"][len(original["chapters"])]
        sys.exit(f"{book['source']}:{extra['line']}: the Persian has only {len(original['chapters'])} chapters")
    for theirs, ours in zip(original["chapters"], book["chapters"]):
        where = f"chapter {ours['n']}"
        for (their_line, their_kind), (line, kind) in zip(theirs["marks"], ours["marks"]):
            if kind != their_kind:
                sys.exit(
                    f"{book['source']}:{line}: {where} has a {kind} here"
                    f" where the Persian has a {their_kind} ({original['source']}:{their_line})"
                )
        if len(ours["marks"]) != len(theirs["marks"]):
            line = ours["marks"][-1][0] if ours["marks"] else ours["line"]
            sys.exit(
                f"{book['source']}:{line}: {where} ends with {len(ours['marks'])} paragraphs and headings"
                f" but the Persian has {len(theirs['marks'])}; one was dropped, added, merged or split"
            )


def head(book, title, description=None, alternates=""):
    lang = book["lang"]
    meta = f'\n  <meta name="description" content="{html.escape(description)}">' if description else ""
    return f"""<!doctype html>
<html lang="{book['code']}" dir="{lang['dir']}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {ROBOTS}
  <title>{html.escape(title)}</title>{meta}{alternates}
  <link rel="preload" href="../fonts/{lang['font']}" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="../book.css">
</head>"""


def same_page(other, n):
    """Address, from a sibling language folder, of chapter n (or the cover) in another language."""
    chapters = other["chapters"]
    page = chapters[n - 1]["file"] if n and n <= len(chapters) else "index.html"
    return f"../{other['code']}/{page}"


def alternates(site, book, n=None):
    return "".join(
        f'\n  <link rel="alternate" hreflang="{other["code"]}" href="{same_page(other, n)}">'
        for other in site
        if other is not book
    )


def language_links(site, book, n=None, short=False, indent="    "):
    """Links to the same page in the other published languages; nothing if there are none."""
    if len(site) < 2:
        return ""
    items = []
    for other in site:
        code = other["code"]
        label = code.upper() if short else other["lang"]["name"]
        if other is book:
            items.append(f'<span lang="{code}" aria-current="true">{label}</span>')
        else:
            items.append(f'<a lang="{code}" hreflang="{code}" href="{same_page(other, n)}">{label}</a>')
    joined = f"\n{indent}  ".join(items)
    return f'\n{indent}<nav class="langs">\n{indent}  {joined}\n{indent}</nav>'


ORNAMENT = '<div class="orn" aria-hidden="true">◆</div>'


def index_page(site, book):
    lang = book["lang"]
    items = []
    for c in book["chapters"]:
        subs = "".join(
            f'\n          <li><a href="{c["file"]}#{s["id"]}">{html.escape(s["title"])}</a></li>'
            for s in c["sections"]
        )
        subs = f"\n        <ol>{subs}\n        </ol>" if subs else ""
        length = ""
        if "length" in c:  # printed pages, known only for the Persian edition
            pages = lang["pages"].format(n=num(book, c["length"]))
            length = f'<span class="dots"></span><span class="len">{pages}</span>'
        items.append(
            f"""      <li>
        <a href="{c['file']}"><span class="no">{c['label']}</span><span class="t">{html.escape(c['title'])}</span>{length}</a>{subs}
      </li>"""
        )
    toc = "\n".join(items)
    title = f"{book['title']} — {book['author']}"
    separator = "، " if book["code"] == "fa" else ", "
    note = f'\n    <p class="note">{lang["note"]}</p>' if lang["note"] else ""
    original = "" if book["code"] == "fa" else "../fa/"
    first = book["chapters"][0]["file"]
    return f"""{head(book, title, book['title'] + separator + book['author'], alternates(site, book))}
<body>

  <header class="sheet cover">
    <h1>{html.escape(book['title'])}</h1>
    {ORNAMENT}
    <p class="part">{book['part']}</p>
    <p class="subtitle">{book['subtitle']}</p>
    <p class="years">{book['years']}</p>
    <p class="author">{html.escape(book['author'])}</p>{note}
    <nav class="actions">
      <a class="primary" id="start" href="{first}" data-prefix="{lang['prefix']}" data-resume="{lang['resume']}">{lang['start']}</a>
      <a href="#fehrest">{lang['toc']}</a>
      <a href="{original}flip/">{lang['flip']}</a>
      <a href="{original}{PDF.name}">{lang['pdf']}</a>
    </nav>{language_links(site, book)}
  </header>

  <section class="sheet dedication">
    <p>{book['dedication']}</p>
  </section>

  <section class="sheet dedication">
    <p>{book['opening']}</p>
  </section>

  <main class="sheet" id="fehrest">
    <h2 class="toc-title">{lang['contents']}</h2>
    {ORNAMENT}
    <ol class="toc">
{toc}
    </ol>
  </main>

  <script src="../reader.js"></script>
</body>
</html>
"""


def chapter_page(site, book, c):
    lang = book["lang"]
    chapters = book["chapters"]
    menu = []
    for other in chapters:
        name = f"{other['label']}: {html.escape(other['title'])}"
        if other is c:
            subs = "".join(
                f'\n              <li><a href="#{s["id"]}">{html.escape(s["title"])}</a></li>'
                for s in c["sections"]
            )
            subs = f"\n            <ol>{subs}\n            </ol>\n          " if subs else ""
            menu.append(f'          <li aria-current="page">{name}{subs}</li>')
        else:
            menu.append(f'          <li><a href="{other["file"]}">{name}</a></li>')
    menu = "\n".join(menu)

    if c["n"] == 1:
        prev = f'<a class="prev" href="index.html#fehrest"><small>{lang["back"]}</small>{lang["contents"]}</a>'
    else:
        p = chapters[c["n"] - 2]
        prev = f'<a class="prev" href="{p["file"]}"><small>{lang["prev"]}</small>{html.escape(p["title"])}</a>'
    if c["n"] == len(chapters):
        nxt = f'<a class="next" href="index.html#fehrest"><small>{lang["end"]}</small>{lang["contents"]}</a>'
    else:
        n = chapters[c["n"]]
        nxt = f'<a class="next" href="{n["file"]}"><small>{lang["next"]}</small>{html.escape(n["title"])}</a>'

    body = "\n      ".join(c["body"])
    title = f"{c['label']}: {c['title']} — {book['title']}"
    folio = lang["folio"].format(n=num(book, c["n"]), total=num(book, len(chapters)))
    return f"""{head(book, title, alternates=alternates(site, book, c['n']))}
<body data-chapter="{c['n']}" data-title="{html.escape(c['label'])}">

  <article class="sheet">
    <div class="running-head">
      <a href="index.html">{html.escape(book['title'])}</a>{language_links(site, book, c['n'], short=True, indent="      ")}
      <details class="contents">
        <summary>{lang['menu']}</summary>
        <ol>
{menu}
        </ol>
      </details>
    </div>

    <header class="opener">
      <p class="no">{c['label']}</p>
      <h1>{html.escape(c['title'])}</h1>
      {ORNAMENT}
    </header>

    <div class="prose">
      {body}
    </div>

    <nav class="chapter-nav">
      {prev}
      {nxt}
    </nav>
    <p class="folio">{folio}</p>
  </article>

  <script src="../reader.js"></script>
</body>
</html>
"""


def forward_page(book, target):
    """A page left at an address from before the languages had folders; it sends the reader on."""
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  {ROBOTS}
  <title>{html.escape(book['title'])}</title>
  <link rel="canonical" href="{target}">
  <script>location.replace("{target}" + location.search + location.hash);</script>
  <meta http-equiv="refresh" content="0; url={target}">
</head>
<body>
  <p><a href="{target}">{html.escape(book['title'])}</a></p>
</body>
</html>
"""


def main():
    drafts = "--drafts" in sys.argv[1:]

    original = parse("fa")
    chapters = original["chapters"]
    if len(chapters) != len(CHAPTER_PAGES):
        sys.exit(f"{len(chapters)} chapters found but CHAPTER_PAGES lists {len(CHAPTER_PAGES)}")
    ends = CHAPTER_PAGES[1:] + [PAGE_COUNT + 1]
    for chapter, page, end in zip(chapters, CHAPTER_PAGES, ends):
        chapter["page"] = page
        chapter["length"] = end - page

    # A translation is published once every chapter is in; until then only --drafts builds it.
    site, notes = [original], []
    for code, lang in LANGS.items():
        if code == "fa" or not lang["source"].exists():
            continue
        book = parse(code)
        check_matches(original, book)
        done = len(book["chapters"])
        if done < len(chapters):
            state = "built as a draft" if drafts else "not published (--drafts to preview)"
            notes.append(f"{code}: {done} of {len(chapters)} chapters translated, {state}")
            if not (drafts and done):
                continue
        site.append(book)

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT, ignore=shutil.ignore_patterns(".DS_Store", "epub", "flip"))
    shutil.copytree(SRC / "flip", OUT / "fa" / "flip", ignore=shutil.ignore_patterns(".DS_Store"))
    shutil.copy2(PDF, OUT / "fa" / PDF.name)
    (OUT / ".nojekyll").write_text("")

    pages = sorted((OUT / "fa" / "flip" / "pages").glob("p*.webp"))
    if len(pages) != PAGE_COUNT:
        sys.exit(f"src/flip/pages has {len(pages)} images but PAGE_COUNT is {PAGE_COUNT}; run tools/render_pages.sh")

    for book in site:
        folder = OUT / book["code"]
        folder.mkdir(exist_ok=True)
        (folder / "index.html").write_text(index_page(site, book), encoding="utf-8")
        for c in book["chapters"]:
            (folder / c["file"]).write_text(chapter_page(site, book, c), encoding="utf-8")

    flip = {
        "pages": PAGE_COUNT,
        "chapters": [{"title": f"{c['label']}: {c['title']}", "page": c["page"]} for c in chapters],
    }
    (OUT / "fa" / "flip" / "chapters.js").write_text(
        "var BOOK = " + json.dumps(flip, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8"
    )

    # Addresses from before the Persian edition moved into fa/ keep working.
    (OUT / "index.html").write_text(forward_page(original, "fa/"), encoding="utf-8")
    for c in chapters:
        (OUT / c["file"]).write_text(forward_page(original, f"fa/{c['file']}"), encoding="utf-8")
    (OUT / "flip").mkdir()
    (OUT / "flip" / "index.html").write_text(forward_page(original, "../fa/flip/"), encoding="utf-8")
    shutil.copy2(PDF, OUT / PDF.name)

    epub.write(original, EPUB)

    paragraphs = sum(len(c["body"]) for c in chapters)
    languages = ", ".join(book["code"] for book in site)
    print(f"{len(chapters)} chapters, {paragraphs} blocks, {PAGE_COUNT} flipbook pages, languages: {languages} -> {OUT.relative_to(ROOT)}/")
    print(f"EPUB -> {EPUB.relative_to(ROOT)}")
    for note in notes:
        print(note)


if __name__ == "__main__":
    main()
