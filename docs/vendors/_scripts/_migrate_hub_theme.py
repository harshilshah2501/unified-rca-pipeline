#!/usr/bin/env python3
"""One-shot: align docs hub HTML with urca-docs.css + doc-nav.js."""
from __future__ import annotations

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent
THEME_LINK = '<link rel="stylesheet" href="/urca-docs.css" />'
NAV_SCRIPT = '<script src="/doc-nav.js" defer></script>'

# Strip these minified one-liners from inline <style> when migrating (base theme duplicates)
STRIP_LINE = re.compile(
    r"^\s*(?:"
    r"\*\{box-sizing:border-box;\}|"
    r"html\{scroll-behavior:smooth;\}|"
    r"body\{margin:0;font-family:[^}]+\}|"
    r"a\{color:[^}]+\}|"
    r"\.wrap\{max-width:[^}]+\}|"
    r"\.eyebrow\{[^}]+\}|"
    r"h1\{font-size:[^}]+\}|"
    r"h2\{font-size:[^}]+\}|"
    r"\.lead\{[^}]+\}|"
    r"table\{width:100%;border-collapse:[^}]+\}|"
    r"th,td\{text-align:left;vertical-align:top;padding:[^}]+\}|"
    r"th\{color:[^}]+\}|"
    r"p\{margin:[^}]+\}|"
    r"p\{color:var\(--muted\);\}|"
    r"ul\{margin:[^}]+\}|"
    r"li\{margin:[^}]+\}|"
    r"code\{font-family:var\(--mono\)[^}]+\}"
    r")\s*$",
    re.MULTILINE,
)

STRIP_BLOCK = re.compile(
    r":root\s*\{[^}]*--bg:[^}]*\}\s*",
    re.DOTALL,
)


def vendor_class(path: str) -> str:
    p = path.lower()
    if any(x in p for x in ("dd-", "datadog", "dd_")):
        return "vendor-dd"
    if any(x in p for x in ("dt-", "dynatrace", "eleven-subsystem", "davis")):
        return "vendor-dt"
    return "urca-doc"


def article_class(name: str, text: str) -> str:
    if name.endswith("index.html"):
        return "hub-index"
    if "shell" in text[:4000]:
        return ""
    return "article"


def migrate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    orig = text
    changes: list[str] = []

    if "refresh" in text[:500] and "url=" in text[:500]:
        return changes

    # Remove google fonts (doc-nav injects)
    text2 = re.sub(
        r'<link[^>]+fonts\.googleapis\.com[^>]*>\s*',
        "",
        text,
        flags=re.IGNORECASE,
    )
    if text2 != text:
        changes.append("removed google fonts")
        text = text2

    # Inline style: strip duplicate base lines
    def shrink_style(m: re.Match[str]) -> str:
        inner = m.group(1)
        inner = STRIP_BLOCK.sub("", inner)
        lines = []
        for line in inner.splitlines():
            if STRIP_LINE.match(line):
                continue
            lines.append(line)
        cleaned = "\n".join(lines).strip()
        if not cleaned or cleaned in ("/* page-specific */",):
            return ""
        return f"<style>\n{cleaned}\n</style>"

    text2 = re.sub(r"<style>([\s\S]*?)</style>", shrink_style, text, count=0)
    text2 = re.sub(r"\n{3,}", "\n\n", text2)
    if text2 != text:
        changes.append("trimmed inline base CSS")
        text = text2

    # Theme link last in head
    if "/urca-docs.css" not in text:
        text = text.replace("</head>", f"{THEME_LINK}\n</head>", 1)
        changes.append("added urca-docs.css")
    else:
        # ensure last stylesheet before </head>
        text = re.sub(r'<link rel="stylesheet" href="/urca-docs.css"\s*/>\s*', "", text)
        text = text.replace("</head>", f"{THEME_LINK}\n</head>", 1)

    # doc-nav
    if "doc-nav.js" not in text:
        if "</body>" in text:
            text = text.replace("</body>", f"{NAV_SCRIPT}\n</body>", 1)
            changes.append("added doc-nav.js")

    # body classes
    vc = vendor_class(path.name)
    ac = article_class(path.name, text)
    classes = " ".join(c for c in [vc, ac] if c)

    if re.search(r"<body[^>]*class=", text):
        def add_classes(m: re.Match[str]) -> str:
            existing = m.group(1)
            parts = set(existing.split())
            for c in classes.split():
                parts.add(c)
            return f'<body class="{" ".join(sorted(parts))}">'

        text2 = re.sub(r'<body class="([^"]*)">', add_classes, text, count=1)
    else:
        text2 = text.replace("<body>", f'<body class="{classes}">', 1)
        if text2 == text:
            text2 = re.sub(r"<body(\s*)>", f'<body class="{classes}"\\1>', text, count=1)

    if text2 != text:
        changes.append(f"body class={classes}")
        text = text2

    # wrap pages: use .wrap if main-only without shell
    if '<div class="wrap">' in text and 'class="wrap article"' not in text and ac == "article":
        text = text.replace('<div class="wrap">', '<div class="wrap article">', 1)
        changes.append("wrap.article")

    if "<main>" in text and 'class="article"' not in text.split("<main>", 1)[0][-20:]:
        text = text.replace("<main>", '<main class="article">', 1)
        if "main.article" in text:
            changes.append("main.article")

    if text != orig:
        path.write_text(text, encoding="utf-8")

    return changes


def main() -> None:
    updated = 0
    for html in sorted(DOCS.glob("*.html")):
        if html.name.startswith("_"):
            continue
        ch = migrate(html)
        if ch:
            updated += 1
            print(f"{html.name}: {', '.join(ch)}")
    print(f"Done — {updated} files updated")


if __name__ == "__main__":
    main()
