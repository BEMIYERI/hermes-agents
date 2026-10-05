# -*- coding: utf-8 -*-
"""
gsa_alert.py v2.2 — surveillant SIGNALS MULTI-MARCHE + SWING H1 -> push (cron no_agent).
Cartes poussees UNIQUEMENT a la transition (d edup par marche+barre). Stdout vide = rien.
"""
import datetime
import json
import os
import time

import MetaTrader5 as mt5

XM_PATH = r"C:\Program Files\XM Global MT5\terminal64.exe"
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gsa_alert_state.json")

MARKETS = {
    "GOLD":   (65, 25.0, 75.0),
    "EURUSD": (30, 30.0, 70.0),
    "GBPUSD": (35, 30.0, 70.0),
    "USDJPY": (35, 30.0, 70.0),
    "BTCUSD": (6000, 25.0, 75.0),
}
POOL_BY_HOUR = {
    range(0, 7):   ["USDJPY", "EURUSD", "GBPUSD", "GOLD"],
    range(7, 16):  ["EURUSD", "GOLD", "GBPUSD", "USDJPY"],
    range(16, 21): ["GOLD", "EURUSD", "GBPUSD", "USDJPY"],
    range(21, 22): ["BTCUSD"],
    range(22, 24): ["USDJPY", "EURUSD", "GBPUSD", "GOLD", "BTCUSD"],
}
WEEKEND_POOL = ["BTCUSD"]


def load_state():
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st):
    try:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(st, f)
    except Exception:
        pass


def ema(v, p):
    k = 2.0 / (p + 1.0)
    o = [float(v[0])]
    for x in v[1:]:
        o.append(float(x) * k + o[-1] * (1.0 - k))
    return o


def rsi(closes, period=14):
    d = [closes[i + 1] - closes[i] for i in range(len(closes) - 1)]
    if len(d) < period:
        return 50.0
    ag = sum(x for x in d[:period] if x > 0) / period
    al = sum(-x for x in d[:period] if x < 0) / period
    for x in d[period:]:
        ag = (ag * (period - 1) + (x if x > 0 else 0.0)) / period
        al = (al * (period - 1) + (-x if x < 0 else 0.0)) / period
    if al == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + ag / al)


def atr(h, l, c, period=14):
    trs = []
    for i in range(1, len(c)):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    if len(trs) < period:
        return 0.0
    a = sum(trs[:period]) / period
    for t in trs[period:]:
        a = (a * (period - 1) + t) / period
    return a


def pool_now(now_utc):
    if now_utc.weekday() >= 5:
        return WEEKEND_POOL
    for rng, pool in POOL_BY_HOUR.items():
        if now_utc.hour in rng:
            return pool
    return ["BTCUSD"]


def swing_block(cards, st):
    """SWING GOLD H1: Donchian48 + EMA200 (meme code que gsa_swing.py)."""
    mt5.symbol_select("GOLD", True)
    h1 = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_H1, 1, 320)
    if h1 is None or h1.shape[0] < 260:
        return
    ch = [float(x) for x in h1["close"]]
    hh = [float(x) for x in h1["high"]]
    hl = [float(x) for x in h1["low"]]
    m = len(ch) - 1
    e = ch[0]
    k = 2.0 / 201.0
    for z in range(1, m + 1):
        e = ch[z] * k + e * (1.0 - k)
    hi48 = max(hh[m - 48:m])
    lo48 = min(hl[m - 48:m])
    a = 0.0
    for z in range(1, 15):
        a += max(hh[z] - hl[z], abs(hh[z] - ch[z - 1]), abs(hl[z] - ch[z - 1])) / 14.0
    for z in range(15, m + 1):
        tr = max(hh[z] - hl[z], abs(hh[z] - ch[z - 1]), abs(hl[z] - ch[z - 1]))
        a = (a * 13.0 + tr) / 14.0
    lastc = ch[m]
    sw = 1 if (lastc > hi48 and lastc > e) else (-1 if (lastc < lo48 and lastc < e) else 0)
    barT = int(h1["time"][-1])
    prev = st.get("SWING", [0, 0])
    if sw != 0 and (prev[1] != sw or prev[0] != barT):
        st["SWING"] = [barT, sw]
        si = mt5.symbol_info("GOLD")
        upp01 = si.trade_tick_value * si.point / si.trade_tick_size * 0.01
        slp = 1.5 * a
        usd = slp * upp01
        side = "BUY" if sw == 1 else "SELL"
        slp_px = lastc - slp if sw == 1 else lastc + slp
        tpp = lastc + 3 * slp if sw == 1 else lastc - 3 * slp
        ai = mt5.account_info()
        cards.append(chr(10).join([
            "SWING H1 GOLD - " + side,
            "Px %.2f | SL %.2f (-$%.0f) | TP %.2f (+$%.0f)" % (lastc, slp_px, usd, tpp, 3 * usd),
            "Cassure canal 48xH1 + EMA200 (validee IS+OOS 2 ans).",
            "Risque $%.0f = %.0f%% du solde %.0f$ (lot 0.01)." % (usd, 100.0 * usd / ai.balance, ai.balance),
            "L'executeur SWING prend la position automatiquement (magic 777201).",
        ]))


def main():
    if not mt5.initialize(path=XM_PATH):
        return
    cards = []
    st = load_state()
    try:
        pool = pool_now(datetime.datetime.now(datetime.timezone.utc))
        for sym in pool:
            maxspr, rlo, rhi = MARKETS[sym]
            mt5.symbol_select(sym, True)
            si = mt5.symbol_info(sym)
            tick = mt5.symbol_info_tick(sym)
            if si is None or tick is None:
                continue
            pt = si.point
            m1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 250)
            m15 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 120)
            if m1 is None or m1.shape[0] < 120 or m15 is None or m15.shape[0] < 60:
                continue
            if tick.time - int(m1["time"][-1]) > 180:
                continue
            c1 = [float(x) for x in m1["close"]][:-1]
            h1b = [float(x) for x in m1["high"]][:-1]
            l1b = [float(x) for x in m1["low"]][:-1]
            c15 = [float(x) for x in m15["close"]][:-1]
            px = c1[-1]
            e9, e21 = ema(c1, 9)[-1], ema(c1, 21)[-1]
            E9, E21 = ema(c15, 9)[-1], ema(c15, 21)[-1]
            rv = rsi(c1)
            ap = atr(h1b, l1b, c1) / pt
            spr = int(round((tick.ask - tick.bid) / pt))
            sig = 1 if (px > e9 and px > e21 and E9 > E21) else (-1 if (px < e9 and px < e21 and E9 < E21) else 0)
            quality = sig != 0 and spr <= maxspr and rlo < rv < rhi
            bar = int(m1["time"][-2])
            prev = st.get(sym, [0, 0])
            if quality and (prev[0] != bar or prev[1] != sig):
                st[sym] = [bar, sig]
                usd_spr = spr * si.trade_tick_value * pt / si.trade_tick_size * 0.01
                cards.append(chr(10).join([
                    "SIGNAL M1 %s - %s (secondaire, scalp AUTO=off)" % ("BUY" if sig == 1 else "SELL", sym),
                    "Px %.2f | M15 %s | RSI %.0f | ATR %.0f pt | Spread %d pt (%.2f$)" % (
                        px, "BULL" if E9 > E21 else "BEAR", rv, ap, spr, usd_spr),
                    "Fenetre courante: " + " ".join(pool),
                ]))
        swing_block(cards, st)
        st["last_scan"] = int(time.time())
        save_state(st)
    finally:
        mt5.shutdown()
    if cards:
        print(chr(10).join(cards))


if __name__ == "__main__":
    main()
