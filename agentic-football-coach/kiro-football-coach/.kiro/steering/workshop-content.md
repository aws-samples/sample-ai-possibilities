# Workshop Content Reference

Quick-reference for teaching participants. Remember: you are a tutor — explain concepts, show patterns, but NEVER write code for participants.

## Match Format

5v5 | 5-minute matches | 60 ticks/sec | 500ms agent response limit | single half, no halftime.

## Agent Loop

Every ~2 seconds, the match server sends game state to your agent. Your agent analyzes and returns commands. The server validates and executes, then repeats.

## Game State Payload

```json
{
  "gameState": {
    "tick": 42, "gameTime": 84.0, "playMode": "PlayOn",
    "score": { "home": 1, "away": 0 },
    "ball": { "position": { "x": 30, "y": 10, "z": 0 }, "velocity": { "x": 2, "y": 0, "z": 0 } },
    "players": [{ "playerId": 0, "teamId": 0, "position": { "x": 25, "y": 10, "z": 0 }, "hasBall": false }]
  },
  "teamId": 0,
  "myPlayers": [0, 1, 2, 3, 4]
}
```

## Command Format

Each agent returns a JSON array of commands:
```json
[
  {"commandType": "SET_STANCE", "playerId": 0, "parameters": {"stance": 1}, "teamId": 0},
  {"commandType": "PRESS_BALL", "playerId": 1, "parameters": {"intensity": 0.7}, "teamId": 0},
  {"commandType": "MARK", "playerId": 2, "parameters": {"target_player_id": 1, "tightness": "LOOSE"}, "teamId": 0}
]
```

## Available Command Types

| Command | Description | Key Parameters |
|---------|-------------|----------------|
| `MOVE_TO` | Move player to a position | `target_x`, `target_y`, `sprint` (bool) |
| `SHOOT` | Shoot at goal | `aim_location` (TL/TR/BL/BR), `power` (0-1) |
| `PASS` | Pass to a teammate | `target_player_id`, `type` (short/long) |
| `PRESS_BALL` | Pressure the ball carrier | `intensity` (0-1) |
| `SET_STANCE` | Change tactical stance | `stance`: 0=BALANCED, 1=DEFENSIVE, 2=ATTACKING |
| `CLEAR_OVERRIDE` | Remove manual instructions, return to default AI | — |
| `MARK` | Mark an opponent | `target_player_id`, `tightness` (TIGHT/NORMAL/LOOSE) |
| `FOLLOW_PLAYER` | Shadow a specific player | `target_player_id`, `target_team` (HOME/AWAY), `distance` |

## Player Stats

- Physical: Speed, Stamina, Strength (1-100)
- Technical: Shooting, Passing, Dribbling, Tackling (1-100)
- Goalkeeper: Reflexes, Positioning, Handling (1-100)
- Runtime: Current Stamina (depletes), Yellow Cards, Red Card, Injured

## Player Positions

Goalkeeper (hands allowed in penalty area), Defenders, Midfielders, Forwards. Field zones: defensive third, midfield, attacking third, penalty box, goal area.

## Scoring & Fouls

Goal = ball crosses goal line between posts. Kickoff after each goal. Most goals after 5 min wins.

Yellow cards: persistent fouling, dangerous play, unsporting behavior, tactical fouls. Red cards: 2 yellows, serious foul play, violent conduct, denying obvious goal. Consequences: free kick, penalty (foul in box), ejection (red card — team plays with 4).

Ball out of play: goal kick (attacker last touch), corner kick (defender last touch), throw-in (sideline).

## Amazon Bedrock AgentCore

AgentCore is an enterprise-grade suite of services for deploying and operating AI agents at scale. Works with any framework and any foundation model.

**Key Services (teach with football analogies):**
- **Runtime** — Hosts your agents so they respond to game ticks in real-time. Each deployed agent gets a unique Runtime ARN.
- **Identity** — Each player agent gets role-specific permissions (striker accesses shooting tools, goalkeeper controls penalty area).
- **Gateway** — Agents discover the right tool for the moment (midfielder finds "quick pass" tool, striker finds "power shot" tool).
- **Memory** — Short-term (within match) and long-term (across matches). Shared across team — when one defender learns a pattern, all defenders gain that knowledge.
- **Observability** — Trace agent decision-making step by step. Monitor all 5 agents simultaneously.
- **Code Interpreter** — Run physics calculations in real-time (shooting angles, trajectories).
- **Browser** — Agents can browse tactical analysis sites for real-world football intelligence.

**Why AgentCore matters:** Faster time to value, flexibility and choice (any framework, any model), security and trust (enterprise-grade, session isolation).

## Coaching System

Send natural-language instructions during matches via Coach Instructions panel. Max 20/min, publicly visible. Conversation history is scoped to current match session. Agents may ignore instructions. Treat coaching as prompt engineering — be specific, scope to roles, avoid conflicting directives.

## Key Strategies

**Offensive**: Possession Play (patient short passes), Counter-Attack (defend deep, fast transitions), High Press (win ball in opponent half, high stamina), Wing Play (wide positioning, crosses).
**Defensive**: Zonal Defense (cover areas), Man-to-Man Marking (track specific opponents), Compact Defense (tight formation), Offside Trap (synchronized forward movement).
**Tactical concepts**: ball possession decisions, movement without ball, passing triangles, game-state awareness (winning → possess, losing → risk more), stamina management.

## Phase Key Facts

1. **Setup** — AWS Workshop Studio, 12-digit event code, regions us-east-1/us-west-2. Install Kiro IDE from kiro.dev. Set up IAM Identity Center user for Kiro subscription. For details activate `aws-setup` skill.
2. **AI Fundamentals** — Agents = LLM reasoning + tools + memory + guardrails + observability. System prompts define agent identity and tactical philosophy. State management tracks conversation history and agent state.
3. **Football Basics & AgentCore** — See command types and stats above. AgentCore services: Runtime, Identity, Gateway, Memory, Observability, Code Interpreter, Browser. For full detail activate `football-rules` and `bedrock-agentcore` skills.
4. **Framework Choice** — Strands (explicit agent loop control) vs LangChain (higher-level abstractions, well-established ecosystem). Both deploy to AgentCore.
5. **Build & Deploy** — Clone from GitHub: `fifa-agentic-football-strands` or `fifa-agentic-football-langchain`. Install deps with `pip install -r requirements.txt`. Test locally with `agentcore dev` + `agentcore invoke --dev`. Deploy with `./deploy-local.sh`. Save the Agent ARN. Guide participant through exploring the code — do NOT write code for them. For SDK patterns activate `strands-agents` or `langgraph-agents` skill.
6. **Register & Play** — Player Portal: log in, create/join team, register for tournament, register agent ARN (5 agents for 5 players). Play training matches vs Kiro Phantoms. Watch via live 2D viewer. Send coach instructions. Activate `football-strategy` skill.
7. **Enhance** — Teach enhancement concepts with sample patterns. Strands: structured output, custom tools, hooks, guardrails, multi-agent, MCP, knowledge bases, state/session management. LangChain: tools, guardrails, prompt tuning, multi-agent, state management. Participant implements themselves. Redeploy with `./deploy-local.sh` (ARN stays same). Activate framework skill for patterns.
8. **Match Day** — Live 2D viewer (blue/red dots, white ball, gold ring = ball holder). Coach Instructions panel for real-time tactics. Coaching as prompt engineering. Activate `football-strategy` skill.
9. **Compete & Cleanup** — Competition matches scheduled by admin. Leaderboard: 3pts win, 1pt draw, 0pts loss. Play multiple training matches (LLM non-determinism). Cleanup: `agentcore destroy`, verify with `agentcore status`. Activate `football-strategy` skill.