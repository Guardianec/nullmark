# SKD measured results

Pre-registration: `1e9c2efc325faed2dfa0cd0f3719ee9bfb5fc0bc`. The full run used 240 new prompts, 480 source continuations, and 9580 eligible attack attempts. No weights were changed after detector outcomes.

[Full measured tables](benchmarks/qwen-v030/summary.md) · [Protocol](skd.md) · [Matched ablations](skd-ablation-results.md)

The matched-pool experiment tests ranking at the same number of localized edits. Whole-text cosine does not establish factual correctness; failures and abstentions remain separate from evasion.

Frozen evaluator target FPR is 1%; the original held-out SynthID d20 weighted FPR was 3/99 (3.03%). No v0.3 recalibration.

## Eligibility

- kgw: 239/240 eligible (99.58%), 0 misses, 1 baseline abstentions.
- synthid: 240/240 eligible (100.00%), 0 misses, 0 baseline abstentions.

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

## Historical context

The frozen v0.2 sparse attacks exhausted their candidate pools and plateaued below roughly 1% actual word edits. Their prompt corpus and mechanics differ from v0.3, so their denominators are not pooled. See [the historical results](baseline-attack-results.md).

## Limits

Candidate-local embedding checks can miss factual changes and awkward grammar. Context leverage and replaceability can tie across many candidates; a constant feature contributes no ranking information. Thirty shared topics span eight prompt styles, creating topic dependence that the sample bootstrap does not model. This is one local model/key setup, with no cross-key or cross-scheme transfer study.

The post-hoc correlations are descriptive dependent observations. They never feed back into this benchmark's candidate generation, weights or selectors. See the qualitative inspection for concrete language failures.
