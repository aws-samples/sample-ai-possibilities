"""Local test for command parsing — no AWS, no network, no model call.

Run:  python3 lib/test_parsing.py

Covers the case that is easy to miss: a model that writes Python's `True` instead of
JSON's `true`. Before this was handled, every command carrying a boolean was silently
discarded and the agent fell back to rule-based play for the whole match. The other half
matters just as much — a string that merely CONTAINS the word "True" must survive
untouched, because rewriting the model's prose would be worse than dropping a command.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import json_tolerant
from parsing import parse_commands

TEAM_ID = 0
MY_PLAYER_ID = 3


def test_python_boolean_is_recovered():
    print("=== PYTHON BOOLEAN ===")
    text = '[{"commandType":"MOVE_TO","parameters":{"target_x":2.0,"target_y":0.0,"sprint":True}}]'
    print(f"  model wrote: {text}")
    cmds = parse_commands(text, TEAM_ID, MY_PLAYER_ID)
    assert len(cmds) == 1, "FAIL: the command was dropped"
    assert cmds[0]["commandType"] == "MOVE_TO"
    assert cmds[0]["parameters"]["sprint"] is True
    assert cmds[0]["teamId"] == TEAM_ID and cmds[0]["playerId"] == MY_PLAYER_ID
    print(f"  recovered:   {cmds[0]}")
    print()


def test_recovery_is_reported():
    print("=== RECOVERY CALLBACK ===")
    seen = []
    text = '[{"commandType":"SHOOT","parameters":{"aim_location":"TR","power":0.8,"chip":False}}]'
    cmds = parse_commands(text, TEAM_ID, MY_PLAYER_ID, seen.append)
    assert len(cmds) == 1, "FAIL: the command was dropped"
    assert len(seen) == 1, "FAIL: recovery was not reported to the callback"
    print(f"  callback fired once, so you can log how often your model does this")
    print()


def test_valid_json_reports_nothing():
    print("=== VALID JSON IS UNTOUCHED ===")
    seen = []
    text = '[{"commandType":"PRESS_BALL","parameters":{"intensity":0.8}}]'
    cmds = parse_commands(text, TEAM_ID, MY_PLAYER_ID, seen.append)
    assert len(cmds) == 1
    assert seen == [], "FAIL: well-formed JSON must not be reported as recovered"
    print("  no callback — the strict parse succeeded, nothing was rewritten")
    print()


def test_none_and_trailing_comma():
    print("=== None + TRAILING COMMA ===")
    text = '[{"commandType":"MARK","parameters":{"target_player_id":None},},]'
    cmds = parse_commands(text, TEAM_ID, MY_PLAYER_ID)
    assert len(cmds) == 1, "FAIL: the command was dropped"
    # None became null, so parsing.py's own default for target_player_id applies.
    assert cmds[0]["parameters"]["target_player_id"] == 0
    print(f"  recovered:   {cmds[0]}")
    print()


def test_code_fence():
    print("=== MARKDOWN CODE FENCE ===")
    text = '```json\n{"commandType":"SET_STANCE","parameters":{"stance":1,"aggressive":True}}\n```'
    cmds = parse_commands(text, TEAM_ID, MY_PLAYER_ID)
    assert len(cmds) == 1 and cmds[0]["commandType"] == "SET_STANCE"
    print(f"  recovered:   {cmds[0]}")
    print()


def test_string_containing_true_is_left_alone():
    print("=== MUST NOT CORRUPT: 'True' INSIDE A STRING ===")
    text = '[{"commandType":"MOVE_TO","parameters":{"target_x":1,"target_y":1,"note":"True story"}}]'
    cmds = parse_commands(text, TEAM_ID, MY_PLAYER_ID)
    assert cmds[0]["parameters"]["note"] == "True story", "FAIL: rewrote text inside a string"
    print(f"  note preserved: {cmds[0]['parameters']['note']!r}")
    print()


def test_escaped_quotes_do_not_break_string_tracking():
    raw = '{"note":"he said \\"True\\" loudly","flag":True}'
    fixed = json_tolerant.normalise_json_text(raw)
    assert '\\"True\\"' in fixed, "FAIL: rewrote text inside a string"
    assert '"flag":true' in fixed, "FAIL: did not rewrite the real literal"


def test_identifier_is_not_split():
    assert json_tolerant.normalise_json_text('{"a":Truthy}') == '{"a":Truthy}'
    assert json_tolerant.normalise_json_text('{"a":NotTrue}') == '{"a":NotTrue}'


def test_valid_json_is_byte_identical():
    raw = '[{"commandType":"PASS","parameters":{"target_player_id":3}}]'
    assert json_tolerant.normalise_json_text(raw) == raw


def test_junk_still_yields_nothing():
    # Recovery must not invent commands out of prose — the fallback should still run.
    assert parse_commands("I think we should attack down the left", TEAM_ID, MY_PLAYER_ID) == []
    assert parse_commands("", TEAM_ID, MY_PLAYER_ID) == []


def test_unknown_command_still_dropped():
    assert parse_commands('[{"commandType":"FLY","parameters":{}}]', TEAM_ID, MY_PLAYER_ID) == []


def test_move_to_still_clamped():
    cmds = parse_commands(
        '[{"commandType":"MOVE_TO","parameters":{"target_x":900,"target_y":-900}}]',
        TEAM_ID, MY_PLAYER_ID)
    assert cmds[0]["parameters"]["target_x"] == 55
    assert cmds[0]["parameters"]["target_y"] == -35


def test_bracket_in_prose_does_not_eat_the_command():
    """A bracketed aside anywhere in the response must not swallow the array.

    The array used to be located with a greedy `\\[[\\s\\S]*\\]`, so the span ran
    from the first `[` in the whole response to the last `]`. Any bracket in
    the prose made the combined span unparseable and the agent silently fell
    back to rule-based play for that tick.
    """
    cases = [
        'Options [A] or [B]. I choose: [{"commandType":"SHOOT","parameters":{"aim_location":"TR","power":0.9}}]',
        'I will move. [{"commandType":"MOVE_TO","parameters":{"target_x":3,"target_y":1}}] Done [end]',
        '[1, 2] then [{"commandType":"PRESS_BALL","parameters":{}}]',
        'See step [2]: [{"commandType":"INTERCEPT","parameters":{}}] // ref [4]',
    ]
    for text in cases:
        cmds = parse_commands(text, TEAM_ID, MY_PLAYER_ID)
        assert len(cmds) == 1, f"expected 1 command, got {len(cmds)} for: {text}"
        assert cmds[0]["playerId"] == MY_PLAYER_ID
        assert cmds[0]["teamId"] == TEAM_ID
    print("=== BRACKET IN PROSE: command array still found ===")


def test_bracket_inside_a_json_string_is_not_a_delimiter():
    cmds = parse_commands(
        '[{"commandType":"PASS","parameters":{"target_player_id":2,"type":"GROUND","note":"go [left]"}}]',
        TEAM_ID, MY_PLAYER_ID)
    assert len(cmds) == 1
    assert cmds[0]["parameters"]["note"] == "go [left]"
    print("=== STRING BRACKETS: not treated as delimiters ===")


def test_nested_array_inside_a_command_survives():
    cmds = parse_commands(
        '[{"commandType":"MOVE_TO","parameters":{"path":[1,2],"target_x":2,"target_y":0}}]',
        TEAM_ID, MY_PLAYER_ID)
    assert len(cmds) == 1
    assert cmds[0]["parameters"]["path"] == [1, 2]
    print("=== NESTED ARRAY: preserved ===")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"{len(fns)} tests passed")
