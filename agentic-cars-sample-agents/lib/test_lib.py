"""Offline unit tests for the Cars Edition agent lib (no relay / AgentCore / network).

Run: python3 -m pytest lib/test_lib.py   (or: python3 lib/test_lib.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import arena
import fallback
import json_tolerant
import parsing
from prompt import system_prompt_for
from state import summarize_state


def _status(ball_z=0.0, phase="PLAYING"):
    return {
        "currentPhase": phase, "gameTime": 30.0, "score": {"home": 1, "away": 0},
        "homeTeamCode": "HOME1",
        "ball": {"position": {"x": 2.0, "y": 1.0, "z": ball_z}, "controllerCarId": None},
        "cars": [
            {"teamCode": "HOME1", "agentId": "HOME1-1", "role": "GOALKEEPER", "position": {"x": 0, "y": 0.4, "z": -38}, "speed": 0},
            {"teamCode": "HOME1", "agentId": "HOME1-2", "role": "DEFENDER", "position": {"x": 5, "y": 0.4, "z": -20}, "speed": 3},
            {"teamCode": "AWAY1", "agentId": "AWAY1-1", "role": "GOALKEEPER", "position": {"x": 0, "y": 0.4, "z": 38}, "speed": 0},
            {"teamCode": "AWAY1", "agentId": "AWAY1-4", "role": "STRIKER", "position": {"x": 1, "y": 0.4, "z": 5}, "speed": 9},
        ],
    }


def test_parse_posture_levers_normalise_enums_and_stamp_identity():
    cmds = parsing.parse_commands(
        '[{"commandType":"set_pressing","parameters":{"level":"high"}},'
        ' {"commandType":"SET_TEAM_STANCE","parameters":{"stance":"attack"}}]', "HOME1-3", "HOME1")
    assert [c["commandType"] for c in cmds] == ["SET_PRESSING", "SET_TEAM_STANCE"]
    assert cmds[0]["parameters"] == {"level": "HIGH"} and cmds[1]["parameters"] == {"stance": "ATTACK"}
    assert all(c["agentId"] == "HOME1-3" and c["teamCode"] == "HOME1" for c in cmds)


def test_parse_clamps_move_to_inside_the_arena():
    cmds = parsing.parse_commands('[{"commandType":"MOVE_TO","parameters":{"target_x":500,"target_y":-900,"sprint":true}}]', "a", "T")
    p = cmds[0]["parameters"]
    assert p["target_x"] == arena.HALF_X - arena.MARGIN and p["target_y"] == -(arena.HALF_Z - arena.MARGIN) and p["sprint"] is True


def test_parse_rejects_bad_shape_and_unknown_commands_but_keeps_the_rest():
    cmds = parsing.parse_commands(
        '[{"commandType":"SET_SHAPE","parameters":{"shape":"2-2-2"}},{"commandType":"FLY","parameters":{}},'
        '{"commandType":"SET_SHAPE","parameters":{"shape":"1-0-3"}}]', "a", "T")
    assert [c["commandType"] for c in cmds] == ["SET_SHAPE"] and cmds[0]["parameters"]["shape"] == "1-0-3"


def test_parse_caps_at_three_and_dedupes_command_types():
    text = '[' + ','.join('{"commandType":"SET_TEMPO","parameters":{"level":"FULL"}}' for _ in range(3)) + \
           ',{"commandType":"SET_WIDTH","parameters":{"level":"WIDE"}},{"commandType":"SHOOT","parameters":{}},' \
           '{"commandType":"PASS","parameters":{"target_player_id":2}}]'
    cmds = parsing.parse_commands(text, "a", "T")
    assert [c["commandType"] for c in cmds] == ["SET_TEMPO", "SET_WIDTH", "SHOOT"]
    assert cmds[2]["parameters"] == {"aim_location": "CENTER", "power": 0.8}


def test_parse_requires_targets_and_defaults_bump_to_carrier():
    assert parsing.parse_commands('[{"commandType":"PASS","parameters":{}}]', "a", "T") == []
    cmds = parsing.parse_commands('[{"commandType":"BUMP","parameters":{}},{"commandType":"MARK","parameters":{"target_player_id":"2","tightness":"loose"}}]', "a", "T")
    assert [c["commandType"] for c in cmds] == ["BUMP"] and cmds[0]["parameters"] == {"target_player_id": -1}
    mark = parsing.parse_commands('[{"commandType":"MARK","parameters":{"target_player_id":"2","tightness":"loose"}}]', "a", "T")
    assert mark[0]["parameters"] == {"target_player_id": 2, "tightness": "LOOSE"}


def test_parse_drops_housekeeping_that_would_cancel_a_moment_command():
    cmds = parsing.parse_commands('[{"commandType":"INTERCEPT","parameters":{}},{"commandType":"CLEAR_OVERRIDE","parameters":{}}]', "a", "T")
    assert [c["commandType"] for c in cmds] == ["INTERCEPT"]
    alone = parsing.parse_commands('[{"commandType":"CLEAR_OVERRIDE","parameters":{}}]', "a", "T")
    assert [c["commandType"] for c in alone] == ["CLEAR_OVERRIDE"]


def test_parse_salvages_commands_from_a_broken_array_and_keeps_one_moment_command():
    broken = ('[{"commandType": "SET_TEAM_STANCE", "parameters": {"stance": "ATTACK"}}, '
              '{"commandType": "PRESS_BALL", "parameters": {"intensity": 0.5}}, '
              '{"commandType": "MOVE_TO", "parameters": {"target_x": -18.2, "target_y": -18.8}}}]')
    seen = []
    cmds = parsing.parse_commands(broken, "a", "T", seen.append)
    assert [c["commandType"] for c in cmds] == ["SET_TEAM_STANCE", "PRESS_BALL"] and seen
    fenced = '```json\n[{"commandType": "MOVE_TO", "parameters": {"target_x": 1, "target_y": 2, "sprint": true}}}\n```'
    assert [c["commandType"] for c in parsing.parse_commands(fenced, "a", "T")] == ["MOVE_TO"]


def test_parse_keeps_a_positive_duration_and_drops_junk():
    cmds = parsing.parse_commands('Sure: [{"commandType":"PRESS_BALL","parameters":{"intensity":3},"duration":"4"}]', "a", "T")
    assert cmds[0]["parameters"] == {"intensity": 1.0} and cmds[0]["duration"] == 4.0
    assert parsing.parse_commands("no json here", "a", "T") == []


def test_parse_recovers_python_booleans_and_reports_it():
    seen = []
    cmds = parsing.parse_commands('[{"commandType":"INTERCEPT","parameters":{"aggressive":True}}]', "a", "T", seen.append)
    assert cmds[0]["parameters"] == {"aggressive": True} and len(seen) == 1
    seen.clear()
    parsing.parse_commands('[{"commandType":"INTERCEPT","parameters":{"aggressive":true}}]', "a", "T", seen.append)
    assert seen == []


def test_normalise_is_a_no_op_for_valid_json():
    raw = '[{"commandType":"RESET","parameters":{}}]'
    assert json_tolerant.normalise_json_text(raw) == raw


def test_fallback_opening_follows_the_variant_posture_then_stops():
    seq = [fallback.opening_command("a", "T", "aggressive", n) for n in range(7)]
    assert [c["commandType"] for c in seq[:6]] == list(fallback.OPENING) and seq[6] is None
    assert seq[0]["parameters"] == {"stance": "ATTACK"} and seq[1]["parameters"] == {"shape": "1-0-3"}
    assert fallback.opening_command("a", "T", "defensive", 1)["parameters"] == {"shape": "2-1-1"}


def test_fallback_moment_commands_follow_role_and_ball_third():
    gk = fallback.moment_command(_status(), "HOME1-1", "HOME1", "GOALKEEPER", 1)
    assert gk["commandType"] == "DEFENSIVE_CLEAR"
    assert fallback.moment_command(_status(ball_z=-30), "HOME1-2", "HOME1", "DEFENDER", 1)["commandType"] == "INTERCEPT"
    assert fallback.moment_command(_status(ball_z=30), "HOME1-2", "HOME1", "DEFENDER", 1) is None
    assert fallback.moment_command(_status(ball_z=35), "HOME1-5", "HOME1", "STRIKER", 1)["commandType"] == "SHOOT"
    assert fallback.moment_command(_status(ball_z=-5), "HOME1-5", "HOME1", "STRIKER", 1)["commandType"] == "PRESS_BALL"
    assert fallback.last_resort("a", "T")["commandType"] == "CLEAR_OVERRIDE"


def test_state_briefing_reads_the_pitch_from_the_agents_side():
    s = summarize_state(_status(ball_z=-30), "HOME1", "HOME1-2", "DEFENDER", 1, ["press high"], 120)
    assert "LEADING" in s and "defensive third" in s and "90s left" in s
    assert "Opponents (index: role" in s and "Coach instructions: press high" in s
    away = summarize_state(_status(ball_z=-30), "AWAY1", "AWAY1-4", "STRIKER", -1)
    assert "AWAY team" in s or "AWAY team" in away
    assert "attacking third" in away and "TRAILING" in away


def test_system_prompt_carries_arena_role_and_variant():
    p = system_prompt_for("STRIKER", "defensive")
    assert f"z = -{int(arena.HALF_Z)}" in p and "STRIKER" in p and "Squad style: defensive" in p
    assert "target_y for z" in p


def test_arena_thirds_flip_with_the_attacking_end():
    assert arena.third(30, 1) == "attacking third" and arena.third(30, -1) == "defensive third"
    assert arena.side(20) == "right" and arena.side(-20) == "left" and arena.side(0) == "centre"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
