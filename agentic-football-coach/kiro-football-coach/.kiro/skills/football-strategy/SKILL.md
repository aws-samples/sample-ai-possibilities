---
name: football-strategy
description: "Activate when discussing strategy, tactics, or agent behavior design"
---

# Football Strategies & Tactics

Strategies and tactical concepts for programming smarter football agents. Each strategy includes agent-behavior mappings that translate directly to code decisions.

## Offensive Strategies

### Possession Play

**Goal:** Keep the ball, tire out opponents, wait for the perfect opening.

| Aspect | Detail |
|--------|--------|
| Style | Many short passes, patient build-up |
| Tempo | Slow, controlled |
| Risk | Low — fewer turnovers |
| Best When | Leading, or opponent presses aggressively |

**Agent-Behavior Mapping:**
- Prefer `SHORT_PASS` over `LONG_PASS` — higher accuracy, lower turnover risk
- Use `DRIBBLE` only in safe zones (own half, no nearby opponents)
- Movement: teammates constantly reposition to offer passing angles
- Decision logic: if no forward pass is safe, pass backward or sideways to retain possession
- Stamina: low consumption — rely on `WALK` and `RUN`, avoid `SPRINT`

```
if no_safe_forward_pass:
    pass_backward_or_sideways()
else:
    short_pass_to_best_positioned_teammate()
```

### Counter-Attack

**Goal:** Defend deep, win the ball, then attack quickly with speed.

| Aspect | Detail |
|--------|--------|
| Style | Direct, fast transitions from defense to attack |
| Tempo | Slow in defense, explosive in attack |
| Risk | Medium — relies on speed and timing |
| Best When | Opponent dominates possession, you have fast forwards |

**Agent-Behavior Mapping:**
- Defenders: `MARK` and `INTERCEPT` in own half, stay compact
- On ball win: immediate `LONG_PASS` or `THROUGH_PASS` to forwards
- Forwards: `SPRINT` into space behind opponent defense on transition
- Midfielders: quick `RUN` forward to support the attack
- Key trigger: ball possession change → switch from defensive to attacking mode instantly

```
if just_won_ball:
    long_pass_to_forward_in_space()
    forwards.sprint_toward_goal()
```

### High Press

**Goal:** Pressure opponents immediately, win the ball in their half.

| Aspect | Detail |
|--------|--------|
| Style | Aggressive, high defensive line |
| Tempo | Fast, intense |
| Risk | High — leaves space behind if beaten |
| Best When | Losing, need to force turnovers, high team stamina |

**Agent-Behavior Mapping:**
- All outfield players push into opponent's half when they have the ball
- Use `TACKLE` and `INTERCEPT` aggressively in attacking third
- `SPRINT` to close down ball carrier quickly
- If beaten, `RUN` back immediately to recover
- Stamina: very high consumption — monitor stamina levels, drop press when tired
- Coordination: press as a unit, not individually

```
if opponent_has_ball and ball_in_opponent_half:
    nearest_player.sprint_to_ball_carrier()
    teammates.cut_passing_lanes()
```

### Wing Play

**Goal:** Attack down the flanks, cross into the box.

| Aspect | Detail |
|--------|--------|
| Style | Wide positioning, crosses into penalty area |
| Tempo | Medium to fast |
| Risk | Medium — crosses can be intercepted |
| Best When | You have strong headers, opponent is narrow |

**Agent-Behavior Mapping:**
- Wide players: `RUN` along sidelines, stretch the defense
- Use `DRIBBLE` down the wing to create crossing opportunities
- `CROSS` into the penalty box when in advanced wide positions
- Central players: `RUN` into the box to meet crosses, use `HEADER`
- Passing: `SHORT_PASS` to switch play from one wing to the other

```
if wide_player_has_ball and in_crossing_zone:
    cross_to_penalty_box()
    central_players.run_into_box()
```

## Defensive Strategies

### Zonal Defense

**Goal:** Each player defends a specific area, maintain team shape.

| Aspect | Detail |
|--------|--------|
| Style | Area-based, structured |
| Weakness | Gaps between zones if spacing is poor |
| Best When | Default defensive setup, balanced approach |

**Agent-Behavior Mapping:**
- Assign each player a zone (x, y coordinate range)
- Use `STOP` or `WALK` to hold position within assigned zone
- `INTERCEPT` passes that enter your zone
- `TACKLE` only when opponent enters your zone with the ball
- Do NOT chase opponents outside your zone — trust teammates
- Coordination: zones overlap slightly to prevent gaps

```
if ball_in_my_zone:
    move_toward_ball()
    if opponent_has_ball_in_zone:
        tackle()
else:
    hold_zone_position()
```

### Man-to-Man Marking

**Goal:** Each defender tracks a specific opponent closely.

| Aspect | Detail |
|--------|--------|
| Style | Player-based, tight coverage |
| Weakness | Can be pulled out of position by decoy runs |
| Best When | Opponent has a star player to neutralize |

**Agent-Behavior Mapping:**
- Assign each defender a specific opponent player ID
- Use `MARK` action to follow assigned opponent
- Match opponent's movement: if they `RUN`, you `RUN`
- `TACKLE` when your assigned opponent receives the ball
- Stamina risk: high — constant movement mirroring opponent
- Fallback: if stamina drops below threshold, switch to zonal

```
if assigned_opponent_has_ball:
    tackle()
elif assigned_opponent_moving:
    mark(assigned_opponent_id)
    match_opponent_speed()
```

### Compact Defense

**Goal:** Keep all players close together, deny space.

| Aspect | Detail |
|--------|--------|
| Style | Tight formation, narrow shape |
| Weakness | Vulnerable to wide play and crosses |
| Best When | Protecting a lead, opponent plays through the middle |

**Agent-Behavior Mapping:**
- All outfield players stay within a tight radius of the ball
- Use `WALK` to maintain formation — minimize gaps between players
- `INTERCEPT` passes in congested areas (high success rate)
- Do NOT spread wide — sacrifice wing coverage for central density
- Shift the compact block toward the ball side of the field

```
if ball_on_left_side:
    shift_formation_left()
    maintain_tight_spacing()
elif ball_on_right_side:
    shift_formation_right()
    maintain_tight_spacing()
```

### Offside Trap

**Goal:** Catch attackers offside by moving defenders forward together.

| Aspect | Detail |
|--------|--------|
| Style | Synchronized defensive line movement |
| Weakness | Devastating if mistimed — attacker is through on goal |
| Risk | Very high — requires perfect coordination |
| Best When | Opponent relies on through balls, your defenders are fast |

**Agent-Behavior Mapping:**
- All defenders move forward simultaneously on a trigger (e.g., opponent about to pass)
- Use `RUN` forward as a unit just before the pass is made
- Requires awareness of opponent forward positions
- If trap fails: nearest defender must `SPRINT` back immediately
- Timing is everything — too early and opponents adjust, too late and they're onside

```
if opponent_preparing_through_pass:
    all_defenders.run_forward_together()
    if trap_failed:
        nearest_defender.sprint_back()
```

## Tactical Programming Concepts

### Ball Possession Decisions

Your agent must decide what to do with the ball every tick. Use this decision tree:

| Situation | Recommended Action | Reasoning |
|-----------|-------------------|-----------|
| Close to goal, clear shot | `SHOOT` | Best scoring opportunity |
| Under pressure, teammate open | `SHORT_PASS` | Relieve pressure, keep possession |
| Teammate making a run behind defense | `THROUGH_PASS` | Exploit space, create chance |
| Wide position, teammates in box | `CROSS` | Deliver ball to scoring zone |
| No good options, safe area | `DRIBBLE` | Buy time, wait for movement |
| Need to switch play quickly | `LONG_PASS` | Change point of attack |

**Priority order:** Shoot → Through Pass → Short Pass → Cross → Dribble → Long Pass

### Movement Without the Ball

What your agent does without the ball is just as important as what it does with it.

**Making Runs:**
- Move into open space to receive a pass
- Time runs to stay onside
- Agent action: `RUN` or `SPRINT` into space, signal availability

**Creating Space:**
- Pull defenders away to open gaps for teammates
- Make decoy runs in the opposite direction of the intended play
- Agent action: `RUN` away from the ball to drag a marker

**Supporting the Ball Carrier:**
- Position at passing distance from the teammate with the ball
- Form triangles with two other players for multiple passing options
- Agent action: `WALK` or `RUN` to maintain optimal passing distance

### Team Coordination Patterns

**Passing Triangles:**
- Three players form a triangle around the ball carrier
- Ensures at least two passing options at all times
- Rotate positions as the ball moves

**Overlapping Runs:**
- A player runs past the ball carrier on the outside
- Creates a 2v1 situation against the defender
- Effective on the wings

**Switching Play:**
- Pass to the opposite side of the field to exploit space
- Use `LONG_PASS` to switch quickly
- Forces the opponent to shift their defensive shape

### Game-State Awareness

Adapt strategy based on the current match situation:

| Game State | Strategy Adjustment |
|------------|-------------------|
| Winning by 2+ goals | Possession play, conserve stamina, waste time |
| Winning by 1 goal | Balanced, protect lead but stay dangerous |
| Drawing | Look for opportunities, balanced risk |
| Losing by 1 goal | Push higher, take more shots, increase tempo |
| Losing by 2+ goals | High press, maximum aggression, all-out attack |
| Last 30 seconds, winning | All players defend, clear the ball |
| Last 30 seconds, losing | Everyone forward, goalkeeper too if desperate |

```
if score_difference >= 2:
    strategy = "possession_conserve"
elif score_difference == 1:
    strategy = "balanced_protect"
elif score_difference == 0:
    strategy = "balanced_opportunistic"
elif score_difference == -1:
    strategy = "aggressive_push"
else:
    strategy = "all_out_attack"
```

### Stamina Management

Stamina is a finite resource. Poor management means your players slow down in critical moments.

**Sprint Wisely:**
- Reserve `SPRINT` for critical moments: breakaways, last-ditch defense, final minutes
- Use `RUN` for normal movement, `WALK` when not under pressure
- Monitor current stamina — below 30% means significantly reduced speed

**Rotation:**
- Alternate which players press and which recover
- Don't have all players sprinting simultaneously
- Let tired players hold position while fresh players do the running

**Positioning Over Running:**
- Good positioning reduces the need for sprinting
- Anticipate where the ball will go, not where it is now
- Agent logic: calculate optimal position based on ball trajectory and teammate positions

| Stamina Level | Recommended Behavior |
|---------------|---------------------|
| 80-100% | Full intensity, sprint when needed |
| 50-79% | Moderate, prefer RUN over SPRINT |
| 30-49% | Conservative, mostly WALK and RUN |
| Below 30% | Minimal movement, hold position, WALK only |

## Combining Strategies

Effective agents don't use a single strategy — they adapt. Consider a hybrid approach:

1. **Start with possession play** to control the game and read the opponent
2. **Switch to counter-attack** if the opponent presses high
3. **Use high press** when losing and stamina is still high
4. **Fall back to compact defense** when protecting a lead with low stamina
5. **Deploy offside trap** selectively against through-ball-heavy opponents

The best agents read the game state every tick and adjust their strategy dynamically.

## References

- See `content-reference/en/strategies.md` for full detail
