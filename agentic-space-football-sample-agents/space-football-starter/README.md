# Space Football — Starter Ship Agents

Five AI agents that each manage one **ship** in a 5v5 Space Football match, built with the
[Strands Agents SDK](https://github.com/strands-agents/sdk-python) and deployed to
[Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/).

Space Football is vehicle-football in a space arena. Unlike classic soccer, an agent here is a
**manager, not a joystick**: you don't steer the ship every tick — you set a **standing policy**
(a team-tactics vote, a ship role, a marking assignment, or a contingency) and the ship executes
it until you change it. This is the deliberately-not-optimal starter squad; beating it is the game.

## Architecture

```
agentic-space-football-sample-agents/
├── lib/                    # Shared library (single source of truth, used by all agents)
└── space-football-starter/
    ├── ship-keeper/        # Keeper  (slot 1) — Nova Micro
    ├── ship-sweeper/       # Sweeper (slot 2) — Nova Lite
    ├── ship-support/       # Support (slot 3) — Nova Pro
    ├── ship-runner/        # Runner  (slot 4) — Nova Lite
    ├── ship-striker/       # Striker (slot 5) — Nova Micro
    ├── deploy-all.sh       # Build + deploy (macOS/Linux)
    ├── deploy-all-windows.ps1
    └── README.md
```

Each agent has the same structure:

```
ship-<role>/
├── src/main.py                          # Agent code (role + model + wiring)
├── .bedrock_agentcore.yaml.template     # AgentCore config template
├── requirements.txt                     # Python dependencies
└── test_local.py                        # Local tests (no AWS needed)
```

### How it works

Every agent's `main.py` is tiny — it picks a role + model and wires up the shared lib:

```python
ROLE_LABEL = "KEEPER"
agent  = create_agent(system_prompt_for(ROLE_LABEL), model_id="us.amazon.nova-micro-v1:0")
invoke = create_invoke_handler(app, agent, AGENT_ID, ROLE_LABEL)
```

The shared `lib/` provides:
- `prompt.py` — the starter system prompt + a one-line per-role note (the thing you tune)
- `agent_base.py` — agent factory + AgentCore invoke handler with 3-layer error handling
  (LLM → rule-based opening policy → last-resort safe command)
- `state.py` — summarises the game state into a compact, football-first briefing for the LLM
- `parsing.py` — extracts + validates ONE command from the LLM response
- `fallback.py` — rule-based opening policy per role when the LLM is unavailable
- `_bootstrap.py` — resolves `lib/` for both local dev and the deployed layout

### The model — why it differs from classic soccer

- **Team tactics are a VOTE.** `SET_TEAM_TACTICS` is not an order — the engine plays the **median**
  of all five agents' votes (plurality for categorical levers), under a 2-vote quorum. One agent
  can't move the team alone. If the state shows `yourVoteIgnored`, you were outvoted — persuade your
  teammates with `SEND_TEAM_MESSAGE` rather than re-sending the same vote.
- **Latency is never punished.** A ship keeps running its last policy every tick while the agent
  thinks, so a slow, correct answer beats a fast, sloppy one. Small models are first-class here.
- **Contingencies are your insurance.** `SET_CONTINGENCY` is re-evaluated every tick, so set a
  "trailing late → chase" / "leading late → shut it down" pair in the first cycle and the team reacts
  to a late goal instantly, even if the model is slow.
- **Reason about the DERIVED read, not raw coordinates.** The state gives you plain-language football
  (possession, threat, open post, score state) so you don't do geometry in the prompt.

Commands: `SET_TEAM_TACTICS, SET_BIKE_ROLE, SET_MARKING, SET_CONTINGENCY, CLEAR_CONTINGENCY,
SEND_TEAM_MESSAGE, CALL_TIMEOUT, CLEAR_POLICY, RESET_TEAM`.

## Prerequisites

- Python 3.10+
- AWS CLI configured with valid credentials
- AgentCore CLI: `pip install bedrock-agentcore-starter-toolkit`
- `rsync` (pre-installed on macOS/Linux)
- AWS account with Bedrock model access (Nova Micro, Lite, and/or Pro)

## Quick Start

### 1. Run local tests (no AWS needed)

```bash
# The full shared-lib unit suite (parsing / fallback / state / prompt)
python3 lib/test_lib.py

# A single ship's smoke test
python3 space-football-starter/ship-keeper/test_local.py
```

### 2. Deploy to AWS

**macOS / Linux:**
```bash
cd space-football-starter
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh            # all 5 ships
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh ship-keeper # a single ship
```

**Windows (PowerShell):**
```powershell
$env:AWS_DEFAULT_REGION = "us-east-1"
.\deploy-all-windows.ps1
.\deploy-all-windows.ps1 -AgentName ship-keeper
```

The deploy script stages each agent into `_build/<ship>/` (its `src/` + the shared `lib/` +
`requirements.txt`), generates `.bedrock_agentcore.yaml` from the template (substituting your AWS
account/region), runs `agentcore deploy`, and cleans up. This keeps `lib/` as a single source of
truth — you never copy it into each agent's tree.

## Creating your own team

Copy the starter and make it yours:

```bash
cp -r space-football-starter my-team
```

Then tune:

- **`lib/prompt.py`** — the system prompt is where the game is won. Change the tactics, the role
  notes, when to vote aggressive vs. defensive, when to argue vs. concede a vote. Keep it short —
  long prompts = slower agents = fewer decisions.
- **`ship-<role>/src/main.py`** — change `ROLE_LABEL` or the `MODEL_ID` (try a bigger model on your
  playmaker, a fast one on the keeper).
- **`ship-<role>/.bedrock_agentcore.yaml.template`** — update `default_agent` + the agent name if you
  rename a ship.

Because team tactics are a vote, a whole team of clones is not optimal — a little disagreement, with
good contingencies, plays better than five identical prompts.

## License

See the repository root `LICENSE`.
