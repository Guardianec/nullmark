"""Trusted token inspection using the same pinned HF primitives as the detectors.

Generation tokens include their actual prompt context. Detector tokens instead use
retokenized continuation text, matching the experiment harness exactly.
"""

from dataclasses import dataclass

import torch

from nullmark.models import Generation, TextGenerationBackend
from nullmark.watermark.base import DetectionResult, WatermarkScheme
from nullmark.watermark.kgw import KGWScheme
from nullmark.watermark.synthid import SynthIDScheme


@dataclass(frozen=True)
class KGWState:
    green: bool
    cumulative_z: float | None


@dataclass(frozen=True)
class SynthIDState:
    g_values: list[int]
    mean_g: float
    cumulative_mean_g: float | None
    cumulative_score: float | None = None


@dataclass(frozen=True)
class TokenInspection:
    index: int
    token_id: int
    token_text: str
    context: list[int]
    context_text: str
    scored: bool
    reason: str
    special: bool = False
    kgw: KGWState | None = None
    synthid: SynthIDState | None = None


@dataclass(frozen=True)
class InspectedSample:
    text: str
    token_count: int
    seconds: float
    tokens: list[TokenInspection]
    detector_tokens: list[TokenInspection]
    detection: DetectionResult | None
    roundtrip_exact: bool


@dataclass(frozen=True)
class PairedGeneration:
    seed: int
    scheme: str
    public_parameters: dict
    plain: InspectedSample | None
    marked: InspectedSample
    first_divergence: int | None


def _decode(model: TextGenerationBackend, ids: list[int]) -> str:
    return model.decode(ids)


@torch.inference_mode()
def inspect_tokens(
    model: TextGenerationBackend,
    scheme: WatermarkScheme | None,
    ids: list[int],
    *,
    prompt_ids: list[int] | None = None,
) -> list[TokenInspection]:
    """Inspect original generation or detector input; never return private parameters."""
    generation = prompt_ids is not None
    prefix = prompt_ids or []
    full = prefix + ids
    offset = len(prefix)
    device = model.watermark_device
    special = model.special_token_ids
    processor = None
    detector = None
    values, mask = None, None
    width = 0
    if scheme is not None:
        processor = scheme.generation_config().construct_processor(model.vocab_size, device)
        width = (
            scheme.config.context_width
            if isinstance(scheme, KGWScheme)
            else scheme.config.ngram_len - 1
        )
        # SynthID skips its first n-1 generation calls and does not use the prompt.
        if isinstance(scheme, SynthIDScheme):
            full, offset = ids, 0
            if len(ids) > width:
                vs, ms = scheme.scoring_data(ids)
                values, mask = vs[0], ms[0]
        else:
            detector = scheme.detector()
    count, total = 0, 0
    weighted_total = 0.0
    weights = (
        torch.linspace(10, 1, scheme.config.depth, dtype=torch.float64).tolist()
        if isinstance(scheme, SynthIDScheme)
        else []
    )
    rows = []
    ended = False
    start = int(not generation and bool(ids) and ids[0] == model.detector_config.bos_token_id)
    for i, token in enumerate(ids):
        pos = offset + i
        context = full[max(start if not generation else 0, pos - width) : pos]
        scored = scheme is not None and len(context) == width and i >= start
        reason = "scored" if scored else "initial context" if scheme else "no detector selected"
        kgw, synthid = None, None
        if token in model.eos_token_ids:
            ended = True
        if ended:
            scored, reason = False, "special token / EOS suffix"
        if isinstance(scheme, KGWScheme) and len(context) == width and not ended:
            tensor = torch.tensor(context, dtype=torch.long, device=device)
            green = bool((processor._get_greenlist_ids(tensor) == token).any().item())
            # HF 4.57.6 Counter uses tensor identity: repeated n-grams count separately.
            # Preserve v0.1 detector behavior; regression tests compare repeated-text traces.
            if scored:
                count += 1
                total += int(green)
            z = float(detector._compute_z_score(total, count)) if count else None
            kgw = KGWState(green, z)
        elif isinstance(scheme, SynthIDScheme) and values is not None and i >= width:
            gs = [int(v) for v in values[i - width].tolist()]
            if not bool(mask[i - width]):
                scored, reason = False, "repeated context / EOS suffix"
            if scored:
                count += 1
                total += sum(gs)
                weighted_total += sum(g * w for g, w in zip(gs, weights, strict=True))
            cumulative = total / (count * scheme.config.depth) if count else None
            score = (
                (weighted_total / (count * sum(weights)) if count else None)
                if scheme.config.statistic == "weighted_mean"
                else cumulative
            )
            synthid = SynthIDState(gs, sum(gs) / len(gs), cumulative, score)
        rows.append(
            TokenInspection(
                i,
                token,
                _decode(model, [token]),
                context,
                _decode(model, context),
                scored,
                reason,
                token in special,
                kgw,
                synthid,
            )
        )
    return rows


def inspect_sample(
    model: TextGenerationBackend, scheme: WatermarkScheme | None, prompt: str, sample: Generation
) -> InspectedSample:
    retokenized = model.encode(sample.text)
    return InspectedSample(
        sample.text,
        len(sample.token_ids),
        sample.seconds,
        inspect_tokens(
            model,
            scheme,
            sample.token_ids,
            prompt_ids=sample.prompt_token_ids
            if sample.prompt_token_ids is not None
            else model.encode_prompt(prompt),
        ),
        inspect_tokens(model, scheme, retokenized),
        scheme.detect(sample.text) if scheme else None,
        retokenized == sample.token_ids,
    )


def paired_generation(
    model: TextGenerationBackend,
    scheme: WatermarkScheme | None,
    prompt: str,
    *,
    seed: int,
    paired: bool = True,
) -> PairedGeneration:
    plain = model.generate(prompt, seed=seed) if paired and scheme else None
    marked = (
        scheme.generate(model, prompt, seed=seed) if scheme else model.generate(prompt, seed=seed)
    )
    divergence = None
    if plain:
        divergence = next(
            (
                i
                for i, (a, b) in enumerate(zip(plain.token_ids, marked.token_ids, strict=False))
                if a != b
            ),
            min(len(plain.token_ids), len(marked.token_ids))
            if len(plain.token_ids) != len(marked.token_ids)
            else None,
        )
    return PairedGeneration(
        seed,
        scheme.metadata()["scheme"] if scheme else "none",
        scheme.metadata() if scheme else {},
        inspect_sample(model, scheme, prompt, plain) if plain else None,
        inspect_sample(model, scheme, prompt, marked),
        divergence,
    )
