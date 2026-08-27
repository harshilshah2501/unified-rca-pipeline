# Integration (read-join harness) — after Pillar A and Pillar B unit tests are green

**Not a product merge.** A and B remain independent writers (`history/` vs `map/`). This package only **joins at read** for WorkingSet / door-C lab checks.

Imports **both** packages’ read APIs. Not part of the Pillar A teammate zip.

To run later, put both `pillar-a/poc` and `pillar-b/poc` on `PYTHONPATH` (or install editable) and point fixtures at `integration/fixtures/lab_checkout` (mixed metric + topo stream).

Join modules: `join/harness.py`, `join/maintain.py`.
