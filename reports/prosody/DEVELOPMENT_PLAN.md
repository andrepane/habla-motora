# Prosody 8A: predeclared technical investigation

Base: main 87e61ea53476be363b48739151b6007e7252a24b. No UI/HTTP route. No human WAV.

75 acoustic recipes x 2 sample rates x 3 PCM widths = 450 WAV per split. All seven profiles x exact crop / fixed 250 ms exterior context run in development (6300 extractions). Selected-only Pitch copies retain every interior undefined frame; exterior frames cannot enter native statistics. Context can influence native relative-amplitude thresholds and trajectory. Centres, counts and 100 ms edge availability are evaluated separately: frame coverage is not total temporal coverage.

Blocked uses different phases/seeds and a 1.037 base-frequency multiplier, plus .93 slope multiplier for log-linear ramps. It is not generated or executed before the persisted freeze. Same families prevent confusing scope changes with held-out performance. This is a deterministic controlled benchmark, not a human-independent population sample.

Primary in-scope clean controls: constants within 55–600 Hz, duration controls, linear Hz/ST ramps, sinusoidal modulation and steps. Reference boundaries have an a priori guard of 3/floor seconds for core F0 errors. Whole-track/edge errors remain reported. Outside-range constants, severe noise and ambiguous harmonics are characterization, never silently removed.

Selection on development: minimize a macro-average of per-family (missed periodic fraction + 5*gross-frequency-error fraction + 5*false-defined fraction) across in-range families, excluding intentionally out-of-range constants and SNR <=10 dB. Ties within 0.001 favor lower core cents error, then no-context, then simpler profile. All family scores and alternatives remain available. This scoring is engineering utility, not a probability or clinical score.

Range rule selection: reject global range publication in localized reference controls single_island/middle_only/split_ends; maximize availability in remaining periodic controls, first minimizing false publication. Three prespecified rules compare N, span, frame coverage and occupied temporal quintiles. Count is not independent sample size.

Jump rule selection: development injected x2/x0.5 tracks have either contiguous or one missing 5 ms cell (eligible warnings); changes after >=20 ms undefined gaps are negative temporal controls. Compare 10/20/50 ms limits, prioritize no long-gap warnings and then short-event sensitivity. These labels test the warning policy, not whether a human jump is a tracking error. Every >6 ST transition keeps direction, delta_t and gap evidence even when no warning is issued.

Proposed acceptance after configuration selection, to freeze before held-out: clean in-scope core median <=20 cents/P95 <=50 cents; core defined >=98%; no octave errors in constant/duration controls; native quantile error <=max(1 Hz,2% reference); robust ST range error <=.2 ST; ST slope error <=max(.05 ST/s,5% reference); silence false-defined <=2%. Noise20 median <=50 cents and coverage loss <=10 percentage points. For gaps >=500 ms, reference recall >=95%, median boundary errors <=3/floor seconds. Per-condition failures must be reported; no overall average can erase them. Synthetic steps/sinusoids may have distinct whole-track versus transition-core behavior. The frozen acceptance implementation must preserve these checks rather than fit thresholds to development outcomes.

Final results classify each criterion passed/failed, not forced success. A blocked failure forbids adjustment against the same blocked set. All original modules/configurations stay unchanged. Existing six xfails remain explicit. Validation is technical extraction/calculation only; human prosodic validity remains pending.
