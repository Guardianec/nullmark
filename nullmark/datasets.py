"""Original prompts; custom JSONL is resolved relative to the config file."""

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from nullmark.config import DatasetConfig


@dataclass(frozen=True)
class Prompt:
    id: str
    style: str
    text: str


BUILTIN = (
    Prompt("factual", "factual", "Explain how a public library serves a small town."),
    Prompt("essay", "essay", "Write a short essay about learning a difficult skill."),
    Prompt("technical", "technical", "Explain how a computer stores and retrieves a file."),
    Prompt("narrative", "narrative", "Tell a story about a traveler who misses the last train."),
    Prompt(
        "instructions", "instructions", "Describe the steps for planting herbs in a window box."
    ),
    Prompt("argument", "argument", "Argue for preserving quiet public spaces in growing cities."),
    Prompt("science", "science", "Explain why the Moon appears to change shape over a month."),
    Prompt("knowledge", "knowledge", "Describe how maps help people understand unfamiliar places."),
)


def load_prompts(config: DatasetConfig, base: Path) -> tuple[list[Prompt], str]:
    if config.source == "builtin-v1":
        prompts = list(BUILTIN)
    else:
        rows = [json.loads(line) for line in (base / config.path).read_text("utf-8").splitlines()]
        if any(
            not isinstance(row, dict)
            or set(row) != {"id", "style", "text"}
            or any(not isinstance(value, str) for value in row.values())
            for row in rows
        ):
            raise ValueError("each prompt row must contain only string id, style and text fields")
        prompts = [Prompt(**row) for row in rows]
    if not prompts or len({p.id for p in prompts}) != len(prompts):
        raise ValueError("prompt IDs must be unique and the dataset nonempty")
    if any(not p.id or not p.text.strip() for p in prompts):
        raise ValueError("prompt IDs and text must be nonempty")
    if config.sample_count > len(prompts):
        raise ValueError(f"sample_count exceeds dataset size ({len(prompts)})")
    selected = prompts[: config.sample_count]
    digest = sha256(json.dumps([asdict(p) for p in selected], sort_keys=True).encode()).hexdigest()
    return selected, digest
