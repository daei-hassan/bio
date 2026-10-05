#!/usr/bin/env python3
"""Build the book site from docs/text/zendegi-nameh-final.md into _site/.

Standard library only:  python3 build.py
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "docs" / "text" / "zendegi-nameh-final.md"
PDF = ROOT / "docs" / "text" / "zendegi-nameh-final.pdf"
SRC = ROOT / "src"
OUT = ROOT / "_site"

# Printed page each chapter starts on in the PDF, and the PDF's page count.
# Used for chapter lengths in the contents and for chapter jumps in the flipbook.
CHAPTER_PAGES = [5, 18, 46, 78, 84, 117, 122, 139]
PAGE_COUNT = 204

# Remove this line's content to let search engines list the site.
ROBOTS = '<meta name="robots" content="noindex">'

VERSE_LINE = re.compile(r"^\*[^*]+\*(<br>)?$")
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n):
    return str(n).translate(FA_DIGITS)


def fail(line_no, message):
    sys.exit(f"{SOURCE.name}:{line_no}: {message}")


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


def parse():
    lines = list(enumerate(SOURCE.read_text(encoding="utf-8").split("\n"), 1))

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
        if heading == "فهرست مطالب":
            continue  # regenerated from the headings
        if ":" not in heading:
            fail(section["line"], 'chapter headings must look like "## فصل اول: تولد"')
        label, title = (part.strip() for part in heading.split(":", 1))
        chapter = {"label": label, "title": title, "sections": [], "body": []}
        for start, block in blocks(section["lines"]):
            if block[0].startswith("#"):
                if not block[0].startswith("### ") or len(block) != 1:
                    fail(start, "only ### sub-headings are supported inside a chapter")
                text = block[0][4:].strip()
                anchor = f"s{len(chapter['sections']) + 1}"
                chapter["sections"].append({"id": anchor, "title": text})
                chapter["body"].append(f'<h2 id="{anchor}">{inline(text, start)}</h2>')
            else:
                chapter["body"].append(render_block(start, block))
        book["chapters"].append(chapter)

    if len(book["chapters"]) != len(CHAPTER_PAGES):
        sys.exit(f"{len(book['chapters'])} chapters found but CHAPTER_PAGES lists {len(CHAPTER_PAGES)}")
    ends = CHAPTER_PAGES[1:] + [PAGE_COUNT + 1]
    for n, chapter in enumerate(book["chapters"], 1):
        chapter["n"] = n
        chapter["file"] = f"fasl-{n}.html"
        chapter["page"] = CHAPTER_PAGES[n - 1]
        chapter["length"] = ends[n - 1] - CHAPTER_PAGES[n - 1]
    return book


def head(title, description=None):
    meta = f'\n  <meta name="description" content="{html.escape(description)}">' if description else ""
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {ROBOTS}
  <title>{html.escape(title)}</title>{meta}
  <link rel="preload" href="fonts/noto-naskh-arabic-arabic.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="book.css">
</head>"""


ORNAMENT = '<div class="orn" aria-hidden="true">◆</div>'


def index_page(book):
    items = []
    for c in book["chapters"]:
        subs = "".join(
            f'\n          <li><a href="{c["file"]}#{s["id"]}">{html.escape(s["title"])}</a></li>'
            for s in c["sections"]
        )
        subs = f"\n        <ol>{subs}\n        </ol>" if subs else ""
        items.append(
            f"""      <li>
        <a href="{c['file']}"><span class="no">{c['label']}</span><span class="t">{html.escape(c['title'])}</span><span class="dots"></span><span class="len">{fa(c['length'])} صفحه</span></a>{subs}
      </li>"""
        )
    toc = "\n".join(items)
    title = f"{book['title']} — {book['author']}"
    return f"""{head(title, f"{book['title']}، {book['author']}")}
<body>

  <header class="sheet cover">
    <h1>{html.escape(book['title'])}</h1>
    {ORNAMENT}
    <p class="part">{book['part']}</p>
    <p class="subtitle">{book['subtitle']}</p>
    <p class="years">{book['years']}</p>
    <p class="author">{html.escape(book['author'])}</p>
    <nav class="actions">
      <a class="primary" id="start" href="fasl-1.html">آغاز مطالعه</a>
      <a href="#fehrest">فهرست</a>
      <a href="flip/">نسخه‌ی ورق‌زدنی</a>
      <a href="{PDF.name}">دریافت PDF</a>
    </nav>
  </header>

  <section class="sheet dedication">
    <p>{book['dedication']}</p>
  </section>

  <section class="sheet dedication">
    <p>{book['opening']}</p>
  </section>

  <main class="sheet" id="fehrest">
    <h2 class="toc-title">فهرست مطالب</h2>
    {ORNAMENT}
    <ol class="toc">
{toc}
    </ol>
  </main>

  <script src="reader.js"></script>
</body>
</html>
"""


def chapter_page(book, c):
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
        prev = '<a class="prev" href="index.html#fehrest"><small>→ بازگشت</small>فهرست مطالب</a>'
    else:
        p = chapters[c["n"] - 2]
        prev = f'<a class="prev" href="{p["file"]}"><small>→ فصل قبل</small>{html.escape(p["title"])}</a>'
    if c["n"] == len(chapters):
        nxt = '<a class="next" href="index.html#fehrest"><small>پایان ←</small>فهرست مطالب</a>'
    else:
        n = chapters[c["n"]]
        nxt = f'<a class="next" href="{n["file"]}"><small>فصل بعد ←</small>{html.escape(n["title"])}</a>'

    body = "\n      ".join(c["body"])
    title = f"{c['label']}: {c['title']} — {book['title']}"
    return f"""{head(title)}
<body data-chapter="{c['n']}" data-title="{html.escape(c['label'])}">

  <article class="sheet">
    <div class="running-head">
      <a href="index.html">{html.escape(book['title'])}</a>
      <details class="contents">
        <summary>فهرست ☰</summary>
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
    <p class="folio">فصل {fa(c['n'])} از {fa(len(chapters))}</p>
  </article>

  <script src="reader.js"></script>
</body>
</html>
"""


def main():
    book = parse()

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT, ignore=shutil.ignore_patterns(".DS_Store"))
    shutil.copy2(PDF, OUT / PDF.name)
    (OUT / ".nojekyll").write_text("")

    pages = sorted((OUT / "flip" / "pages").glob("p*.webp"))
    if len(pages) != PAGE_COUNT:
        sys.exit(f"src/flip/pages has {len(pages)} images but PAGE_COUNT is {PAGE_COUNT}; run tools/render_pages.sh")

    (OUT / "index.html").write_text(index_page(book), encoding="utf-8")
    for c in book["chapters"]:
        (OUT / c["file"]).write_text(chapter_page(book, c), encoding="utf-8")

    flip = {
        "pages": PAGE_COUNT,
        "chapters": [{"title": f"{c['label']}: {c['title']}", "page": c["page"]} for c in book["chapters"]],
    }
    (OUT / "flip" / "chapters.js").write_text(
        "var BOOK = " + json.dumps(flip, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8"
    )

    paragraphs = sum(len(c["body"]) for c in book["chapters"])
    print(f"{len(book['chapters'])} chapters, {paragraphs} blocks, {PAGE_COUNT} flipbook pages -> {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
