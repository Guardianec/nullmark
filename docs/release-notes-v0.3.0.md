# NullMark v0.3.0 — Sparse Keyless Disruption

SKD tests whether public linguistic signals can rank a fixed set of local edits
to weaken watermark evidence while preserving text. It uses the existing local
Qwen model, canonical source-span proposals, structural/anchor validation,
deduplication and non-overlapping selection. All methods share one pool per sample.

The fixed score combines ordinary entropy (+1), generic context leverage (+1.25),
tokenizer instability (+1), linguistic minimality (+1) and semantic distortion
risk (−1.5), normalized within each sample. No detector information enters it.
Random-pool, entropy-only, context-only, tokenizer-only and full SKD are evaluated
at exact 1/2/3/5 localized edits, with actual counts and coverage reported.

The completed real Qwen study contains 240 fresh prompts, 480 source continuations,
479 eligible pools and 9,580 attempts. Eligibility is 239/240 KGW and 240/240
SynthID; every eligible pool supports all budgets. No execution failures occurred.

Full SKD evasion at 1/2/3/5 edits is 0/0/0/0% KGW and 0/0/.42/.42% SynthID.
All SKD-vs-random score-reduction intervals include zero. Against entropy-only,
SynthID k=2 and k=3 show small positive score-drop differences with unadjusted
95% intervals above zero; other intervals include zero. This does not establish
a general evasion advantage. Post-attack abstentions remain separate: at five
SKD edits, 74/239 KGW and 60/240 SynthID attempts abstain.

Mean five-edit cosine is .9959 KGW / .9955 SynthID; word-edit fractions are
4.52% / 4.67%, token-edit fractions 3.71% / 3.81%. Applicable literal anchors
are retained. The fixed qualitative inspection nevertheless documents grammar,
boundary duplication, technical-meaning and physical-action changes. Embedding
similarity and literal-anchor protection do not establish factual correctness.

The Playground adds a candidate inspector with real raw/normalized feature values,
selected spans, numbered replacements, before/diff/after text, quality and a
separately labeled evaluator-only result. The published screenshot replays saved
real benchmark artifacts using the production components.

Validation: 272 tests pass, one optional pretrained integration test skipped;
offline CPU CI, clean-wheel smoke, real isolated-worker guards, exact historical
GPT-2 text/token replay, archive privacy checks, and browser inspection. The
public ZIP includes all candidate features and outputs, quality, denominators,
paired bootstrap intervals, descriptive feature/effect correlations and seven plots.

Scientific preregistration: `1e9c2efc325faed2dfa0cd0f3719ee9bfb5fc0bc`.
Two implementation corrections were recorded before any post-attack evaluation;
invalidated attempts are preserved locally and source generations remained
byte-identical. Weights/features were not tuned to detector outcomes. The frozen
SynthID evaluator had 3/99 observed held-out FPR at a 1% target; no recalibration.

[Full research report](https://github.com/Guardianec/nullmark/blob/v0.3.0/docs/skd-final-report.md) ·
[Protocol](https://github.com/Guardianec/nullmark/blob/v0.3.0/docs/skd.md) ·
[Measured results](https://github.com/Guardianec/nullmark/blob/v0.3.0/docs/skd-results.md) ·
[Qualitative failures](https://github.com/Guardianec/nullmark/blob/v0.3.0/docs/skd-inspection.md)

One model/key setup and 30 shared topics limit generalization. Bootstrap samples
are not independent topic clusters; correlations are descriptive and dependent.
No universal watermark removal or theoretical optimality is claimed. No detector
feedback, adaptive query loop, key inference, new watermark family or v0.4 work.
Historical v0.2 calibration, results, tag and release remain unchanged.
