"""Four single-pass baselines. No evaluator imports, interfaces or feedback."""

import hashlib
import random
import re
from time import perf_counter

from nullmark.attacks.base import AttackOutput
from nullmark.attacks.text import anchors, candidates, distance, words

VERSION = "1"
TEMPLATE = "baseline-prose-v1"
NAMES = ("random_edit", "synonym_replace", "paraphrase", "entropy_rewrite")
# Conservative alternatives; selection is uniformly shuffled, never scored.
ALTERNATIVES = {
    "important": "significant",
    "useful": "helpful",
    "large": "big",
    "small": "little",
    "often": "frequently",
    "also": "additionally",
    "simple": "straightforward",
    "quickly": "rapidly",
    "usually": "generally",
    "different": "distinct",
    "allows": "permits",
    "helps": "assists",
    "begin": "start",
    "finish": "complete",
    "however": "nevertheless",
    "therefore": "thus",
    "because": "since",
    "method": "approach",
    "methods": "approaches",
    "shows": "demonstrates",
    "provide": "supply",
    "reduce": "decrease",
    "increase": "raise",
    "carefully": "cautiously",
}


def validate_output(original, output, prompt=""):
    if not isinstance(output, str) or not output.strip():
        raise ValueError("empty attack output")
    if output == prompt or len(output) > max(300, len(original) * 2):
        raise ValueError("prompt echo or excessive expansion")
    if re.match(r"\s*(?:here (?:is|are)|rewritten text\s*:|sure[,!]|```|<think>)", output, re.I):
        raise ValueError("model commentary or preamble")
    if "</think>" in output or "[im_end]" in output:
        raise ValueError("model control text")
    return output  # No silent content sanitation.


class BaselineAttack:
    def __init__(self, name, budget=None, model=None):
        if name not in NAMES:
            raise ValueError("unknown attack")
        if name != "paraphrase" and (budget is None or not 0 < budget <= 0.2):
            raise ValueError("sparse budget must be in (0, .2]")
        if name == "paraphrase" and budget is not None:
            raise ValueError("paraphrase has no fixed budget")
        self.name, self.budget, self.model = name, budget, model

    def transform(self, sample, *, seed):
        start = perf_counter()
        if self.name != "random_edit" and self.model is None:
            raise ValueError("this attack requires a transformation model")
        notes = []
        if self.name == "paraphrase":
            text = self.model.paraphrase(sample.text, seed)
        else:
            pool = candidates(sample.text)
            if self.name == "random_edit":
                replacements = {
                    m.start(): ALTERNATIVES[m.group()] for m in pool if m.group() in ALTERNATIVES
                }
            else:
                replacements = self.model.replacements(sample.text, pool, seed)
            pool = [m for m in pool if m.start() in replacements]
            random.Random(seed).shuffle(pool)
            if self.name == "entropy_rewrite":
                entropy = self.model.entropies(sample.text, pool)
                pool.sort(key=lambda m: entropy[m.start()], reverse=True)
            count = int(len(words(sample.text)) * self.budget)
            chosen = pool[:count]
            text = sample.text
            for m in sorted(chosen, key=lambda m: m.start(), reverse=True):
                replacement = replacements[m.start()]
                if not re.fullmatch(r"[a-z]+", replacement) or replacement == m.group():
                    raise ValueError("replacement must be one lowercase word")
                text = text[: m.start()] + replacement + text[m.end() :]
            if len(chosen) < count:
                notes.append("safe candidates exhausted; requested budget is an upper bound")
        validate_output(sample.text, text, sample.prompt)
        word_edits = distance(words(sample.text), words(text))
        if self.budget is not None and word_edits > int(len(words(sample.text)) * self.budget):
            raise ValueError("word budget exceeded")
        if anchors(sample.text) != anchors(text):
            notes.append("factual anchors changed; inspect quality metrics")
        tokenize = self.model.tokenize if self.model else lambda t: re.findall(r"\w+|[^\w\s]", t)
        return AttackOutput(
            text,
            self.name,
            VERSION,
            seed,
            self.budget,
            hashlib.sha256(sample.text.encode()).hexdigest(),
            self.model.digest if self.model else "none",
            self.model.sampling if self.model else {},
            TEMPLATE,
            word_edits,
            distance(tokenize(sample.text), tokenize(text)),
            perf_counter() - start,
            notes,
        )
