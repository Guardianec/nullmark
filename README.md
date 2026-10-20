# NullMark

**Measuring the Minimum Semantic Edit Required to Break Keyed LLM Watermarks**

Current release: **v0.1.0 — reproducibility foundation**.

NullMark is a research benchmark for the robustness of open generative-text
watermarks. Version 0.1 establishes reproducible generation, detection, paired
controls, hidden key configurations, and auditable experiment records. It does
not implement attacks.

The eventual research question is the **Minimum Disruption Budget (MDB)**:
how little meaning-preserving editing is sufficient to change a keyed detector's
decision, under a specified threat model? MDB search and semantic similarity
optimization are future work. Small smoke runs establish plumbing, not robustness
claims.

NullMark is not intended for defeating commercial provenance systems, recovering
proprietary keys, or querying private production detectors. All experiments here
use open implementations and locally controlled model inference.

## Quick start

Python 3.11 or newer; Python 3.11–3.12 are tested in CI. No GPU is required.
From a checkout, create and activate a virtual environment:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv/Scripts/Activate.ps1
python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[dev]'
nullmark --help
nullmark --version
```

Run the completely offline smoke model after installing dependencies:

```sh
nullmark experiment run configs/experiments/cpu_smoke.yaml --output results/smoke
nullmark experiment summarize results/smoke
```

This uses a tiny, random-weight GPT-2 architecture and an internal 512-token
vocabulary. Its output is synthetic word sequences, **not ordinary language**.
It exercises the real Transformers watermark processors and detectors without
downloading weights. Use pretrained GPT-2 for actual language generation.

## Reproducing Experiment 001

```sh
nullmark experiment run configs/experiments/001_watermark_reproducibility.yaml --output results/experiment001
nullmark experiment summarize results/experiment001
```

The first run downloads the pinned `openai-community/gpt2` model and tokenizer
(approximately 550 MB of weights). This CPU configuration uses eight original
prompts, two hidden key configurations per family, and up to 192 new tokens per
generation. It produces 48 samples and 64 detector observations: 16 watermarked
and 16 plain observations per detector. Each plain continuation is evaluated by
both detectors with the matching key index. A marked sample is evaluated by its
own family's detector. This is explicitly a **smoke experiment**, not a calibrated
or statistically powered benchmark.

Random watermark keys come from an OS-random private master, independent of the
public sampling seed. Reproduce the exact keys and generated samples locally:

```sh
nullmark experiment run results/smoke/config.resolved.yaml --secrets results/smoke/private/secrets.json --output results/replay
```

Use the same package environment, model revision, device and thread count.
Generated text, token IDs and scores should replay on that environment; paths,
run IDs, timings and environment metadata will differ. Bitwise equivalence across
different hardware, PyTorch versions, or CPU/GPU backends is not promised. An
existing output directory is always refused.

Configuration is strict YAML: unknown fields, invalid ranges, unpinned pretrained
model revisions, and secret watermark fields are rejected. Custom datasets use
`source: jsonl`, `path: prompts.jsonl`, and `sample_count`; rows contain `id`,
`style`, and `text`. Paths resolve relative to the configuration. A resolved run
stores its selected prompt snapshot and SHA-256 digest.

## Generate and detect a single controlled sample

After creating `results/smoke`:

```sh
nullmark generate --config configs/experiments/cpu_smoke.yaml --scheme none --prompt "Explain a public library."
nullmark generate --config configs/experiments/cpu_smoke.yaml --scheme kgw --secrets results/smoke/private/secrets.json --key-index 0 --prompt "Explain a public library." > results/continuation.txt
nullmark detect --config configs/experiments/cpu_smoke.yaml --scheme kgw --secrets results/smoke/private/secrets.json --key-index 0 --text-file results/continuation.txt
```

Use `--scheme synthid` for SynthID. Detection is a trusted evaluator operation;
it requires the private master and the same configuration/model/tokenizer.
Generate writes continuation text only to stdout, without an added newline.
Save redirected text as UTF-8 (PowerShell 7 does this by default).

## Architecture and artifacts

```text
local causal model + open watermark processor
                    ↓
            text-only AttackInput
                    ↓
      future blind transformation (v0.2+)
                    ↓
  trusted evaluator + private key configuration → detector
```

`nullmark.models` owns model loading and deterministic sampling. The watermark
registry wraps both families behind `generate`, `detect`, and public `metadata`
methods. `nullmark.experiments` orchestrates paired samples and the trusted
`nullmark.evaluation` modules aggregate results.

`nullmark.attacks.base` exposes only an immutable sample ID, prompt, text, and a
transformation protocol. No attack implementation ships in 0.1. An AST test
guards the current package's imports. This is an architectural boundary, **not a
Python security sandbox**: future untrusted attack workers must run separately,
without access to evaluator files, memory or detector feedback.

```text
results/<experiment>/<run>/       # or the explicit --output directory
  config.resolved.yaml           # public config, no secrets
  prompts.jsonl                  # original selected prompts
  manifest.json                 # model/tokenizer revision, dataset hash, environment
  public_samples.jsonl           # ONLY sample_id, prompt, text; attacker input
  generation.jsonl               # evaluator provenance, labels, seeds, key hashes, lengths
  evaluation.jsonl               # evaluator scores and predictions; never blind-attack input
  failures.jsonl                 # stage and exception type; no exception contents
  metrics.json                   # pooled/per-key descriptive statistics
  summary.md
  private/
    secrets.json                 # local master; NEVER publish to a blind attacker
    tokens.jsonl                 # exact original continuation token IDs
```

Only `public_samples.jsonl` is the attacker-facing export. Generation metadata,
evaluation scores, resolved config and summary are separate research artifacts;
do not hand the whole run folder to a blind attack. Generated results, private
artifacts, environments and model caches are Git-ignored. POSIX private directories
use mode 0700 and master files 0600. Windows inherits the workspace ACL; restrict
access to that folder if sharing the computer.

## Watermark implementations

Both adapters import **Transformers 4.57.6** (Apache-2.0), rather than vendoring
generation algorithms:

| Family | Generation | Detection |
| --- | --- | --- |
| SynthID-Text | `SynthIDTextWatermarkingConfig` | HF reference g-values, context/EOS masks, reference mean statistic |
| KGW-style | `WatermarkingConfig`, `lefthash` | HF `WatermarkDetector`, unique n-grams by default |

SynthID varies the key at each depth and the sampling-table seed; KGW varies the
hashing key. Context sizes, thresholds and other public parameters are configured
in YAML. SynthID uses a mean-g threshold of 0.60 by default; it is uncalibrated,
not a probability, and has no claimed p-value or target false-positive rate.
NullMark does not use an untrained Bayesian detector. KGW reports a z-score and
one-sided normal-approximation p-value (computed with `erfc`); that approximation
does not establish empirical calibration. Key derivation is for experimental
separation, not a claim of cryptographic security for the upstream schemes.

Detection retokenizes **continuation text only**, excluding the prompt and
unscored initial context. Original token IDs are retained privately, and round-trip
differences are counted. Very short or entirely masked inputs abstain; abstentions
and generation/detection failures are reported separately and excluded from
classification-rate denominators. Scores from different families are not pooled.

## Verification

```sh
ruff check .
ruff format --check .
pytest -q
python -m build
```

Default tests need no network or pretrained model: config validation, adapter
contracts, positive/plain/wrong-key detection, deterministic replay, state reset,
public export isolation, architecture imports, failure accounting, full experiment
replay and CLI commands. GitHub Actions runs these checks and an offline CPU
experiment on Python 3.11 and 3.12. There is no configured static type checker;
the package uses type hints at its main interfaces.

An opt-in pretrained integration test is available with `NULLMARK_PRETRAINED=1`
in the environment, then `pytest -q -m integration`. It downloads the same pinned
GPT-2 model. [Release verification](docs/release-verification.md) records the
actual local checks and representative results for this release.

## Research notes, licensing and roadmap

See [research design](docs/research-design.md), [third-party attribution](THIRD_PARTY.md)
and [changelog](CHANGELOG.md). NullMark is licensed under Apache-2.0. The built-in
prompts are original project material under that license. Model weights remain
under their own upstream license.

The finite roadmap is:

- **v0.1 — Reproducibility** (this release)
- **v0.2 — Baseline Attacks**
- **v0.3 — Sparse Keyless Disruption (SKD)**
- **v0.4 — Cross-key and cross-watermark generalization**
- **v0.5 — Robustness benchmark and reporting**
- **v1.0 — Research-quality release**

No baseline edits, paraphrasing, SKD, MDB optimization, learned attacks, commercial
API tests, or dashboard are implemented in v0.1.
