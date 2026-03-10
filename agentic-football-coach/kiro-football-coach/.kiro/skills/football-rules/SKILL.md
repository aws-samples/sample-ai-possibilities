---
name: football-rules
description: "Activate when discussing game rules, player actions, scoring, fouls, cards, or match format"
---

# Football Game Rules & Mechanics

Comprehensive reference for the Agentic Football 5v5 game — actions, player stats, fouls, match format, and coaching.

## Match Format

| Attribute | Value |
|-----------|-------|
| Team Size | 5 players per team |
| Match Duration | 5 minutes (single half, no halftime) |
| Game Speed | 60 ticks per second |
| Agent Response Time | 500ms maximum per decision |

Every tick, the server sends game state to your agent. Your agent analyzes the situation (within 500ms) and returns an action. The server validates and executes it, then repeats.

## Player Positions

- **Goalkeeper** — protects the goal, only player who can use hands in the penalty area
- **Defenders** — stop opponents from scoring
- **Midfielders** — connect defense and attack, control the middle
- **Forwards (Strikers)** — focus on scoring goals

## Actions

### Movement Actions

| Action | Description | When to Use |
|--------|-------------|-------------|
| WALK | Slow movement (conserves stamina) | Positioning, when not urgent |
| RUN | Fast movement (uses stamina) | Chasing ball, getting into position |
| SPRINT | Maximum speed (high stamina cost) | Critical moments, breakaways |
| STOP | Stop moving | When in position, waiting for pass |

Parameters: Direction (N, NE, E, SE, S, SW, W, NW), Speed (1-10)

### Ball Actions (When You Have Possession)

| Action | Description | Parameters |
|--------|-------------|------------|
| SHORT_PASS | Ground pass to nearby teammate | Target player ID, Power (1-5) |
| LONG_PASS | Aerial pass to distant teammate | Target player ID, Power (1-10) |
| THROUGH_PASS | Pass into space ahead of teammate | Direction, Power |
| CROSS | Aerial pass into penalty box | Target zone, Power |
| SHOOT | Attempt to score | Direction, Power (1-10) |
| DRIBBLE | Move while keeping the ball | Direction, Speed |

### Defensive Actions (When You Don't Have the Ball)

| Action | Description | Risk Level |
|--------|-------------|------------|
| TACKLE | Attempt to take the ball | Medium — can foul |
| SLIDE_TACKLE | Sliding tackle | High — likely foul if mistimed |
| INTERCEPT | Position to intercept a pass | Low |
| MARK | Follow a specific opponent | Low |

### Goalkeeper Actions

| Action | Description |
|--------|-------------|
| DIVE | Dive to save a shot (left/right/up) |
| CATCH | Catch the ball |
| PUNCH | Punch the ball away |
| THROW | Throw to a teammate |
| GOAL_KICK | Long kick from the goal area |

### Special Actions

| Action | Description |
|--------|-------------|
| IDLE | Do nothing (default if agent times out) |
| HEADER | Head the ball (automatic when ball is aerial) |
| CELEBRATE | Celebration animation after scoring |

## Player Stats

### Physical Stats

| Stat | Range | Effect |
|------|-------|--------|
| Speed | 1-100 | Maximum movement speed |
| Stamina | 1-100 | Endurance; depletes during running/sprinting |
| Strength | 1-100 | Tackle effectiveness, ball retention |

### Technical Stats

| Stat | Range | Effect |
|------|-------|--------|
| Shooting | 1-100 | Shot accuracy and power |
| Passing | 1-100 | Pass accuracy |
| Dribbling | 1-100 | Ball control while moving |
| Tackling | 1-100 | Tackle success rate |

### Goalkeeper Stats

| Stat | Range | Effect |
|------|-------|--------|
| Reflexes | 1-100 | Save reaction time |
| Positioning | 1-100 | Optimal position selection |
| Handling | 1-100 | Catch vs punch decision quality |

### Runtime State

| State | Description |
|-------|-------------|
| Current Stamina | Depletes during match, affects speed |
| Yellow Cards | 2 yellows = red card = ejection |
| Red Card | Player is ejected from match |
| Injured | Reduces speed and effectiveness |

## Scoring

- **Goal**: Ball completely crosses the goal line between the posts
- **Kickoff**: After each goal, play restarts from center
- **Winner**: Team with most goals after 5 minutes

## Fouls and Cards

### Yellow Card Offenses
- Persistent fouling
- Dangerous play
- Unsporting behavior
- Tactical fouls

### Red Card Offenses
- Receiving 2 yellow cards
- Serious foul play
- Violent conduct
- Denying obvious goal-scoring opportunity

### Consequences
- **Free Kick** — awarded to fouled team
- **Penalty** — free kick from penalty spot if foul is in the box
- **Red Card** — player ejected, team plays with 4 players

## Ball Out of Play

- **Goal Kick** — ball goes out over goal line (not a goal), last touched by attacker
- **Corner Kick** — ball goes out over goal line, last touched by defender
- **Throw-In** — ball goes out over sideline

## Game State (What Your Agent Sees)

Each tick your agent receives:
- **Your Player**: position (x, y), ball possession status, stats, current stamina
- **The Ball**: position, velocity, current possessor
- **Teammates**: positions, stats, stamina, possession status (4 teammates)
- **Opponents**: positions, visible stats, possession status (5 opponents)
- **Match Context**: current score, time remaining, coach instructions, player messages

Your agent cannot see: opponent agent code/strategy, future predictions, hidden stats, or other agents' decision-making.

## Coaching System

During live matches, coaches can send natural language instructions to agents via the Viewer Portal.

**Examples:**
- "Press higher, win the ball back quickly"
- "Hold position, wait for counter-attack"
- "Focus on possession, slow the game down"

**Limitations:**
- Max 20 instructions per minute per team
- All instructions are public (visible to all viewers)
- Agents may choose to ignore instructions

**Conversation History:**
- Instructions accumulate within a match session as conversation history
- Agents interpret new instructions in context of prior ones
- History resets between matches — no carryover

**Coaching Tips:**
- Be specific: "Win the ball back in the opponent's half" > "press more"
- Specify scope: "defenders hold position" or "forwards push higher"
- Avoid conflicting directives in a single message
- Build on prior instructions rather than repeating context

## The Field

Key zones:
- **Defensive Third** — area near your own goal
- **Midfield** — central area, possession battles
- **Attacking Third** — area near opponent's goal
- **Penalty Box** — rectangle in front of each goal (fouls here = penalties)
- **Goal Area** — small box in front of goal (goalkeeper's domain)

Spatial concepts: width (spread for passing options), depth (support at different distances), spacing (prevent crowding), positioning (right place, right time).

## References

- See `content-reference/en/game-mechanics.md` for full detail
