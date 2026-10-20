"""Explicit exports: text-only attack inputs and separate evaluator provenance."""

from nullmark.attacks.base import AttackInput


def export_sample(sample: AttackInput) -> dict[str, str]:
    # An allowlist prevents future evaluator fields from leaking through generic serialization.
    return {"sample_id": sample.sample_id, "prompt": sample.prompt, "text": sample.text}


def attack_input(row: dict) -> AttackInput:
    return AttackInput(sample_id=row["sample_id"], prompt=row["prompt"], text=row["text"])
