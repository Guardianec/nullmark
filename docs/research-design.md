# Research design — v0.1

NullMark asks how a keyed open text watermark behaves under controlled generation
and, in later milestones, meaning-preserving edits. The first release validates
the experiment machinery. It makes no claims about watermark-breaking attacks.

## Threat model and information boundary

The future blind attacker knows the prompt, continuation text, sample identifier,
public algorithm family, and published research methodology. It receives neither
keys nor detector statistics, model generation state, or a detector query oracle.
The evaluator knows the model/tokenizer revision, all watermark settings, private
master, derived keys, exact original token IDs, ground truth and detector outputs.
The experiment runner is trusted; it does not invoke any attack in this release.

The intended flow is watermarker → sample → attacker boundary → evaluator.
`AttackInput` has a fixed, text-only allowlist. Public exports are constructed from
that allowlist rather than serializing a rich experiment object. AST checks reject
evaluator, model and watermark imports in the current attack package. Such checks
prevent accidental coupling; they do not isolate arbitrary Python. When executing
untrusted future attacks, use a separate process/environment/filesystem that only
has the public sample export. Do not mount private run files there.

The research outcome is a change in the held-out detector's behavior, so future
attacks do not need to recover a key. Revealing scores during transformation would
change the experiment into a detector-query attack. Blind and feedback-enabled
threat models require separate, explicitly labeled evaluations; feedback is not
supported in 0.1.

## Generation and replay

A public seed controls sampling; it never controls key generation. A private,
OS-random 256-bit master is domain-separated through HMAC-SHA256 by scheme,
key index, and SynthID depth/table parameter. The first 32 digest bits, plus one,
form an upstream-compatible positive integer parameter. These values are not
claims about cryptographic security of the upstream watermark. Key references
are SHA-256 digests of canonical private configuration; plaintext keys are not
written to exported experiment rows. The local master suffices to regenerate
them under the versioned `nullmark-v1` derivation.

Save the private master to replay a run. Publishing the master or all run files
would invalidate blind evaluation. Keep private replay artifacts under evaluator
access control. The normal resolved YAML contains no secrets, and exported
sampling seeds cannot derive the master. Tests search all non-private output
files for the master and actual derived key values.

Sampling uses a fresh scoped Torch RNG per sample. Corresponding plain and marked
conditions use the same sampling seed; different prompt/key pairs use a SHA-256
derived seed. Process-global deterministic algorithms and configured thread counts
are recorded; CPU is the tested backend. The built-in smoke model's fixed weight
initialization seed is independent of both generation and watermark randomness.
Full pretrained model commit IDs are mandatory, remote model code is disabled,
and only safetensors weights are loaded. Tokenizer and model use the same revision.
The prompt subset, dataset digest, package versions, platform, source Git revision
when available, model identifier and configuration are stored in every run.

## Detector choices and statistics

SynthID generation uses the Google DeepMind/Hugging Face integration. Its
reference g-values are extracted with the matching secret config; repeated
contexts and EOS/padding suffixes are masked. We average unmasked g-values across
all depths, following the reference mean detector. The 0.60 threshold is a
configurable smoke default. It is not a calibrated posterior or a guarantee of a
specific FPR. A trained Bayesian detector is deliberately not substituted with
random parameters. Experiments on texts of different lengths need length-aware
calibration on independent controls.

KGW uses Transformers' `lefthash` green-list bias and corresponding detector;
repeated n-grams are counted once by default. Its nominal z-score uses the
configured green-list ratio. Vocabulary partition sizes are rounded down by the
reference implementation, so that nominal ratio is approximate on small
vocabularies. We compute its upper-tail normal p-value with the standard library
`erfc`, rather than the upstream p-value approximation. Dependencies among tokens,
repeated contexts, entropy, and sample length limit the interpretation of this
p-value. It is not the probability that a document is watermarked.

Text is decoded without cleanup and retokenized before detection. The prompt is
excluded, as are the initial continuation positions without sufficient context.
The original continuation IDs are retained for auditing; a mismatch count flags
tokenizer round trips. A detector with insufficient usable text abstains instead
of returning an invented negative score. Failures and abstentions are counted
separately; TPR/FPR/accuracy use only successful non-abstaining observations.
Generation failures are never silently treated as correct negatives.

Raw data, pooled and per-key TPR/FPR, accuracy, mean/median/population standard
deviation/range of scores and lengths, generation timings, failures, and total
runtime are retained. Each plain sample is evaluated by both families; those
observations and key-conditioned generations are correlated. No independence,
confidence interval, calibrated FPR or population generalization is inferred from
the tiny default runs.

## Scientifically valid future comparisons

Hold model, tokenizer, prompts, sampling policy, length budgets, detector thresholds
and key distribution constant across compared conditions. Calibrate detectors on
disjoint data before measuring attacks. Predefine false-positive targets, report
abstention/failure coverage and uncertainty, and split development/evaluation
prompts and keys. Define edit cost and semantic preservation before searching for
MDB. Compare methods at matched query/compute/edit budgets. Report length and
style strata, all controls and raw results, including unsuccessful trials. Never
select test keys or tune thresholds using attack outcomes on the held-out test set.
These are evaluation requirements for future work, not implemented attack features.

## Limitations

- The offline model is untrained and cannot establish language quality or research conclusions.
- GPT-2 is small; its behavior cannot establish generalization to stronger models.
- The smoke prompt/key counts are too small for reliable rare false-positive estimates.
- SynthID thresholds need independent empirical calibration; no Bayesian training ships here.
- CPU replay is tested; cross-environment bitwise replay and CUDA behavior are not guaranteed.
- Parameter randomization is not a cryptographic security proof or production-key inference.
- Architecture checks are not a sandbox, and filesystem ACLs remain the evaluator's responsibility.
- Version 0.1 contains no transformations, semantic scoring, MDB search or robustness benchmark.

## References

- Kirchenbauer et al., *A Watermark for Large Language Models*, ICML 2023:
  https://arxiv.org/abs/2301.10226 and https://github.com/jwkirchenbauer/lm-watermarking
- Dathathri et al., *Scalable watermarking for identifying large language model outputs*,
  Nature 2024: https://doi.org/10.1038/s41586-024-08025-4
- Google DeepMind SynthID-Text implementation and mean detector:
  https://github.com/google-deepmind/synthid-text and
  https://github.com/google-deepmind/synthid-text/blob/main/src/synthid_text/detector_mean.py
- Pinned Transformers generation and detection implementation:
  https://github.com/huggingface/transformers/tree/v4.57.6/src/transformers/generation
- GPT-2 model card and license:
  https://huggingface.co/openai-community/gpt2
