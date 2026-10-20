# Visual Playground — v0.1.1

The playground is a local research instrument for existing generation and
detection behavior. The CLI remains the authoritative reproducible experiment
workflow; this interface is interactive exploration and demonstration.

## Install and launch

```sh
pip install -e ".[gui]"
nullmark playground
```

Open http://127.0.0.1:8765. Change the port with
`nullmark playground --host 127.0.0.1 --port 8766`. Stop with Ctrl+C.
Only loopback host choices are supported. Core CLI commands and tests do not
require GUI dependencies. GUI tests use `pip install -e ".[dev,gui,gui-test]"`.

FastAPI/Uvicorn serve bundled HTML, CSS and JavaScript without a frontend build
step. Generation runs in a worker thread; a nonblocking lock admits one generation
or key change at a time. The active model/device is cached; switching evicts it.
CPU is tested; selecting unavailable CUDA returns a controlled error.

## Models and workflow

- **builtin-tiny:** offline, fast, fixed random weights and a synthetic vocabulary.
  Demonstrates software behavior, not natural language quality.
- **GPT-2:** `openai-community/gpt2`, pinned to
  `607a30d783dfa663caf39e06633721c8d4cfcd7e`, as in Experiment 001.
  Natural-language continuations; first use may download weights/tokenizer.
  Slower on CPU. Prompt plus output must fit its 1024-token context.

Choose None, KGW or SynthID, set public parameters/seed, enter a prompt and generate.
Output is limited to 16–512 tokens; prompts to 16,000 characters, with model
context limits checked separately. Loading/generation displays a progress state.
Errors appear inline; terminal logs retain the error class, suppressing upstream
message contents that may contain private settings.

Paired plain and marked paths share model, prompt and public seed. Panels show
counts, relevant detector score/threshold/prediction and first divergence. Later
positions need not align: a changed sample changes future context. Watermarks
bias sampling; they insert no visible symbols. None generates one plain sample
without a detector.

## Hidden keys

The process creates an OS-random master in memory. Key index selects a stable slot
under that master. Repeating settings/seed reuses it; **Fresh key** rotates the
master for future requests. Existing results retain their original context.
Restart discards the master: use CLI private replay files for durable replay.
There is no reveal control, key upload or key-file HTTP route.

Only HMAC-SHA256(master, `nullmark-v1/key-ref/<scheme>/<index>`) is returned. A direct
hash permits testing guessed small-keyspace secrets offline; the new reference
cannot be recomputed from derived-key guesses alone. It identifies the key slot,
not all public parameters. This assumes a private random master, not stronger
upstream watermark security. Old v0.1.0 fingerprints remain vulnerable; replace
them and rotate affected masters where secrecy matters. Key derivation is unchanged.

## KGW: membership and evidence

Green uses a solid underline; red a dotted underline, with G/R text in accessible
names/tooltips and the inspector. Special/unavailable tokens appear neutral.
Membership uses the pinned HF processor and actual generation context including
the prompt. The inspector shows position, text, ID, context text/IDs, membership
and a context-stream cumulative z. Public controls affect the next generation.

The chart instead follows **retokenized continuation text only**, matching the
experiment detector, excluding prompt and initial context. Its final score matches
the detector. These streams may differ after decoding and retokenization; the
inspector reports round-trip equality. The generation-context cumulative score
is not the final experiment score.

Pinned HF 4.57.6's `ignore_repeated_ngrams=True` counter uses tensor identities:
repeated n-grams actually count separately. The playground preserves v0.1
detection and traces its actual behavior. Repeated text is not independent
evidence. Regression tests cover it; any future detector correction needs
separate scientific evaluation/versioning.

Detection reports z-score, threshold, prediction, tokens scored and a standard
normal-approximation upper-tail p-value. This is not empirical calibration,
probability of AI generation, or proof of authorship.

## SynthID: depth values and masks

SynthID has no red/green partition. Select tokens for depth g-values, token mean-g
and cumulative mean-g. The processor's first n−1 generation calls are unwatermarked;
subsequent state uses preceding continuation tokens, not prompt context. Repeated
contexts and EOS suffixes use the existing reference mean detector's masks.
Neutral positions are initial context or masked.

The chart overlays the threshold on cumulative mean-g for both samples.
**The threshold is uncalibrated. This visualization does not establish a statistical
false-positive rate.** Scores are not posterior probabilities of AI generation.
Panels show score, threshold, prediction and usable count. Entirely masked/short
inputs return `insufficient_text`, inviting a longer continuation.

## Stepper, charts and limits

Click/focus token buttons or use Previous/Next for watermark-state inspection.
Charts label axes/threshold; panels and the inspector provide numeric text
equivalents. No animation is required. Desktop is primary; narrow screens stack
panels. Controls have labels, focus states and non-color token distinctions.

Generation logits, ranked distributions and base/marked probabilities are omitted:
v0.1 did not record them. Token states use exact generated IDs. GPT-2 byte-level
tokens may split Unicode characters, causing replacement glyphs in individually
decoded fragments; the exact decoded continuation is available separately.
There is no folder browser, persistence, benchmark runner, job queue, attack logic,
additional watermark family or future experiment dashboard.

## Local security model

This is trusted researcher/evaluator tooling with detector feedback, outside the
blind attack interface. It is not hardened for hostile networks or shared users.
Loopback binding, host/origin checks, bounded JSON, fixed asset paths and a content
security policy reduce accidental exposure. No raw master/derived key is returned,
no private file is served, and no arbitrary code/plugin endpoint exists. Text is
inserted as text nodes, not HTML. No uploads, telemetry or external web assets;
only optional normal Hugging Face model downloads may use the network. Keep
private replay files away from future untrusted workers.

No attacks ship here. Next: **v0.2 — Baseline Attacks**.
