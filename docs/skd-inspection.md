# Deterministic qualitative inspection

Status: **KGW half inspected; SynthID half pending the fixed run**.

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

## Pending

Inspect the same predeclared SynthID cases after their outputs are finalized,
then add the measured whole-text quality and detector results without changing
the attack. Final representative 1/3/5 edit examples and the release screenshot
must use saved protocol-v3 benchmark artifacts.
