"""Device selection shared by every training entry point.

Scripts call :func:`get_device` instead of hard-coding "cpu" or "cuda", so the
same command runs on this CPU container and on a Colab/Kaggle T4. The returned
description is stored in each result file.
"""

from __future__ import annotations

import os
import platform

import torch


def get_device(prefer: str | None = None) -> tuple[torch.device, dict]:
    """Return (device, info). ``prefer`` (or env WSP_DEVICE) may force "cpu" or "cuda"."""
    want = (prefer or os.environ.get("WSP_DEVICE") or "auto").lower()
    cuda_ok = torch.cuda.is_available()
    if want == "cuda" and not cuda_ok:
        raise RuntimeError("WSP_DEVICE=cuda requested but torch.cuda.is_available() is False")
    use_cuda = cuda_ok and want != "cpu"
    dev = torch.device("cuda" if use_cuda else "cpu")
    info = {
        "device": str(dev),
        "cuda_available": cuda_ok,
        "device_name": torch.cuda.get_device_name(0) if use_cuda else platform.processor() or platform.machine(),
        "torch": torch.__version__,
        "cpu_threads": torch.get_num_threads(),
        "host_kind": "kaggle" if os.path.exists("/kaggle") else ("colab" if "COLAB_RELEASE_TAG" in os.environ else "other"),
    }
    return dev, info


def rng_state(device: torch.device) -> dict:
    st = {"cpu": torch.get_rng_state()}
    if device.type == "cuda":
        st["cuda"] = torch.cuda.get_rng_state_all()
    return st


def set_rng_state(st, device: torch.device) -> None:
    if isinstance(st, torch.Tensor):  # older checkpoints stored the CPU state only
        torch.set_rng_state(st)
        return
    torch.set_rng_state(st["cpu"])
    if device.type == "cuda" and "cuda" in st:
        torch.cuda.set_rng_state_all(st["cuda"])
