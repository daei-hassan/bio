"""Write the parsed book as an EPUB 3 file. Called by build.py.

Standard library only.
"""
import html
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

SRC = Path(__file__).resolve().parent / "src"

# Identifies the book to reading apps. Keep it the same for every edition, so a
# new file replaces the old one in a reader's library. A translation gets its own.
BOOK_ID = "urn:uuid:84d40b0b-e023-418a-970a-83801ace2e3b"
LANG, DIRECTION = "fa", "rtl"
CONTENTS = "فهرست مطالب"

ORNAMENT = '<p class="orn" aria-hidden="true">◆</p>'

# (id, path inside the book, source file, media type, manifest properties)
ASSETS = [
    ("css", "book.css", SRC / "epub" / "book.css", "text/css", ""),
    ("cover-image", "cover.jpg", SRC / "epub" / "cover.jpg", "image/jpeg", "cover-image"),
    ("font-arabic", "fonts/noto-naskh-arabic-arabic.woff2", SRC / "fonts" / "noto-naskh-arabic-arabic.woff2", "font/woff2", ""),
    ("font-latin", "fonts/noto-naskh-arabic-latin.woff2", SRC / "fonts" / "noto-naskh-arabic-latin.woff2", "font/woff2", ""),
    ("font-licence", "fonts/OFL.txt", SRC / "fonts" / "OFL.txt", "text/plain", ""),
]

CONTAINER = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def xhtml(fragment):
    """The site's HTML fragments are XHTML apart from the unclosed <br>."""
    return fragment.replace("<br>", "<br/>")


def page(title, body):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{LANG}" xml:lang="{LANG}" dir="{DIRECTION}">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="book.css"/>
</head>
<body>
{body}
</body>
</html>
"""


def title_page(book):
    return f"""  <div class="title-page">
    <h1>{html.escape(book['title'])}</h1>
    {ORNAMENT}
    <p class="part">{xhtml(book['part'])}</p>
    <p class="subtitle">{xhtml(book['subtitle'])}</p>
    <p class="years">{xhtml(book['years'])}</p>
    <p class="author">{html.escape(book['author'])}</p>
  </div>"""


def dedication_page(text):
    return f"""  <div class="dedication">
    <p>{xhtml(text)}</p>
  </div>"""


def contents_page(book):
    items = []
    for c in book["chapters"]:
        subs = "".join(
            f'\n          <li><a href="fasl-{c["n"]}.xhtml#{s["id"]}">{html.escape(s["title"])}</a></li>'
            for s in c["sections"]
        )
        subs = f"\n        <ol>{subs}\n        </ol>\n      " if subs else ""
        name = f"{c['label']}: {html.escape(c['title'])}"
        items.append(f'      <li><a href="fasl-{c["n"]}.xhtml">{name}</a>{subs}</li>')
    toc = "\n".join(items)
    return f"""  <nav epub:type="toc" id="toc">
    <h1>{CONTENTS}</h1>
    <ol>
{toc}
    </ol>
  </nav>"""


def chapter_page(c):
    body = xhtml("\n      ".join(c["body"]))
    return f"""  <section epub:type="chapter">
    <header class="opener">
      <p class="no">{html.escape(c['label'])}</p>
      <h1>{html.escape(c['title'])}</h1>
      {ORNAMENT}
    </header>
    <div class="prose">
      {body}
    </div>
  </section>"""


def package(book, documents):
    items = [
        f'    <item id="{name}" href="{name}.xhtml" media-type="application/xhtml+xml"'
        + (' properties="nav"' if name == "nav" else "")
        + "/>"
        for name, _ in documents
    ]
    for name, href, _, media_type, properties in ASSETS:
        properties = f' properties="{properties}"' if properties else ""
        items.append(f'    <item id="{name}" href="{href}" media-type="{media_type}"{properties}/>')
    manifest = "\n".join(items)
    spine = "\n".join(f'    <itemref idref="{name}"/>' for name, _ in documents)
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="{LANG}" dir="{DIRECTION}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">{BOOK_ID}</dc:identifier>
    <dc:title>{html.escape(book['title'])}</dc:title>
    <dc:creator>{html.escape(book['author'])}</dc:creator>
    <dc:language>{LANG}</dc:language>
    <meta property="dcterms:modified">{modified}</meta>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest>
{manifest}
  </manifest>
  <spine page-progression-direction="{DIRECTION}">
{spine}
  </spine>
</package>
"""


def write(book, out):
    """Write the book to the EPUB file `out`."""
    documents = [
        ("title", page(book["title"], title_page(book))),
        ("dedication", page(book["title"], dedication_page(book["dedication"]))),
        ("opening", page(book["title"], dedication_page(book["opening"]))),
        ("nav", page(CONTENTS, contents_page(book))),
    ]
    for c in book["chapters"]:
        documents.append((f"fasl-{c['n']}", page(f"{c['label']}: {c['title']}", chapter_page(c))))

    files = {"META-INF/container.xml": CONTAINER, "OEBPS/content.opf": package(book, documents)}
    for name, text in documents:
        files[f"OEBPS/{name}.xhtml"] = text

    # A reading app refuses a book with one malformed file, so stop here instead.
    for name, text in files.items():
        try:
            ElementTree.fromstring(text.encode("utf-8"))
        except ElementTree.ParseError as error:
            sys.exit(f"{out.name}: {name} is not well-formed XML: {error}")

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w") as book_file:
        # The format requires this entry first and uncompressed.
        book_file.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        for name, text in files.items():
            book_file.writestr(name, text, zipfile.ZIP_DEFLATED)
        for _, href, source, _, _ in ASSETS:
            book_file.write(source, f"OEBPS/{href}", zipfile.ZIP_DEFLATED)
