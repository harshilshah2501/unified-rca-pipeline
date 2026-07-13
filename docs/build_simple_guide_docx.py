#!/usr/bin/env python3
"""Build Lean_RCA_Simple_Guide.docx from Lean_RCA_Simple_Guide.md."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt

DOCS = Path(__file__).resolve().parent
MD = DOCS / "Lean_RCA_Simple_Guide.md"
DOCX = DOCS / "Lean_RCA_Simple_Guide.docx"


def main() -> None:
    md = MD.read_text()
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    lines = md.splitlines()
    i = 0
    table_buf: list[str] = []

    def flush_table() -> None:
        nonlocal table_buf
        if not table_buf:
            return
        rows: list[list[str]] = []
        for row in table_buf:
            if set(row.replace("|", "").strip()) <= set("-: "):
                continue
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            rows.append(cells)
        table_buf = []
        if not rows:
            return
        cols = max(len(r) for r in rows)
        t = doc.add_table(rows=len(rows), cols=cols)
        t.style = "Table Grid"
        for ri, row in enumerate(rows):
            for ci in range(cols):
                cell = t.rows[ri].cells[ci]
                cell.text = row[ci] if ci < len(row) else ""
                if ri == 0:
                    for p in cell.paragraphs:
                        for run in p.runs:
                            run.bold = True
        doc.add_paragraph()

    def add_inline(paragraph, text: str) -> None:
        pattern = re.compile(r"(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))")
        pos = 0
        for m in pattern.finditer(text):
            if m.start() > pos:
                paragraph.add_run(text[pos : m.start()])
            token = m.group(1)
            if token.startswith("**"):
                run = paragraph.add_run(token[2:-2])
                run.bold = True
            else:
                link = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
                assert link
                run = paragraph.add_run(f"{link.group(1)} ({link.group(2)})")
                run.italic = True
            pos = m.end()
        if pos < len(text):
            paragraph.add_run(text[pos:])

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("|"):
            table_buf.append(line)
            i += 1
            while i < len(lines) and lines[i].startswith("|"):
                table_buf.append(lines[i])
                i += 1
            flush_table()
            continue
        flush_table()
        if line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=0)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=1)
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=2)
        elif line.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            add_inline(p, line[2:].strip())
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            add_inline(p, line)
        i += 1

    flush_table()
    doc.save(DOCX)
    print(f"Wrote {DOCX} ({DOCX.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
