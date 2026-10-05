# MQL5 Indicator Deployment for MT5 Trading Agents

## Purpose

On-chart visual indicators (dashboards, signal arrows, SL/TP lines, multi-timeframe overlays) complement the Python trading agent by rendering analysis directly on the MT5 chart. This reference covers deployment of `.mq5` indicators — distinct from Expert Advisors (EAs), which execute trades.

## File Placement

Put the source in the **instance data tree**, which is user-writable and needs no UAC elevation:

```
%APPDATA%\MetaQuotes\Terminal\<InstanceID>\MQL5\Experts\      (for an EA / dashboard EA)
%APPDATA%\MetaQuotes\Terminal\<InstanceID>\MQL5\Indicators\  (for a real indicator)
```

The instance id is the folder name under `Terminal\`; it is stable for a given installation. Keep a second copy of the source in the user profile as the backup of record.

Prefer this over `C:\Program Files\XM Global MT5\MQL5\...`, which requires an elevated helper script per copy. Note that writing into `C:\Program Files\...\MQL5\` can also fail outright with a permission error even when the terminal is installed there — the roaming tree is the location MT5 itself uses.

## Compilation

### Headless CLI — the primary path

```python
import subprocess, time, os

src = r"%APPDATA%\MetaQuotes\Terminal\<InstanceID>\MQL5\Experts\MyDashboard.mq5"
log = r"C:\mq5t\compile.log"
os.makedirs(os.path.dirname(log), exist_ok=True)
if os.path.exists(log):
    os.remove(log)

subprocess.run([r"C:\Program Files\XM Global MT5\MetaEditor64.exe",
                f"/compile:{src}", f"/log:{log}"], capture_output=True)
for _ in range(15):
    time.sleep(1.5)
    if os.path.exists(log):
        break
print(open(log, "rb").read().decode("utf-16"))
```

Conditions, all of which fail **silently** — exit code 0, no log file, no `.ex5`, no error message:
- the source must already be inside the instance MQL5 tree,
- the `/log` path must contain **no spaces** (a log path under `C:\Program Files\...` produces nothing),
- the log is written asynchronously: poll for it for 2–5 s after the process returns.

**Establish a control before debugging your own source.** Compile an already-working EA from the same tree. If it reports 0 errors, the install, the command and the log path are all sound and the fault is in your source. This one step replaces a dozen blind signature variants.

### GUI fallback

Only if the CLI produces no log after the control check: open `MetaEditor64.exe <path.mq5>`, press F7, read the Errors panel. Do not build an automated pyautogui loop around this — it is slow, timing-dependent, and it hides the compiler's actual message, which is the only thing worth reading.

## Error 209: rewrite the dashboard as an EA

`error 209: OnCalculate function not found in custom indicator` (preceded by `warning 70: 'OnCalculate' function declared with wrong type or/and parameters`) on an older MetaEditor build means **the build accepts no indicator `OnCalculate` at all** — 3-arg, 4-arg and 11-arg forms fail identically, with or without `indicator_buffers` / `indicator_plots`, in-tree or out.

The distinguishing evidence: the same build compiles Experts Advisors (`OnInit`/`OnTick`/`OnDeinit`) cleanly. If EAs compile and your indicator does not, do not keep re-bisecting the signature — **rewrite the component as an Expert Advisor that does the same job.** A real-time dashboard only needs a tick handler: read the handles, update the chart objects, log periodically. You lose native EMA plot lines on the chart; nothing else changes.

Check the build number before assuming a signature bug:
`powershell -NoProfile -Command "(Get-Item 'C:\Program Files\XM Global MT5\MetaEditor64.exe').VersionInfo.FileVersion"`.

### EA shape that compiles

- `OnInit` — create `iMA`/`iRSI`/`iATR` handles for each timeframe, bail with `INIT_FAILED` if any is `INVALID_HANDLE`, return `INIT_SUCCEEDED`.
- `OnTick` — a small `bool Val(int handle, double &out)` helper wrapping `CopyBuffer(handle, 0, 0, 1, buf)` keeps the handler readable.
- `OnDeinit` — `ObjectsDeleteAll(0, "<prefix>_")` then `IndicatorRelease` on every handle.

Design points:
- Give every object the same **prefix** so a signal flip or a clean unload removes all of them in one call.
- Anchor dashboard text with `OBJPROP_CORNER` + `OBJPROP_XDISTANCE` / `OBJPROP_YDISTANCE` rather than a price/time anchor — it then stays pinned to the chart corner and survives scrolling.
- Create each object once (`if(ObjectFind(0,name)<0) ObjectCreate(...)`) and afterwards only update properties; re-creating every tick causes flicker and is wasted work.
- A display-only EA needs no trading permission; MT5 will still load it with the box ticked.

## MQL5 syntax pitfalls

### Buffer declaration

Indicator buffers are `double` arrays. The `buffer` keyword does not exist in MQL5 — `buffer MyBuffer[];` fails to compile, and on some builds the failure surfaces only as a missing `.ex5`. Declare buffers as `double` and register them in `OnInit` via `SetIndexBuffer(0, MyBuffer, INDICATOR_DATA)`.

Note: `INDICATOR_DATA` and `SetIndexLabel` are absent on older builds — if they report as undeclared, that is a build limitation, not a typo in your code.

### Object property type mismatches

`ObjectSetInteger` vs `ObjectSetDouble` is decided by the property, and picking wrong yields `error 262: cannot convert enum` plus `error 199: wrong parameters count` on the same line:

| Property | Correct setter |
|---|---|
| `OBJPROP_PRICE` | `ObjectSetDouble` — using `ObjectSetInteger` is the single most common cause of 262/199 pairs on arrow and hline objects |
| `OBJPROP_TIME` | `ObjectSetInteger` |
| `OBJPROP_ARROWCODE` | `ObjectSetInteger` (233 = up, 234 = down) |
| `OBJPROP_COLOR`, `OBJPROP_FONTSIZE`, `OBJPROP_STYLE` | `ObjectSetInteger` |
| `OBJPROP_TEXT` | `ObjectSetString` |

Related:
- `PLOT_DRAW_TYPE` is an **integer** property — `PlotIndexSetInteger`, not `PlotIndexSetDouble`.
- `OBJPROP_ARROW` does not exist; the property is `OBJPROP_ARROWCODE`.
- `OBJPROP_ANGLE` is not supported on `OBJ_TEXT` in these builds — drop it.

### Trade-request globals absent on old builds

`MqlTradeResult` is a **reduced** struct here: it carries `retcode`, `order`,
`deal`, `volume`, `price` — but **not** `sl` / `tp`. Logging `res.sl` gives
`error 256: undeclared identifier`. Log the values you *sent* (`req.sl`,
`req.tp`), which is also more useful for an audit.

`iATR()` takes no handle argument. To read an ATR you created, use
`CopyBuffer(handle, 0, 1, 1, arr)` — `iATR(symbol, tf, period, 1, handle)`
is `error 199: wrong parameters count`.

`CopyClose` rejects a statically-sized array when the series flag is set
(`warning 63`). `ArrayResize(c, 3)` before `ArraySetAsSeries` fixes it.

`GlobalVariableToString` / `GlobalVariableToDouble` do not exist. Use
`GlobalVariableGet` (returns `double`) and encode dates as a compact number:

```mql5
MqlDateTime dt;
TimeToStruct(TimeCurrent(), dt);
double today = (double)(dt.year * 10000 + dt.mon * 100 + dt.day);
```

`TimeYear` / `TimeMonth` / `TimeDay` do not exist either. `CLOSE_NULL` is
absent — pass a real array. `TradeAllowed()` is absent; use
`AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)` alongside
`TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)` and
`MQLInfoInteger(MQL_TRADE_ALLOWED)`. `OBJPROP_BACKGROUND_COLOR` is absent
(`OBJPROP_BGCOLOR`).

Cast enums explicitly when assigning a `long` flag variable to a typed field:
`req.type_filling = (ENUM_ORDER_TYPE_FILLING)g_fillMode;` — otherwise
`warning 42: implicit enum conversion`.

### Filling mode must be read, not assumed

Never hardcode `ORDER_FILLING_IOC`. Query the symbol and pick a supported bit —
on a FOK-only symbol an IOC request is simply rejected:

```mql5
long f = (long)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
// bit 0 = IOC, bit 1 = FOK, bit 2 = RETURN
if      ((f & 1) != 0) g_fillMode = ORDER_FILLING_IOC;
else if ((f & 2) != 0) g_fillMode = ORDER_FILLING_FOK;
else                    g_fillMode = ORDER_FILLING_RETURN;
```

### Magic number, and the Position-vs-Order trap

Always set `req.magic` and filter every position by `POSITION_MAGIC`. Without
it an EA adopts the user's own manual positions as its own and closes them.

When closing a position by ticket, read it with the **Position** accessors —
`PositionGetInteger(POSITION_TYPE)`, `PositionGetDouble(POSITION_VOLUME)`,
`PositionGetString(POSITION_SYMBOL)`. Using the `OrderGet*` family on a
position ticket reads a different record entirely, so the close can go out
with the wrong direction or wrong volume.

### Name collisions

- Declaring a global `double Buf[]` **and** an `OnCalculate` parameter of the same name produces `warning 62: declaration hides global variable`. Declare buffer arrays only as `OnCalculate` parameters.
- Reusing a name already bound in the same function scope (e.g. a local `last` when `last` is already used) is `error 125: variable already defined`. Give the periodic-log timestamp a distinct name such as `lastLog`.

## Multi-timeframe data access

An indicator attached to an M1 chart can display M5 or M15 data by creating separate indicator handles:

```mql5
// In OnInit():
int h_ema9_m5  = iMA(_Symbol, PERIOD_M5,  9, 0, MODE_EMA, PRICE_CLOSE);
int h_ema21_m5 = iMA(_Symbol, PERIOD_M5,  21, 0, MODE_EMA, PRICE_CLOSE);
int h_ema9_m15 = iMA(_Symbol, PERIOD_M15, 9, 0, MODE_EMA, PRICE_CLOSE);
int h_ema21_m15= iMA(_Symbol, PERIOD_M15, 21, 0, MODE_EMA, PRICE_CLOSE);

// In OnCalculate(), retrieve current values:
double arr_m5_ema9[], arr_m15_ema9[];
if(CopyBuffer(h_ema9_m5,  0, 0, 1, arr_m5_ema9)  > 0)  ema9_m5  = arr_m5_ema9[0];
if(CopyBuffer(h_ema9_m15, 0, 0, 1, arr_m15_ema9) > 0)  ema9_m15 = arr_m15_ema9[0];
```

Do not attempt to calculate M5/M15 values by averaging M1 bars — the EMA periods would be incorrect. Always use timeframe-specific handles.

### Object drawing (dashboard, arrows, lines)

Indicators can draw visual objects on the chart:

```mql5
// Text dashboard: anchor it to a chart corner, not to a price/time
if(ObjectFind(0,"MyDashboard")<0)
   ObjectCreate(0, "MyDashboard", OBJ_TEXT, 0, 0, 0);
ObjectSetInteger(0, "MyDashboard", OBJPROP_CORNER, CORNER_LEFT_UPPER);
ObjectSetInteger(0, "MyDashboard", OBJPROP_XDISTANCE, 12);
ObjectSetInteger(0, "MyDashboard", OBJPROP_YDISTANCE, 20);
ObjectSetString (0, "MyDashboard", OBJPROP_TEXT, dashboard_text);
ObjectSetInteger(0, "MyDashboard", OBJPROP_COLOR, clrWhite);
ObjectSetInteger(0, "MyDashboard", OBJPROP_FONTSIZE, 8);

// Entry arrow (233 = up, 234 = down) - OBJPROP_PRICE needs ObjectSetDouble
if(ObjectFind(0,"EntryArrow")<0)
   ObjectCreate(0, "EntryArrow", OBJ_ARROW, 0, 0, arrow_price);
ObjectSetDouble  (0, "EntryArrow", OBJPROP_PRICE, arrow_price);
ObjectSetInteger (0, "EntryArrow", OBJPROP_ARROWCODE, 233);
ObjectSetInteger (0, "EntryArrow", OBJPROP_COLOR, clrLime);

// Horizontal SL/TP lines - also OBJSetDouble for the price
ObjectCreate(0, "SL_Line", OBJ_HLINE, 0, 0, sl_price);
ObjectSetDouble  (0, "SL_Line", OBJPROP_PRICE, sl_price);
ObjectSetInteger (0, "SL_Line", OBJPROP_COLOR, clrRed);
ObjectSetInteger (0, "SL_Line", OBJPROP_STYLE, STYLE_DASH);
```

Create each object once, then update properties on subsequent ticks. `ObjectDelete` + `ObjectCreate` on every tick flickers and leaks; the correct pattern is `if(ObjectFind(...) < 0) ObjectCreate(...)` followed by property updates. To clear a whole overlay, prefix every name and use `ObjectsDeleteAll(0, "PREFIX_")`.

## Attaching to Chart

After compilation, the indicator appears in MT5's **Navigator** panel (Ctrl+N) under the **Indicators** section, inside the `<IndicatorName>` subfolder.

To attach:
- **Double-click** the indicator name, or
- **Drag and drop** onto the target chart

The indicator's `OnCalculate()` begins executing immediately, drawing the dashboard and arrows.

To remove: right-click the chart → Indicators → uncheck the indicator name, or delete objects individually via the Objects menu.

## Troubleshooting Checklist

| Symptom | Likely cause | Check |
|---------|-------------|-------|
| `/compile` returns 0, no log, no `.ex5` | log path contains spaces, or source outside the instance MQL5 tree | move the log to `C:\...`, put the source in `%APPDATA%\MetaQuotes\Terminal\<id>\MQL5\` |
| `.ex5` not generated after a valid compile | real syntax error | read the CLI log — it names file, line and error code |
| `error 209: OnCalculate function not found` | build accepts no indicator `OnCalculate` | compile an EA from the same tree; if it passes, rewrite the dashboard as an EA |
| `error 262` + `error 199` on one line | wrong property setter (`ObjectSetInteger` on a double property) | `OBJPROP_PRICE` → `ObjectSetDouble`; `PLOT_DRAW_TYPE` → `PlotIndexSetInteger` |
| `warning 62: hides global variable` | buffer declared both as a global and as an `OnCalculate` parameter | keep the declaration only as the parameter |
| `error 125: variable already defined` | name reused in the same function scope | rename (e.g. the periodic-log timestamp → `lastLog`) |
| `.ex5` not generated, no errors shown | `buffer` used instead of `double` for a buffer declaration | verify source: search for the `buffer` keyword |
| Panel text unreadable, candles show through it | `OBJPROP_BACK = true` on the panel background sends it **behind** the chart | `BACK=false` + `FILL=true`; also set `ZORDER` on every label (MT5 puts labels behind graphic objects by default) |
| `OBJPROP_TRANSPARENCY` reported undeclared | older build — the named property does not exist | `ObjectSetInteger(0, name, 0, 82);` (index form, 0 = sub-window) |
| `input int TF = 15;` then `iMA(_Symbol, TF, ...)` | `error 262: cannot convert enum` | declare the input as `input ENUM_TIMEFRAMES TF = PERIOD_M15;` |
| Access denied writing the source | targeting `C:\Program Files\...` | write to the instance MQL5 tree instead |
| Dashboard not appearing on chart | not attached, or wrong symbol/timeframe | Navigator → drag onto the chart; confirm symbol is `GOLD` and TF is M1 |
| Dashboard appears but values are wrong | M5/M15 handles missing or `CopyBuffer` failing | confirm the `iMA()` handles for M5/M15 are created in `OnInit()` and `CopyBuffer` returns > 0 |
| Arrows not showing | wrong arrow code, or price coordinate off-screen | 233 = up, 234 = down; check the price sits in the visible range |
| Compilation works sometimes, not others | copy not finished before the compile call | poll for the destination file, then compile |

## A batch edit script must be all-or-nothing, and must verify at the end

MetaEditor rewriting the source from its in-memory copy (see SKILL.md, Step 5.5)
is only half the risk. The other half is the **repair script** written
afterwards: a sequence of `sub()` calls that asserts each match is unique and
aborts partway. When it aborts, every earlier `sub()` has usually **already been
written to disk**, leaving the file in a hybrid state — half the new fixes, half
the old code — that can still produce a clean-looking log.

The rule that removes the class of error: **accumulate every substitution in
memory, write the file exactly once at the end, and print a verification table of
expected-present and expected-absent markers after the write.** A partially
applied batch is then impossible by construction.

```python
src = read(path)
edits = [(old, new, "label"), ...]
applied = failed = 0
for old, new, label in edits:
    if src.count(old) != 1:
        print("SKIP (not unique):", label); failed += 1; continue
    src = src.replace(old, new); applied += 1
write(path, src)                      # single write, after the whole batch

for label, pat, must in checks:        # must=True -> present, must=False -> gone
    n = src.count(pat)
    assert (n > 0) == must, f"{label}: {n}"
```

Corollary: **when several edits target the same region, count occurrences before
editing.** Expected-present markers can already be present (an earlier partial
run) while expected-absent ones are still there — that combination means *some*
fixes landed and others did not, and it is invisible unless both columns are
printed side by side.

Keep an off-tree backup of the source and `md5sum` it after compiling: a mismatch
means the file was rewritten, not that the build failed.

## Reporting results honestly

A clean compile (`0 errors, 0 warnings`) proves the source builds — not that it behaves as advertised on a live chart. Do not hand the user a "dashboard ready" claim until it has actually been seen running on a chart, and say plainly when validation stopped at compilation (values unverified against the live account: spread, tick value, sizing).

When iterating on a dashboard, several earlier versions usually sit next to the working one. Leave them alone unless asked, and list them as dead files the user may want removed — deleting someone's files unprompted is not yours to decide.

## Compilation is not verification — check the guardrails statically

A trading EA can compile with **0 errors** while containing every safety defect that matters. `Result: 0 errors` says nothing about whether a stop loss is ever set, whether the magic number is respected, or whether the cost model survives the real spread. Assert those properties on the **source text** before reporting the EA as ready.

```python
import re
src = open(ea_path, encoding="utf-8").read()

# a stop loss can never be sent at zero
assert re.search(r"if\s*\(\s*req\.sl\s*==\s*0", src), "no SL-zero guard"
assert "0" not in [a.rstrip("0").rstrip(".")
                   for a in re.findall(r"req\.sl\s*=\s*([0-9.]+)\s*;", src)], \
    "SL assigned a literal 0"

# magic number is set and enforced on close
assert re.search(r"req\.magic\s*=", src)
assert re.search(r"Close\w*[\s\S]{0,600}?POSITION_MAGIC\s*\)\s*!=\s*MagicNumber", src)

# position closed via Position* accessors, never Order* (reads the wrong record)
assert "OrderGetInteger(ORDER_TYPE)" not in src

# success is verified, not assumed
assert "TRADE_RETCODE_DONE" in src and re.search(r"res\.(deal|order)", src)

# filling mode is queried, not hardcoded
assert "SYMBOL_FILLING_MODE" in src

# the master switch defaults OFF
assert re.search(r"input\s+bool\s+EnableTrading\s*=\s*false", src)
```

Scope assertions to the *behaviour*, not the spelling: assert that a magic
mismatch is **refused**, not that a function is named `ClosePosition` — a
naive name check fails on a correctly-implemented `CloseOurPosition` and
teaches you to distrust a test that was wrong rather than the code that was
wrong.

State the limit of this check when reporting: static assertions prove the
guardrails are **present**, never that they behave correctly under load.
The remaining gap is attaching to a chart and observing it, and that step is
the user's.

## Health check must treat a naked position as the top emergency

`balance` is a lie about exposure. A position with no stop loss can be
arbitrarily far underwater while the balance still looks fine. Order the
health gates by blast radius:

1. **unprotected position (`sl == 0`)** — the loss is unbounded; stop everything
2. floating loss over ~15% of balance
3. equity under the trading floor
4. kill switch
5. daily loss / consecutive losses / trade quota / spread

Check this against *all* open positions on the symbol, not only the ones
carrying your magic — a naked manual position is still your emergency. Report
it as `STOP_SYSTEM`, not `NO_TRADE`: the difference is whether new entries are
merely declined or the whole agent halts.

## Relationship to Python Agent

The indicator is a **visualization complement** to the Python agent, not a replacement:

- The Python agent (`gold_scalper_analysis.py`) performs the full multi-timeframe analysis and produces the signal decision.
- The MQL5 indicator renders the same analysis (EMAs, RSI, ATR, signal arrow, SL/TP lines) directly on the chart for visual confirmation.
- The two should stay consistent: if the Python agent detects a LONG signal, the M1 chart indicator should show a green up-arrow at the same price level.

If the indicator and Python agent diverge, investigate:
1. Timeframe mismatch (indicator on M5 but Python analyzing M1)
2. Symbol mismatch (indicator on XAUUSD but Python on GOLD)
3. Handle failures in the indicator (check MetaEditor error log)
4. Stale data (restart indicator or refresh chart)

## Cleaning Up

When replacing an indicator version:
1. Remove the old indicator from all charts first (Objects menu or Navigator uncheck)
2. Delete the old `.ex5` and `.mq5` from the Indicators folder
3. Copy the new `.mq5`
4. Compile
5. Re-attach to chart

This avoids conflicts between old and new object names.
