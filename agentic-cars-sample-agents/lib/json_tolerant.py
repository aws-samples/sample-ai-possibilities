"""Recover JSON from model output that used Python literals, trailing commas or code fences.

Only ever consulted AFTER a strict ``json.loads`` has already failed, so valid JSON keeps its
existing behaviour bit for bit.

Motivating failure: a midfielder on Nova Pro emitted
``[{"commandType":"MOVE_TO","parameters":{"target_x":2.0,"sprint":True}}]`` — valid Python, invalid
JSON — so every command carrying a boolean parameter was discarded and the agent silently played
rule-based football for a whole match (~1020 fallback events) with no visible signal.

What is recovered, and nothing else:
  * bare ``True`` / ``False`` / ``None`` tokens outside strings -> ``true`` / ``false`` / ``null``
  * a trailing comma before ``}`` or ``]``
  * a markdown code fence wrapping the payload

Single-quoted strings are deliberately NOT rewritten: apostrophes inside prose make that guess
unsafe, and a single-quoted payload never parsed before either.

DUPLICATED, DELIBERATELY — the same file exists at all of:
  agents/ai-teams/lib/json_tolerant.py
  agents/ai-teams-rallyball/lib/json_tolerant.py
  agents/ci/strands/lib/json_tolerant.py
  agents/ai-teams-cars/lib/json_tolerant.py
  apps/infra/lambdas/player-agent-provisioner/agent_code_rallyball/lib/json_tolerant.py
  apps/infra/lambdas/player-agent-provisioner/agent_code_cars/lib/json_tolerant.py
Each directory is packaged into its own agent zip and cannot import from the others.
apps/infra/tests/agent-parser-parity.test.ts fails if the copies drift.
"""

import json
import re

_PY_LITERALS = (("True", "true"), ("False", "false"), ("None", "null"))

_WORD_CHAR = re.compile(r"[A-Za-z0-9_]")

_FENCED_BLOCK = re.compile(r"```[A-Za-z0-9_+-]*[ \t]*\r?\n?([\s\S]*?)```")


def _is_word_char(ch: str) -> bool:
    return bool(ch) and bool(_WORD_CHAR.match(ch))


def _strip_fences(text: str) -> str:
    """Return the contents of the first markdown code fence, or the text unchanged."""
    if "```" not in text:
        return text
    match = _FENCED_BLOCK.search(text)
    if match and match.group(1).strip():
        return match.group(1)
    return text.replace("```", " ")


def normalise_json_text(text: str) -> str:
    """Rewrite Python-flavoured JSON into JSON, leaving string contents untouched."""
    src = _strip_fences(text)
    out = []
    i = 0
    n = len(src)
    in_string = False
    while i < n:
        ch = src[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        replaced = False
        for py, js in _PY_LITERALS:
            if not src.startswith(py, i):
                continue
            before = src[i - 1] if i > 0 else ""
            after = src[i + len(py)] if i + len(py) < n else ""
            if _is_word_char(before) or _is_word_char(after):
                continue
            out.append(js)
            i += len(py)
            replaced = True
            break
        if replaced:
            continue

        if ch == ",":
            j = i + 1
            while j < n and src[j].isspace():
                j += 1
            if j < n and src[j] in "}]":
                i += 1  # drop the trailing comma
                continue

        out.append(ch)
        i += 1
    return "".join(out)


def parse_json_tolerant(text: str):
    """Parse ``text`` as JSON, retrying once on a normalised copy.

    Returns ``(value, recovered)`` where ``recovered`` is True only when the strict parse failed
    and the normalised retry succeeded, or ``None`` when nothing parses.
    """
    try:
        return json.loads(text), False
    except json.JSONDecodeError:
        pass

    normalised = normalise_json_text(text)
    if normalised == text:
        return None
    try:
        return json.loads(normalised), True
    except json.JSONDecodeError:
        return None
