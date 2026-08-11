# AI Team — Unified Memory and Gateway Agents

This team combines the tactical tool access from the AgentCore Gateway workshop with the per-role tick history from the AgentCore Memory workshop. It retains the existing `ai-team-strands-gateway` directory so the workshop source is not duplicated, but its templates deploy a distinct set of `*_unified_agent` runtimes.

## What is included

- **Five roles:** GK, DEF, MID, FWD1, FWD2.
- **AgentCore Memory:** each role retains team-scoped history across ticks through the existing `MEMORY_ID` resource.
- **AgentCore Gateway:** agents call the existing MCP endpoint in `GATEWAY_URL` for pass, space, shot, and defensive analysis.
- **Tactical changes:** high press remains the baseline after its 1–0 win; agents limit expensive tool calls to decision points; forwards now require a clear evaluated chance before shooting.
- **Models:** GK and FWD1 use Nova Lite, DEF and FWD2 use Nova Lite, and MID uses Nova Pro for the most complex coordination decisions.

The memory implementation is role-scoped because the game payload does not provide a match ID. It should not be used as an authoritative cross-match record. If the game later supplies `matchId`, include it in the memory session ID to isolate history per match.

## Existing resource inputs

This deployment script deliberately does not create or change a Memory resource, Gateway, or Gateway Lambda tools. Set the identifiers from the workshop deployments:

```bash
export MEMORY_ID="<existing-agentcore-memory-id>"
export GATEWAY_URL="https://<existing-gateway-id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
export TEAM_ID="kasia-rook"
```

If Gateway authentication is enabled, also set `GATEWAY_ACCESS_TOKEN`. The workshop Gateway is configured for no authentication, so no token is normally needed.

## Validate locally

```bash
python3 ai-gk/test_local.py
python3 ai-def/test_local.py
python3 ai-mid/test_local.py
python3 ai-fwd1/test_local.py
python3 ai-fwd2/test_local.py
```

These tests validate state interpretation, command parsing, and deterministic fallbacks without using AWS. Test an actual model separately with the matching role's `test_local.py --llm` once the required environment variables are set.

## Deploy when ready

Deployment creates/updates only the five distinct unified AgentCore runtimes. It reuses the supplied Memory and Gateway resources and scopes the added access policy to those specific resource IDs.

```bash
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh
```

To deploy one role:

```bash
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh ai-fwd1
```

## Match reports

Manually supplied reports are stored in `match-reports/`. Keep the raw report details, the verified winner and score, tactical observations, and one next experiment. Do not change multiple tactical variables based on one match.
