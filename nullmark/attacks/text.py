"""Neutral text accounting and conservative candidate protection."""

import re
from collections import Counter

WORD = re.compile(r"\b\w+(?:['’]\w+)?\b")
ANCHOR = re.compile(
    r"https?://[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]+|"
    r"(?<!\w)[+-]?\d+(?:[.,:/-]\d+)*(?:\s?%)?(?!\w)"
)
PROTECTED = re.compile(
    r'```[\s\S]*?```|`[^`]*`|"[^"\n]*"|“[^”]*”|'
    r"(?<!\w)'[^'\n]+'(?!\w)|‘[^’]*’|"
    r"https?://\S+|[\w.+-]+@[\w.-]+|\$[^$]+\$|\b[A-Z][\w-]*\b|"
    r"\b(?:not|no|never|neither|nor|without|cannot|\w+n't)\b",
)
GRAMMAR_WORDS = frozenset(
    (
        "that this these those which what where when while with without within from into onto "
        "about after before because since until unless than then there their they them whose "
        "whom whether either neither both each every some such very also only just even still "
        "have has had does doing been being would could should must might shall will"
    ).split()
)


def words(text):
    return WORD.findall(text)


def distance(a, b):
    """Exact Levenshtein distance, linear working memory."""
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        following = [i]
        for j, y in enumerate(b, 1):
            following.append(min(following[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = following
    return row[-1]


def candidates(text):
    protected = [(m.start(), m.end()) for m in PROTECTED.finditer(text)]
    # Formula/code lines are conservatively excluded; a number never excludes a paragraph.
    for m in re.finditer(r"(?m)^.*[={}<>].*$", text):
        protected.append((m.start(), m.end()))
    return [
        m
        for m in WORD.finditer(text)
        if len(m.group()) > 3
        and m.group().isalpha()
        and m.group().islower()
        and m.group() not in GRAMMAR_WORDS
        and not any(m.start() < end and m.end() > start for start, end in protected)
    ]


def anchors(text):
    return Counter(m.group().rstrip(".,;!?)") for m in ANCHOR.finditer(text))
