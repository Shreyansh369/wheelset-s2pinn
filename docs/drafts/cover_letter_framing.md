# Cover letter: framing of a simulation-only study (DRAFT, not applied)

Status: draft for the corresponding author's approval. The Step-8 STOP covers `paper/submission/cover_letter.tex`,
so nothing here has been applied. No numbers are added: the cover letter keeps the ones it already has
(the 5.6% coupling bias). Any new number would be a generated macro checked in the consistency read-through.

## Why the framing matters

All results come from simulation. An MSSP editor will screen for two things: whether the paper claims more than a
simulation can show, and whether the simulation is a strawman (the estimator fitted to data from its own model).
The letter should answer both in two sentences, without apologising, and point to the paragraph of §5 that
covers it ("Realism of the synthetic data").

## Proposed text

Replace the last two sentences of the **Contributions** paragraph ("Periods must be compared within one payload
band; mixed-payload pooling is not supported. The results are from simulation; a controlled rig or field test is
the next step before operational use.") with:

> Periods must be compared within one payload band; mixed-payload pooling is not supported.
>
> **Scope of the evidence.** The study is a simulation study, and we claim no performance on a real vehicle. It
> does not rely on the estimator fitting data from its own model. The uncertainty budget tests the method
> against what a matched-model study leaves out: random simultaneous errors of all fixed parameters, nonlinear
> Hertzian contact from an independent time-domain generator, a payload-dependent primary suspension,
> foundation drift between periods and wheel roughness at rotation orders. It states which features of measured
> records are not represented (Section 5, "Realism of the synthetic data"). The contribution is the
> identifiability result and an estimator whose error sources are quantified before a field test. That test, an
> axlebox whose support stiffness is changed in a controlled way, is specified in the paper's measurement
> requirements and is the next step.

## Alternative (shorter, if the one-page limit binds)

> The results are from simulation, but not from a matched model alone: the uncertainty budget includes random
> simultaneous parameter errors, nonlinear contact from an independent generator, payload-dependent suspension
> and foundation drift, and Section 5 lists what the simulated records do not contain. A controlled rig or
> field test is the next step before operational use.

## Checks before applying

- "independent time-domain generator": §4 "Nonlinear Hertzian contact" and "Generator check" describe it.
  Keep the word "independent" only if the read-through confirms that the generator shares no code path with
  the estimator's frequency-domain model, beyond the model definition itself.
- "specified in the paper's measurement requirements": §3.6 lists the requirements; the controlled-change test
  is named in §5 "No field data". If the read-through finds §3.6 does not name it, say "named in Section 5".
