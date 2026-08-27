# Integration (join) — after Pillar A and Pillar B unit tests are green

Imports **both** packages. Not part of the Pillar A teammate zip.

To run later, put both `pillar-a/poc` and `pillar-b/poc` on `PYTHONPATH` (or install editable) and point fixtures at `integration/fixtures/lab_checkout` (mixed metric + topo stream).

Join modules: `join/harness.py`, `join/maintain.py`.
