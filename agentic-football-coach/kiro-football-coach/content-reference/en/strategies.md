# Football Strategies and Tactics

Comprehensive reference for offensive strategies, defensive strategies, and tactical programming concepts for AI football agents.

---

## Offensive Strategies

### Possession Play

- Keep the ball through many short passes
- Tire out opponents by making them chase
- Wait for the perfect opportunity to attack
- **Agent behavior:** Patient passing, maintain formation, prioritize safe passes over risky forward balls

### Counter-Attack

- Defend deep, absorb pressure
- Attack quickly when you win the ball
- Use speed to catch opponents out of position
- Direct, fast passes forward
- **Agent behavior:** Quick transitions from defense to attack, sprint forward on ball recovery, long passes to exploit space behind the opponent's defensive line

### High Press

- Pressure opponents immediately when they have the ball
- Try to win the ball in the opponent's half
- Requires high stamina and coordination
- **Agent behavior:** Aggressive positioning high up the pitch, quick tackling, close down passing lanes, coordinate press triggers as a unit

### Wing Play

- Attack down the sides of the field
- Cross the ball into the penalty box
- Stretch the opponent's defense horizontally
- **Agent behavior:** Wide positioning for wingers, overlapping runs from fullbacks, crossing into the box, target forwards positioned centrally

---

## Defensive Strategies

### Zonal Defense

- Each player defends a specific area of the field
- Maintain team shape and spacing regardless of opponent movement
- **Agent behavior:** Hold assigned position, cover designated zone, shift as a unit when ball moves, prioritize zone integrity over tracking individual opponents

### Man-to-Man Marking

- Each defender tracks a specific opponent
- Follow your assigned player closely wherever they move
- **Agent behavior:** Mark specific opponent ID, follow their movements, stay within tackling distance, switch only when explicitly reassigned

### Compact Defense

- Keep all players close together in a tight block
- Make it hard for opponents to find space between the lines
- **Agent behavior:** Maintain tight formation, reduce gaps between players, compress the space between defense and midfield, force opponents wide

### Offside Trap

- Defenders move forward together to catch attackers offside
- Requires perfect timing and coordination among all defenders
- **Agent behavior:** Synchronized forward movement on a trigger (e.g., opponent about to pass), awareness of all opponent positions, step up as a line

---

## Tactical Programming Concepts

These concepts translate directly to agent decision-making logic.

### Ball Possession Decisions

| Situation | Recommended Action |
|---|---|
| Safe position, no good passing options | Keep the ball, dribble or hold |
| Teammate in better position | Pass (short or through) |
| Under pressure from opponent | Pass quickly or clear |
| Creating an attack | Pass forward or switch play |
| Close to goal, clear shot, good angle | Shoot |
| Close to goal, blocked shot | Look for pass or reposition |

### Movement Without the Ball

- **Making runs:** Move into open space to receive a pass; time the run to stay onside
- **Creating space:** Pull defenders away from key areas to open gaps for teammates
- **Supporting the ball carrier:** Position yourself nearby to offer a passing option
- **Recovering position:** Track back to defensive shape when possession is lost

### Team Coordination Patterns

- **Passing triangles:** Three players form a triangle for easy short-passing options; rotate the triangle as play moves
- **Overlapping runs:** Fullback or midfielder runs past the ball carrier on the outside to receive a forward pass and deliver a cross
- **Switching play:** Long pass to the opposite side of the field to exploit space where the opponent is thin
- **Third-man runs:** Player A passes to Player B, who lays off to Player C making a run — bypasses the first line of pressure

### Game State Awareness

| Game State | Tactical Adjustment |
|---|---|
| **Winning** | Focus on possession, protect the lead, manage the clock, reduce risk |
| **Losing** | Take more risks, press higher, shoot more often, commit extra players forward |
| **Drawing** | Balanced approach, look for opportunities, don't overcommit |
| **Late in match + winning** | Time management, keep ball in opponent's half, avoid unnecessary fouls |
| **Late in match + losing** | All-out attack, goalkeeper can push up for set pieces, accept defensive risk |

### Stamina Management

- **Sprint wisely:** Save sprints for critical moments (breakaways, last-ditch tackles, goal-scoring chances)
- **Rotation:** Players take turns pressing and recovering; don't have the same player sprint every tick
- **Positioning:** Good positioning reduces the need for running — be in the right place before the ball arrives
- **Walk when possible:** Use WALK instead of RUN when not under time pressure to conserve stamina
- **Monitor current stamina:** Adjust aggression based on remaining stamina; a tired player is slower and less effective

---

## Strategy-to-Agent Mapping Summary

| Strategy | Key Actions | Stamina Impact | Risk Level |
|---|---|---|---|
| Possession Play | SHORT_PASS, DRIBBLE, WALK | Low | Low |
| Counter-Attack | SPRINT, LONG_PASS, THROUGH_PASS, SHOOT | High (bursts) | Medium |
| High Press | RUN, TACKLE, INTERCEPT, SPRINT | High (sustained) | Medium-High |
| Wing Play | RUN, CROSS, SPRINT, DRIBBLE | Medium | Medium |
| Zonal Defense | WALK, STOP, INTERCEPT, MARK | Low | Low |
| Man-to-Man Marking | RUN, MARK, TACKLE | Medium | Medium |
| Compact Defense | WALK, STOP, MARK, INTERCEPT | Low | Low |
| Offside Trap | RUN (synchronized), STOP | Low-Medium | High |
