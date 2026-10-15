# DDK v2 experimental: association of 20/40 ms envelopes

V1 is unchanged. `backend.ddk_v2.compare_wav(wav_bytes)` returns independent `v1` and `v2` records. This experimental engine is not activated in `/ddk-analysis` or the frontend. No automatic phonetic identity, clinical interpretation or human-speech validation is claimed. Human validation remains milestone 6B.

## Frozen algorithm

Both scales use Hann-weighted mean-square energy (not Hann-squared weighting), the original digital floor, a rounded 5 ms sample hop, independent P10+6/P90−25 thresholds and original 3 dB topographic contrast. A scale-specific extraction copy isolates v2 from the v1 module/configuration. It includes original boundary semantics; window data may extend outside the selected interval, but incomplete maxima are rejected and audited.

All 40 ms maxima partition the interval. Between successive maxima, the minimum plateau defines the boundary at its temporal midpoint. If equal minima occur in disjoint plateaus, use the first contiguous minimum plateau. Boundaries belong to the left basin. Construct this partition before checking structural eligibility; never reassign a maximum from a rejected basin to a distant accepted one.

Structural eligibility requires complete boundaries, energy at/above its threshold and contrast at/above 3 dB, before minimum-separation suppression. Fine eligibility uses the same tests at 20 ms before suppression. Within each eligible basin choose the eligible fine maximum with greatest energy, then shortest distance to the structural maximum, then earliest time. Retain its original fine timestamp exactly. Other eligible fine maxima have reason `same_structure_secondary`. Apply original descending-energy suppression with separation strictly less than 50 ms. Exactly 50 ms is allowed. Neither duration nor proximity alone merges events.

Energy, contrast, width at peak−3 dB, background margins, independent thresholds, scale offset, boundaries, associations, competitors, intermediate valleys and all applicable rejection reasons are exported. Width uses interpolated nearest crossings; incomplete crossings return null and are not a rejection filter. The sensitivity flag is abs(threshold margin) ≤1 dB at either scale and never changes acceptance. No scale offset is used to move a timestamp. Selection can still choose a transient instead of a sustained emission when the transient dominates fine energy.

`compare_wav` validates the WAV/interval through the unchanged v1 analyzer and uses independent v2 detection. Empty evidence retains zero count but null rate. Expected v2 detector failure gives null count/rate and preserves v1. There is no hidden fallback to v1 events. Manual review of existing v1 records is untouched; this experiment does not reinterpret previous review operations as v2 operations.

## Comparison protocol

Run `python -m tests.report_ddk_v2 --human /absolute/path/ddk.wav --out /absolute/path/comparison.json` with repository root on Python path. Human input is optional and is not stored in the repository. The report never adjusts configuration. Matching uses ordered maximum-cardinality, minimum-total-error one-to-one alignment within 10 ms (clean) or 20 ms (characterization).

* Clean: 36 conditions, 882 known events: six rates, two sample rates, three PCM widths, unchanged generator.
* Existing characterization: all 14 cases, unchanged generator, same deterministic seed. Unrecoverable quantized weak events and high noise are reported as losses, not successful timing measurements.
* Compound: transient plus emission at 60/80/100 ms; 2/5/10 ms transient; 20/40/80 ms emission; −12/−6/0/+6 dB transient amplitude ratio; both sample rates and all PCM widths; offsets 0/2.5 ms and Gaussian noise amplitudes 0/.03. Reference timestamp is emission center. Extras represent additional candidates; they are duplicates only when a reference emission was also recovered.
* Independent controls: two known emissions at 60/80/100 ms. Losses are reported as omissions/potential fusions, not proof that every loss is a fusion.
* Internal double: one generated composite emitter made of two overlapping 160 ms lobes. Reference count is one. There is no unique prescribed timestamp: temporal error is null rather than fabricated. This is an acoustic controlled construction, not a phonetic claim.
* Weak next to strong: amplitude .015 versus .3, known centers. Isolated transient: 5 ms, 3000 Hz, known center.
* Basin fragmentation: controlled envelope fixture and full association test, with a below-threshold structural maximum between two fine maxima assigned to one simulated source. This tests association topology, not an assertion that those injected envelopes necessarily arise from a particular WAV. A separate offline eligible-only partition is compared; it is not enabled as a detector mode. Apply the same offline alternative to the human WAV for characterization.

The independent/internal/weak/isolated controls are clean signals; duplicate execution inside the compound noise loop is deduplicated in the report. Noise amplitudes are not calibrated SNR. No human phonetic timestamp ground truth is supplied; false positive/negative or timing-error estimates are therefore not assigned to the human WAV.

## Superiority gate

No clean or recoverable-characterization regression, strictly fewer redundant compound candidates, no new omissions/fusions in independent controls, matched timing ≤10/20 ms, full traceability and preservation of v1/previous tests/six xfail. Failures must be stated explicitly. A lower human count alone never satisfies the gate. A failed gate leaves v2 experimental and does not authorize changing basin rules or opening a PR.

## Basin finding before interpreting counts

In the controlled topology fixture, structural energies `[0,10,1.5,2,1,10,0]` define piecewise-linear knots spaced 50 ms apart (full association fixture evaluated on the shared 5 ms grid). Maxima are at 50/150/250 ms, with the middle maximum below threshold 3. Fine maxima at 50/175 ms represent one stipulated simulated source. All-maxima boundaries at 100/200 ms assign the second fine maximum to the rejected middle basin. Removing only the rejected maximum for the offline alternative gives a boundary at 200 ms, assigning both fine maxima to the first eligible basin. Their associations differ; the strongest representative and final count (one) are unchanged. This illustrates fragmentation without inventing an extra event. These injected contours are an association unit fixture, not a physical signal reconstruction.

On the supplied human WAV, the unchanged approved v2 partition yields 13 events at 0.360, 0.615, 0.805, 1.340, 1.555, 1.820, 2.380, 2.605, 3.380, 3.565, 3.735, 3.800, 4.085 seconds. All are original fine-scale timestamps; none was relocated to 40 ms. The accepted v1 maximum at 2.815 s is excluded because its associated structural maximum lacks contrast. The explicitly separate eligible-only alternative restores that maximum and yields 14. The consonant-transient-compatible pair at 3.735/3.800 s and the weak late maximum at 4.085 s remain. This is an exploratory acoustic characterization; no automatic phonetic annotation or independent human event-level truth is available. The known 12 syllables were never an optimization target.

For an independently reproducible numerical summary use `python -m tests.summarize_ddk_v2 comparison.json summary.json`. It reports all per-condition increases in extras or misses rather than hiding them in aggregate counts. The independent-control gate also includes weak-next-to-strong cases, since they contain two known independent events. Count-only internal-double cases do not acquire a fabricated timing reference.

### Physical acoustic fixture for fragmentation

`tests.synthetic_ddk_v2.basin_fragmentation_wav()` generates one 240 Hz carrier with a Gaussian amplitude envelope and two deterministic modulations. Parameters were frozen from seed-606 topology exploration, trial 6; this deliberately constructed positive control is not an unbiased performance corpus. No detector configuration was tuned. V1 gives four maxima (0.445, 0.530, 0.615, 0.700 s); approved v2 gives one (0.615 s). A 40 ms maximum at 0.530 s lies between fine maxima of the same generated emitter and is ineligible because its contrast is 2.740957452 dB. Its basin spans 0.455–0.550 s and rejects the accepted fine maximum at 0.530 s. The eligible-only alternative changes associations but retains the same final representative/count in this fixture. This complements the injected shared-grid association fixture and the human case where the alternative changes the count. The source has known emission count one but no prescribed unique maximum timestamp: temporal error is null.

## Recovery and verification (2026-10-14)

The uncommitted implementation and complete 2,592-condition compound report were recovered from the prior workspace at base `af1648ca6b1adeee18f2823e5627ebf76a17d947`. No conceptual redesign was performed. The full recovered bank is persisted in `docs/ddk_v2_comparison.json.gz` (gzip-compressed JSON), including per-condition results and full real-WAV candidate/structure audit. Its recovery metadata records the original report hash, source hashes and the deterministic sample re-executed for exact equality (36 compound conditions, seed 20261014). All 14 characterization cases were re-executed with exact equality. The clean matrix, physical fragmentation fixture, human WAV and general tests were verified again. This is reuse of a completed recovered bank, not a claim that all compound conditions were rerun during recovery.

A floating-point boundary fix in v2 keeps exactly 50 ms eligible even when decimal subtraction gives 0.04999999999999999. The tolerance is 1e-12 seconds and does not admit a different sample/frame spacing. V1 code/configuration remain byte-for-byte unchanged. Added association tests cover energy/distance/earliest-time ranking and separate structures at 45/50/55 ms. The offline alternative uses the same numerical tolerance.

The numerical gates are necessary experimental checks, not general superiority or clinical validation. The internal-double count-only control remains unresolved (72 detections for 36 stipulated sources in both versions). Compound extras decrease by 180/2016 (8.93%), leaving 1,836. The existing weak-quantized and high-noise characterization losses remain (42 in each version). The human recording still has 13 detections for four known `/pa-ta-ka/` sequences (12 stipulated syllables), without event-level timing truth; neither 13 nor the alternative's 14 is treated as correct. The 2.815 s event removed by the approved partition must remain visible as a possible omission in the audit.

No frontend/API activation, no phonetic recognition, no automatic clinical grouping and no PR are part of this investigation.

## Numerical results

| Bank | Reference | V1 | V2 | Interpretation |
|---|---:|---:|---:|---|
| Clean, 36 conditions | 882 events | 882 | 882 | No extras/omissions; maximum error 2.495 ms |
| Characterization, 14 cases | 252 events | 210 | 210 | Same 42 losses; no extras; matched error ≤1.667 ms |
| Transient + emission, 2,592 conditions | 2,592 emissions | 4,608 | 4,428 | Extras 2,016 → 1,836; no omissions |
| Independent emissions, 36 conditions | 72 events | 72 | 72 | No extras/omissions |
| Weak next to strong, 36 conditions | 72 events | 72 | 72 | No extras/omissions |
| Internal double, 36 conditions | 36 sources | 72 | 72 | 36 extras in both; unresolved |
| Isolated transient, 12 conditions | 12 events | 12 | 12 | No extras/omissions |
| Physical fragmentation fixture | 1 source | 4 | 1 | Alternative also 1; association differs |
| Supplied human WAV | 12 stipulated syllables, no event timing truth | 24 | 13 | Eligible-only alternative 14; not validation |

All six explicit numerical gates in the summary pass. No per-condition increase in synthetic extras or omissions was observed. Traceability and unmodified v1 are retained. The broader objective of reliably identifying every human syllable, and eliminating every internal double, is **not demonstrated**.

## General-suite verification

All 368 collected pytest cases were executed: 355 passed directly, six remained expected strict xfails, and seven hit Praat’s unchanged 15 s timeout during parallel execution. Repeating those seven in one process passed all seven. Final unique outcomes: **362 passed, 6 expected xfails, 0 unresolved failures**. All 52 v2-specific cases passed. `npm run test:ui`: **19 passed**. Host verification used Praat 6.4.27 from the archive whose SHA-256 matches the Dockerfile; Docker and browser suites were not rerun. See `ddk_v2_verification.json` and compressed raw logs for commands, counts and timeout/retry evidence. No timeout or acoustic algorithm was changed to obtain this result.
