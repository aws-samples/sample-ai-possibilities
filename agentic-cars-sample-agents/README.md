# Agentic Football Cup: Cars Edition sample agents

Sample AI teams for **Cars Edition**, the 5-a-side car football title on the Agentic Football platform
(sibling of [`agentic-football-sample-agents`](../agentic-football-sample-agents) for classic soccer and
[`agentic-space-football-sample-agents`](../agentic-space-football-sample-agents) for Space Football).

Each team is five agents, one per car. A car has its own autonomous driver; your agent steers its
priorities with a short list of commands every ~2 seconds. Built with the
[Strands Agents SDK](https://github.com/strands-agents/sdk-python), deployed to
[Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/) with the
[AgentCore CLI](https://www.npmjs.com/package/@aws/agentcore).

## Contents

```
agentic-cars-sample-agents/
├── lib/                                   # shared library used by every team (single source of truth)
│   ├── arena.py        # arena geometry: x across (±26.5 m), z along (±42 m), goals 18 m wide on the z ends
│   ├── prompt.py       # base system prompt (arena, command reference, output contract) + role/squad notes
│   ├── parsing.py      # tolerant JSON parser + command sanitiser (enums, clamps, 1-3 commands)
│   ├── fallback.py     # rule-based posture + moment commands used when the model returns nothing usable
│   ├── state.py        # turns the relay game state into a short briefing for the model
│   ├── agent_base.py   # Strands agent factory + AgentCore entrypoint with three-layer fallback
│   ├── test_lib.py     # offline unit tests for the library
│   └── test_helpers.py # mock AgentCore runtime + a real sandbox game state for local tests
├── ai-team-strands-balanced/              # 1-1-2 shape, balanced posture
├── ai-team-strands-extremely-aggressive/  # 1-0-3 shape, high press, eager shooting
└── ai-team-strands-extremely-defensive/   # 2-1-1 shape, low press, patient shooting
```

Each team:

```
ai-team-strands-<style>/
├── agentcore/            # AgentCore CLI project (agentcore.json lists the five runtimes) + CDK app
├── car-goalkeeper/       # GOALKEEPER
├── car-defender/         # DEFENDER
├── car-support/          # SUPPORT
├── car-striker-1/        # STRIKER
├── car-striker-2/        # STRIKER
│   ├── src/main.py       # the agent: role, model, extra instructions
│   ├── pyproject.toml    # dependencies (lower bound + major ceiling)
│   └── test_local.py     # offline checks, --llm for one real model call
└── deploy_all.py         # injects lib/ and runs `agentcore deploy` for all five
```

## Prerequisites

- Python 3.10+
- Node.js 20+ and npm; `npm install -g @aws/agentcore aws-cdk` (AgentCore CLI 0.31 or newer)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (the CLI packages Python dependencies with it)
- AWS CLI with credentials for the account that will host the agents
- Bedrock model access in that account for the models you pick (the samples use Amazon Nova Micro, Lite and 2 Lite)
- One-time per account and region: `cdk bootstrap aws://<account-id>/<region>` (`deploy_all.py` runs it for you)

## Quick start

```bash
# 1. Offline checks, no AWS needed
python3 lib/test_lib.py
python3 ai-team-strands-balanced/car-goalkeeper/test_local.py

# 2. One real model call (AWS credentials + Bedrock access)
python3 ai-team-strands-balanced/car-goalkeeper/test_local.py --llm

# 3. Deploy a team (about five minutes)
cd ai-team-strands-balanced
AWS_DEFAULT_REGION=us-east-1 python3 deploy_all.py

# 4. Collect the five runtime ARNs (run from the team folder) and paste them into your team's squad page
agentcore status --json | python3 -c "import json,sys; [print(r['name'], r['identifier']) for r in json.load(sys.stdin)['resources'] if r.get('resourceType')=='agent']"

# 5. Remove everything when you are done (from the team folder)
agentcore remove all -y
```

The platform invokes each runtime with `{"prompt": "<json>"}` where the JSON carries
`gameState` (the relay status), `teamCode`, `agentId` (`<teamCode>-<n>`), `role`, `attackingZ` (+1 or -1,
the z end you attack), `durationSeconds` and optional `coachInstructions`. The agent replies with a JSON
array of one to three commands.

## The arena

Measured on the live game server. `MOVE_TO` takes `target_x` for x and `target_y` for z.

| Measure | Value |
|---|---|
| Width (x) | 53 m, x from -26.5 to +26.5 |
| Length (z) | 84 m, z from -42 to +42 |
| Goal lines | z = -42 and z = +42 |
| Goal mouth | 18 m wide (x from -9 to +9), 8 m high |
| Thirds | defensive, middle and attacking thirds are 28 m each along z |
| Shooting | shots from inside 15 m go in often; from 25 m they rarely do |

Which end a team attacks changes per match. The briefing states it, and `attackingZ` is in the payload.

## Commands

Posture levers are team-wide and persist until changed. The vendor recommends them as the main tool
for an agent that is called every two seconds with a second of thinking time:

| Command | Parameters |
|---|---|
| `SET_TEAM_STANCE` | `stance`: ATTACK, BALANCED, DEFEND |
| `SET_SHAPE` | `shape`: defenders-support-forwards over the four outfield cars, e.g. `1-1-2`, `1-0-3`, `2-1-1` |
| `SET_PRESSING` | `level`: HIGH, NORMAL, LOW |
| `SET_SHOT_SELECTION` | `level`: EAGER, NORMAL, PATIENT |
| `SET_TEMPO` | `level`: FULL, NORMAL, MEASURED |
| `SET_WIDTH` | `level`: WIDE, NORMAL, NARROW |

Moment commands act on your own car. The driver lines them up and executes them; send at most one per reply:

| Command | Parameters |
|---|---|
| `SHOOT` | `aim_location`: TL, TR, BL, BR, CENTER; `power` 0 to 1 |
| `PASS` | `target_player_id` (teammate index from the briefing), `lead` |
| `BUMP` | `target_player_id` (opponent index, -1 = ball carrier), `sprint` |
| `MOVE_TO` | `target_x`, `target_y` (that is z), `sprint` |
| `PRESS_BALL` | `intensity` 0 to 1 |
| `INTERCEPT` | `aggressive` |
| `MARK` | `target_player_id`, `tightness`: LOOSE, TIGHT |
| `FOLLOW_PLAYER` | `target_player_id`, `target_team`: HOME, AWAY; `distance` |
| `DEFENSIVE_CLEAR` | `power` 0 to 1 |

Housekeeping: `CLEAR_OVERRIDE` (hand the car back to its driver), `RESET` (whole team), `SET_ROLE_PARAMS`
(`role`, `forward_bias`, `press_intensity`, `shoot_distance`, `defend_distance`, `speed_bias`). Do not send
`CLEAR_OVERRIDE` or `RESET` in the same reply as a moment command; it would cancel it.

Reply format: `[{"commandType": "SET_PRESSING", "parameters": {"level": "HIGH"}}, {"commandType": "SHOOT", "parameters": {"aim_location": "TR", "power": 0.9}}]`.
The library's parser normalises casing, clamps numbers to the arena and the 0 to 1 ranges, drops
unknown commands and keeps the first moment command, so a slightly off reply still plays.

## Making the team yours

Edit `car-<role>/src/main.py`:

1. `ROLE` and `TEAM_VARIANT` pick the role notes and the fallback posture from the shared library.
2. `MODEL_ID` picks the Bedrock model. The platform allows the Amazon Nova family and the Anthropic Claude
   models listed on the squad page; both the ids shown there and cross-region inference profile ids work.
3. `EXTRA_INSTRUCTIONS` is your tactics. Keep the base prompt from `system_prompt_for()`: it carries the
   arena and the output contract the parser expects.

To add or rename a car, add a runtime entry to `agentcore/agentcore.json` (same shape as the existing
five, `codeLocation` pointing at the new folder) and the folder name to `ALL_AGENTS` in `deploy_all.py`.

## Reading your match back

After a match the platform's post-match report shows each car's command counts and a replay of the match.
The game server also records an attribution log: every command it received, with the match clock, the
team and the car that sent it. Comparing that log with the goals in the result tells you which of your
instructions led to shots and which were ignored because they arrived while the driver was already
executing another intent. Use it to trim the instructions that never change the play.

## Notes

- Observability: every runtime is created with `OTEL_METRICS_EXPORTER=none` in `agentcore.json`. Traces
  and logs stay on; the per-cycle custom metrics are what costs money at match volume.
- Dependencies are pinned with a lower bound and a major-version ceiling (for example
  `strands-agents>=1.61,<2`) so a routine update cannot break a deployed team.
- Tested with AgentCore CLI 0.31.1, `aws-cdk-lib` 2.261, `@aws/agentcore-cdk` 0.1.0-alpha.54.
