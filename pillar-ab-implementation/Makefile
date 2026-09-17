# Pillar A+B slice helpers (run from pillar-ab-implementation/)
.PHONY: check-schemas test-a test-b

check-schemas:
	python3 scripts/check_schema_mirrors.py

test-a:
	$(MAKE) -C pillar-a/poc test-all

test-b:
	$(MAKE) -C pillar-b/poc test-all
