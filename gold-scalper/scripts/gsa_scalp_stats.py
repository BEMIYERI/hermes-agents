# -*- coding: utf-8 -*-
"""gsa_scalp_stats.py - analyse le dataset de collecte (gsa_scalp_dataset.jsonl).
Usage: python3 gsa_scalp_stats.py [jours]
Sortie: stats par marche (n, winrate, TP-vs-timeexit, PnL, MFE/MAE median,
ce que des SL alternatifs auraient donne) + verdict global.
"""
import json, os, sys, time

S = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(S, "gsa_scalp_dataset.jsonl")

def med(v):
    return sorted(v)[len(v) // 2] if v else None

def main(days=14):
    if not os.path.exists(D):
        print("pas de dataset")
        return
    cut = time.time() - days * 86400
    opens = {}
    closes = []
    for line in open(D, encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        ts = time.mktime(time.strptime(r["ts"], "%Y-%m-%d %H:%M:%S"))
        if ts < cut:
            continue
        if r["ev"] == "open":
            opens[r["key"]] = r
        elif r["ev"] == "close":
            r["open_ctx"] = opens.get(r.get("key", ""), {})
            closes.append(r)
    if not closes:
        print("donnees: %d entrees, 0 sortie closee - pas encore analysable" % len(opens))
        return
    print("=== STATS COLLECTE scalp SANS SL (14j, %d trades clos) ===" % len(closes))
    by_sym = {}
    for c in closes:
        by_sym.setdefault(c["sym"], []).append(c)
    for sym, rows in sorted(by_sym.items()):
        pnls = [r["pnl"] for r in rows]
        wins = len([p for p in pnls if p > 0])
        tp_hits = len([r for r in rows if "time" not in (r.get("reason") or "").lower() and "TP" not in (r.get("reason") or "").upper()][:0]) # placeholder
        reasons = {}
        for r in rows:
            reasons[r.get("reason", "?")] = reasons.get(r.get("reason", "?"), 0) + 1
        mfes = med([r["mfe"] for r in rows if r.get("mfe") is not None])
        maes = med([r["mae"] for r in rows if r.get("mae") is not None])
        # simulation: si un SL avait existe a X fois la MAE mediane, combien de trades survivraient jusqu'au TP?
        print("%-8s n=%3d wr=%4.1f%% pnl=%+7.2f$ moy=%+.3f$ | sorties %s | MFEmed %.5f MAEm med %.5f" % (
            sym, len(rows), 100.0 * wins / len(rows), sum(pnls), sum(pnls) / len(rows),
            ",".join("%s:%d" % (k, v) for k, v in reasons.items()),
            mfes if mfes is not None else -1, maes if maes is not None else -1))
    tot = sum(r["pnl"] for r in closes)
    wr = 100.0 * len([r for r in closes if r["pnl"] > 0]) / len(closes)
    print("GLOBAL: n=%d wr=%.1f%% pnl=%+.2f$ sur %d jours" % (len(closes), wr, tot, days))
    if len(closes) >= 40:
        print("=> echantillon suffisant pour decision: demander 'analyse scalp data'")
    else:
        print("=> continuer la collecte (objectif 40+ trades pour decider)")

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
