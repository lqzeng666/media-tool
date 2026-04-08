"""Project persistence - save/load generated content to local files."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

PROJECTS_DIR = Path("output/projects")


def _ensure_dir():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def save_project(state: dict, name: str = "") -> str:
    """Save current project state to disk. Returns project ID."""
    _ensure_dir()

    project_id = f"{int(time.time())}_{name or 'untitled'}"
    project_id = project_id.replace(" ", "-").replace("/", "-")[:80]
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(exist_ok=True)

    # Separate binary data from metadata
    meta = {}
    for key, val in state.items():
        if key in ("ppt_bytes", "podcast_audio", "video_bytes") and val:
            # Save binary files separately
            ext = {"ppt_bytes": "pptx", "podcast_audio": "mp3", "video_bytes": "mp4"}[key]
            fpath = project_dir / f"{key}.{ext}"
            if isinstance(val, bytes):
                fpath.write_bytes(val)
            meta[key] = f"__file__:{fpath.name}"
        elif key in ("xhs_images", "slide_images", "comic_images") and val:
            # Save image lists as individual files
            img_dir = project_dir / key
            img_dir.mkdir(exist_ok=True)
            filenames = []
            for i, img_b64 in enumerate(val):
                fname = f"{i:03d}.png.b64"
                (img_dir / fname).write_text(img_b64)
                filenames.append(fname)
            meta[key] = f"__imgdir__:{key}"
        else:
            meta[key] = val

    # Save metadata
    (project_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # Save a summary for listing
    summary = {
        "id": project_id,
        "topic": state.get("topic", ""),
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "materials_count": len(state.get("materials", [])),
        "has_outline": state.get("outline") is not None and state.get("outline") != "skipped",
        "outputs": [],
    }
    if state.get("ppt_bytes"):
        summary["outputs"].append("PPT")
    if state.get("xhs_images"):
        summary["outputs"].append("小红书图文")
    if state.get("comic_images"):
        summary["outputs"].append("漫画")
    if state.get("video_bytes"):
        summary["outputs"].append("视频")
    if state.get("podcast_audio"):
        summary["outputs"].append("播客")

    (project_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False), encoding="utf-8"
    )

    return project_id


def load_project(project_id: str) -> dict:
    """Load a saved project. Returns state dict."""
    project_dir = PROJECTS_DIR / project_id
    if not (project_dir / "meta.json").exists():
        raise FileNotFoundError(f"Project not found: {project_id}")

    meta = json.loads((project_dir / "meta.json").read_text(encoding="utf-8"))

    state = {}
    for key, val in meta.items():
        if isinstance(val, str) and val.startswith("__file__:"):
            fname = val.split(":", 1)[1]
            fpath = project_dir / fname
            if fpath.exists():
                state[key] = fpath.read_bytes()
            else:
                state[key] = None
        elif isinstance(val, str) and val.startswith("__imgdir__:"):
            dirname = val.split(":", 1)[1]
            img_dir = project_dir / dirname
            if img_dir.exists():
                files = sorted(img_dir.iterdir())
                state[key] = [f.read_text() for f in files]
            else:
                state[key] = None
        else:
            state[key] = val

    return state


def list_projects() -> list[dict]:
    """List all saved projects, newest first."""
    _ensure_dir()
    projects = []
    for d in sorted(PROJECTS_DIR.iterdir(), reverse=True):
        summary_file = d / "summary.json"
        if summary_file.exists():
            try:
                summary = json.loads(summary_file.read_text(encoding="utf-8"))
                projects.append(summary)
            except (json.JSONDecodeError, OSError):
                continue
    return projects


def delete_project(project_id: str):
    """Delete a saved project."""
    import shutil
    project_dir = PROJECTS_DIR / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
