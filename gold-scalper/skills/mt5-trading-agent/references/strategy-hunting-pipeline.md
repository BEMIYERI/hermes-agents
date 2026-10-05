# Online Strategy & EA Hunting Pipeline (agentic)

Class of task: user wants the system to discover trading strategies/robots on the
Internet, test them with real costs, and archive verdicts — continuously, without
installing anything into the trading terminal.

## Architecture (two LLM cron agents + one folder)
```
gsa_research/               (or <project>/research/)
  index.json                catalogue = TEST QUEUE (status=new) + registry (tested)
  strategies/*.md  ea/*.md  notes written by CHERCHEUR
  reports/*.md              full test reports
  dossier_accepte/<id>/     the accepted ones
  dossier_rejete/<id>/      the rejected ones
    each <id>/ = strategie.md|ea.md + rapport.md + verdict.txt
```
- **CHERCHEUR** (agent cron, hourly H+00, deliver='local'): web_search with rotating
  queries; keeps `chasse_journal` (last 15 queries/URLs) in index.json to avoid
  repetition. Archives ONLY finds whose rules are fully mechanical (trigger, SL, TP,
  filters, timeframe, markets) — marketing without rules = `non-testable`.
- **TESTEUR** (agent cron, hourly H+30): pops up to 3 items `status=new` from the
  queue, backtests each, archives into the dossiers, updates index.json
  (`status=tested, dossier, verdict, is_a/oos_a/is_b/oos_b`). Empty queue answers
  'FILE VIDE' in one line and exits. Long jobs break at ~12 min mid-item but always
  finish the CURRENT item's archiving; the rest waits for the next hour.
- Adoption = human decision, always. The agent that hunts never installs; the agent
  that tests never trades.

## Policy filters — automatic dossier_rejete without a test
grid / martingale / hedging-recovery; paid products (see ethics gate below);
requires VPS latency < 30 ms (measure own ping first — 145 ms here);
requires raw spread < 0.3 pip (measure live spread — GOLD is 5.5 pips here);
recommends capital > $200 on a small account; typical gain < 3x round-trip cost.
Declare the measured values next to each rejected requirement — the filter is
numeric, not stylistic.

## Two-mode test protocol (make blocked tests produce palpable results)
User mandate: when environment constraints block execution, adapt them so the test
RUNS — but never fake the signal.
- **Mode A tel-quel**: rules faithful to source, real broker costs. Often n=0 (that
  IS the verdict on broker compatibility — several credible free scalpers self-block
  on their own spread gate at retail spreads).
- **Mode B adapte-XM**: relax ONLY environment blockers — spread gates -> real
  values, latency/VPS demands, capital recommendation, session windows. NEVER touch
  entry rules, SL, TP. Each relaxation logged as a `DEVIATION:` line in rapport.md.
- Verdict computed on Mode B (the most favorable honest reading), but verdict.txt
  MUST cite both numbers: `tel quel: X$/tr | adapte: Y$/tr`.
- Adoption gate: IS>0 AND OOS>0 AND avg/trade>0 AND risk<=25$/trade AND n>=20.

## Harness rules repeated into every tester prompt
`mt5.initialize(path=...)` when several terminals run; READ-ONLY (never order_send);
bars/deals timestamps are SERVER time (+UTC offset — widen the query window into
server 'now'); cost model: half-spread adverse at entry + 1.5x spread x unit per
round trip, SL priority when SL+TP in same bar, volume_min lots only; IS/OOS 70/30;
sample < 20 = 'insuffisant', say so.

## Parallel fan-out for many candidates at once
`delegate_task` with one leaf per candidate and a strict `output_schema`
(`id, verdict enum[adoptable|rejete|insuffisant|non-testable], n, is_net, oos_net,
avg, why, report_path`). Each child writes ONLY its own report file; the PARENT
merges index.json and the dossiers (children must never write the catalogue —
concurrent children clobber it). Put the full harness rules in EVERY child context;
children share nothing else.

## Ethics gate — paid EA 'so I can use it without paying'
Requests to crack / license-bypass a paid EA: REFUSE plainly (illegal; MT5/MQL5 ban
risk; and cracked binaries are the #1 credential-stealer vector against traders —
a poisoned .ex5 threatens the account itself). Offer the legal ladder instead:
official time-limited Market demos (chercheur records `demo_officielle: URL +
conditions` in the note; direct trial install stays a human decision), re-implementation
of PUBLISHED rules (ideas are not copyrightable — this is the normal test path), and
public live tracks (Myfxbook/signal pages) as evidence. Expect the user to accept the
substitution — keep the pipeline running, never the binary.

## What the hunt keeps finding (durable priors, not new failures to relearn)
At retail spreads, entry filters cannot rescue high frequency: filters that skip
~1% of signals or reduce exposure without flipping the sign are noise-dressings.
The literature and our own re-tests converge: the honest frontier is LOWER frequency
on M5+ where the move is several times the spread (session opens, Donchian-style
channels with HTF filters). Search queries accordingly, and say plainly when
`dossier_accepte` is empty — an empty accepted-folder is evidence the gate works,
not that it failed.
