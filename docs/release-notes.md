NullMark v0.1.1 adds the **Visual Playground**, a local interactive view of the
existing watermark generation and detection pipeline.

- Optional FastAPI/Uvicorn interface with bundled assets and localhost defaults.
- Offline builtin-tiny and pinned GPT-2; None, KGW and SynthID modes.
- Same-seed plain/marked comparison, first divergence, token inspector and stepper.
- KGW context-aware membership and cumulative detector z-score traces.
- SynthID per-depth g-values and cumulative mean-g, explicitly uncalibrated.
- Shared typed inspection; short-text and retokenization handling.
- Master-bound HMAC references replace guessable direct-secret hashes.
  Key derivation stays unchanged; old fingerprints require replacement.
- Core/GUI regression tests, optional GUI CI and clean-install verification.

```sh
pip install -e ".[gui]"
nullmark playground
```

The CLI remains authoritative for reproducible experiments. The GUI is trusted
local exploration tooling. Detector scores are not proof of authorship; SynthID
has no calibrated false-positive rate. Pinned HF KGW repeated-n-gram counting
behavior is documented and preserved. No generation-time probabilities are fabricated.

**No attack algorithms were implemented. Next: v0.2 — Baseline Attacks.**
