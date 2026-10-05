#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rapport pour la revue automatique GOLD SCALPER AI.

Produit un resume chiffre et sans opinion : etat du compte, position en cours,
statistiques de l'EA, evenements sur la fenetre demandee, et multi-TF.
Lu par le job cron, qui en fait l'analyse redigee.

Usage : python gsa_report.py [minutes_de_la_fenetre]   (defaut 30)
"""

import os
import sys
import json
import glob
import datetime
from collections import Counter

import MetaTrader5 as mt5

QUEUE = r"C:\Users\nanga\AppData\Local\hermes\cache\gsa_events.jsonl"
STATE = r"C:\Users\nanga\AppData\Local\hermes\cache\gsa_state.json"
LOGDIR = (r"C:\Users\nanga\AppData\Roaming\MetaQuotes\Terminal"
          r"\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Logs")
SYMBOL = "GOLD"
WINDOW_MIN = int(os.environ.get("GSA_WINDOW_MIN", "30"))

now = datetime.datetime.now()
since = now - datetime.timedelta(minutes=WINDOW_MIN)
out = {"genere_le": now.strftime("%Y-%m-%d %H:%M:%S"), "fenetre_min": WINDOW_MIN}

# ---------------------------------------------------------------- compte
if not mt5.initialize():
    out["erreur"] = "MT5 inaccessible"
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0)

acc = mt5.account_info()
if acc is None:
    out["erreur"] = "account_info() a retourne None"
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0)

out["compte"] = {
    "login": acc.login,
    "demo": acc.trade_mode == 0,
    "balance": round(acc.balance, 2),
    "equity": round(acc.equity, 2),
    "margin_free": round(acc.margin_free, 2),
    "variation_jour_pct": round(acc.profit, 2),
}

# ---------------------------------------------------------------- position
positions = mt5.positions_get(symbol=SYMBOL)
sym = mt5.symbol_info(SYMBOL)
tick = mt5.symbol_info_tick(SYMBOL)
pt = sym.point if sym else 0.01

if positions:
    p = positions[0]
    out["position"] = {
        "type": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
        "volume": p.volume,
        "entree": p.price_open,
        "sl": p.sl, "tp": p.tp,
        "profit_usd": round(p.profit, 2),
        "duree_min": int((now.timestamp() - p.time) // 60),
        "dist_sl_pts": round(abs(p.price_open - p.sl) / pt, 1) if p.sl else None,
        "dist_tp_pts": round(abs(p.tp - p.price_open) / pt, 1) if p.tp else None,
        "commentaire": p.comment,
    }
else:
    out["position"] = None

out["marche"] = {
    "bid": tick.bid if tick else None,
    "ask": tick.ask if tick else None,
    "spread_pts": sym.spread if sym else None,
}

# ---------------------------------------------------------------- multi-TF
import numpy as np


def ema(a, p):
    if len(a) == 0:
        return None
    k = 2.0 / (p + 1.0)
    o = a[0]
    for x in a[1:]:
        o = x * k + o * (1 - k)
    return o


def rsi(c, p=14):
    """RSI de Wilder sur les dernieres bougies."""
    if len(c) < p + 1:
        return None
    d = np.diff(c[-(p + 1):])
    up = d[d > 0].sum() / p
    dn = (-d[d < 0]).sum() / p
    if dn == 0:
        return 100.0 if up > 0 else 50.0
    return float(100.0 - 100.0 / (1.0 + up / dn))


def atr(r, p=14):
    if len(r) < 2:
        return None
    h, l, c = r["high"], r["low"], r["close"]
    tr = np.maximum(h[1:] - l[1:],
                    np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    return float(np.mean(tr[-p:]))


m = {}
for tf, label, ema_p in ((mt5.TIMEFRAME_M15, "M15", (9, 21, 50, 200)),
                         (mt5.TIMEFRAME_M5, "M5", (9, 21)),
                         (mt5.TIMEFRAME_M1, "M1", (9, 21))):
    r = mt5.copy_rates_range(SYMBOL, tf, now - datetime.timedelta(days=25), now)
    if r is None or len(r) < 5:
        m[label] = {"erreur": "historique indisponible"}
        continue
    c = r["close"]
    d = {"atr": round(atr(r), 2)}
    for e in ema_p:
        d["ema%d" % e] = round(ema(c, e), 2)
    d["rsi14"] = round(rsi(c), 1) if rsi(c) is not None else None
    d["biais"] = ("BULL" if c[-1] > d.get("ema21", d.get("ema50", c[-1])) else "BEAR")
    m[label] = d
out["multi_tf"] = m

# ---------------------------------------------------------------- evenements
events = []
if os.path.exists(QUEUE):
    with open(QUEUE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            try:
                ts = datetime.datetime.fromisoformat(e["ts"])
            except Exception:
                continue
            if ts >= since:
                events.append(e)

counts = Counter(e["kind"] for e in events)
out["evenements"] = {
    "total": len(events),
    "par_type": dict(counts),
    "notables": [
        {"ts": e["ts"], "kind": e["kind"], "titre": e["title"], "detail": e["detail"]}
        for e in events if e["kind"] in ("POSITION_OUVERTE", "POSITION_FERMEE",
                                         "ERREUR_ORDRE", "CAPITAL_CRITIQUE",
                                         "DRAWDOWN", "MT5_DOWN")
    ],
}

# ---------------------------------------------------------------- journal EA
import re
rx_open = re.compile(r"TRADE (OUVERT|SWING OUVERT)", re.I)
rx_close = re.compile(r"TRADE (?:CLOSED|SWING CLOS) - (\w+)", re.I)
rx_sl = re.compile(r"\[GSAI\]\s+SL\s+(\d+)\s+pts.*?TP\s+(\d+)\s+pts.*?R:R\s+1:([\d.]+)"
                   r".*?risque\s+([\d.]+)%", re.I)
rx_att = re.compile(r"\[GSAI\]\s+ATTENTE\s*\|\s*([^|]+)\|", re.I)

files = glob.glob(os.path.join(LOGDIR, "*.log"))
ea = {"lignes_attente": 0, "raisons_attente": Counter(), "trades_ouverts": 0,
      "trades_closes": 0, "dernier_sl": None, "activite_recente": False,
      "swing": {"trades_ouverts": 0, "trades_closes": 0, "bloques": Counter(),
                "seuil_annonce": False}}
if files:
    lg = max(files, key=os.path.getmtime)
    try:
        with open(lg, "rb") as f:
            raw = f.read()
        txt = raw.decode("utf-16-le", errors="ignore")
    except Exception:
        txt = ""
    # garder seulement la fenetre : on prend le texte brut recent
    for line in txt.split("\n"):
        if "GSAI" not in line and "GSA-SWING" not in line:
            continue
        is_swing = "GSA-SWING" in line
        if rx_open.search(line):
            if is_swing:
                ea["swing"]["trades_ouverts"] += 1
            else:
                ea["trades_ouverts"] += 1
        elif rx_close.search(line):
            if is_swing:
                ea["swing"]["trades_closes"] += 1
            else:
                ea["trades_closes"] += 1
        elif is_swing and "pas de trade" in line:
            m = line.split("|", 1)[-1].strip()[:50]
            ea["swing"]["bloques"][m] += 1
        elif is_swing and "SEUIL A ATTEINDRE" in line:
            ea["swing"]["seuil_annonce"] = True
        m_sl = rx_sl.search(line)
        if m_sl:
            ea["dernier_sl"] = {"sl_pts": int(m_sl.group(1)), "tp_pts": int(m_sl.group(2)),
                                "rr": float(m_sl.group(3)),
                                "risque_pct": float(m_sl.group(4))}
        m_at = rx_att.search(line)
        if m_at:
            ea["lignes_attente"] += 1
            ea["raisons_attente"][m_at.group(1).strip()[:60]] += 1
    ea["raisons_attente"] = dict(ea["raisons_attente"].most_common(6))
    ea["swing"]["bloques"] = dict(ea["swing"]["bloques"].most_common(6))
    try:
        ea["taille_log_octets"] = os.path.getsize(lg)
        ea["log_modifie"] = datetime.datetime.fromtimestamp(
            os.path.getmtime(lg)).strftime("%H:%M:%S")
    except Exception:
        pass
out["ea"] = ea

# ---------------------------------------------------------------- etat superviseur
if os.path.exists(STATE):
    try:
        with open(STATE, encoding="utf-8") as f:
            out["superviseur"] = json.load(f)
    except Exception:
        pass

print(json.dumps(out, ensure_ascii=False, indent=1))
