"""Independence: Pillar A sketch modules must not import graph or join."""

import ast
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[2]
SKETCH_ROOT = POC_ROOT / "sketch"


def test_sketch_does_not_import_graph_or_join():
    names: set[str] = set()
    for path in SKETCH_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
    assert "graph" not in names
    assert "join" not in names
