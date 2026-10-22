# v0.3.0 final research report

Release: [NullMark v0.3.0 — Sparse Keyless Disruption](https://github.com/Guardianec/nullmark/releases/tag/v0.3.0). The released tag identifies the final merged commit; its exact SHA and final CI run are also reported in the release handoff.

## Release and evidence (items 1–7)

- Release branch/PR: [codex/release-v0.3.0, PR #3](https://github.com/Guardianec/nullmark/pull/3). Scientific preregistration: `1e9c2efc325faed2dfa0cd0f3719ee9bfb5fc0bc`.
- Full offline suite: **272 passed, 1 optional integration skipped**. Clean installed-wheel historical GPT-2 text/token replay passes for plain, KGW and SynthID. [Release verification](skd-release-verification.md) records build, privacy, browser and CI checks.
- Corpus: **240 fresh prompts**, 30 topics × eight styles, disjoint IDs/text from development, calibration and v0.2. **480 source continuations**, 479 eligible candidate pools and **9,580 evaluated attempts**. One KGW baseline abstention; no baseline misses.
- Eligibility: KGW **239/240 (99.58%)**; SynthID **240/240 (100%)**. Candidate coverage ≥1/2/3/5: KGW **239/239 at each budget**, SynthID **240/240 at each budget**. Every selector realizes exact k; no candidate exhaustion or pipeline failure in this run.

## Features and weights (items 8–9)

**Score = E + 1.25 L + T + R − 1.5 D**, on per-sample midrank-normalized features (ties shared; constant/singleton = .5). All weights remained fixed before detector outcomes.

|Feature|Raw definition|
|---|---|
|E|Mean ordinary Qwen next-token entropy in nats over the source span; omit the first unpredicted token.|
|L|Count aligned unchanged tokens whose preceding generic eight-token histories change after the edit.|
|T|Qwen token Levenshtein distance in the edited window plus four boundary words per side.|
|R|Minimality proxy: 1 / (1 + word edit distance of the replacement); not model confidence.|
|D|1 − local MiniLM cosine + .25 × absolute word-length difference / maximum span length.|

The shared pool uses three bounded batches of at most 12 canonical source spans, local cosine ≥.85, structural/anchor filters and final-text deduplication. Selection applies non-overlapping spans once. [Exact protocol](skd.md); [two pre-evaluation implementation corrections and preserved invalid runs](skd-protocol-amendment.md).

## All selectors and quality (items 10–20)

All five selectors use the identical pool per sample. N includes failures and abstentions; evasion requires a calibrated NOT DETECTED result. Δ score is before minus after, in native scheme units. Semantic/word/token/anchor columns are means; anchor means exclude texts with no applicable anchors. Anchors check literal numbers/dates/percentages/URLs/emails, not all factual claims. Full distributions and quality-conditioned denominators are in [metrics.json](benchmarks/qwen-v030/metrics.json).

|Scheme|Method|k|N|Evasion|Abstention|Failures|Δ score|Semantic|Word fraction|Token fraction|Anchors|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|kgw|random_pool|1|239|0.00%|14.64%|0|0.1160|0.9983|0.0109|0.0088|1.0000|
|kgw|random_pool|2|239|0.00%|17.99%|0|0.2294|0.9968|0.0211|0.0168|1.0000|
|kgw|random_pool|3|239|0.00%|23.85%|0|0.3516|0.9955|0.0313|0.0248|1.0000|
|kgw|random_pool|5|239|0.00%|28.03%|0|0.5704|0.9927|0.0528|0.0418|1.0000|
|synthid|random_pool|1|240|0.00%|5.42%|0|0.0023|0.9985|0.0103|0.0080|1.0000|
|synthid|random_pool|2|240|0.00%|12.08%|0|0.0044|0.9971|0.0208|0.0164|1.0000|
|synthid|random_pool|3|240|0.00%|17.08%|0|0.0064|0.9956|0.0317|0.0249|1.0000|
|synthid|random_pool|5|240|0.00%|18.33%|0|0.0108|0.9921|0.0533|0.0420|1.0000|
|kgw|entropy_only|1|239|0.00%|17.57%|0|0.1107|0.9983|0.0084|0.0065|1.0000|
|kgw|entropy_only|2|239|0.00%|27.20%|0|0.2164|0.9965|0.0178|0.0139|1.0000|
|kgw|entropy_only|3|239|0.00%|35.15%|0|0.3366|0.9952|0.0268|0.0210|1.0000|
|kgw|entropy_only|5|239|0.00%|44.35%|0|0.5592|0.9923|0.0465|0.0361|1.0000|
|synthid|entropy_only|1|240|0.00%|8.75%|0|0.0022|0.9973|0.0087|0.0070|1.0000|
|synthid|entropy_only|2|240|0.42%|20.00%|0|0.0042|0.9957|0.0175|0.0139|1.0000|
|synthid|entropy_only|3|240|0.42%|25.42%|0|0.0064|0.9938|0.0268|0.0211|1.0000|
|synthid|entropy_only|5|240|0.42%|31.67%|0|0.0109|0.9909|0.0470|0.0366|1.0000|
|kgw|context_only|1|239|0.00%|9.62%|0|0.1692|0.9979|0.0159|0.0125|1.0000|
|kgw|context_only|2|239|0.00%|11.30%|0|0.3471|0.9955|0.0312|0.0245|1.0000|
|kgw|context_only|3|239|0.00%|16.74%|0|0.4795|0.9937|0.0448|0.0353|1.0000|
|kgw|context_only|5|239|0.00%|22.59%|0|0.6978|0.9915|0.0664|0.0524|1.0000|
|synthid|context_only|1|240|0.00%|9.58%|0|0.0029|0.9976|0.0159|0.0123|1.0000|
|synthid|context_only|2|240|0.00%|12.08%|0|0.0054|0.9957|0.0309|0.0237|1.0000|
|synthid|context_only|3|240|0.00%|14.17%|0|0.0081|0.9938|0.0447|0.0346|1.0000|
|synthid|context_only|5|240|0.42%|17.50%|0|0.0124|0.9903|0.0672|0.0527|1.0000|
|kgw|tokenizer_only|1|239|0.00%|23.01%|0|0.2042|0.9970|0.0213|0.0191|1.0000|
|kgw|tokenizer_only|2|239|0.00%|22.18%|0|0.3446|0.9948|0.0395|0.0350|1.0000|
|kgw|tokenizer_only|3|239|0.00%|23.01%|0|0.4983|0.9925|0.0565|0.0491|1.0000|
|kgw|tokenizer_only|5|239|0.42%|24.27%|0|0.7755|0.9886|0.0869|0.0740|1.0000|
|synthid|tokenizer_only|1|240|0.00%|17.92%|0|0.0027|0.9962|0.0217|0.0193|1.0000|
|synthid|tokenizer_only|2|240|0.00%|17.50%|0|0.0056|0.9937|0.0402|0.0353|1.0000|
|synthid|tokenizer_only|3|240|0.42%|17.50%|0|0.0080|0.9915|0.0572|0.0497|1.0000|
|synthid|tokenizer_only|5|240|1.25%|23.33%|0|0.0129|0.9877|0.0873|0.0745|1.0000|
|kgw|skd|1|239|0.00%|16.74%|0|0.1030|0.9992|0.0094|0.0081|1.0000|
|kgw|skd|2|239|0.00%|19.67%|0|0.2126|0.9985|0.0183|0.0151|1.0000|
|kgw|skd|3|239|0.00%|23.01%|0|0.3265|0.9977|0.0271|0.0222|1.0000|
|kgw|skd|5|239|0.00%|30.96%|0|0.5604|0.9959|0.0452|0.0371|1.0000|
|synthid|skd|1|240|0.00%|12.08%|0|0.0024|0.9990|0.0101|0.0086|1.0000|
|synthid|skd|2|240|0.00%|16.25%|0|0.0047|0.9980|0.0196|0.0164|1.0000|
|synthid|skd|3|240|0.42%|20.00%|0|0.0072|0.9973|0.0293|0.0242|1.0000|
|synthid|skd|5|240|0.42%|25.00%|0|0.0115|0.9955|0.0467|0.0381|1.0000|


## Measured conclusion

SKD realizes every requested edit budget, but this run does **not establish a
detector-score reduction advantage over matched random selection**: all eight
SKD-minus-random 95% intervals include zero. KGW has no full-SKD evasions at any
budget; SynthID has 0/240, 0/240, 1/240 and 1/240 at 1/2/3/5 edits. These are
separate budgets, not two independent successes. Abstentions are not evasions.

Against entropy-only selection, the SynthID score-reduction difference is positive
at k=2 (0.000546, interval [0.000049, 0.001053]) and k=3 (0.000763,
interval [0.000185, 0.001337]); other intervals include zero. These are small,
unadjusted exploratory comparisons, with no multiplicity correction. They do not
establish a general evasion advantage. KGW z-score and SynthID weighted-mean
reductions have different units and must not be compared numerically across schemes.

At five edits, full SKD preserves mean whole-text cosine .9959 (KGW) / .9955
(SynthID), versus random .9927 / .9921. The selectors match localized edit counts,
not word/token edit distance: full SKD averages 4.52% / 4.67% word edits, versus
random 5.28% / 5.33%. Higher cosine can therefore partly reflect smaller edits.
Tokenizer-only produces the largest mean score drop at k=5 (.7755 / .0129), but
also larger mean word changes (8.69% / 8.73%) and lower cosine (.9886 / .9877).

Post-attack abstention is substantial: full SKD k=5 gives 74/239 KGW and 60/240
SynthID abstentions. Frozen calibration only supports specific scored lengths;
edits can move inputs outside that support. Those outcomes stay in the eligible
denominator and never count as evasion. Zero pipeline failures describes execution,
not language correctness. [The predeclared inspection](skd-inspection.md) documents
meaning and grammar failures even with high cosine.


## Paired intervals and correlations (items 21–23)

Paired intervals use 5,000 sample bootstrap resamples, seed 20261024, on exact-k common subsets (239 KGW / 240 SynthID; no missing score pairs). Positive differences favor SKD. Shared topics limit sample independence. Correlations deduplicate observed one-edit candidate IDs, with dependent observations within samples; they are descriptive post-hoc results.

 every selector to realize k edits. Pool coverage and all-eligible results remain visible alongside the comparable subsets.

|Scheme|k|Reference|Pairs|SKD minus reference score reduction|95% bootstrap interval|
|---|---:|---|---:|---:|---|
|kgw|1|random_pool|239|-0.013022|[-0.044220, 0.018865]|
|kgw|1|entropy_only|239|-0.007646|[-0.035614, 0.019713]|
|kgw|2|random_pool|239|-0.016786|[-0.060303, 0.024907]|
|kgw|2|entropy_only|239|-0.003715|[-0.042985, 0.033516]|
|kgw|3|random_pool|239|-0.025116|[-0.080931, 0.026868]|
|kgw|3|entropy_only|239|-0.010074|[-0.057456, 0.035393]|
|kgw|5|random_pool|239|-0.010011|[-0.074211, 0.050413]|
|kgw|5|entropy_only|239|0.001165|[-0.055845, 0.056547]|
|synthid|1|random_pool|240|0.000142|[-0.000278, 0.000554]|
|synthid|1|entropy_only|240|0.000217|[-0.000141, 0.000576]|
|synthid|2|random_pool|240|0.000360|[-0.000233, 0.000942]|
|synthid|2|entropy_only|240|0.000546|[0.000049, 0.001053]|
|synthid|3|random_pool|240|0.000737|[-0.000057, 0.001488]|
|synthid|3|entropy_only|240|0.000763|[0.000185, 0.001337]|
|synthid|5|random_pool|240|0.000721|[-0.000127, 0.001567]|
|synthid|5|entropy_only|240|0.000612|[-0.000055, 0.001315]|

Positive differences favor SKD. A confidence interval crossing zero does not establish a ranking advantage. The percentile intervals use 5,000 paired sample resamples and public seed 20261024. Missing-score pairs are listed in the machine-readable artifact.

## Post-hoc one-edit feature/effect correlations

|Scheme|Feature|Unique observed candidate edits|Spearman|
|---|---|---:|---:|
|kgw|E|1063|-0.048595|
|kgw|L|1063|0.140799|
|kgw|T|1063|0.223062|
|kgw|R|1063|-0.209476|
|kgw|D|1063|0.120864|
|synthid|E|1080|0.017229|
|synthid|L|1080|0.121126|
|synthid|T|1080|0.136319|
|synthid|R|1080|-0.127336|
|synthid|D|1080|0.079963|

[All methods, budgets, quality and coverage tables](benchmarks/qwen-v030/summary.md). The public feature artifacts contain raw values and normalized ranks; the diagnostics file reports selected feature means by scheme, selector and budget.


## Representative saved examples (items 24–26)

The predeclared `kgw:skd-v1-argument-01` rain-garden example illustrates each requested budget without choosing successful evasions after seeing outcomes. The original z-score is 4.720643; all three attacked examples remain DETECTED at frozen threshold 1.960392.

|Edits|Actual selected replacements, in source order|After score|Whole-text cosine|
|---:|---|---:|---:|
|1|`nearby` → `adjacent`|4.553540|0.999964|
|3|`nearby` → `adjacent`; `often` → `frequently`; `emergency dredging` → `urgent dredging`|4.386438|0.999705|
|5|`nearby` → `adjacent`; `like` → `such`; `often` → `frequently`; `rainfall` → `precipitation`; `emergency dredging` → `urgent dredging`|4.720643|0.998995|

The five-edit output contains “As impervious surfaces such concrete and asphalt expand”: `like` → `such` drops the required “as”. Its whole-text cosine .998995 does not certify grammar. The three-edit GUI replay is shown below; the full public ZIP includes original and attacked text for every method/budget.

![Actual saved Qwen SKD replay: candidates, features, selected edits, diff, quality and evaluator-only results](images/playground-skd.jpg)

## Language failures and scope (items 27–29)

The fixed qualitative review covered 48 sample/budget pairs, 90 method outputs, all eight styles and both schemes at 1/3/5 edits, on the first topic only. It is not a full-corpus human pass rate. Examples include KGW flow `rate` → `speed` (different physical quantities), removal of an adult-supervision requirement by tokenizer-only, SynthID `kicked a` → `threw a`, a unit word changed from inch to centimeter, and duplicated boundary words (“treat treat”, “rapid rapid”). Some source texts already end at the fixed 192-token cap; source faults remain distinct. [Full pre-evaluation inspection](skd-inspection.md).

**No detector feedback entered SKD.** All candidate pools and all methods/budgets were finalized before post-attack evaluator construction. The worker received public text/resources and opaque IDs, with no scheme/key/threshold/calibration/native IDs. Post-hoc correlations did not change proposals, features, weights or selections. Scientific process isolation is not a hostile-code OS sandbox.

**v0.4 was not started.** No cross-key/transfer study, new watermark family, adaptive detector queries, minimum-disruption search, policy learning or further SKD tuning was implemented. Optional paraphrase and leave-one-out diagnostics were omitted from this bounded milestone. This is one local model/key setup; universal removal and theoretical optimality are not claimed.
