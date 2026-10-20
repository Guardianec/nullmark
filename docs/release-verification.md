# v0.1.1 release verification

## Final detector calibration protocol

- Implementation commit `3320de444f7d7cd219acd001862e453e0db17703` passed
  [GitHub CI](https://github.com/Guardianec/nullmark/actions/runs/39427720808)
  and the paired pull-request workflow run.
- Local full suite: **146 passed, 1 skipped**. Ruff lint/format passed. The
  default skip remains the opt-in pinned GPT-2 integration test.
- Saved historical Experiment 001 samples replayed exact text and original IDs
  for plain, SynthID and KGW from the existing offline GPT-2 cache. The historical
  YAML is unchanged from `d1b4716`.
- v0.1.1 wheel/source distribution built successfully, including calibration
  modules, source configs/dataset and fixed Playground assets, with no private
  directories or model weights. The installed core-only wheel completed the
  12-sample offline smoke experiment with zero generation/detection failures.
- New tests verify clean-only fitting before held-out generation, disjoint splits,
  finite-sample ranks/ties, uncertainty warnings, immutable artifact reload and
  compatibility checks, raw/weighted means, native/visible diagnostics, length
  abstention, baseline detection eligibility, per-sample frozen decision exports,
  and calibrated/uncalibrated Playground behavior. Legacy CLI predictions are
  explicitly tagged demo-only and do not expose a calibrated DETECTED state.
- Protocol compatibility is independent of application release version: unchanged
  detector-v1 artifacts remain reusable, while detector-protocol changes are rejected.
- Browser verification exercised the named weighted-mean mode, token inspection,
  selected-statistic trace, visible/usable counts and score-only presentation.
  [Screenshot](images/playground-calibration.png).
- Actual local Qwen study completed: **128 calibration / 100 evaluation prompts**,
  **1,140 generations / 3,192 score rows**, 114.60 minutes excluding model loading.
  All seven frozen artifact hashes match the snapshot taken before held-out scoring.
  Public aggregate metrics, provenance, split IDs/prompts, artifacts and histograms
  are linked from the [measured report](detector-calibration-results.md).
- Depth-20 weighted mean is the frozen exploratory recommendation: **97/98 TPR,
  3/99 observed FPR**, 1% target, 3/200 length abstentions. No SynthID mode achieved
  observed FPR ≤1%; sparse-tail and mode-selection uncertainty are documented.
- Browser verification with the actual matching artifact/private master replayed a
  held-out narrative seed and produced plain NOT DETECTED / marked DETECTED, with
  the weighted trace and calibrated threshold. No browser errors or warnings.
  [Calibrated screenshot](images/playground-calibrated-qwen.png).

The [calibration protocol](detector-calibration.md) documents statistical support
and limitations separately from software checks. Historical five-prompt evidence
below remains a smoke observation, not an empirical operating-point validation.

## Ollama / direct GGUF amendment

The focused local-model amendment was verified on 2026-10-20:

- Full suite: **106 passed, 1 skipped**. The pretrained integration test passed
  separately using the existing pinned GPT-2 cache in offline mode.
- Ruff lint/format and whitespace checks passed.
- Existing Ollama `qwen3.5:9b-q4_K_M` weights passed native callback capability,
  paired KGW/SynthID, wrong-key KGW, CPU/GPU inference and exact experiment replay
  checks. No duplicate model checkpoint was downloaded.
- Historical Experiment 001 text and original token IDs replayed exactly in all
  three schemes with explicit historical sampling settings.
- Wheel and source distribution built successfully. The installed core-only
  wheel ran the 12-sample offline smoke experiment without failures; its environment
  contains neither FastAPI nor llama-cpp-python. The installed GUI wheel passed
  fixed-asset, three-scheme builtin-tiny, sampling metadata and discovery checks
  without llama-cpp-python, and selecting Qwen returned a clean optional-extra hint.
- Qwen plain, paired KGW and paired SynthID were checked in the browser. Exact
  contexts, token selection and traces worked, with no console errors/warnings.
  Layouts at 1440/768/390px were inspected without horizontal page overflow.
  Screenshot: `docs/images/playground-qwen.jpg`.
- Repository and distribution scans found no model weights, caches, credentials
  or raw private key values from the local verification runs.
- [Local model verification](local-model-verification.md) records the exact model,
  runtime/template digests, five paired score comparisons, representative prose
  and limitations. Score increases are distinguished from threshold crossings.

## Original Visual Playground verification

Verified 2026-10-20 on Windows x86-64, Python 3.12.8, PyTorch 2.6.0+cpu,
Transformers 4.57.6, FastAPI 0.115.14, Starlette 0.46.2 and Uvicorn 0.34.3.

- Full suite: **73 passed, 1 skipped**. The opt-in pretrained test also **passed** separately.
  One upstream Starlette/AnyIO deprecation warning does not affect the result.
- Ruff lint, formatting and diff whitespace checks passed.
- Wheel and source distribution built with isolated build environments. Both
  contain the fixed playground assets and exclude private files/models/caches.
- A newly created `.venv-v011` installed the wheel with CPU core dependencies.
  From outside the source directory, the installed package reported 0.1.1,
  CLI help worked, and playground launch without FastAPI printed the clean
  optional-dependency install hint. Dependency compatibility check passed.
- The installed core CLI ran the offline smoke experiment: 12 samples,
  no generation/detection failures or abstentions. These are software checks,
  not statistically powered watermark results.
- After installing the wheel's `[gui,gui-test]` extras, the installed app's main
  route, fixed assets and all three offline generation endpoints passed.
- Master-bound key-reference regressions include different masters producing
  the same forced small KGW integer but different opaque references. Existing
  export-isolation/replay tests remain intact.
- Token inspection tests compare full and prefix cumulative traces against
  existing detectors, including repeated n-grams, context widths, SynthID depths,
  short text, special tokens and retokenization differences. No logits are invented.
- Browser verification exercised builtin-tiny None/KGW/SynthID, paired output,
  fresh hidden key/index, token selection/stepper and charts. Pinned pretrained
  GPT-2 was also generated in all three modes. A separate GPT-2 service check
  confirmed detector-token counts and final cumulative scores for both paired
  samples. Weights came from the existing local pinned cache, without cloud APIs.
- A naturally one-token GPT-2 output displayed `insufficient_text` in both
  paired panels and an informative chart state. Unavailable CUDA displayed a
  controlled inline error. Backend tests cover malformed settings, oversized
  requests, model/context failures, concurrent requests and sanitized errors.
- Desktop/tablet/narrow browser widths (1440/768/390) were visually inspected;
  no horizontal page overflow at 390px. Browser console checks found no errors
  or warnings. Screenshots: `docs/images/playground-kgw.jpg` and
  `docs/images/playground-synthid.jpg`, approximately 236 KB each.
- CI retains separate core Python 3.11/3.12 jobs without GUI extras and adds
  one offline GUI smoke job. Actual commit status is available on
  [GitHub Actions](https://github.com/Guardianec/nullmark/actions).

The Windows sandbox cannot complete asyncio's loopback socket-pair setup, so
server and GUI tests ran with local networking allowed. Headroom stored the
source excerpt but its configured compression proxy was unreachable; focused
source reads were used. No guarantee of automatic traffic compression is made.

Original playground limits: Transformers CPU only was verified; SynthID is uncalibrated; no recorded
generation logits/probabilities, persistent GUI keys, run-folder browser or attack
algorithms. Pinned HF's repeated KGW tensor n-grams count separately despite its
unique-n-gram option; the existing detector is preserved and the trace matches it.
Old v0.1.0 fingerprints need replacement/affected-master rotation where secrecy
matters. See [playground](playground.md) for the local security and score model.

Next milestone: **v0.2 — Baseline Attacks**. It was not started.

---

# v0.1.0 release verification (historical)

Local verification date: 2026-10-20. Windows x86-64, Python 3.12.8,
PyTorch 2.6.0+cpu and Transformers 4.57.6. No GPU or commercial API was used.

## Checks

- Full default pytest suite: **36 passed, 1 skipped**. The skipped test is the
  opt-in pretrained integration test; it was also run separately and **passed**.
- Ruff lint and formatting checks passed. No static type checker is configured.
- Wheel and source distribution built successfully with `python -m build`.
- The wheel was installed into a separate clean virtual environment with the
  verified dependency versions. Imports resolved to that environment's
  `site-packages`, outside the source checkout; `pip check` passed.
- Installed CLI help/version, offline experiment, summaries, plain generation,
  and keyed KGW/SynthID generation and detection were exercised.
- The documented replay command reproduced identical public samples and detector
  results using the saved private master. Only timings/run metadata differed.
- Experiment 001's resolved config, prompts, raw samples, generation records,
  scores, failures, metrics, summary and private token/master artifacts were inspected.
- No experiment master or raw derived watermark parameter appeared in non-private
  experiment files or tracked release files. Distribution contents excluded private
  artifacts, model weights and caches.
- CLI parse/validation errors are sanitized, and redirected stdout/stderr are
  UTF-8, including on Windows.
- [GitHub Actions](https://github.com/Guardianec/nullmark/actions) installs the
  package, checks Ruff, runs pytest and a separate offline CPU experiment, and
  builds distributions on Python 3.11 and 3.12. The initial implementation's
  [complete matrix run](https://github.com/Guardianec/nullmark/actions/runs/39388995740)
  passed; release-head status is available on the Actions page.

The desktop sandbox required placing temporary build/test directories inside the
workspace. This changes neither package behavior nor CI's normal temporary paths.
For the original release checks, the local Headroom service was unavailable;
verification used targeted reads and short logs. During the final calibration
review, on-demand compression worked and exact originals were retrieved before
numerical conclusions (hash `7aa533119097740a537dc36a`); its optional proxy reported
unreachable. This does not imply that all Codex traffic is compressed.

## Observed pretrained GPT-2 smoke run

Command:

```sh
nullmark experiment run configs/experiments/001_watermark_reproducibility.yaml --output results/experiment001
```

Eight original prompts × two hidden key configurations × three generation
conditions produced **48 samples** and **64 detector observations**. Runtime was
**283.22 seconds**, including model loading. Generated continuation lengths ranged
from **1 to 192 tokens**, with mean **170.125** and median **192**. There were
**zero generation failures** and **zero detector exceptions**.

| Detector | Scored marked | Scored plain | TPR | FPR | Accuracy | Abstentions | Mean marked score | Mean plain score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SynthID mean-g | 15 | 15 | 100% | 0% | 100% | 2 | 0.68077 | 0.50807 |
| KGW z-score | 15 | 15 | 100% | 0% | 100% | 2 | 14.66537 | 0.09195 |

One plain continuation and one marked continuation for each family ended too early
to score. The plain continuation is shared between detectors, so these are three
short samples yielding four abstaining detector observations. Rates exclude
abstentions. **These are small, uncalibrated smoke results, not research-scale
evidence or a measured population FPR.**

Twenty of the 48 continuations differed when their decoded text was retokenized.
Reported detection always used the actual saved text, not the private original
token stream. Those original IDs remain available locally for auditing.

Fresh runs derive fresh keys and may produce different metrics. Exact local replay
requires the original private master, which is deliberately excluded from this
repository. The run folder remains under `results/experiment001` in the development
workspace; generated artifacts are Git-ignored.

The separate offline smoke run produced 12 samples, no failures or abstentions,
100% observed TPR and 0% observed FPR for both families. Its random-weight model
tests software behavior and cannot support language-quality or research conclusions.

## Release limits

No trained SynthID Bayesian detector, process sandbox, cross-hardware replay
guarantee, dashboard or attack algorithm is included. Empirical raw/weighted
calibration and static histograms are included. Larger independent confirmation
is required for strict population-FPR claims; the completed SynthID study exceeds
its 1% target on held-out data. Windows private-file protection depends on workspace ACLs.

No v0.2 feature was implemented. The next milestone is **v0.2 — Baseline Attacks**.
