# Cover letter (draft; to be completed and signed by the corresponding author)

To the Editor-in-Chief,
*Mechanical Systems and Signal Processing*

Dear Editor,

We submit the manuscript **"Tracking the support stiffness of railway wheelset bearings from in-service
axle-box acceleration without measuring rail roughness: a multi-pass debiased Whittle likelihood"**
for consideration as a Research Paper in *Mechanical Systems and Signal Processing*.

Axle-box acceleration is now recorded routinely in service, mainly for track monitoring. The
vertical support stiffness of the wheelset bearings (the roller contacts in series with the housing,
adapter and pad) sets a resonance in the same frequency band. This stiffness falls when fits loosen,
when the housing, adapter or pad degrades, or when the clearance grows. Identifying it from
in-service data is hard because the rail roughness that excites the response is unknown.

To our knowledge, this is the first method to identify the vertical stiffness of the axle-box bearing
support from in-service axle-box acceleration without measuring rail roughness. The support resonance
and the roughness are separated by pooling passes at different speeds and payloads in a single
debiased Whittle likelihood, in which roughness levels are free nuisance parameters. Joint estimation
of vehicle or track parameters with unknown excitation has been studied for track stiffness (Carrigan
& Talbot 2023; Shen et al. 2023) and for road-vehicle suspensions (Liu et al. 2024; An et al. 2024).
There, roughness is handled by deconvolution, a single level parameter, or axle time lags, and the
targets lie below the axle-box support band.

The manuscript gives the estimator, a rail-coupled multi-wheel forward model and a complete
simulation error budget for a representative freight wagon: Cramér–Rao bounds, Monte Carlo bias and
coverage, model-form sensitivity, simulation-calibrated intervals, detection limits for changes
between monitoring periods, and false-alarm rates under track drift. We believe it fits the journal's
scope in system identification, signal processing for condition monitoring, and vehicle–track
dynamics, and builds directly on recent MSSP work on axle-box acceleration (Carrigan & Talbot 2023;
Shen et al. 2023).

All results are from simulation. The code that produces every number, table and figure is openly
available (https://github.com/Shreyansh369/wheelset-s2pinn). The manuscript has not been published
and is not under consideration elsewhere. All authors have approved the submission and declare no
competing interests.

Suggested reviewers (optional): [to be added by the authors]

Yours sincerely,

[Corresponding author name, affiliation, e-mail]
