"""Write generated scenes and invoke Manim CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _find_manim() -> str:
    manim = shutil.which("manim")
    if manim:
        return manim
    venv_manim = Path(sys.executable).parent / "manim"
    if venv_manim.exists():
        return str(venv_manim)
    raise RuntimeError(
        "manim CLI not found on PATH. Install with: pip install manim\n"
        "Also ensure ffmpeg is installed for video output."
    )


def write_scene(code: str, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")
    return path


def render(scene_path: Path, output: Path, quality: str = "ql") -> Path:
    scene_path = Path(scene_path).resolve()
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    manim = _find_manim()
    q_flag = f"-q{quality[-1]}" if quality.startswith("q") else f"-q{quality}"

    project_root = scene_path.parent
    rvc_root = project_root
    while rvc_root.name != "RCA-MANIM-Generator-System" and rvc_root.parent != rvc_root:
        rvc_root = rvc_root.parent
    repo_root = rvc_root.parent

    env = dict(**__import__("os").environ)
    env.setdefault("MANIM_USE_LATEX", "false")
    pythonpath = env.get("PYTHONPATH", "")
    extra_paths = [str(rvc_root), str(repo_root)]
    env["PYTHONPATH"] = ":".join(extra_paths + ([pythonpath] if pythonpath else []))

    cmd = [
        manim,
        q_flag,
        str(scene_path),
        "RCAScene",
        "-o",
        output.stem,
    ]
    result = subprocess.run(cmd, cwd=str(rvc_root), env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"manim render failed (exit {result.returncode}):\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    rendered = _locate_output(scene_path, output.stem, quality)
    if rendered and rendered.resolve() != output.resolve():
        shutil.copy2(rendered, output)
    elif not output.exists() and rendered:
        shutil.copy2(rendered, output)

    if not output.exists():
        candidates = list(rvc_root.rglob(f"{output.stem}.mp4"))
        if candidates:
            shutil.copy2(candidates[0], output)
        else:
            raise FileNotFoundError(
                f"Rendered MP4 not found. manim stdout:\n{result.stdout}\n{result.stderr}"
            )
    return output


def _locate_output(scene_path: Path, stem: str, quality: str) -> Path | None:
    quality_dir = {"ql": "480p15", "qm": "720p30", "qh": "1080p60"}.get(quality, "480p15")
    candidates = [
        scene_path.parent / "media" / "videos" / scene_path.stem / quality_dir / f"{stem}.mp4",
        scene_path.parent.parent / "media" / "videos" / scene_path.stem / quality_dir / f"{stem}.mp4",
    ]
    rvc_root = scene_path
    while rvc_root.name != "RCA-MANIM-Generator-System" and rvc_root.parent != rvc_root:
        rvc_root = rvc_root.parent
    candidates.append(
        rvc_root / "media" / "videos" / scene_path.stem / quality_dir / f"{stem}.mp4"
    )
    for path in candidates:
        if path.exists():
            return path
    return None


def check_dependencies() -> list[str]:
    missing: list[str] = []
    if not shutil.which("manim"):
        missing.append("manim")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    return missing
