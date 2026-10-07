"""Independence: graph unit tests must not import sketch; sketch must not import graph."""

import ast
from pathlib import Path

GRAPH_ROOT = Path(__file__).resolve().parents[2]
SKETCH_ROOT = GRAPH_ROOT.parent / "sketch"


def _imports_of(package_dir: Path) -> set[str]:
    names: set[str] = set()
    for path in package_dir.rglob("*.py"):
        if "tests" in path.parts and path.name.startswith("test_"):
            # allow join tests only outside these packages
            pass
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
    return names


def test_graph_does_not_import_sketch():
    # Only scan production modules under graph/, not tests that are join
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


def test_sketch_does_not_import_graph():
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
