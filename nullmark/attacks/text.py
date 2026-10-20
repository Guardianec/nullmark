"""Neutral text accounting and conservative candidate protection."""

import re
from collections import Counter

WORD = re.compile(r"\b\w+(?:['’]\w+)?\b")
ANCHOR = re.compile(
    r"https?://[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]+|"
    r"\b\d+(?:[.,:/-]\d+)*(?:\s?%)?\b"
)
PROTECTED = re.compile(
    r'```[\s\S]*?```|`[^`]*`|"[^"\n]*"|“[^”]*”|'
    r"https?://\S+|[\w.+-]+@[\w.-]+|\$[^$]+\$|\b[A-Z][\w-]*\b|"
    r"\b(?:not|no|never|neither|nor|without|cannot|\w+n't)\b",
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
        and not any(m.start() < end and m.end() > start for start, end in protected)
    ]


def anchors(text):
    return Counter(m.group().rstrip(".,;!?)") for m in ANCHOR.finditer(text))
