# wheelset-s2pinn

A stochastic separable PINN for identifying railway axle-bearing support stiffness and damping from across-pass axlebox-acceleration statistics. This is the parent paper; two child papers will reuse this library.

Sources: `docs/wheelset_model.pdf` (model), `docs/s2pinn_research_review.pdf`, and Li & Onwunta, S²-PINN, arXiv:2610.03303. The S²-PINN PDF is not committed.

## Layout

```
config/            physical parameters (each value tagged with its source or "placeholder")
src/reference/     L1-lin FE, frequency- and time-domain solvers, Monte Carlo   (Phase 1)
src/model/         gPC basis (anisotropic, mixed Legendre/Hermite), closed-form moments, separable PINN
src/inverse/       moment-matching identification, bootstrap                    (Phase 3)
src/baselines/                                                                  (Phase 4)
src/analysis/      Phase 0 studies: H1 on SDOF, Eq. (41) damping bias
src/utils/         results.py: the single writer for results/ (config, seed, git hash, cost)
experiments/       one script per table or figure; each writes to results/
results/           JSON and figures written by scripts, never edited by hand
tests/             verification checks and moment unit tests
third_party/s2pinn the authors' code, a git submodule pinned at 1cd6fa2 (no licence file upstream)
docs/              sources, literature check, derivations
```

## Setup

```bash
git submodule update --init
pip install -r requirements.txt
pytest -q
```

## Phase 0

| Script | Output |
|---|---|
| `experiments/p0_reproduce_s2pinn_resumable.py --seed 42 --colloc 4096` (CPU, ~5 h; vs Table 14) | `results/p0/s2pinn_repro_seed42_nc4096.json` |
| `experiments/p0_reproduce_s2pinn_resumable.py --seed 42 --device cuda` (T4, paper default Nc=32768) | `results/p0/s2pinn_repro_seed42.json` |
| `experiments/p0_h1_sdof.py`, then `experiments/p0_h1_summary.py` | `results/p0/h1_sdof*.json`, figures |
| `experiments/p0_eq41.py` | `results/p0/eq41.json` |
| `experiments/gate_report.py G0` | `results/gates/G0.json` |

## Running on a GPU (Colab or Kaggle T4)

This container is CPU-only (no CUDA), so training runs for Phase 2 onward go through
`notebooks/t4_runner.ipynb`. It clones this repo, runs one `experiments/*.py` command
with its repo configs, and pushes the new `results/` files back to the branch (with a
`GITHUB_TOKEN` secret) or zips them for download.

Every training entry point follows the same rules:
- pick the device with `src.utils.device.get_device()` (the `WSP_DEVICE` env var or a `--device` flag overrides it);
- write results only through `src.utils.results.save_result`, which records the device;
- checkpoint under `results/` and resume, so a run can span several sessions.
