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

# Input tracking: every results/**/*.jsonl rows file this process reads (through open, Path.open or
# Path.read_text) is recorded, and save_result writes its SHA-256 into provenance.input_hashes. The git commit
# says which code produced a result; the hashes say exactly which rows it was computed from.
_INPUTS: set[Path] = set()


def _note_input(f) -> None:
    try:
        q = Path(f).resolve()
    except (TypeError, ValueError):
        return
    if q.suffix == ".jsonl" and RESULTS_DIR in q.parents:
        _INPUTS.add(q)


def _track(fn):
    def wrapped(file, *a, **k):
        mode = a[0] if a else k.get("mode", "r")
        if "r" in mode and "+" not in mode:
            _note_input(file)
        return fn(file, *a, **k)
    return wrapped


if not getattr(Path, "_inputs_tracked", False):
    import builtins
    builtins.open = _track(builtins.open)
    _path_open, _path_read_text = Path.open, Path.read_text
    Path.open = lambda self, *a, **k: (_note_input(self) if not a or ("r" in a[0] and "+" not in a[0]) else None,
                                       _path_open(self, *a, **k))[1]
    Path.read_text = lambda self, *a, **k: (_note_input(self), _path_read_text(self, *a, **k))[1]
    Path._inputs_tracked = True


def input_hashes() -> dict[str, str]:
    import hashlib
    return {str(q.relative_to(REPO_ROOT)): hashlib.sha256(q.read_bytes()).hexdigest()
            for q in sorted(_INPUTS) if q.exists()}


CONFIG_HASH_VERSION = "values-v2"


def config_values(text: str) -> Any:
    """Parsed YAML with every `source` field and all comments removed and YAML 1.1 numeric strings ('1.0e9')
    read as floats: what the configuration says, not how its sources are cited."""
    import yaml
    from src.reference.params import _num

    def strip(node):
        if isinstance(node, dict):
            return {str(k): strip(v) for k, v in node.items() if k != "source"}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return _num(node)
    return strip(yaml.safe_load(text))


def canonical_json(obj: Any) -> str:
    """Sorted keys, no whitespace, floats in Python's shortest round-trip repr."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def config_hash_from_texts(texts: dict[str, str | None]) -> str:
    import hashlib
    doc = {f: (config_values(t) if t is not None else None) for f, t in sorted(texts.items())}
    return hashlib.sha256(canonical_json(doc).encode()).hexdigest()[:12]


def config_hash(config_dir: Path | None = None) -> str:
    """values-v2 config hash: sha256 (12 hex) of the canonical JSON of params.yaml + track.yaml as parsed, with
    source fields and comments removed, so that correcting a citation does not change the configuration's
    identity. Byte hashes recorded before 19 Oct 2026 map to it through config/hash_aliases.yaml, proven by
    scripts/check_config_values.py."""
    d = Path(os.environ.get("WHEELSET_CONFIG_DIR", REPO_ROOT / "config")) if config_dir is None else Path(config_dir)
    return config_hash_from_texts({f: ((d / f).read_text() if (d / f).exists() else None) for f in ("params.yaml", "track.yaml")})


def config_hash_bytes(texts: dict[str, bytes | None]) -> str:
    """The byte hash used before values-v2 (sha256 of the raw files), for the alias proof only."""
    import hashlib
    h = hashlib.sha256()
    for f in ("params.yaml", "track.yaml"):
        h.update(texts.get(f) or b"")
    return h.hexdigest()[:12]


def _estimator_version() -> str | None:
    import sys
    mod = sys.modules.get("src.inverse.multipass")
    return getattr(mod, "ESTIMATOR_VERSION", None) if mod else None


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        # -dirty when code, config or docs differ from HEAD; result files written meanwhile (rows landing, or an
        # earlier save_result of the same script) do not make the code that produced this result dirty
        dirty = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=no", "--", ".", ":!results"],
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
            "config_dir": os.environ.get("WHEELSET_CONFIG_DIR", "config"),
            "config_hash": config_hash(),
            "config_hash_version": CONFIG_HASH_VERSION,
            "estimator_version": _estimator_version(),
            "input_hashes": input_hashes(),
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
