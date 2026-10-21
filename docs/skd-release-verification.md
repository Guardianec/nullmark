# v0.3 release verification

Release status: **pending the complete real Experiment 004 and final evidence review**.
No v0.3 tag or GitHub Release has been created at this checkpoint.

The frozen v0.2.0 tag, published release and main commit were verified on GitHub
before editing: `c06819dbbda232f3d7cef07a89e3da33ac5d6ff3`,
[green final CI](https://github.com/Guardianec/nullmark/actions/runs/39568086946).
The v0.3 branch starts at that exact commit. Historical calibration artifacts,
v0.2 benchmark documents/configuration, corpus and baseline implementations are
unchanged.

The initial pre-registration commit is
`5f152135e25cd0ce0a9079c5da2b555274b0d3d0`. The fixed design was pushed before
the real run; [CI passed](https://github.com/Guardianec/nullmark/actions/runs/39573586678)
and [the draft release PR](https://github.com/Guardianec/nullmark/pull/3) is open.

The structured-output correction is pre-registered in
`1af06d32635eede8b19e5dc01f61226556bd2e66`. The initial candidate attempt was
preserved and invalidated before any post-attack detector evaluation. The
[documented amendment](skd-protocol-amendment.md) records the bounded canonical-span
interface, unchanged weights and byte-identical reuse of the 480 source samples.
The corrected offline suite passed **269 tests, 1 skipped**, in 59.94 seconds.

The source-format validation correction is pre-registered in
`1e9c2efc325faed2dfa0cd0f3719ee9bfb5fc0bc`. Both earlier candidate attempts remain
preserved with zero post-attack evaluator rows. Protocol v3 validates exact
selected-span reconstruction and source/candidate identities in both worker and
supervisor. The latest full suite passed **272 tests, 1 skipped**, in 59.33 seconds.

## Completed checks

- Full offline suite: **272 passed, 1 skipped**, 59.33 seconds. The skipped test is
  the optional pretrained-model integration test. GUI fixtures and the complete
  SKD generation/attack/evaluation/report pipeline fixture run without Qwen,
  Ollama, embedding downloads or network access.
- Ruff check and format check pass.
- Wheel and source distribution build successfully. Both archives include the
  GUI assets; scans found no private directories, cached models, credentials or
  actual private masters.
- A fresh `.venv-v030` installed the wheel and pinned CPU dependencies from the
  project cache. The installed package path was verified outside the checkout
  import path. Core Experiment 001 smoke, GUI generation for all three tiny
  schemes, and the isolated attack-worker smoke pass.
- The actual SKD worker runs with evaluator/watermark imports and private-file
  access explicitly forbidden, using deterministic public-resource fixtures.
- Historical pretrained Experiment 001 replay matches saved plain, SynthID and
  KGW text and native token IDs exactly for the three representative samples.
- All frozen v0.1.1 calibration files load. Re-aggregating the saved local v0.2
  benchmark reproduces its saved metrics exactly (32 groups).
- Browser checks exercised the SKD selector, exact edit counts, optional research
  selector, clickable source spans, actual development feature values and
  selected-edit numbering. The development view was explicitly marked as
  unevaluated by a detector. No browser errors/warnings were observed. At widths
  390 and 768, document scroll width equals client width; no horizontal overflow.

Windows sandbox restrictions required workspace-local temporary directories and
an elevated local test/model process. Initial sandbox test/build cleanup failures
were not counted as successful verification; the full suite and clean install
were rerun successfully. No language model was downloaded. The Headroom
compression proxy was unreachable, so targeted reads were used; this makes no
claim that Codex traffic is automatically compressed.

## Pending release gates

The complete real Qwen benchmark, deterministic qualitative inspection,
publication of measured results/candidate features, a real benchmark screenshot,
final rebuilt archives, final CI and v0.3 tag/release are still required. The
benchmark is run from an editable Git checkout so its pre-registration integrity
check can verify the committed source and corpus. v0.4 has not been started.
