# Supervising a Running MT5 EA

Covers what to build when the user cannot be at the screen: an out-of-band process
that watches the EA and the account, and pushes events to two independent channels.

## Why a supervisor rather than UI automation

MT5 exposes no API to attach an EA to a chart or to read/write an attached EA's
inputs. The main window's UI tree is opaque, but the dock windows are not: indicator
attach IS automatable via pywinauto UIA on the Navigator child window (double-click
the TreeItem -> click OK on the properties dialog), the indicator list opens with
Ctrl+I on a focused chart, and a recompiled `.ex5` only takes effect after
delete-from-list + re-attach. What remains out of reach: an attached EA's input
dialog and its algo-trading permission. For those, a supervisor plus **one** manual
step is the honest architecture — but do not over-claim that attaching is always a
user action.

The control surface the agent *does* have is three-fold and is enough:

| Channel | Gives you |
|---|---|
| The `.mq5` source | read, rewrite, recompile — full control of logic |
| `MQL5/Logs/*.log` | every `Print()` the EA emits, including the ones you wrote to debug it |
| `MetaTrader5` Python API | balance, equity, positions, quotes, spread, history |

## Architecture

```
EA (MQL5)  --Print()-->  MQL5/Logs/20260930.log
                                |
Python supervisor --poll 3s--> tail new lines  (offset in state dict)
          |                     |
          |                     +--> parse: TRADE OUVERT / TRADE CLOSED / retcode ERROR
          |
          +--> MetaTrader5 API: account_info, positions_get, symbol_info
          |
          +--> alert(kind, title, detail, severity)
                    |
                    +--> append JSONL   -> chat reads the file
                    +--> Windows toast   -> PowerShell + WinRT
```

## Alerting: what to fire on

Alert on money, positions and failure. **Do not alert on every rejected signal** —
an EA that filters constantly would fire a notification every polling interval and
the user would disable it. Record refusals in state; notify only:

- `POSITION_OUVERTE` / `POSITION_FERMEE` — include direction, volume, entry, SL, TP,
  and both distances in points, plus P&L on close
- `ERREUR_ORDRE` — retcode **and** its description
- `SPREAD` over threshold, `DRAWDOWN` over threshold % of peak equity,
  `CAPITAL_CRITIQUE` under the survival floor
- `MT5_DOWN` when `mt5.initialize()` fails

Position detection keys off the ticket changing, which catches opens and closes
without parsing the log at all.

Two exit refinements proven on small accounts: **soft stop** — close at market when
floating PnL reaches ~80% of the SL risk (cleaner fill than the server SL, caps
real loss below it); **whipsaw refusal** — if `max(high)-min(low)` over the last 10
closed bars exceeds ~4x ATR(14), refuse entries even when the signal is perfectly
aligned: news storms produce aligned-looking momentum setups that all stop out.

## Windows toast without installing anything

`win10toast` and `plyer` are usually absent and are not needed. The OS already
exposes the toast API; drive it from PowerShell:

```python
script = (
    "[Windows.UI.Notifications.ToastNotificationManager, "
    "Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null\n"
    "$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
    "[Windows.UI.Notifications.ToastTemplateType]::ToastText02)\n"
    "$n = $t.GetElementsByTagName('text')\n"
    "$n.Item(0).AppendChild($t.CreateTextNode(" + ps_quote(title) + ")) | Out-Null\n"
    "$n.Item(1).AppendChild($t.CreateTextNode(" + ps_quote(detail) + ")) | Out-Null\n"
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
    "'...').Show([Windows.UI.Notifications.ToastNotification]::new($t))\n"
)
subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
               capture_output=True, timeout=15, creationflags=CREATE_NO_WINDOW)
```

Quote via single quotes with `'` doubled. Guard the whole call in `try/except` — a
failing toast must never take the supervisor down — and serialise calls with a lock
so concurrent alerts don't interleave in PowerShell.

## Pitfall: do not share state keys between different types

The most common supervisor bug is one dict holding both a file offset (`int`) and a
position ticket (`str`), then comparing them:

```
'<' not supported between instances of 'int' and 'str'
```

This throws *inside* the poll, so the process looks alive, prints its banner, and
writes no state at all. Give each concern its own key — `log_pos` for the byte
offset, `pos` for the ticket — and give them different types by construction.

Related: the first poll has no prior state, so it will emit a spurious
"position closed" for a position that never existed. Gate the transition logic on a
`seen` flag rather than special-casing.

## Pitfall: position the log offset at the end on start-up

Set the byte offset to the current file size when the supervisor starts, so it does
not replay the entire historical log as a flood of alerts on the first cycle.

## Pitfall: `copy_rates` does not exist

`mt5.copy_rates` is not part of the package; use
`mt5.copy_rates_range(symbol, timeframe, datetime_from, datetime_to)`, which needs
`datetime` objects, not timestamps.

## Pitfall: `history_deals_get` wants Unix timestamps — and never gate risk on history

The mirror of the rule above: `mt5.history_deals_get(datetime_obj, ...)` returns
EMPTY **silently** — pass `time.time()` floats. The symptom is a daily-loss or
trades-per-day stop computed from history that never trips, so the engine keeps
trading past its own circuit-breaker. After a terminal restart the history cache
can additionally omit your own deals entirely (SL/TP hits invisible, or a ghost IN
deal with no position and no OUT — re-query before alarming, it is a sync hole).
Therefore:

- **Risk gates read a LOCAL ledger** (JSON state `{date: {pnl, n}}` updated on every
  close the engine observes); MT5 history is a cross-check, never the gate.
- **Watchdog server-side closes**: persist each open ticket with its sl/tp/ts; when
  the ticket vanishes from `positions_get` with no visible OUT deal, book an
  estimated PnL (assume SL) so the gate still trips.

## Alert channel UX (user preference)

On the MT5 side, `Alert()` pops a modal "Alerte" window that steals focus (and
blocks Ctrl+I until closed) — users reject it as invasive. Terminal-side alerts are
`PlaySound()` (distinct sound per event class) + `SendNotification()` + journal
`Print()`. Chat pushes go through the Hermes cron `no_agent` watchdog pattern:
stdout is delivered verbatim, **empty stdout sends nothing** — stay silent unless
there is a real event. Do not integrate WebRequest-based pushes on old MT5 builds
(POST signature mismatches into error 199).

## Chat channel

Append one JSON object per line to a queue file and read it on demand. A JSONL queue
is inspectable, survives restarts, and needs no socket or service:

```json
{"ts":"2026-09-30T11:34:24","kind":"POSITION_OUVERTE","title":"Position ouverte BUY",
 "detail":"GOLD lot 0.02 @ 4188.30 | SL 4178.30 | TP 4190.05","severity":"good"}
```

`severity` in `info|good|warn|bad` lets the reader rank urgency. Also write a
`--status` command that dumps the current account/position state plus the last N
events, so the user can check at any moment without waiting for a message.

## Scheduled review on top of the supervisor

Once a supervisor exists, a periodic written review is a thin addition — **if** a
report script produces the numbers and the job only narrates them. Do not ask the
scheduled job to re-derive facts it could read.

The script emits a JSON snapshot: account, open position, quotes, multi-timeframe
ATR/EMA/RSI, the event window, and statistics parsed from the EA log. A
data-collection script keeps the scheduled run cheap and stops the model from
hallucinating figures it could have measured.

Cron constraints, each learned by a failed creation:

- **Scripts must live in the profile's `scripts/` directory**, referenced by bare
  filename. An absolute path is rejected outright.
- **No arguments.** The runner concatenates the argument string onto the
  filename, so `gsa_report.py 30` looks for a file with that literal name and the
  job errors. Pass tunables through an environment variable instead
  (`WINDOW_MIN = int(os.environ.get("GSA_WINDOW_MIN", "30"))`).
- **`deliver` defaults to `local`**, which saves the output and sends nothing.
  Always set `deliver="all"` or the user will never receive a single review.
- Optional array fields (`skills`, `enabled_toolsets`) may fail schema validation
  even when the tool schema declares them as string arrays. Put the domain rules
  in the prompt text, which must be self-contained anyway since the job runs in a
  fresh session with no chat history.

`continuity: true` lets each review see the previous one, so it can avoid
repeating the same finding instead of restating it every cycle.

Write the review prompt to a fixed shape — situation / what the robot did /
market / diagnosis / alerts / one-line recommendation — and state that it must
cite the log's own refusal string rather than speculate about a cause, and say a
datum is missing rather than fill it in.

## Verify before declaring it working

Run a `--test` mode that exercises each channel independently and prints which ones
answered, plus the MT5 connection. Then start the process, wait at least two poll
cycles, and confirm: no exception lines in stdout, a state file exists with a fresh
timestamp, and the queue gained exactly one startup event — not a stream.
