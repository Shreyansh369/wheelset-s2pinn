# Legacy: not part of the paper

This folder keeps code, documents and results from the first, exploratory phase of the project: a
stochastic separable physics-informed neural network (S²-PINN) surrogate with generalised polynomial
chaos (gPC) and moment matching for the wheelset problem, the reproduction of the S²-PINN diffusion
benchmark, the H1 degree study on an SDOF oscillator and the Eq. (41) damping-bias study.

None of it is used by the paper (`paper/`) or by any script that produces its tables, figures or
numbers. It is kept for the record only and is not maintained. Paths inside these files refer to the
original layout (`src/model`, `experiments/p0_*`, `results/p0`).

The third-party S²-PINN code (Li and Onwunta, https://github.com/DMax1314/s2pinn, which has no licence
file) was used as a git submodule in that phase. It is **not** included in this repository or in the
release; fetch it yourself at commit 1cd6fa2 if you want to rerun the legacy reproduction. Legacy
dependencies: `requirements-legacy.txt`.
