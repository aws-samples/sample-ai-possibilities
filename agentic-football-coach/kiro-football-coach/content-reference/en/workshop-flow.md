# Workshop Flow — Agentic Football World Cup

This document describes the workshop progression that the coach uses to guide and teach participants. The coach is a tutor — it explains concepts, shows patterns, and guides participants through hands-on steps. It NEVER writes code for participants.

## Phase 1: Welcome & Setup

Participants receive their AWS Workshop Studio access (12-digit event access code), authenticate via OTP, and configure AWS CLI credentials. The workshop runs in us-east-1 or us-west-2.

**Kiro IDE Setup:**
1. Install Kiro from [kiro.dev](https://kiro.dev)
2. In the AWS console, set up an IAM Identity Center user (provide username, email, first name, last name)
3. Accept the Identity Center email invitation and create a password
4. Disable MFA on Identity Center (Settings → Authentication → Multi-factor authentication → Never)
5. In the AWS console, search for Kiro, go to Settings, click "Sign up for Kiro", select IAM Identity Center, add the user with Kiro Pro subscription
6. In Kiro IDE, sign in via IAM Identity Center using the Sign in URL from the Kiro console

**AWS CLI Credentials:**
1. In Workshop Studio, navigate to AWS Account Access → Get AWS CLI credentials
2. Copy and export: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, AWS_DEFAULT_REGION
3. Verify: `aws sts get-caller-identity`

**Key outcomes:** AWS console access, CLI credentials configured, Kiro IDE installed and signed in, environment ready.

## Phase 2: AI Agent Fundamentals

**Teach these concepts:**

AI agents are autonomous software entities that use an LLM as their "brain" to make decisions about tools and actions. They maintain conversation context and create execution plans.

Core agentic system components:
- **Foundation Models** — The reasoning engine powering agent decisions
- **Agent Orchestration** — Coordinates multiple agents and manages workflow execution
- **Tool Integration** — Connects agents to external systems and data sources
- **Memory & Context** — Maintains conversation history and state across interactions
- **Guardrails & Safety** — Ensures responsible AI behavior and policy compliance
- **Monitoring & Observability** — Tracks agent performance and decision quality

**System Prompts** define the agent's identity, role, and baseline tactical philosophy. For football agents: position, tactical instructions, decision-making priorities, behavioral constraints.

**State Management** covers conversation history (sequence of observations and decisions during a match) and agent state (formation, stamina estimates, tactical objectives). Strands manages state through built-in memory constructs; LangChain manages state explicitly through the chain/executor.

**Key outcomes:** Understanding of agent types, core agentic system architecture, system prompts, and state management.

## Phase 3: Football Basics & Amazon Bedrock AgentCore

**Football fundamentals for the 5v5 AI format:**
- Positions: Goalkeeper, Defenders, Midfielders, Forwards
- Field zones: Defensive Third, Midfield, Attacking Third, Penalty Box, Goal Area
- Spatial concepts: Width, depth, spacing, positioning
- Basic rules: No hands (except goalkeeper), fouls → free kicks, offside rule
- Strategies: Possession Play, Counter-Attack, High Press, Wing Play (offensive); Zonal Defense, Man-to-Man Marking, Compact Defense, Offside Trap (defensive)
- Tactical concepts: stamina management, game state awareness, team coordination

**Amazon Bedrock AgentCore:**
AgentCore is an enterprise-grade suite of services for deploying and operating AI agents at scale. Works with any framework (Strands, LangChain, CrewAI, LlamaIndex) and any foundation model.

Key services (teach with football analogies):
- **Runtime** — Hosts your agents so they respond to game ticks in real-time. Each deployed agent gets a unique Runtime ARN.
- **Identity** — Each player agent gets role-specific permissions. Striker accesses shooting tools, goalkeeper controls penalty area.
- **Gateway** — Agents discover the right tool for the moment. Midfielder finds "quick pass" tool, striker finds "power shot" tool.
- **Memory** — Short-term (within match) and long-term (across matches). Shared across team.
- **Observability** — Trace agent decision-making step by step. Monitor all 5 agents simultaneously.
- **Code Interpreter** — Run physics calculations in real-time (shooting angles, trajectories).
- **Browser** — Agents can browse tactical analysis sites for real-world football intelligence.

Why AgentCore matters: Faster time to value, flexibility and choice, security and trust.

**Key outcomes:** Understanding of football positions, field layout, rules, strategies, and AgentCore services.

## Phase 4: Framework Choice

Participants choose between two agent frameworks:

| Consideration | Strands Agents SDK | LangChain SDK |
|---|---|---|
| Abstraction level | Lower — explicit control over agent loop | Higher — well-established ecosystem |
| Agent creation | `Agent(model=model, tools=tools)` | `create_react_agent(model, tools)` |
| State management | Built-in agent memory constructs | Explicit — pass through chain/executor |
| Tool definition | `@tool` from `strands` | `@tool` from `langchain_core.tools` |
| Multi-agent | Swarm, GraphBuilder, agents-as-tools | StateGraph with nodes and edges |
| Best for | Custom workflows, fine-grained logic | Structured multi-step reasoning |

Both deploy to Amazon Bedrock AgentCore. Present both neutrally and let participants decide.

**Key outcomes:** Framework selected, understanding of trade-offs.

## Phase 5: Build & Deploy Agent

**Architecture:** Match Server + Agent Loop (managed centrally) ↔ Your 5 Agents on AgentCore (your AWS account). Each team has 5 players, each controlled by its own AgentCore agent.

**Guide participants through (they do the work):**
1. Clone the repo — Strands: `git clone https://github.com/aws-samples/fifa-agentic-football-strands.git`. LangChain: `git clone https://github.com/aws-samples/fifa-agentic-football-langchain.git`
2. Set up environment — Create Python venv, install dependencies
3. Explore the code — Walk through `src/main.py` explaining: BedrockAgentCoreApp runtime, agent creation, game state summarizer, command parser, rule-based fallback
4. Test locally — `agentcore dev` + `agentcore invoke --dev '...'`
5. Deploy — `./deploy-local.sh` (handles IAM role, packaging, S3 upload, deployment)
6. Save Agent ARN — format: `arn:aws:bedrock-agentcore:<region>:<account-id>:runtime/<agent-id>`

**Key outcomes:** Working sample agent deployed to AgentCore, Agent ARN obtained.

## Phase 6: Register & Play

**Guide participants through:**
1. Log in to the Player Portal with credentials from workshop instructor
2. Create or join a team — My Teams → Create Team
3. Register for tournament — Find active tournament → Register → select team
4. Register agent — Agents → enter name and ARN → Register Agent (repeat for all 5 players)
5. Play training matches — Matches → Training Match → Start Match (vs Kiro Phantoms)
6. Watch live — 2D viewer (blue=Team A, red=Team B, white=ball, gold ring=ball holder)
7. Send coach instructions — Coach Instructions panel during live matches

**Key outcomes:** Agent registered, training matches played, coaching system understood.

## Phase 7: Enhance Agent

**Teach enhancement concepts with sample patterns. Participant implements themselves.**

Strands SDK enhancements:
- Structured Output (Pydantic models for validated actions)
- Custom Tools (tactical analysis functions with @tool)
- Observability (metrics, traces, latency tracking)
- Hooks (monitoring, tool call limiting with HookProvider)
- Model switching (Nova Micro vs Claude)
- Guardrails (content filtering via BedrockModel)
- State tracking (opponent patterns via agent.state)
- Retry strategies (throttling handling)
- Multi-agent pipelines (analyze → plan → act with GraphBuilder)
- MCP Tools (external tool servers)
- Knowledge Bases (RAG with Bedrock Knowledge Bases)
- Conversation Management (SlidingWindow, Null, Summarizing)
- Session Management (FileSessionManager, S3SessionManager)
- Multi-Modal (images and documents for analysis)

LangChain enhancements:
- Tool patterns (@tool from langchain_core.tools, class-based tools)
- Guardrails integration (via ChatBedrock)
- Prompt improvement (system prompt refinement)
- State management (MessagesState, custom TypedDict, MemorySaver)
- Multi-agent (StateGraph with nodes and edges)
- MCP Tools, Knowledge Bases, Multi-Modal
- Performance tuning (model selection, parallel tools, temperature)

After changes, redeploy with `./deploy-local.sh` — the ARN stays the same.

**Key outcomes:** Agent with improved decision-making, observability, and resilience.

## Phase 8: Match Day

**Live Match Viewer:**
- 2D top-down football field view at 30 FPS via WebSocket
- Blue dots (Team A), Red dots (Team B), White dot (ball), Gold ring (ball holder)
- Player names, score, countdown timer, recent events

**Coach Instructions:**
- Send real-time tactical instructions via Coach Instructions panel
- Instructions take effect on the next tick — no redeployment needed
- Conversation history scoped to current match session (resets between matches)
- Coaching as prompt engineering: be specific, scope to roles, avoid conflicting directives

**Key outcomes:** Live match observation, real-time coaching practiced.

## Phase 9: Compete & Cleanup

- Competition matches scheduled by tournament admins
- Leaderboard: 3pts win, 1pt draw, 0pts loss
- Play multiple training matches to exploit LLM non-determinism
- Iterate: watch → analyze → improve → redeploy → repeat
- Cleanup: `agentcore destroy` from agent project directory. Verify with `agentcore status`.

**Key outcomes:** Competitive matches played, strategies refined, resources cleaned up.

---

## Workshop Metadata

| Attribute | Value |
|---|---|
| Content Level | 200 |
| Duration | ~4 hours |
| Audience | Solutions Architects, Software Developers, AI Practitioners |
| Prerequisites | AWS Management Console familiarity, Amazon Bedrock basics |
| Supported Regions | us-east-1, us-west-2 |
| AWS Services | Amazon Bedrock, Bedrock AgentCore, Strands Agents SDK, LangChain |