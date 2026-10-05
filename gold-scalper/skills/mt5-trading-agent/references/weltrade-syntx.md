# Weltrade SyntX — Measurements & Patterns

## Probe Pattern (new broker, first session)

Always measure the live account before writing strategy code.

```python
import MetaTrader5 as mt5
mt5.initialize()
acc = mt5.account_info()
print(f"login={acc.login} server={acc.server} balance={acc.balance}")

# Measure every symbol you plan to trade
for sym in mt5.symbols_get():
    tick = mt5.symbol_info_tick(sym.name)
    info = mt5.symbol_info(sym.name)
    spread = (tick.ask - tick.bid) / info.point if tick and info.point > 0 else 0
    print(f"{sym.name:<20} spread={spread:.0f} digits={info.digits} vol_min={info.volume_min} filling={info.filling_mode} tick_val={info.trade_tick_value}")
mt5.shutdown()
```

Critical fields to record:
- `filling_mode`: 1 = IOC, 2 = FOK. **Weltrade SyntX = IOC (1), not FOK.**
- `trade_tick_value`: $0.01 per point per lot for synthetics (not $1.0 like GOLD/XM)
- `point`: 0.01 (digits=2)
- `volume_min`: often 0.01 for FX Vol, 0.1 for PainX/GainX

## Symbol Naming

Weltrade SyntX symbols follow a pattern:
- **FX Vol 10/20/25/40/50/60/75/80/99/100** — forex volatility indices
- **SFX Vol 10/20/25/40/50/60/75/80/99/100** — stock volatility indices
- **PainX/GainX 400/600/800/999/1200** — progression indices
- **SwitchX/BreakX/TrendX 600/1200/1800** — trend indices
- **FlipX 1-5** — flip indices
- **FiboX, PlusX 1, QuadX** — other indices
- **MAX PainX/MAX GainX 1000/2000** — max variants

**Some symbols have bid=ask=0 (no price data) — not tradeable on all accounts.**
Always verify with `mt5.symbol_info_tick()` before assuming a symbol is active.

## Amplitude vs Spread Check (MANDATORY before scalping)

Before deploying any scalping M1 strategy, verify that M1 amplitude exceeds spread.

```python
import numpy as np
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 10080)  # 7 days
amps = np.array([r['high'] - r['low'] for r in rates])
spread_pts = (mt5.symbol_info_tick(symbol).ask - mt5.symbol_info_tick(symbol).bid) / mt5.symbol_info(symbol).point

above_spread = (amps > spread_pts).sum()
print(f"spread={spread_pts:.0f} med_amplitude={np.median(amps):.1f} bars_above_spread={above_spread}/{len(amps)} ({above_spread/len(amps)*100:.1f}%)")

if above_spread == 0:
    print("SCALPING M1 IMPOSSIBLE — no bar exceeds spread")
    # Fallback: check H1
    rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 168)
    amps_h1 = np.array([r['high'] - r['low'] for r in rates_h1])
    above_h1 = (amps_h1 > spread_pts).sum()
    print(f"H1: med={np.median(amps_h1):.1f} above_spread={above_h1}/{len(amps_h1)} ({above_h1/len(amps_h1)*100:.0f}%)")
```

**Weltrade SyntX finding (2026-10-02, 7 days):**
- FX Vol 20/60: 0/10080 M1 bars > spread → scalping impossible; H1 viable (29-32%)
- SFX Vol 20/99: 0/10080 M1 bars > spread; H1 barely viable (1-3%)
- SFX Vol has algorithmic spikes ~30 min — separate danger

## Cost Model (Weltrade SyntX)

```
point_value = tick_value * (tick_size / point)  = 0.01 * (0.01 / 0.01) = 0.01$/point per lot
cost_roundtrip = spread_pts * point_value * lot
```

At lot 0.01: 1 pt = $0.0001 (100x cheaper than GOLD/XM at $0.01/pt).

**Viable symbols on $227 demo account:**
- FX Vol 60 (spread 407, cost $4.07/trade, 1.79% of $227)
- FX Vol 20 (spread 428, cost $4.28/trade, 1.88%)
- SFX Vol 20 (spread 399, cost $3.99, 1.75% — but H1 only 1% bars above spread)
- SFX Vol 99 (spread 87, cost $0.87 — but amplitude 3.4 pts median, no edge)

**TP minimum (15% rule):** TP_min = spread / 0.15
- FX Vol 60: TP_min = 407/0.15 = **2713 pts**
- FX Vol 20: TP_min = 428/0.15 = **2853 pts**

## Spike Protection (SFX Vol)

SFX Vol spikes algorithmically every ~30 min. Amplitude can jump 200-500 pts in 2-3 seconds.

Detection: amplitude > 5×ATR in < 3 bars = spike.
Mitigation: no entry for 3 M1 bars after spike detection.

## EA Attachment Limitation

**MT5 EA attachment cannot be automated programmatically.** The Navigator panel is a dockable internal panel, not a separate window — UIA automation (pywinauto, EnumChildWindows) cannot reliably interact with it.

The user must attach the EA manually:
1. Open chart for the symbol
2. F7 → Navigator → Advisors
3. Find the EA → drag onto chart
4. Check "Allow live trading" → OK

The `.ex5` file must be in `<InstanceID>/MQL5/Experts/` before the EA appears in Navigator.

## Compilation

```bash
cd "%APPDATA%\MetaQuotes\Terminal\<InstanceID>\MQL5\Experts"
MetaEditor64.exe /portable /compile:Name.mq5 /log:Name.log
```

Log is UTF-16: `tr -d '\0' < Name.log`.
Kill existing MetaEditor64 first: `taskkill /F /IM MetaEditor64.exe`.
Verify source after compile: `md5sum` against off-tree backup.
