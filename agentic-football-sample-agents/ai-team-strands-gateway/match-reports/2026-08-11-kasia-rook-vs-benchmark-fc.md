# Kasia Rook 1–0 The Benchmark FC

- **Recorded:** 2026-08-11
- **Source:** Manually copied tournament match report
- **Verified result:** Kasia Rook won 1–0
- **Strategy baseline:** Aggressive press

## Decisive event

At 1', the Benchmark FC goalkeeper scored an own goal under Kasia Rook's early pressure. This was the only goal and decided the match.

## Team statistics

| Metric | Kasia Rook | The Benchmark FC |
| --- | ---: | ---: |
| Possession | 48% | 52% |
| Shots | 4 | 5 |
| Shots on target | 1 | 0 |
| Commands | 335 | 335 |
| Average latency | 1,007 ms | 973 ms |

## Kasia Rook command mix

| Command | Count |
| --- | ---: |
| Press | 182 |
| Move | 110 |
| Shoot | 16 |
| Pass | 15 |
| Clear | 11 |
| Mark | 1 |

## Kasia Rook role performance

| Role | Average latency | Success rate |
| --- | ---: | ---: |
| GK | 724 ms | 100% |
| DEF | 1,188 ms | 100% |
| MID | 977 ms | 100% |
| FWD1 | 688 ms | 100% |
| FWD2 | 820 ms | 100% |

## Analysis

- The aggressive press was effective: it forced the decisive goalkeeper error and held the opponent to zero shots on target despite lower possession.
- The team should retain its high-press baseline rather than overreact to the possession deficit.
- Kasia Rook took 16 shooting actions for one shot on target, so the next targeted improvement is shot selection, not press intensity.
- DEF was the slowest role; tool calls should be limited to decisions where they change the command.

## Next experiment

Keep the high press unchanged. Require forwards to shoot only when a live-state and `evaluate_shot` assessment indicate a clear chance; otherwise pass or make an attacking run. Compare this change over several matches before adjusting another tactic.

## Original report notes

- MVP: Alessia (FWD)
- Fastest: Alessia (FWD), 688 ms average
- Most tactical: Drew Midway (GK), 67 commands
- Benchmark FC command mix: 164 Move, 85 Press, 31 GK Distribute, 19 Shoot, 16 Pass, 11 Clear, 7 Intercept, 2 Mark
- Benchmark FC coaching note: distribute earlier and reduce repetitive moves to escape Kasia's press.
