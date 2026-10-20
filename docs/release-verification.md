# v0.1.0 release verification

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
The local Headroom service was unavailable; verification used targeted reads and
short logs.

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

No calibrated SynthID Bayesian detector, process sandbox, cross-hardware replay
guarantee, static plots, dashboard or attack algorithm is included. Detector
threshold calibration and larger, independently split datasets are required for
future research claims. Windows private-file protection depends on workspace ACLs.

No v0.2 feature was implemented. The next milestone is **v0.2 — Baseline Attacks**.
