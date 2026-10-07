# Pillar A+B slice helpers (run from pillar-ab-implementation/)
.PHONY: check-schemas check-map-physical generate-map-arrow-schema test-a test-b

check-schemas: check-map-physical
	python3 scripts/check_schema_mirrors.py

# Phase-1: JSON Schema ↔ physical overlay ↔ map-vortex/src/schema.rs
check-map-physical:
	python3 scripts/check_map_physical_schema.py

# Phase-2: regenerate Arrow schema.rs from physical overlays
generate-map-arrow-schema:
	python3 scripts/generate_map_arrow_schema.py

test-a:
	$(MAKE) -C pillar-a/poc test-all

test-b:
	$(MAKE) -C pillar-b/poc test-all
