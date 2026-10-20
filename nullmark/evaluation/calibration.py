"""Frozen, condition-bound empirical operating points for trusted evaluation.

Strict score > threshold; ties are negative. The ceil((n+1)*(1-alpha))
order statistic uses no interpolation. Under exchangeable clean samples its
marginal false-positive probability is at most alpha. This is not a confidence
guarantee for a particular population, model, key, or conditional length bucket.
"""

import hashlib
import json
import math
import warnings
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from nullmark import __version__
from nullmark.watermark.base import DetectionResult, WatermarkScheme


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def conditions(model, scheme: WatermarkScheme, key_ref: str) -> dict:
    """Public identity only; never serialize keys or local model paths."""
    public = scheme.metadata()
    return {
        "model": model.metadata(),
        "generation": model.settings.model_dump(),
        "watermark": {k: v for k, v in public.items() if k != "threshold"},
        "key_ref": key_ref,
        "score_input": "retokenized visible continuation; prompt excluded",
        "nullmark": __version__,
    }


@dataclass(frozen=True)
class OperatingPoint:
    target_fpr: float
    number_of_clean_samples: int
    empirical_threshold: float
    observed_calibration_fpr: float
    supported: bool
    warnings: tuple[str, ...]
    order_index: int


def empirical_threshold(scores: list[float], target_fpr: float) -> OperatingPoint:
    if not 0 < target_fpr < 1:
        raise ValueError("target FPR must be between zero and one")
    if not scores or any(not math.isfinite(s) for s in scores):
        raise ValueError("clean calibration scores must be nonempty and finite")
    ordered = sorted(scores)
    n = len(ordered)
    # Decimal input avoids binary rounding moving an integer order index up one.
    from decimal import ROUND_CEILING, Decimal

    k = int(((n + 1) * (1 - Decimal(str(target_fpr)))).to_integral_value(ROUND_CEILING))
    supported = k <= n and n >= math.ceil(1 / target_fpr)
    notes = []
    if not supported:
        notes.append("Too few clean samples to resolve the requested FPR; exploratory only.")
    if n * target_fpr < 5:
        notes.append("Fewer than five expected tail samples; operating point has high uncertainty.")
    for note in notes:
        warnings.warn(note, UserWarning, stacklevel=2)
    threshold = ordered[min(k, n) - 1]
    return OperatingPoint(
        target_fpr,
        n,
        threshold,
        sum(s > threshold for s in scores) / n,
        supported,
        tuple(notes),
        k,
    )


@dataclass(frozen=True)
class CalibratedDetector:
    scheme: str
    statistic: str
    operating_point: OperatingPoint
    conditions_json: str
    calibration_dataset_hash: str
    minimum_usable_tokens: int
    maximum_usable_tokens: int
    created_at: str
    calibration_id: str

    @classmethod
    def fit(
        cls,
        *,
        scheme: str,
        statistic: str,
        clean: list[DetectionResult],
        target_fpr: float,
        context: dict,
        dataset_hash: str,
        minimum_usable_tokens: int = 64,
        maximum_usable_tokens: int = 4096,
    ):
        if minimum_usable_tokens < 1 or maximum_usable_tokens < minimum_usable_tokens:
            raise ValueError("invalid usable length regime")
        if any(r.statistic != statistic for r in clean):
            raise ValueError("calibration statistic mismatch")
        usable = [
            r
            for r in clean
            if r.score is not None
            and minimum_usable_tokens <= r.tokens_scored <= maximum_usable_tokens
        ]
        point = empirical_threshold([r.score for r in usable], target_fpr)
        # Refuse extrapolation beyond observed clean length support. A pooled
        # threshold still does not promise conditional FPR in each length bucket.
        low = min(r.tokens_scored for r in usable)
        high = max(r.tokens_scored for r in usable)
        created = datetime.now(UTC).isoformat()
        payload = dict(
            scheme=scheme,
            statistic=statistic,
            operating_point=asdict(point),
            conditions=context,
            calibration_dataset_hash=dataset_hash,
            minimum_usable_tokens=low,
            maximum_usable_tokens=high,
            created_at=created,
            version=1,
        )
        identity = hashlib.sha256(canonical(payload).encode()).hexdigest()
        return cls(
            scheme, statistic, point, canonical(context), dataset_hash, low, high, created, identity
        )

    def to_dict(self) -> dict:
        result = asdict(self)
        result["conditions"] = json.loads(result.pop("conditions_json"))
        result["version"] = 1
        return result

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, allow_nan=False) + "\n", "utf-8")

    @classmethod
    def from_dict(cls, value: dict):
        data = dict(value)
        if data.pop("version") != 1:
            raise ValueError("unsupported calibration artifact version")
        identity = data.pop("calibration_id")
        if hashlib.sha256(canonical({**data, "version": 1}).encode()).hexdigest() != identity:
            raise ValueError("calibration artifact integrity mismatch")
        point = data.pop("operating_point")
        if (
            not 0 < point["target_fpr"] < 1
            or not math.isfinite(point["empirical_threshold"])
            or data["minimum_usable_tokens"] < 1
            or data["maximum_usable_tokens"] < data["minimum_usable_tokens"]
        ):
            raise ValueError("invalid calibration artifact")
        point["warnings"] = tuple(point["warnings"])
        data["conditions_json"] = canonical(data.pop("conditions"))
        return cls(**data, operating_point=OperatingPoint(**point), calibration_id=identity)

    @classmethod
    def load(cls, path: Path):
        return cls.from_dict(json.loads(path.read_text("utf-8")))

    def require_compatible(self, context: dict) -> None:
        if canonical(context) != self.conditions_json:
            raise ValueError(
                "calibration does not match model, watermark, sampling or key reference"
            )

    def evaluate(self, result: DetectionResult, *, context: dict) -> dict:
        self.require_compatible(context)
        if result.statistic != self.statistic:
            raise ValueError("detector statistic does not match calibration")
        reason = None
        if result.score is None or not math.isfinite(result.score):
            reason = "scoring_impossible"
        elif not self.operating_point.supported:
            reason = "calibration_sample_count"
        elif not self.minimum_usable_tokens <= result.tokens_scored <= self.maximum_usable_tokens:
            reason = "unsupported_length"
        prediction = None if reason else result.score > self.operating_point.empirical_threshold
        return {
            **result.to_dict(),
            "prediction": prediction,
            "threshold": self.operating_point.empirical_threshold,
            "state": "INSUFFICIENT EVIDENCE"
            if reason
            else "DETECTED"
            if prediction
            else "NOT DETECTED",
            "status": reason or "ok",
            "calibration_id": self.calibration_id,
            "target_fpr": self.operating_point.target_fpr,
            "decision_scope": "calibrated",
        }


def uncalibrated(result: DetectionResult) -> dict:
    return {
        **result.to_dict(),
        "prediction": None,
        "threshold": None,
        "legacy_threshold": result.threshold,
        "calibration_id": None,
        "target_fpr": None,
        "state": "INSUFFICIENT EVIDENCE",
        "decision_scope": "score_only",
        "status": "uncalibrated" if result.score is not None else "scoring_impossible",
    }


def require_frozen_evaluator(detector: CalibratedDetector | None, *, context: dict):
    """Guard for future attack-success metrics; implements no attack behavior."""
    if detector is None or not detector.operating_point.supported:
        raise ValueError("attack-success claims require a supported calibration artifact")
    detector.require_compatible(context)
    return detector


def token_diagnostic(scheme: WatermarkScheme, generated, model) -> dict:
    visible_ids = model.encode(generated.text)
    native = scheme.score_ids(generated.token_ids)
    visible = scheme.score_ids(visible_ids)
    return {
        "native_score": native.score,
        "visible_score": visible.score,
        "score_delta": None
        if native.score is None or visible.score is None
        else native.score - visible.score,
        "token_roundtrip_exact": generated.token_ids == visible_ids,
        "native_token_count": len(generated.token_ids),
        "retokenized_token_count": len(visible_ids),
        "usable_detector_token_count": visible.tokens_scored,
        "detection": visible.to_dict(),
    }
