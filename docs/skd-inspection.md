# Deterministic qualitative inspection

Status: **Both schemes inspected: 48 sample/budget pairs, 90 method outputs**.

The [inspection plan](skd-inspection-plan.json) was committed before attack
outcomes. It selects the first lexicographic prompt in each style, both schemes,
k=1/3/5, a rotating ablation and full SKD. These prompts all concern rain gardens;
this limited topic coverage is a limitation of the fixed selection rule. This is
an unblinded language inspection, not a factual verification or preference study.

The KGW half below was inspected while the protocol-v3 attack stage was running,
with **zero post-attack detector evaluations**. No weights or quality thresholds
were changed in response. “Safe” in coverage artifacts means passing the stated
structural/embedding filters, not verified linguistic or factual safety.

## KGW findings

|Style|Inspected selections at 1/3/5 edits|Observed examples and limitations|
|---|---|---|
|Argument|Random pool, full SKD|SKD 1/3 edits retain the broad argument in these examples. At 5 edits, `like` → `such` produces “surfaces such concrete” without “as.” Random 5 replaces `direct runoff into combined` with `surface water flow`, damaging the sewer-management relation and grammar.|
|Essay|Entropy, full SKD|SKD already breaks grammar at 1 edit: `the` → `that` produces “before that clouds break” (local cosine .990). Entropy 3/5 changes `is an efficient` to `works as a rapid`, changing efficiency into speed. `metallic tang` → `sharp metallic taste` shifts a smell description toward taste.|
|Factual|Context, full SKD|`shallow` → `low` weakens the precise description of a depression. SKD 5 includes `is an analysis of` → `a study of their`, yielding “Below a study of their their practical purposes” (local cosine .973). Context also makes this malformed replacement.|
|Instructions|Tokenizer, full SKD|SKD replacements such as `underground` → `subterranean` are locally close, though less plain. Tokenizer 3/5 changes `ensure adult supervision for` to `guarantee adult`, removing the supervision requirement and breaking the following construction despite local cosine .905.|
|Knowledge|Full SKD|`typical` → `common` is a close 1-edit substitution. Larger budgets change metaphor and phrasing (`thick with the glow` → `heavy with the light`); no numerical or named-entity edits occur in this set. The source already uses figurative descriptions, so these are not claims of scientific precision.|
|Narrative|Random pool, full SKD|Names, the garden number and explicit negations remain intact. SKD 5 changes joint `popping` to `bumping`, altering the described event; `fresh volunteer` is less natural than `new volunteer`. Random 5 changes `sun` to `day`, weakening the sunlight/heat relation. The original story already has awkward physical descriptions and ends unfinished.|
|Science|Entropy, full SKD|SKD 3/5 changes `rate of water leaving` to `speed of water exiting` (local cosine .958). Flow rate and speed are different physical quantities, so this is meaningful technical drift. Many other substitutions are close, but embedding similarity does not resolve this distinction.|
|Technical|Context, full SKD|Context 1 inserts an extra `is` through `urban neighborhoods where space` → `city areas where space is`; context 3/5 also drops the integration preposition. SKD's `existing infrastructure` → `current infrastructure` is close, while `vertical` → `upward` gives less precise technical wording.|

Several source continuations already stop mid-sentence at the fixed 192-token
generation cap. This source truncation is distinct from attack-induced damage.
No altered literal negation, number or protected proper name was observed in this
planned KGW set, consistent with the hard filters; implicit requirements and
technical meaning can still change. Multiword proposals can duplicate boundary
words or remove grammatical structure. A high local embedding cosine can coexist
with these failures, including one-edit failures.

## SynthID findings

The same fixed selection was inspected after the first eight SynthID candidate
pools were finalized, still with **zero post-attack detector evaluations**.

|Style|Inspected selections at 1/3/5 edits|Observed examples and limitations|
|---|---|---|
|Argument|Random pool, full SKD|SKD changes `direct` mitigation to `clear` mitigation inside a longer span, weakening a causal description. `sewer` → `sewage` shifts infrastructure terminology to its contents; the local cosine is .982. Other substitutions such as `necessary` → `required` are close.|
|Essay|Entropy, full SKD|Full SKD mostly changes flow imagery and style in this example. Entropy 5 changes `concrete` to `stone`, altering a stated material (local cosine .863); density → busyness also broadens the original concept.|
|Factual|Context, full SKD|SKD 1 `form of` → `type of` is close. Context removes `designed` while changing `green infrastructure` to `sustainable infrastructure`; larger budgets generalize some engineering terms. The source already simplifies the relationship between rain gardens and bioswales.|
|Instructions|Tokenizer, full SKD|Tokenizer 3/5 replaces `permeable soil mixes suited` with `drought-resistant soil blends`, changing the stated soil property and damaging the following “to local climate” phrase (local cosine .936). SKD's `traffic` → `flow` makes a safety-planning term less specific. Literal negations remain in place.|
|Knowledge|Full SKD|Most inspected substitutions are close (`perfectly` → `completely`, `likely` → `probably`). `flowers` → `blooms` and `looks` → `appears` are mainly stylistic in the given context. This does not independently verify the source's ecological claims.|
|Narrative|Random pool, full SKD|SKD 5 changes `kicked a` → `threw a`, a different physical action despite local cosine .987. It also changes the word `inch` to `centimeter` in an idiom, showing that unit words are not numeric-string anchors. Random 3/5 changes water going `into` the soil to water going `onto` it (local cosine .996), altering the infiltration relation.|
|Science|Entropy, full SKD|SKD 3/5 changes `specifically engineered to` → `designed to treat`, yielding “designed to treat treat urban runoff” because the next source word is retained (local cosine .980). Other changes remove emphasis such as `critical` or replace approximate explanatory wording.|
|Technical|Context, full SKD|Context 1 drops `as` through `system typically functions as` → `system generally functions`. SKD 3/5 and context 3/5 change `while allowing` → `permitting rapid`, producing “permitting rapid rapid infiltration” (local cosine .992). One SKD 5 edit repairs the source's existing `a engineered` article error; the source error must not be attributed to the attack.|

## Interpretation and remaining evidence

Both schemes exhibit grammar or meaning failures in the predeclared examples.
Many replacements preserve the broad topic, but the present filters do not
establish meaning preservation. High local cosine can overlook articles,
prepositions, duplicated boundary words, physical actions and technical terms.
Numeric-string/URL/negation protection does not constitute protection of all
quantities or implicit requirements; unit words can still change.

The inspection did not change weights, filters, candidate generation or any
selection. It is a limited qualitative sample, not an estimated full-corpus
human quality-pass rate. Add the measured whole-text quality and detector results
after the fixed evaluation completes. Final representative 1/3/5 edit examples
and the release screenshot must use saved protocol-v3 benchmark artifacts.
