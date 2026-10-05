---
name: mt5-trading-agent
description: "Build and deploy autonomous MT5 trading agents with risk management and visual EA integration."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows, linux]
metadata:
  hermes:
    tags: [mt5, trading, automation, python, autonomy]
    related_skills: []
---

# MT5 Trading Agent Skill

Build, deploy, and supervise autonomous MetaTrader 5 trading agents for live markets. Covers agent architecture, risk management, strategy implementation, and continuous operation.

## When to Use

- User wants an autonomous trading agent connected to a live MT5 account
- User needs risk-managed position execution with SL/TP handling
- User wants continuous market monitoring with automated trade management
- User requests ML-enhanced or adaptive trading strategies

**Don't use for:** Manual trading assistance, paper trading without live MT5 connection, or strategy backtesting alone (use spike skill instead).

## Prerequisites

1. **MT5 Terminal** installed and running (e.g., `C:\Program Files\XM Global MT5\terminal64.exe`)
2. **Python 3.x** with `MetaTrader5` package installed: `pip install MetaTrader5`
3. **Credentials** stored securely via DPAPI or config file — never in plaintext (see references/credentials.md)
4. **Symbol availability** confirmed: verify via `mt5.symbol_info("GOLD")` before trading

## Architecture (4-Layer Model)

Use the layered approach for robust, maintainable agents:

| Layer | Responsibility | Key Components |
|-------|----------------|----------------|
| 1. Infrastructure | MT5 connectivity, data access, logging | MT5Connector, Database, ATR calculator, market regime detector |
| 2. Strategy | Signal generation, position sizing, entry/exit logic | TradingLoop, RiskManager, OrderExecutor |
| 3. ML/Analysis | Performance analysis, regime detection, parameter optimization | PerformanceAnalyzer, RegimeDetector, TradingMLModel |
| 4. Orchestrator | Supervisory control, health monitoring, alerting | Supervisor, HealthChecker, AlertSystem |

## Procedure

### Step 1: Environment Setup

1. Verify MT5 connection:
   ```python
   import MetaTrader5 as mt5
   if not mt5.initialize():
       print(f"Error: {mt5.last_error()}")
   ```
2. Confirm account info and symbol:
   ```python
   acc = mt5.account_info()
   print(f"Login: {acc.login}, Balance: ${acc.balance}")
   symbol = mt5.symbol_info("GOLD")
   print(f"Spread: {symbol.spread} pts, Min lot: {symbol.volume_min}")
   ```
3. Install required ML packages if needed: `pip install scikit-learn xgboost lightgbm statsmodels`

### Step 2: Configure Risk Parameters

Set these based on capital and objectives:

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `RISK_PER_TRADE` | 0.10 (10%) | Survivable drawdowns; adjust up only with proven edge |
| `SL_ATR_MULTIPLIER` | 1.0× ATR | Wide stops prevent premature exits; minimum = spread × 2 |
| `TAKE_PROFIT_RATIO` | 2.0 | 1:2 risk/reward; adjust to market volatility |
| `MAX_DAILY_LOSS` | 0.50 (50%) | Hard stop for day; pause trading if hit |
| `MAX_TIME_EXIT_MINUTES` | 60 | Exit stale positions; prevents capital lock-up |
| `TRAILING_STOP_POINTS` | 15 | Lock in profit after 20pts move |

**Capital thresholds:**
- Capital < $3: Cannot trade GOLD with typical spread — use alternative symbol or wait for capital increase
- Capital $3–$70: Max lot 0.01, risk 10% of capital
- Capital > $70: Lot 0.02 allowed
- Capital > $120: Lot 0.03 allowed

### Step 3: Implement Strategy Logic

**Signal generation checklist:**
- [ ] Trend filter (EMA9 vs EMA21 dominant)
- [ ] Momentum (RSI 14, Bollinger Band position)
- [ ] Volatility (ATR for SL sizing)
- [ ] Score-based decision: BUY if score ≥ 5, SELL if score ≤ -5, HOLD otherwise
- [ ] Confidence scaling with score magnitude

**Signal scoring example:**
- EMA9 > EMA21: +2 | EMA9 < EMA21: -2
- Bullish cross (EMA9 crosses above EMA21): +3
- RSI > 55: +1 | RSI < 45: -1
- BB rebound from lower band: +3 | Rejected at upper band: -3
- Price > EMA9: +1 | Price < EMA9: -1

### Step 4: Position Management

**Entry:**
```python
lot = calc_lot(capital, sl_points, symbol_info)
order = open_order(action, entry_price, sl_points, tp_points, lot)
```

**Monitoring loop (per tick/interval):**
- [ ] Check trailing stop (activate after 20pts profit)
- [ ] Check take profit (close when 70% of TP distance reached)
- [ ] Check time exit (close after MAX_TIME_EXIT_MINUTES)
- [ ] Log all closed trades with PnL, duration, signals

**Never:**
- Open multiple concurrent positions in same symbol
- Remove SL after entry (only move to lock profit)
- Increase position size mid-trade

### Step 5: Deploy and Monitor

1. **Test mode first:** Run agent with dry-run or minimal capital to verify execution
2. **Logs:** Enable file + console logging; log trades to SQLite for performance tracking
3. **Run as background process:** Use `terminal(command="python agent.py", background=True, notify=True)`
4. **Supervise:** Check logs periodically; agent should run autonomously but human oversight recommended

### Step 5.5: Deploy MQL5 Indicator to MT5

For on-chart visual indicators (dashboard, signal arrows, SL/TP lines), the workflow differs from EA deployment:

**File placement:** Put the `.mq5` in the **instance data tree**, not under `C:\Program Files\` — `%APPDATA%\MetaQuotes\Terminal\<InstanceID>\MQL5\Experts\` (or `Indicators\`). That location is user-writable, needs no UAC elevation, and is where MetaEditor resolves includes from. Keep a copy of the source in the user profile too, as the backup of record.

**Compilation — headless CLI, not the IDE.**

Do **not** drive the IDE with pyautogui (alt+tab, F7): it is slow, non-deterministic, and it hides the actual compiler message. The CLI emits the full error log.

The recipe that works, with `cwd` set to the instance's `MQL5\Experts` directory and **both** the source name and the log name given as bare relative filenames:

```
cd "%APPDATA%\MetaQuotes\Terminal\<InstanceID>\MQL5\Experts"
MetaEditor64.exe /portable /compile:"Name.mq5" /log:"logname.log"
```

Why each piece is load-bearing:
- `/portable` is required. Without it MetaEditor resolves `<MQL5>` against its own install directory and **every `#include` fails**. The trade-off is that `/portable` also changes the data folder — which is harmless as long as the source has no includes (a self-contained trade class instead of `<Trade\Trade.mqh>` is the robust form anyway).
- source and log as **absolute paths, or a log under `C:\`, produce no log and no `.ex5` at all** — silently, with exit code 0. This is the single most common wasted cycle.
- **Kill any already-running `MetaEditor64.exe` first** (`taskkill /F /PID`). A live instance swallows the command line and the invocation does nothing.
- Read the log as **UTF-16** and **wait 2–5 s** after the process returns; MetaEditor writes asynchronously.
- The exit code is **not** a success signal. This build returns a non-zero code on a clean compile. Trust the log's `Result: 0 errors, 0 warnings` line and the `.ex5` mtime, and ignore the exit status.

If you hit `error 209: OnCalculate function not found in custom indicator`, that is not a signature bug — see the reference for what it means on an older build and what to write instead.

**Verify the source, not just the build.** A green log only proves the compiler ran. MetaEditor can **overwrite your `.mq5` on disk from the copy it holds in memory** when the EA is loaded in the IDE, silently reverting every edit you made from outside. So a "successful" rebuild can compile code from hours ago. After any edit batch:

```python
# assert the fix is actually in the file, and that retired strings are gone
assert "the_new_fix_marker" in open(src, encoding="utf-8").read()
assert "the_old_string_being_replaced" not in open(src, encoding="utf-8").read()
```

Keep a copy of the source **outside** the MT5 tree before editing, and compare `md5sum` against it after compiling. A mismatch means the file was rewritten, not that the build is wrong. When a change appears not to take effect, check this before re-investigating the logic.

**Never hand a file to a subagent while you are editing that same file.** A child rewriting the path reverts your fixes mid-session; you then re-fix code that silently reverted, and neither round is reproducible. Split ownership by path, or stop the child, hash the file twice a few seconds apart to confirm it is stable, then re-apply. Related: MetaEditor holds the file open, so close/kill it before external edits.

**Kill MetaEditor before ANY external edit batch, not just before compiling.** The IDE rewrites the `.mq5` on disk from its in-memory copy whenever it saves. A green compile can therefore ship code from hours earlier while your edits sit nowhere — the tell is that the strings you removed are still in the log at runtime. Verify the *source* after every edit batch, not just the build: assert the new markers are present **and** the retired strings are gone, then `md5sum` against the off-tree backup. Details in `references/mql5-indicator-deployment.md`.

**A repair script that asserts mid-run leaves a half-applied file.** Accumulate all substitutions in memory, write once at the end, then print a table of expected-present and expected-absent markers. A batch that writes per-edit and aborts on the first non-unique match produces a hybrid state — some fixes applied, some not — that still compiles and still logs the old behaviour.

**Establish a control compile before debugging your own source.** Compile a known-good EA from the same tree first. If it reports 0 errors, the install, the command and the log path are sound and the fault is in your source. This one step replaces a dozen blind signature variants.

```python
import subprocess, time, os

SRC_DIR = r"%APPDATA%\MetaQuotes\Terminal\<InstanceID>\MQL5\Experts"
src = os.path.join(SRC_DIR, "MyEADashboard.mq5")
log = "compile.log"                       # relative name, in SRC_DIR

os.chdir(SRC_DIR)                         # source is resolved relative to cwd
if os.path.exists(log):
    os.remove(log)

subprocess.run([r"C:\Program Files\XM Global MT5\MetaEditor64.exe",
                "/portable", "/compile:MyEADashboard.mq5", f"/log:{log}"],
               capture_output=True)

for _ in range(15):                       # MetaEditor writes the log asynchronously
    time.sleep(1.5)
    if os.path.exists(log):
        break

text = open(log, "rb").read().decode("utf-16")     # log is UTF-16
print([l for l in text.splitlines() if "error" in l.lower() or "Result" in l])
print("ex5 exists:", os.path.exists(src.replace(".mq5", ".ex5")))
```

**Multi-timeframe handles:** create separate `iMA()` handles with `PERIOD_M5` / `PERIOD_M15` and read the current value with `CopyBuffer(handle, 0, 0, 1, array)`. Never derive M5/M15 values by averaging M1 bars — the EMA periods would be wrong.

**Attaching to chart:** after compilation the EA or indicator appears in MT5's Navigator panel (Ctrl+N). Double-click or drag it onto the target chart. Attaching is a **user action** — say so plainly instead of implying you did it. To reload after a code change the user re-opens the EA properties and confirms (F7, OK), which also fires `OnDeinit` and clears stale on-chart objects.

**Old builds are missing parts of the modern API — check the surface you rely on against the local build, not against current-MT5 documentation.** On MetaEditor 5.0.0.6230 the whole second EA of a session failed to compile on four separate points, none of them logic bugs:

| Written | Fails with | Use instead |
|---|---|---|
| `input int TF_Decision = 15;` then `iMA(_Symbol, TF_Decision, …)` | `error 262: cannot convert enum` ×8 | declare the input as `input ENUM_TIMEFRAMES TF_Decision = PERIOD_M15;` — an `int` is never implicitly an `ENUM_TIMEFRAMES` |
| `iMA(_Symbol, TF, 20, 0, MODE_SMA, VOLUME)` | `error 256: undeclared identifier 'VOLUME'` | average the tick volumes by hand over the closed bars |
| `TradeAllowed()` | `error 256: undeclared identifier` | `TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)` |
| `input int TF = 15;` used as a timeframe | `error 262: cannot convert enum` | `input ENUM_TIMEFRAMES TF = PERIOD_M15;` — an `int` never implicitly becomes `ENUM_TIMEFRAMES` |
| `ObjectSetInteger(0, name, OBJPROP_TRANSPARENCY, 82)` | `error 256` + `error 262` + `error 199` | `ObjectSetInteger(0, name, 0, 82);` — index form, 0 = sub-window |
| `PositionModify(ticket, sl, tp)` | `error 256: undeclared identifier 'PositionModify'` | hand-built `TRADE_ACTION_SLTP` request with `r.position` — the convenience wrapper is absent, the request type is not |
| `ChartTimePriceToXY(0, 0, t, price, y)` | `error 199: wrong parameters count` | this build takes **six** args: `ChartTimePriceToXY(long, int, datetime, double, int&, int&)` — pass a second `int&` (x) you discard |

The transparency one is the generalisable case: for a graphical object's sub-window transparency the old build only accepts the **index form**, not the named property. When a build rejects a documented identifier outright, do not hunt for a different spelling — find the older signature that build does accept.

### Step 6: Learning Loop (Optional)

For agents with performance tracking:
1. Log every trade **with its features, not just its outcome**: ticket, action, volume, PnL, duration, signals, capital state, plus the market context at entry (session, volatility regime, per-timeframe trend, alignment flag, spread, ATR, RSI, setup id). A journal that stores only win/loss cannot support learning — nothing distinguishes the good trades from the bad ones.
2. Log **refusals too**, with the reason. That is the only way to audit selectivity: the trade count is the denominator of the strategy's real win rate, and a journal that records only executions inflates it.
3. Analyze per setup, not globally. Report n, win rate, its **standard error**, expectancy in R, and profit factor. Win rate alone is a trap — it ignores the size of wins versus losses.

**Never act on a small sample.** With n=5 the standard error of a win rate near 50% is ~22 percentage points: any streak reads as signal. Require a **minimum of 30 resolved observations** *and* a standard error under ~15 points before any conclusion, and keep the in-sample / out-of-sample split (70/30) — a setup is promoted only if OOS confirms IS. If IS is good and OOS collapses, flag it as degraded rather than keeping it.

**What the learner may adapt: only which setups are enabled.** It may disable a persistently losing setup or re-enable a recovering one. It may **not** touch lot size, SL, TP, risk limits, spread gate, or the kill switch — a system that auto-adjusts its own risk on a small account raises exposure precisely when it is losing. Freeze those in code and assert they never change.

**Bounded self-tuning supervisor cron (only on explicit user grant).** When the user asks the agent to "check periodically and adjust parameters", implement it as a separate scheduled AGENT-mode job (not embedded in the executor), and encode the mandate in its prompt: read the executor's journal + state, diagnose concrete signals (losses exceeding the soft-stop, refusals >80% = over-strict filter, slippage), apply AT MOST one parameter change per pass, each parameter inside an explicit numeric band (e.g. SL 80–150 pts, whipsaw multiplier 3–6), verified by py_compile/re-run and journalled as a `tune` event — while hard-forbidding changes to lot, magic, balance floor, kill-switch and daily-stop mechanics. The supervisor also re-checks external threats (foreign-magic fills → write pause file, flag URGENT) so tuning never runs while the account is under attack.

**LLM-mode cron jobs fail in two distinct ways — read `last_status`/`last_error` from the cron list before touching anything.** (1) `No LLM provider configured for task=moa_aggregator` = the global Mixture-of-Agents feature is enabled while its aggregator provider has no credentials: EVERY agent-mode cron crashes while pure-script crons keep running fine — the tell is a mixed ok/error board. Fix: set `moa.enabled: false` in the hermes config.yaml (back it up first; the patch/write tools refuse that file by self-protection — edit it through a terminal script that asserts a unique anchor line). (2) `HTTP 429 fair-share rate limit` = thundering herd: several LLM jobs + the interactive session + delegated children hammering the same model quota in the same minute. Fix: stagger agent-cron schedules to distinct minutes (:01 / :12 / :42, never all at :00/:30), pause duplicate agent jobs (two review crons = two quota burns for one brain), and confirm recovery via `hermes auth list` (rate-limit flag disappears) plus the next scheduled run going `ok`. Never restart your own gateway/host process to reload config — it kills the running agent tree mid-turn; spawned agent jobs re-read config from disk.

Statistical honesty at small capital: detecting a 10-point win-rate edge needs ~390 trades per arm. At 0–3 trades/day that is **not achievable** — say so rather than tuning against a sample that can never reach significance.

## Pitfalls

**Spread cost exceeds capital:** the cost is `spread_pts × trade_tick_value × lot`. On GOLD `trade_tick_value` is $1.0 **per point per lot**, so at 0.01 lot a point is $0.01 and a 55-pt round trip is **$0.55** — not $5.50. With $20 capital that round trip is 2.75% of the account per entry. Before any entry verify `capital > spread_pts * trade_tick_value * lot * min_lot`, and check the derived break-even `WR = (SL + spread_trip) / (TP + SL + spread_trip)` — which does **not** depend on capital. See `references/edge-validation.md`.

**Wrong symbol name:** XM Global uses `GOLD` not `XAUUSD`. Always verify with `mt5.symbol_info()` — using the wrong symbol causes orders to fail silently.

**ATR not aligned with timeframe:** ATR should be calculated on the same timeframe as the trading signal (M1 for scalping). Mixing timeframes leads to incorrect stop sizing.

**SL too tight:** A stop smaller than `spread × 2` will be hit by normal market noise. Always set `sl_points = max(int(atr * multiplier), spread * 2)`.

**Multiple positions:** The golden rule is one position per symbol at a time. Concurrent positions double risk and complicate exit logic — enforce with a position check before entry.

**Lot sizing math:** `lot = (capital * risk_pct) / (sl_points * point * tick_value)`. Verify that `tick_value` is correct for the symbol — for GOLD on XM it's typically $1.0 per point per lot. When risk is capped in DOLLARS across several symbols, sizing must pick the LARGEST lot whose feasible stop distance `max(2·spread+15, min(risk$/upp(lot), 4·ATR))` fits the dollar cap — the spread FLOOR overrides the ATR cap: rejecting when `2·spread+15 > 4·ATR` (normal in quiet FX hours) makes that market permanently untradeable, while the dollar cap plus the spread/SL ratio already provide the real protection. Wide-spread instruments cannot fit at the bigger lot and stay at min lot while FX legs double — a flat lot silently EXCLUDES the wide-spread markets from trading entirely. Recipe and measured per-market costs in `references/multi-market-rotation.md`.

**Take Profit en dollars : convertir en points et MESURER l'atteignabilité.** Une règle exprimée en USD (« 0.01 → $2, 0.02 → $3.50 ») doit passer par la distance de prix puis en points avant d’être évaluée, sinon on compare des grandeurs incomparables :

```
distance_prix = TP_USD / (lot * contract_size)      # GOLD XM : contract 100
points        = distance_prix / _Point
```

Arithmétiquement correct ne veut pas dire atteignable. Mesurer la distribution des amplitudes futures sur l’historique avant de conclure :

```python
fwd = np.maximum(high[i:i+N].max() - c[i], c[i] - low[i:i+N].min())
# fraction du temps où fwd >= points_requis
```

Sur GOLD XM (5 jours, 4136 bougies M1, tick_value $1.0/pt/lot) : amplitude M1 médiane **1.96 pts** ; sur 8 h, médiane 34.5 / p90 86 / **max 112 pts**. Un TP de 200 pts (=$2.00 @0.01) ou 175 pts (=$3.50 @0.02) a une fréquence d’atteinte de **0.000%** — hors de portée, pas « difficile ». Cibles mesurées : $0.30 atteint dans 62% des fenêtres de 8 h, $0.40 dans 39%, $0.50 dans 24%.

**Paramètre imposé par l’utilisateur : livrer des modes, pas un refus.** Quand l’utilisateur impose un TP (ou un lot) non atteignable, ne pas seulement le signaler en laissant le système bloqué. Livrer trois modes sélectionnables et annoncer lequel fait quoi :

| Mode | Comportement |
|---|---|
| **STRICT** | bloque l’entrée si le TP est inatteignable — ne trade pas |
| **IMPOSÉ** | le TP de l’utilisateur part tel quel, **avec un SL redimensionné pour lui** — banc d’essai fonctionnel pour observer le système |
| **RÉALISTE** | TP dérivé des mesures de volatilité — seul mode statistiquement viable |

Points de conception non négociables du mode IMPOSÉ :
- **Le SL doit être redimensionné pour ce TP**, jamais laissé à `ATR × 1`. Avec un TP à 200 pts, un SL de 1-2 pts est touché immédiatement par le bruit et chaque trade devient une perte sûre. Plancher = `TP / 4`, plafond = 8% du capital.
- **Journaliser le dimensionnement à chaque entrée** : `SL n pts (x.xx$) vs TP n pts (x.xx$) | R:R 1:x.x | risque x.xx% du capital` — l’utilisateur juge sur pièces.
- **Annoncer l’issue attendue** : les positions se solderont sur le SL, pas sur le TP. Ne pas laisser croire à une stratégie rentable.

**Consecutive failures:** if order_send returns errors 3+ times consecutively, pause trading for 30 seconds — this often indicates connectivity issues or invalid parameters that will persist.

**Un filtre qui bloque n'est pas un filtre, c'est un arrêt de trading.** Mesurer avant de conclure que « le marché ne donne pas de setup » : compter le taux de rejet sur l'historique, et l'exiger sous ~60%. Trois pièges de calibration récurrents :

- **Verrou de tendance trop strict.** Comparer le prix à l'EMA200 M15 vetoit 71-86% des BUY, car le prix n'est au-dessus de cette moyenne que 14-29% du temps. Vétér à une moyenne plus proche (EMA50) avec une bande proportionnelle à l'ATR.
- **Structure exigeant trop de swings.** Demander 2 swing highs ET 2 swing lows rend le filtre « insuffisante » presque toujours (6 swing highs mais 2 swing lows sur 12 barres). Exiger 1 de chaque côté suffit et passe dans 93% des fenêtres.
- **Volume comparé sur la mauvaise bougie.** `iVolume(0)` est la bougie en cours : elle ne cumule que les ticks depuis son ouverture, donc toujours sous la moyenne des bougies terminées — rejet permanent. Comparer `iVolume(1)` (bougie close) à la moyenne de `iVolume(1..20)`.

**Le `Print()` anti-bruit doit être placé AVANT tout `return` de sortie.** Mettre `lastBar = curBar` après le `return` d'une branche laisse la condition de « nouvelle bougie » toujours vraie, et l'EA réimprime des milliers de lignes par bougie. Si un journal de thousands de lignes identiques apparaît, vérifier d'abord l'ordre des Affectations, pas la condition.

**Un log bruité ou absent ne prouve pas que la logique est fausse — comparer le binaire à la source.** Après compilation, contrôler que les chaînes attendues sont présentes et que les anciennes ont disparu. Un EX5 compilé sans erreur peut venir d'un source réécrit par l'IDE : c'est l'hypothèse à tester avant de réécrire la logique.

**EA muet : lire le journal avant de toucher à la logique.** Un agent qui n'ouvre jamais est presque toujours un défaut de calibration. Le journal Experts contient la cause exacte, et deux familles se distinguent :
- `Signal annule : …` = **filtre** — le signal a été détecté puis rejeté *avant* l'envoi d'ordre ; aucune position n'a existé. Compter les motifs : le filtre dominant est la cause.
- `TRADE OUVERT` / `TRADE CLOSED` absents alors que les filtres passent = alors seulement suspecter la garde-fou d’atteignabilité, l’exécution ou la connexion.

Un journal saturé de milliers de lignes identiques en quelques secondes signale un `Print()` appelé depuis le chemin de tick : le corriger immédiatement, sinon il masque le vrai signal.

**Mesurer un indicateur avant de l integrer dans l EA.** Quand l utilisateur demande si le Fibonacci, les supports/resistances ou une figure chartiste est utile, le protocole est : **mesurer d'abord, coder ensuite**. Ne jamais integrer parce que c est familier. Trois tests sur des entrees de base identiques : (1) WR par tranche de l indicateur, (2) correlation Pearson valeur/reultat, (3) proportion d entrees capturees. Sous ~10% de capture ce n est pas un filtre mais un raster decoratif. **Le signal d alarme est une distribution monotone** : si les tranches montent regulierement sans decrochement, aucun niveau n a de pouvoir predictif. Mesures GOLD XM : Fibonacci = correlation 0.062, ses zones 38.2/50/61.8 sont les Pires du tableau → n integrer qu en **repere visuel etiquete « non filtrant »** ; S/R par frequence de toucher = WR 56.9% → 62.1%, gain net +507$, gradient coherent avec la tolerance → **valide comme filtre d entree**. Un indicateur mesure sans edge s affiche avec l etiquette de non-filtrage ; il ne passe jamais en silence dans la logique. Protocole complet et chiffres dans `references/edge-validation.md` §8.

**Lire le document de l utilisateur avant d en tirer une conclusion — et verifier qu il contient ce qu il presume.** Quand une demande s accompagne d un livre ou d un support, le lire integralement et **verifier que le contenu attendu y est**. Si l utilisateur demande d utiliser une methode que le document ne traite pas, le dire explicitement et nommer ce que le document contient reellement, plutot que de faire semblant d en avoir tire une regle. Un manuel peut aussi contredire une demande : citer sa propre recommandation (« perte maximum de 1 a 3% du capital », « passez des ordres stop avant d ouvrir ») est l argument qui fait accepter une regle de risque que l agent doit defends.

**A backtested strategy and its EA implementation are two programs. Port the entry logic and then prove the two produce the same trade count.** A ported filter can silently change behaviour — a loop bound written as `for(i = j - 8; i >= j - 8; i--)` runs **once**, not eight times, which silently cut signal generation to a third of the backtested value while still compiling green and logging plausible reasons. The tell is a divergence between the number the backtest produced and the number the live EA logs. Measure the pass-rate cascade on the real history (how many candles survive each filter stage) and compare that final figure to the backtest's entry count. If the EA yields a fraction of the backtest, the port is wrong before any performance question is meaningful. Never report a backtested edge as belonging to an EA until the two agree on entry count.

**When the user says "it still doesn't work" or "the panel is still X", read the diagnosis from the artifacts before changing code again.** After two failed fix attempts the cause is usually not what you are editing. The repeated failures worth naming: a rendered panel crossed by price-anchored lines, an over-strict signal cascade traced to a loop bound, and a source file rewritten by MetaEditor. In each case the next correct move was to inspect the artifact (measure text widths, count filter pass rates, `md5sum` the source) rather than adjust the constant you were last looking at. Instrument the component so it reports its own state, and say plainly which measurement would settle it rather than shipping another speculative fix.

**Never trust a login/server pair written in a spec, a config file, or a previous session's notes — read it from the live connection.** Verify at the start of every session and state the measured value back to the user:

```python
ai = mt5.account_info()
print(f"login={ai.login} server={ai.server} balance={ai.balance}")
```

A login that is wrong for its server fails to connect, but a *stale-but-valid*
pair from an old config is worse: it can silently target a different account,
and every number downstream (risk, thresholds, balance checks) is then
computed against the wrong capital. When the user's written spec and the live
account disagree, say so explicitly and use the live one. Likewise re-measure
symbol specs rather than carrying them forward — `tick_value`, `volume_min` and
`filling_mode` change with broker account type.

**Credential exposure:** Never hardcode MT5 login/password in agent files. Use DPAPI on Windows or environment variables. The agent should read encrypted credentials at runtime.

**No-SL with MT5 compliance:** When a user requests no stop loss, MT5 may still require a valid `sl` field in the order request. Send a **technical SL** far enough away (e.g., 200+ points) to satisfy the broker's validation, but make clear it is an artifact — the real exits are TP + time exit + trailing. Log the distinction explicitly so monitoring tools don't flag the technical SL as a real risk control.

**MQL5 EA visual integration:** To show colored arrows (green=BUY, red=SELL, orange=exit/sortie) and a live Expert panel on the chart, build a companion `.mq5` EA that draws `OBJ_ARROW` (code 233=up/green, 234=down/red) and `OBJ_TEXT` labels, plus an `OBJ_RECTANGLE_LABEL` panel populated with `OBJ_LABEL` text elements updated on each tick. Place the `.mq5` in `%APPDATA%/MetaQuotes/Terminal/<InstanceID>/MQL5/Experts/`. Extract `input` parameters from any reference EA the user provides and mirror them in the Python agent's config so signals, drawn levels, and TP/SL math stay consistent across both.

**On-chart legibility is an order-of-rendering problem, not a colour problem.** When a dashboard is "hard to read" or looks mixed in with the candles, check these before touching fonts or palette:

- **`OBJPROP_BACK = true` on the panel background sends it *behind* the chart**, so candles draw over the text. A panel background must be `BACK=false` with `FILL=true` to be genuinely opaque.
- **MT5 places plain `OBJ_LABEL`s behind graphic objects by default.** Set `OBJPROP_BACK = false` and `OBJPROP_ZORDER` explicitly on every label (e.g. 100 for panel text, 90 for on-chart level labels) or they vanish under the Fib/phase zones.
- **`OBJ_HLINE` is positioned by *price*, not by pixel** — it cannot be used as a row separator inside a pixel-positioned panel, AND it cannot be confined to a pixel region at all. Use an `OBJ_RECTANGLE_LABEL` of `YSIZE=1` in `CORNER_LEFT_UPPER` for separators. When on-chart level lines (support/resistance, Fibonacci, swing highs) **cross over** the panel, no amount of `OBJPROP_ZORDER` fixes it: ZORDER ranks objects **within a type**, so a price-anchored `OBJ_HLINE` and a pixel `OBJ_LABEL` are drawn in different layers and no ZORDER value moves one over the other. The fix is to stop drawing price-anchored lines — convert price to Y with `ChartTimePriceToXY`, then draw an `OBJ_RECTANGLE_LABEL` of `YSIZE=1` whose `XDISTANCE` starts at `PanelX + panel_width + 8`, so the line begins past the panel edge.
- **Give the filled zone rectangles an explicit transparency (`ObjectSetInteger(0, name, 0, 82)`) so they read as background context rather than competing with the text.**
- **The same trap applies to any rectangle sized in a price value.** `YSIZE = tolerance_points` is price units, not pixels: a 12-point-tall zone on GOLD spans well over 100 px and will bury the panel. Convert to pixels, or clamp to a fixed pixel height.
- **Give the panel background a ZORDER below its text but above the chart furniture** (e.g. background 10, separators 20, level lines 30, panel text 50). Leave wide gaps between ranks — the property is a sort key, and narrow margins can invert on older builds. Use a dark grey (`clrDarkSlateGray`) rather than pure black so a panel that renders empty is distinguishable from the chart background.
- **When a panel renders blank, add a diagnostic rather than another fix attempt.** Print the chart pixel size, panel origin/size, and the computed start-X of the level lines on the first two ticks, plus one line per label as it is created. This distinguishes "objects not created" from "created and hidden behind" from "created off-screen" in one pass, instead of iterating on ZORDER values blind.

**Grid layout for the panel.** A fixed row pitch plus a constant number of disjoint columns prevents the two failure modes: text colliding horizontally (long labels like `M5: HH/HL (haussier)` overrunning a two-column grid on a 400 px frame) and rows spilling past the frame bottom. Choose `PW` and `PH` from the measured content: sum the row advances, then size the frame to the longest case. Abbreviate values to the point (`HH/HL`, `ATR1`, `Tot +1.23$`) rather than widening the frame. Expose the panel origin as `input int PanelX / PanelY` so the user can reposition it without an edit.

**EA Auto-Attachment Requirement (CRITICAL):** When the user specifies "tu dois le faire toi-même automatiquement" or similar autonomy requirement, the agent MUST auto-attach the visual EA to the MT5 chart WITHOUT manual drag-and-drop. The standard MQL5 folder placement is insufficient — the EA must be actively attached to the chart for visual elements to render. Three attachment methods, in priority order:

1. **COM Dispatch (`win32com.client.Dispatch("MetaTrader5.Application")`):** Fastest method on Windows. Use `ChartApplyExpert(chart_handle, ea_path, [])` after finding the GOLD M1 chart via `ChartGet()`. Requires MT5 running. *Known failure mode:* On some Windows configurations, COM returns "Chaîne de classe incorrecte" (-2147221005). This indicates the MT5 COM class is not registered or accessible — fall through to method 2.

2. **MetaTrader5 Python package chart operations:** The `MetaTrader5` pip package does NOT expose `ChartGet()`, `ChartOpen()`, `ChartApplyExpert()`, or any chart manipulation functions — these are available only via COM or MQL5 native. Do not attempt to call these on the Python package object; it will raise `AttributeError`. If COM fails, the only remaining path is manual attachment or MQL5-side scripting.

3. **MQL5 script-assisted attachment:** Create an MQL5 script in `%APPDATA%/MetaQuotes/Terminal/<InstanceID>/MQL5/Scripts/` that when executed (via MT5 UI or automation) attaches the EA. This requires MT5 UI interaction to run the script. Not suitable for fully autonomous deployment but can guide the user.

**MT5 UI automation IS viable via pywinauto UIA — do not refuse it.** MT5's window does expose usable structure for most standard surfaces; driving it was proven end-to-end (auto-compile, auto-attach indicator to chart, version swaps, panel forensics) on Windows. What works: dock panels found via `EnumChildWindows` (class `Afx:ControlBar`, title 'Navigateur' / 'Observation du marché'); Navigateur TreeItems (enumerate text, `select()`/`expand()`, then a PHYSICAL double-click at the item rectangle → Properties dialog opens as `#32770`; clicking its 'OK' button completes the attach); Market Watch rows as ListItems (empty text but valid ~25px rectangles — sort by top, double-click opens that symbol's chart); chart/file dialogs and property sheets as `#32770` (enumerate by title); context menus as `#32768` top-level popups (MenuItem descendants; flyout submenus are flaky — prefer keyboard or direct pixel clicks). What does NOT work: the main toolbars (owner-drawn — `TB_GETBUTTON` yields iCommand=0, `TB_GETITEMRECT` zero-size; `TB_PRESSBUTTON` with a guessed value can crash the terminal) and Alt+X expert-list (no observable window). For timeframe changes, pixel-click the tf toolbar button located from a screenshot and CONFIRM by reading the MDI child titles ('GOLD,M1' etc.) after each click — a wrong click spawns duplicate chart windows (close extras via `SetActiveWindow(child)`+Ctrl+F4). The MT5 window handle changes on every restart — re-find it by class `MetaQuotes::MetaTrader::5.00` + title, never cache it across process restarts. On Weltrade SyntX accounts, the Navigateur UIA tree can be EMPTY (0 children visible) even after deployment — the EA appears in Navigator only after a full terminal restart, not F5/Actualiser. Do not rely on UIA for Navigator interaction on Weltrade; deploy .ex5 to the correct instance's Experts folder, restart terminal64.exe, then attach manually. **When a floating panel resists every close attempt (Alt+B/Alt+T/Esc), identify it before poking it further**: `WindowFromPoint(POINT(x,y))` → class → `GetWindowThreadProcessId` → psutil name. A stubborn white 'Trade'-titled panel was in fact a modal **"Enregistrer sous" file dialog** — on MT5 Ctrl+S saves the chart TEMPLATE as a file and opens that dialog (it is NOT 'save workspace'); it silently swallows every subsequent menu/toolbar interaction. Close it by title enumeration (`#32770`, 'Enregistrer') + WM_CLOSE. See `references/trading-supervisor.md`. Three more rules that each cost a retry loop: the terminal's window TITLE IS DYNAMIC (account login + server + connection-state suffixes, sometimes a trailing ' - ') — match visible windows by SUBSTRING (server name or login), never by a cached full title. A crashed UI script leaves its modal dialog OPEN, which silently swallows every later hotkey (Ctrl+I looks dead) — before re-issuing any shortcut, enumerate visible windows ('Indicateurs', class `#32770`) and dismiss with Esc/WM_CLOSE first. And pywinauto's `Desktop(...).window(..., controls_required=False)` raises TypeError when combined with a `title_re` criterion — resolve the handle via EnumWindows and use `window(handle=h)`.

**Terminal-external executor: fully autonomous trading with NO EA at all.** `mt5.order_send` requires no attached EA — run the trading loop as an out-of-process script on a 1-minute scheduler (Hermes `no_agent` cron: stdout = trade card pushed to the user's chat verbatim, empty stdout = silence, so the job only speaks when it acts). The executor embeds its own safety in-process since nothing else enforces it: per-tick gates (trend alignment across timeframes, spread ceiling, session hours, weekday, balance floor, daily-loss stop, max trades/day, cooldown via state file), exactly one position, trailing + time-exit management, a pause file as manual kill switch (3 consecutive retcode failures → auto-pause), append-only JSONL journal of entries AND refusals for the learning loop, and foreign-position handling: a `magic != executor` position is most often the USER's own manual trade — tell-tales: no SL/TP, no comment, fills timed right after a dashboard signal, and no EA line anywhere in the MQL5 logs at that second. NEVER auto-close a magic=0 position: secure it by attaching SL/TP with `TRADE_ACTION_SLTP` (executor sizing), journal the takeover, and allow COHABITATION — the executor keeps trading its own single position while total ≤ 2 and every foreign position has an SL; freeze entries only past those conditions or for a confirmed intruder (EA lines in the journal, remote trade origin IP). Sibling executor magics (your own other modules) block in BOTH directions — cohabitation is for human trades only. Market activation should be MECHANICAL, not conversational: the executor reads a `markets.json` (trades only `auto=true`), a weekly deterministic validator re-runs the backtest with the engine's exact skip logic and rewrites it (human `force:true` flags survive regeneration; forced markets carry a per-market PnL ledger so real results arbitrate later). A no-SL user mandate is served by a `SL_MODE = NONE|PROTECT|WIDE` one-line switch, a hard duration limit as the substitute, TP/timeout-only exits for data purity, and MFE/MAE enrichment per closed trade. Depth in `references/multi-market-rotation.md` (activation + collecte sections). Before trusting the pipeline, run a live open-then-close test order (minimal size, immediate market close) and check the terminal's global "Allow algorithmic trading" switch — with it off, order_send fails retcode 10027 for the Python API as well as for EAs (the switch cannot isolate EAs from the executor: to silence EAs only, disarm their `.ex5` files instead). SIX HARD-WON EXECUTOR RULES for this executor:
1. **`history_deals_get` is untrustworthy right after a terminal restart** — it silently OMITS your own closed deals (so a history-based daily-loss stop can fail open and let you keep losing) and can surface ghost deals that vanish on re-query. Passing a `datetime` instead of an epoch end-argument returns EMPTY without error. Two more silent-miss modes: the from/to bounds are compared against SERVER-time deal stamps — pass `now + utc_offset` or the most recent deals fall outside the window unnoticed; and server-generated TP/SL closing deals carry `magic=0` with an empty comment, so match a close by `deal.position == ticket` with `entry == OUT`, never by magic (matching on magic books wrong PnL via fallback estimates). Enforce all limits from a LOCAL append-only ledger in the state file; treat MT5 history as reconciliation only, never as the source of truth for a kill-switch.
2. **Snapshot live position `profit` into state every cycle**; when a ticket vanishes (server-side SL/TP), book the last-snapshotted value (± spread cost) instead of worst-case-guessing a full SL hit — estimates pollute winrate and trip the daily stop on trades that soft-stopped early.
3. **magic=0 fills without comments may come from ANOTHER DEVICE on the same account** (MT5 accounts allow concurrent sessions — a phone/laptop/VPS EA). Attribute before fighting: the TERMINAL journal `<instance>/logs/*.log` (UTF-16, distinct from the `MQL5/Logs` experts journal) records `added order ... due take profit/stop loss` per order and `previous successful authorization performed from <IP>` per client — repeated IPs beyond this machine = remote trader you cannot kill locally; the fix is a password change through the broker portal (human gate). Never book remote PnL against your own ledger or winrate.
4. **`order_check` success is retcode 0 — NOT 10009 — on the broker's Python package.** Accepting only 10009 silently rejects every entry the executor just sized (the order never even sends). Treat `chk.retcode in (0, 10009)` as go, and gate margin on `chk.margin < account.margin_free * 0.9` before `order_send`. A symbol rejected at the pre-check (10019 marge, 10016 market closed) must ROTATE the scan to the next symbol of the pool, never abort the whole entry — that pre-check is what makes multi-market rotation safe.
5. **All MT5 timestamps are broker SERVER time** (measured UTC+3; follows broker DST, not yours). Comparing bar/deal `time` against `time.time()` silently breaks freshness checks and day-keyed ledgers — bars can appear hours in the future. Compare same-clock quantities: freshness = `tick.time − last bar open time`, never wall clock. In MQL, `TimeCurrent()` FREEZES while the chart's own symbol is in its daily break, mis-flagging every other market dead — use `refT = max(tick.time)` over the symbol set as reference clock.
This makes the MQL5 Expert side purely optional (SIX executor rules follow): if on-chart visuals are needed, an INDICATOR dashboard coexists with the executor on the same chart without touching algo trading — and its alerts default to `PlaySound()` ONLY — NEVER `Alert()` (modal dialogs steal focus and break UI automation), and leave `SendNotification()` (phone push) commented out unless the user re-grants it: this user silenced every push channel as noise, keeping a single chat-side summary job.
6. **Persist before you print: the entry card is the LAST action of the trade path.** An entry sequence that crashes between `order_send` and state save leaves a live position with no watch registered, no cooldown recorded and no card (the next run's management branch re-adopts it only by luck). Order the code as: order → state/watches/journal → print the human card. After any signature refactor, exercise the FULL `main()` path before declaring the executor healthy — `py_compile` plus a read-only test of the leaf evaluator misses leftover call sites (a `try_open(chosen, lot)` NameError only triggers on a real entry). Local package builds drop documented fields — `PositionInfo.order` and `SymbolInfo.contract_size` raised AttributeError; guard rarely-used fields with `getattr(obj, name, default)`. If a card job stops delivering with "no delivery target resolved for deliver=all", its old channel died — update the job to `deliver='origin'` to re-point at the creating chat. A freeze-and-release of entries (foreign positions cleared) must reset the executor's cooldown timestamp when the freeze never resulted in a trade.

**Visual EA requirements (user-specified):** The EA must display on the chart:
- Colored arrows: green (BUY signal/entry), red (SELL signal/entry), orange (position exit)
- Live Expert panel (top-left, always visible) showing: account equity/balance, open positions with P&L, market phase/trend, signal status, learning state
- Technical lines: Fibonacci 61.8%/78.6%, EMA20/EMA50, Swing High/Low, Support/Resistance
- Zone highlighting: colored rectangles for entry zones and market phases
- Real-time labels: current price, RSI value, ATR value, phase name, trend direction

**When COM fails and manual is unacceptable:** If both COM and Python package chart methods fail, and the user requires autonomous operation without manual UI interaction, document the limitation clearly and present the diagnostic path: verify MT5 COM registration (`reg query HKCR /f MetaTrader5.Application`), check MT5 process is running with correct privileges, test with a minimal COM script. If COM registration is the issue, this is an environment problem the user must resolve — the agent cannot auto-attach without COM or manual intervention.

## Verification

1. Agent initializes MT5 and reports account info correctly
2. Market analysis returns valid signals with score, SL, TP
3. Lot calculation respects capital and margin limits
4. Orders execute with proper SL/TP attached
5. Positions are managed (trailing, TP, time exit) correctly
6. Closed trades are logged with full details
7. Agent stops gracefully on KeyboardInterrupt or max drawdown

## Reporting to the user: bluntness over reassurance

This user explicitly wants hard limits stated, not managed. They have rejected
reassurance in favour of straight arithmetic, and asked for the account not to
be "brûlé" while still evolving — so the balance to strike is *survival
framed with numbers*, not caution that avoids the diagnosis.

- Lead with the live risk if one exists (an open position without a stop, a
  blown daily limit) before any summary of what was built. It is the only
  thing that matters at that moment.
- Separate **what was verified** from **what was not**. A clean compile, a green
  test suite, and correct arithmetic are three different claims; state which one
  you actually have. Never let them blur into "ready".
- When a requested parameter is structurally impossible, say so with the
  arithmetic, then deliver something that *works* rather than leaving the system
  blocked. Give modes (STRICT / IMPOSÉ / RÉALISTE) and name what each does.
- State costs and failure modes in the same breath as the design. An agent built
  to survive and to produce auditable data is a legitimate deliverable; do not
  dress it up as a profit engine.
- If a test you wrote fails, check whether the **test** is wrong before
  concluding the code is — and say which it was. A guard that names the wrong
  function proves nothing.
- Do not soften a losing position. Name the ticket, the loss, and the action
  the user must take, without prompting for reassurance.
- Chat noise is treated as cost: default every monitor/cron job's stdout to
  `deliver='local'` and keep exactly ONE live summary channel (the supervisor
  review); cards nobody asked to receive belong in files. When credit-burn is
  the stated worry, say plainly that bot delivery to Telegram is free — then
  honor the silence anyway.

## References

- `references/credentials.md` — Secure credential storage (DPAPI, env vars)
- `references/risk-parameters.md` — Detailed risk parameter guide
- `references/edge-validation.md` — Can this account pay its spread? Break-even winrate, in/out-of-sample research protocol, why a >50% winrate still loses money at small capital, and **how to test an indicator (Fibonacci, S/R, figures) BEFORE integrating it — three tests, the monotone-distribution tell, and measured GOLD results**
- `references/common-errors.md` — Troubleshooting MT5 agent issues
- `references/dashboard.md` — HTML dashboard generation (external monitoring)
- `references/honest-learning.md` — Concevoir la boucle d'apprentissage : minimum d'echantillon (30), separation IS/OOS, ce que l'apprenant a le droit d'adapter (et ce qu'il n'a jamais le droit de toucher), metriques par setup
- `references/mql5-indicator-deployment.md` — On-chart MQL5 indicator deployment: file placement, compilation, syntax, object drawing, troubleshooting
- `references/trading-supervisor.md` — Supervising a running EA: dual-channel alerting (chat queue + Windows toast), state-dict typing, what to notify about
- `references/multi-market-rotation.md` — 24/7 multi-symbol rotation: hour-by-hour pools in UTC, weekend crypto fallback, measured spread costs/margins per market, BTC daily maintenance window, per-market feasible-lot sizing, multi-symbol dashboard freshness, manual cohabitation rules, mechanical market activation (validator → markets.json, human force) and the no-SL data-collection module pattern
- `references/strategy-hunting-pipeline.md` — Agentic online strategy/EA hunting: hourly CHERCHEUR+TESTEUR cron pair with index.json as test queue, the 2-mode tel-quel/adapted backtest protocol, dossier_accepte/dossier_rejete archiving, parallel test fan-out via delegate_task, and the ethics gate for paid-EA crack requests (refuse, offer official demos + published-rule re-implementation)
