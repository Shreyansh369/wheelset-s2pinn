"""Single entry point for writing results.

Every number that appears in a table, figure or message must come from a file
written by :func:`save_result`. The file records the config, seed, git commit,
wall-clock time and peak memory alongside the payload.
"""

from __future__ import annotations

import json
import os
import platform
import resource
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        dirty = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def peak_cpu_memory_mb() -> float:
    """Peak resident set size of this process, in MB (Linux reports KB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def peak_gpu_memory_mb() -> float | None:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / 2**20
    except ImportError:
        pass
    return None


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _to_jsonable(obj.tolist())
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, float) and not np.isfinite(obj):
        return str(obj)
    return obj


class Timer:
    def __enter__(self) -> "Timer":
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        self.seconds = time.perf_counter() - self.t0


def save_result(
    name: str,
    payload: dict[str, Any],
    cfg: dict[str, Any] | None = None,
    seed: int | None = None,
    wall_seconds: float | None = None,
) -> Path:
    """Write ``results/<name>.json``; ``name`` may contain subdirectories."""
    path = RESULTS_DIR / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "name": name,
        "seed": seed,
        "config": cfg or {},
        "payload": payload,
        "provenance": {
            "git_commit": _git_commit(),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_seconds": wall_seconds,
            "peak_cpu_memory_mb": peak_cpu_memory_mb(),
            "peak_gpu_memory_mb": peak_gpu_memory_mb(),
            "host": platform.node(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
    }
    path.write_text(json.dumps(_to_jsonable(record), indent=2))
    return path


def load_result(name: str) -> dict[str, Any]:
    return json.loads((RESULTS_DIR / f"{name}.json").read_text())
