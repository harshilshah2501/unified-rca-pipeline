"""Independence: Pillar B graph modules must not import sketch or join."""

import ast
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[2]
GRAPH_ROOT = POC_ROOT / "graph"


def test_graph_does_not_import_sketch_or_join():
    names: set[str] = set()
    for path in GRAPH_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
    assert "sketch" not in names
    assert "join" not in names
