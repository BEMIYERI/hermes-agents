# -*- coding: utf-8 -*-
"""
gsa_validator.py — VALIDATEUR HEBDOMADAIRE D'ACTIVATION AUTO MULTI-MARCHE.
Rejoue les regles EXACTES de gsa_swing.py (Donchian48 H1 / 24 H4, SL 1.5xATR,
TP 3x, time-exit 32 barres, lot minimum broker, cout spread x1.5,
SKIP si risque > plafond = comme l'engine live) sur 2 ans, IS 70% / OOS 30%.

ACTIVATION MECANIQUE (pas d'LLM): un marche est auto=True ssi
  n_total >= 20  ET  IS > 0  ET  OOS > 0  ET  mediane du risque <= plafond.
Sinon auto=False (et un marche actif qui echoue est DESACTIVE).

Ecrit C:/Users/nanga/AppData/Local/hermes/scripts/gsa_swing_markets.json
+ carte resume en stdout (livree par cron hebdo).
"""
import datetime
import json
import os
import time

import MetaTrader5 as mt5

XM = r"C:\Program Files\XM Global MT5\terminal64.exe"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gsa_swing_markets.json")

MARKETS = {
    "GOLD":   {"P": 48, "tf": "H1", "cap": 25.0},
    "EURUSD": {"P": 48, "tf": "H1", "cap": 25.0},
    "GBPUSD": {"P": 48, "tf": "H1", "cap": 25.0},
    "USDJPY": {"P": 48, "tf": "H1", "cap": 25.0},
    "BTCUSD": {"P": 48, "tf": "H1", "cap": 25.0},
}
SL_MULT = 1.5
TP_MULT = 3.0
MAX_BARS = 32
DAYS = 730


def ema_s(v, p):
    k = 2.0 / (p + 1.0)
    o = [0.0] * len(v)
    o[0] = v[0]
    for i in range(1, len(v)):
        o[i] = v[i] * k + o[i - 1] * (1.0 - k)
    return o


def atr_n(h, l, c, p=14):
    n = len(c)
    o = [0.0] * n
    a = 0.0
    for i in range(1, n):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        a = a + tr / p if i <= p else (a * (p - 1) + tr) / p
        o[i] = a
    return o


def backtest(S, cfg):
    si = mt5.symbol_info(S)
    if si is None:
        return None
    pt = si.point
    u = si.trade_tick_value * pt / si.trade_tick_size * si.volume_min
    spr = si.spread
    cost = spr * 1.5 * u
    tf = mt5.TIMEFRAME_H1 if cfg["tf"] == "H1" else mt5.TIMEFRAME_H4
    now = time.time()
    r = mt5.copy_rates_range(S, tf,
                             datetime.datetime.fromtimestamp(now - DAYS * 86400, datetime.UTC),
                             datetime.datetime.fromtimestamp(now, datetime.UTC))[-20000:]
    if r is None or len(r) < 800:
        return None
    c = [float(x) for x in r["close"]][:-1]
    h = [float(x) for x in r["high"]][:-1]
    l = [float(x) for x in r["low"]][:-1]
    t = [int(x) for x in r["time"]][:-1]
    n = len(c)
    P = cfg["P"]
    e2 = ema_s(c, 200)
    atr = atr_n(h, l, c)
    dh = [0.0] * n
    dl = [0.0] * n
    for i in range(P, n):
        dh[i] = max(h[i - P:i])
        dl[i] = min(l[i - P:i])
    pnls = []
    risks = []
    skipped = 0
    i = 201
    free = 0
    while i < n - 2:
        if t[i] < free or atr[i] <= 0:
            i += 1
            continue
        sig = 0
        if c[i] > dh[i] and c[i] > e2[i]:
            sig = 1
        elif c[i] < dl[i] and c[i] < e2[i]:
            sig = -1
        if sig == 0:
            i += 1
            continue
        slp = 1.5 * atr[i] / pt
        risk = slp * u
        if risk > cfg["cap"]:
            skipped += 1
            i += 1
            continue
        risks.append(risk)
        entry = c[i] + sig * spr * pt * 0.5
        tp = entry + sig * TP_MULT * slp * pt
        sl = entry - sig * slp * pt
        end = min(n, i + 1 + MAX_BARS)
        pnl = None
        out = end - 1
        for k in range(i + 1, end):
            if sig == 1:
                if l[k] <= sl:
                    pnl = (sl - entry) * u / pt - cost
                    out = k
                    break
                if h[k] >= tp:
                    pnl = (tp - entry) * u / pt - cost
                    out = k
                    break
            else:
                if h[k] >= sl:
                    pnl = (entry - sl) * u / pt - cost
                    out = k
                    break
                if l[k] <= tp:
                    pnl = (entry - tp) * u / pt - cost
                    out = k
                    break
        if pnl is None:
            ex = c[out] + sig * spr * pt * 0.5
            pnl = (ex - entry) * sig * u / pt - cost
        pnls.append(pnl)
        free = t[out]
        i = out + 1
    if not pnls:
        return {"n": 0, "wr": 0, "is": 0, "oos": 0, "net": 0, "dd": 0,
                "med_risk": 0, "skipped": skipped, "auto": False, "reason": "aucun trade"}
    cut = int(len(pnls) * 0.7)
    isn = sum(pnls[:cut])
    oos = sum(pnls[cut:])
    eq = 0.0
    peak = 0.0
    mdd = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    med_risk = sorted(risks)[len(risks) // 2] if risks else 0
    ok = len(pnls) >= 20 and isn > 0 and oos > 0 and med_risk <= MARKETS[S]["cap"]
    reason = ""
    if not ok:
        if len(pnls) < 20:
            reason = "trop peu de trades (%d)" % len(pnls)
        elif isn <= 0:
            reason = "IS negatif (%+.0f$)" % isn
        elif oos <= 0:
            reason = "OOS negatif (%+.0f$)" % oos
        else:
            reason = "risque median %.0f$ > %.0f$" % (med_risk, cfg["cap"])
    return {"n": len(pnls), "wr": round(100.0 * len([x for x in pnls if x > 0]) / len(pnls), 1),
            "is": round(isn, 1), "oos": round(oos, 1), "net": round(eq, 1), "dd": round(mdd, 1),
            "med_risk": round(med_risk, 2), "skipped": skipped, "auto": ok, "reason": reason}


def main():
    if not mt5.initialize(path=XM):
        print("ERREUR: terminal MT5 injoignable (validation annulee)")
        return
    result = {"updated_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "markets": {}}
    lines = ["VALIDATION AUTO-MARCHES (Donchian swing, regles engine exactes, 2 ans)"]
    try:
        for S, cfg in MARKETS.items():
            mt5.symbol_select(S, True)
            v = backtest(S, cfg)
            if v is None:
                continue
            v.update(cfg)
            result["markets"][S] = v
            etat = "ACTIF" if v["auto"] else ("REJETE: " + v["reason"] if v["reason"] else "REJETE")
            lines.append("  %-7s n=%3d wr=%2.0f%% IS %+6.0f$ OOS %+6.0f$ risqm %.0f$ skip %d -> %s" % (
                S, v["n"], v["wr"], v["is"], v["oos"], v["med_risk"], v["skipped"], etat))
    finally:
        mt5.shutdown()
    # fusion avec l'existant pour preserver un marche force manuellement (force=true)
    old = {}
    try:
        old = json.load(open(OUT, encoding="utf-8")).get("markets", {})
    except Exception:
        pass
    for S, v in result["markets"].items():
        if old.get(S, {}).get("force"):
            v["force"] = True
            v["auto"] = old[S].get("auto", False)  # force = l'etat decide par l'humain
            v["reason"] = "FORCE humain"
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    print(chr(10).join(lines))
    actives = [S for S, v in result["markets"].items() if v.get("auto")]
    print("AUTO ACTIF: " + (", ".join(actives) if actives else "AUCUN"))
    print("Fichier: " + OUT)


if __name__ == "__main__":
    main()
