# Weltrade SyntX — Domain Notes

## Index Types & Algorithmic Behavior

|| Index | Behavior | Edge | Avoid? |
|---|---|---|---|---|
| FX Vol | Fixed volatility X%, trend + reversion | Momentum + mean-reversion | No |
| SFX Vol | FX Vol + spike every ~30 min | Spike prediction + reversal | Spike cooldown required |
| PainX | Goes UP only, drops every 400-1200 ticks | Buy + wait for drop | No |
| GainX | Goes DOWN only, jumps every 400-1200 ticks | Sell + wait for jump | No |
| FlipX | 50/50 each tick, fixed step | **NONE** | Always |
| SwitchX | Alternates PainX/GainX after each jump | Mode-switch prediction | No |
| BreakX | Switches mode when new jump breaches level | Trend-following mode | No |
| TrendX | Detects trend from last 2 jumps | Directional bias | No |
| FiboX | Fibonacci sequence steps | Structurally predictable | No |
| Plus X1 | Linear step growth | Pure trend | Low volatility |

## Spike Detection (SFX Vol)

- Spike = amplitude > 5× ATR in < 3 M1 bars
- Cooldown: no entry for 3 M1 bars after spike
- Emergency: spike > 20× ATR in < 5 seconds → STOP_SYSTEM
- Spike log: `spike_log.csv` with ts, direction, amplitude

## Probe-Before-Trade Workflow

1. Open Weltrade MT5 terminal
2. Run `python tools/probe_account.py`
3. Verify: account login, server, balance, symbol specs, spread, tick_value, filling_mode
4. Update AGENT_SPEC.md section 2 with measured values
5. Verify `bash tools/run_all_checks.sh` passes
6. Only then proceed to ANALYSIS mode

## SL_Mode Code Enforcement

Three modes, enforced in risk_engine.py:
- `PROTECTEUR` (default): SL = 1.5×ATR(M1), breakeven +15pts, trailing +25pts
- `LARGE`: SL = 3.0×ATR(M1), no breakeven, trailing +50pts
- `AUCUN`: **refused by code** — verdict NO_TRADE, never executed in LIVE

The user chooses the mode. System never trades in AUCUN.

## Key Differences: Synthetic vs Real Market

|| Real (GOLD/XM) | Synthetic (Weltrade) |
|---|---|---|
| Driver | Geopolitical/economic | Algorithmic/deterministic |
| Sessions | Open/close weekends | 24/7 |
| Spike | No | Yes (SFX ~30min) |
| Spread | Variable, often < 3 pts | 407-428 pts (FX Vol 60: 407, FX Vol 20: 428) — M1 amplitude NEVER exceeds spread |
| Volatility | 10-30% annual | 20-150% configurable |
| Max leverage | 1:1000 | 1:10000 (system caps 1:100) |

## Frozen Dataclass Pattern

LearningState is a frozen dataclass. To update fields:
```python
from dataclasses import replace
self.state = replace(self.state, field=value)
```
Direct assignment (`self.state.field = value`) raises FrozenInstanceError.

## Probe Results (2026-10-02)

Account 43140285 @ Weltrade-Demo: balance $227.74, leverage 1:10000, filling_mode=1 (IOC).
SyntX symbols available after adding to Market Watch: FX Vol 20 (spread 428 pts), FX Vol 60 (407 pts), SFX Vol 20 (398 pts), SFX Vol 60 (407 pts). SFX Vol 20/60 show bid=ask=0 — not tradeable via API.

## Amplitude & Reachability (7-day measure, Weltrade SyntX)

| Timeframe | Symbol | Bars > spread | Viable |
|---|---|---|---|
| M1 | FX Vol 60 | 0/10080 | NO |
| M1 | FX Vol 20 | 0/10080 | NO |
| H1 | FX Vol 60 | ~30-32% | YES |
| H1 | FX Vol 20 | ~29% | YES |

Scalping M1 is STRUCTURALLY impossible on Weltrade SyntX — the spread exceeds the M1 amplitude on every symbol. Only SWING H1 works.

**TP_min (reachable TP in points):**
- FX Vol 60: 2713 pts (15% of 407-pt spread)
- FX Vol 20: 2853 pts (15% of 428-pt spread)

## EA Attachment (Weltrade)

1. Compile: MetaEditor64.exe /portable /compile:"Name.mq5" /log:"logname.log" in the instance's MQL5\Experts folder
2. Deploy .ex5 to `%APPDATA%\MetaQuotes\Terminal\<InstanceID>\MQL5\Experts\`
3. Restart terminal64.exe — the EA appears in Navigator after restart
4. Attach manually: Navigator → clic droit sur l'EA → Attach to chart

**pywinauto UIA automation for Navigator FAILED on Weltrade**: the Navigateur tree was empty (0 children visible via UIA). The EA became visible after terminal restart + proper deployment to the correct instance folder. Do not rely on UIA for Navigator interaction on Weltrade — manual attach is the reliable path.

## User Preferences (verrouillées)

- Scalping M1 malgré l'impossibilité structurelle → livrer 3 modes (STRICT/IMPOSÉ/RÉALISTE) comme pour XM
- 2 positions simultanées = couloirs par catégorie (1 GOLD + 1 AUTRES), lock cross-engine gsa_slot_lock.json
- Module collecte données sans SL (time-exit 1h = substitut choisi par l'humain)
