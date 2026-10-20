"""Tests for possession resolution in state.py.

Run directly:  python test_state.py

These cover the case where the same agentId appears on both teams, which is
how the game server numbers players (agentId_0..agentId_4 per team). Resolving
possession by index alone makes two players believe they hold the same ball.
"""

import copy

from state import get_possession_info, holder_is_me, summarize_state
from test_helpers import GAME_STATE

HOME, AWAY = 0, 1
HOLDER_IDX = 3  # the fixture's ball is held by agentId_3 on the home team


def _ball(**overrides):
    b = copy.deepcopy(GAME_STATE["ball"])
    b.update(overrides)
    return b


def _players():
    return GAME_STATE["players"]


def test_fixture_has_colliding_agent_ids():
    """Guard the premise: agentId is not unique across teams."""
    ids = [p["agentId"] for p in _players()]
    assert len(ids) != len(set(ids)), "fixture no longer collides — revisit _resolve_holder"
    dupes = {i for i in ids if ids.count(i) > 1}
    print(f"=== PREMISE: agentIds shared across teams: {sorted(dupes)} ===")


def test_only_the_holder_reports_has_ball():
    """The opposing player with the same index must not claim the ball."""
    ball, players = _ball(), _players()
    assert holder_is_me(ball, players, HOME, HOLDER_IDX) is True
    assert holder_is_me(ball, players, AWAY, HOLDER_IDX) is False
    print("=== HOLDER: home p3 holds, away p3 does not ===")


def test_possession_side_is_per_team():
    """Same ball, same tick: each team sees the holder from its own side."""
    ball, players = _ball(), _players()
    assert get_possession_info(ball, players, HOME) == (HOLDER_IDX, "MY player 3", True)
    assert get_possession_info(ball, players, AWAY) == (HOLDER_IDX, "OPP player 3", False)
    print("=== SIDES: MY for home, OPP for away ===")


def test_rendered_prompt_is_not_self_contradictory():
    """The away forward used to read 'held by OPP player 3' and hasBall=True."""
    out = summarize_state(GAME_STATE, AWAY, HOLDER_IDX, "FWD1")
    assert "held by OPP player 3" in out
    assert "hasBall=False" in out, out
    print("=== PROMPT: away p3 told opponent holds it, and hasBall=False ===")


def test_server_isfree_is_honoured():
    """isFree is authoritative; it was previously ignored entirely."""
    assert get_possession_info(_ball(isFree=True), _players(), HOME) == (None, "free", False)
    print("=== ISFREE: respected ===")


def test_unresolvable_claim_is_unknown_not_free():
    """A claim we cannot parse must never render as a loose ball.

    Reporting 'free' here is what told a player carrying the ball to go and
    fetch it.
    """
    for bad in ("home_fwd1", "agentId_9", "arn:aws:bedrock:::agent/HomeFwd1"):
        got = get_possession_info(_ball(possessionAgentId=bad), _players(), HOME)
        assert got == (None, "unknown", False), (bad, got)
    print("=== UNRESOLVABLE: reported as unknown, not free ===")


def test_no_claim_is_free():
    ball = _ball()
    ball.pop("possessionAgentId", None)
    ball.pop("isFree", None)
    assert get_possession_info(ball, _players(), HOME) == (None, "free", False)
    print("=== NO CLAIM: genuinely loose ===")


def test_team_code_case_is_tolerated():
    """Uppercase teamCode must not erase the agent's own player.

    The server documents HOME/AWAY while the payload has been seen as
    home/away. Case sensitivity here drops the player from its own prompt and
    lists its teammates as opponents.
    """
    for transform in (str.upper, str.title):
        gs = copy.deepcopy(GAME_STATE)
        for p in gs["players"]:
            p["teamCode"] = transform(p["teamCode"])
        out = summarize_state(gs, AWAY, HOLDER_IDX, "FWD1")
        assert ">>> YOUR PLAYER" in out, f"own player missing with {transform.__name__} teamCode"
        assert "hasBall=False" in out
    print("=== TEAMCODE: upper/title case tolerated ===")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"{len(fns)} tests passed")
