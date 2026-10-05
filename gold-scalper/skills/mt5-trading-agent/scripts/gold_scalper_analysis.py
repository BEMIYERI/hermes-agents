#!/usr/bin/env python3
"""GOLD SCALPER — Multi-timeframe analysis script for MT5.

Polls MT5 for GOLD on M15/M5/M1, computes EMA/RSI/ATR/swing structure,
and prints a formatted signal fiche. Standalone — no dependency on the
agent framework.

Usage:
    python3 gold_scalper_analysis.py

Requirements:
    - MetaTrader5 pip package installed
    - MT5 terminal running with GOLD account logged in
    - pandas, numpy installed
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime

SYMBOL = "GOLD"
ACCOUNT_ID = 336883354
SERVER = "XMGlobal-MT5 9"

TIMEFRAMES = {
    "M15": mt5.TIMEFRAME_M15,
    "M5": mt5.TIMEFRAME_M5,
    "M1": mt5.TIMEFRAME_M1,
}

# Candle counts per timeframe (must have enough history for all indicators)
CANDLE_COUNTS = {
    "M15": 300,
    "M5": 300,
    "M1": 300,
}


def init_mt5():
    """Initialize MT5 connection. Returns True on success."""
    if not mt5.initialize(login=ACCOUNT_ID, server=SERVER):
        # fallback: init without login (terminal must already be logged in)
        if not mt5.initialize():
            print(f"MT5 init failed: {mt5.last_error()}")
            return False
    return True


def get_candles(tf_constant, count):
    """Fetch candles as a DatetimeIndex DataFrame. Returns None on failure."""
    rates = mt5.copy_rates_from_pos(SYMBOL, tf_constant, 0, count)
    if rates is None:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)
    return df


def ema(df, period):
    """Return latest EMA value as a float."""
    return float(df["close"].ewm(span=period, adjust=False).mean().iloc[-1])


def rsi(df, period=14):
    """Return latest RSI value as a float."""
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return float(100 - (100 / (1 + rs)))


def atr(df, period=14):
    """Return latest ATR value as a float."""
    if len(df) < period + 1:
        return None
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr_vals = pd.Series(tr).rolling(window=period).mean().values
    return float(atr_vals[-1])


def swing_structure(df, lookback=30):
    """Detect swing highs/lows in the last `lookback` candles.

    Returns two lists of (timestamp, price) tuples.
    """
    recent = df.iloc[-lookback:]
    highs = []
    lows = []
    for i in range(2, len(recent) - 2):
        h = recent["high"].iloc[i]
        l = recent["low"].iloc[i]
        if h >= recent["high"].iloc[i - 2 : i + 3].max():
            highs.append((recent.index[i], h))
        if l <= recent["low"].iloc[i - 2 : i + 3].min():
            lows.append((recent.index[i], l))
    return highs, lows


def fmt_ts(ts):
    """Format a pandas Timestamp to HH:MM."""
    return ts.strftime("%H:%M")


def main():
    if not init_mt5():
        return

    mt5.symbol_select(SYMBOL, True)
    tick = mt5.symbol_info_tick(SYMBOL)
    bid = tick.bid
    ask = tick.ask

    acc = mt5.account_info()

    print("=" * 60)
    print("GOLD SCALPER AI - ANALYSE MULTI-TEMPORALITE")
    print("=" * 60)
    print(f"Temps: {datetime.now().strftime('%H:%M:%S')}")
    if acc:
        print(f"Compte: {acc.login} | Balance: ${acc.balance:.2f} | Equity: ${acc.equity:.2f}")
    print(f"{SYMBOL}: Bid {bid:.2f} / Ask {ask:.2f}")

    # ---- Fetch all timeframes ----
    data = {}
    for name, tf in TIMEFRAMES.items():
        candles = get_candles(tf, CANDLE_COUNTS[name])
        if candles is not None and len(candles) >= 50:
            data[name] = candles
        else:
            print(f"[WARN] {name} data unavailable (got {len(candles) if candles is not None else 0} candles)")

    # ---- M15 trend ----
    if "M15" in data:
        m15 = data["M15"]
        close15 = m15["close"]
        last15 = float(close15.iloc[-1])
        ema9_15 = ema(m15, 9)
        ema21_15 = ema(m15, 21)
        ema50_15 = ema(m15, 50)
        ema200_15 = ema(m15, 200)
        atr15 = atr(m15, 14)
        rsi15 = rsi(m15, 14)

        print("\n" + "=" * 60)
        print("1. TENDANCE M15 - ENVIRONNEMENT MACRO")
        print("=" * 60)
        print(f"Prix dernier M15: {last15:.2f}")
        print(f"EMA 9:  {ema9_15:.2f}  {'AU-DESSUS' if last15 > ema9_15 else 'EN-DESSOUS'}")
        print(f"EMA 21: {ema21_15:.2f}  {'AU-DESSUS' if last15 > ema21_15 else 'EN-DESSOUS'}")
        print(f"EMA 50: {ema50_15:.2f}  {'AU-DESSUS' if last15 > ema50_15 else 'EN-DESSOUS'}")
        print(f"EMA 200: {ema200_15:.2f}  {'TL BULL (au-dessus)' if last15 > ema200_15 else 'TL BEAR (en-dessous)'}")
        print(f"ATR M15 (14): {atr15:.2f} pts = ${atr15:.2f}/lot")
        rsi_label = "SURACHETE (>70)" if rsi15 > 70 else "SURVENTE (<30)" if rsi15 < 30 else "NORMAL"
        print(f"RSI M15 (14): {rsi15:.1f} - {rsi_label}")

        hh15 = float(m15["high"].iloc[-20:].max())
        ll15 = float(m15["low"].iloc[-20:].min())
        print(f"HH (20b M15): {hh15:.2f}")
        print(f"LL (20b M15): {ll15:.2f}")
        print(f"Range M15 20b: {hh15 - ll15:.2f} pts")

        mom15 = (last15 - float(close15.iloc[-10])) / float(close15.iloc[-10]) * 100
        print(f"Momentum M15 (10b): {mom15:+.2f}% - {'BULL' if mom15 > 0.3 else 'BEAR' if mom15 < -0.3 else 'CONSOL'}")

    # ---- M5 structure ----
    if "M5" in data:
        m5 = data["M5"]
        last5 = float(m5["close"].iloc[-1])
        ema9_5 = ema(m5, 9)
        ema21_5 = ema(m5, 21)
        rsi5 = rsi(m5, 10)
        atr5 = atr(m5, 14)

        print("\n" + "=" * 60)
        print("2. STRUCTURE M5 - S/O / STRUCTURE PRECISE")
        print("=" * 60)
        print(f"Prix dernier M5: {last5:.2f}")
        print(f"EMA 9 M5:  {ema9_5:.2f}")
        print(f"EMA 21 M5: {ema21_5:.2f}")
        print(f"RSI M5 (10): {rsi5:.1f}")
        print(f"ATR M5 (14): {atr5:.2f} pts")

        highs5, lows5 = swing_structure(m5)
        last_h = highs5[-3:] if len(highs5) >= 3 else highs5
        last_l = lows5[-3:] if len(lows5) >= 3 else lows5

        print(f"Derniers swing highs M5: {[(fmt_ts(t), f'{v:.2f}') for t, v in last_h]}")
        print(f"Derniers swing lows M5:  {[(fmt_ts(t), f'{v:.2f}') for t, v in last_l]}")

        if len(last_h) >= 2:
            hh_trend = "HIGHER HIGHS ▲" if last_h[-1][1] > last_h[-2][1] else "LOWER HIGHS ▼"
            print(f"Trend swings highs: {hh_trend}")
        if len(last_l) >= 2:
            ll_trend = "LOWER LOWS ▼" if last_l[-1][1] < last_l[-2][1] else "HIGHER LOWS ▲"
            print(f"Trend swings lows: {ll_trend}")

        mom5 = (last5 - float(m5["close"].iloc[-20])) / float(m5["close"].iloc[-20]) * 100
        print(f"Momentum M5 (20b): {mom5:+.2f}%")

    # ---- M1 entry ----
    if "M1" in data:
        m1 = data["M1"]
        last1 = float(m1["close"].iloc[-1])
        m1_range = float(m1["high"].iloc[-1]) - float(m1["low"].iloc[-1])
        ema9_1 = ema(m1, 9)
        ema21_1 = ema(m1, 21)
        rsi1 = rsi(m1, 10)
        atr1 = atr(m1, 14)
        last_time = m1.index[-1]

        print("\n" + "=" * 60)
        print("3. ENTREE M1 - PRIX PRECIS / TRIGGER")
        print("=" * 60)
        print(f"Prix M1: {last1:.2f} ({fmt_ts(last_time)})")
        print(f"Range M1 (courante): {m1_range:.2f} pts")
        print(f"EMA 9 M1:  {ema9_1:.2f}")
        print(f"EMA 21 M1: {ema21_1:.2f}")
        print(f"RSI M1 (10): {rsi1:.1f}")
        print(f"ATR M1 (14): {atr1:.2f} pts = ${atr1:.2f}/lot")

        mom1 = (last1 - float(m1["close"].iloc[-20])) / float(m1["close"].iloc[-20]) * 100
        print(f"Momentum M1 (20b): {mom1:+.2f}%")

        print("\n--- SCENARIOS ENTREE M1 ---")

        if last1 > ema9_1 and last1 > ema21_1:
            print("BULLISH: Prix > EMA 9 & 21 → Long en pullback vers EMA 9/21")
            print(f"  Zone entry long: {ema9_1:.2f} - {ema21_1:.2f}")
            sl_long = ema21_1 - atr1 * 0.5
            tp_long = last1 + atr1 * 1.5
            rr = (tp_long - last1) / max(0.01, (last1 - sl_long))
            print(f"  SL long: {sl_long:.2f} (below EMA 21, 0.5 ATR)")
            print(f"  TP long: {tp_long:.2f} (1.5 ATR)")
            print(f"  RR ratio: 1:{rr:.1f}")
        elif last1 < ema9_1 and last1 < ema21_1:
            print("BEARISH: Prix < EMA 9 & 21 → Short en pullback vers EMA 9/21")
            print(f"  Zone entry short: {ema9_1:.2f} - {ema21_1:.2f}")
            sl_short = ema21_1 + atr1 * 0.5
            tp_short = last1 - atr1 * 1.5
            rr = (last1 - tp_short) / max(0.01, (sl_short - last1))
            print(f"  SL short: {sl_short:.2f} (above EMA 21, 0.5 ATR)")
            print(f"  TP short: {tp_short:.2f} (1.5 ATR)")
            print(f"  RR ratio: 1:{rr:.1f}")
        else:
            print("NEUTRE: Prix entre EMA 9 et 21 → Attendre breakout")

    # ---- Spread / Risk ----
    print("\n" + "=" * 60)
    print("4. SPREAD / COUTS / RISQUE")
    print("=" * 60)

    spread_pts = ask - bid
    # GOLD on XM Global: tick_value = $1.0/point/lot (digits=2)
    tick_value = 1.0
    min_lot = 0.01
    max_lot = 100.0

    print(f"Spread reel: {spread_pts:.2f} pts = ${spread_pts:.2f}/lot")
    print(f"Spread $, lot 0.01: ${spread_pts * tick_value * 0.01:.3f}")
    print(f"Spread $, lot 0.05: ${spread_pts * tick_value * 0.05:.2f}")
    print(f"Spread $, lot 0.10: ${spread_pts * tick_value * 0.10:.2f}")
    print(f"Tick value: ${tick_value}/point/lot (GOLD XM standard)")
    print(f"Lot min: {min_lot} | Lot max: {max_lot} | Leverage: 1000:1")

    if acc:
        capital = acc.balance
        for lot in [0.01, 0.05, 0.10]:
            spread_cost = spread_pts * tick_value * lot
            print(f"  Spread cost {lot}L: ${spread_cost:.2f} ({(spread_cost/capital)*100:.1f}% du capital)")

    # ---- Synthesis ----
    print("\n" + "=" * 60)
    print("5. SYNTHESE SIGNAL GOLD SCALPER")
    print("=" * 60)
    print(f"{SYMBOL} @ M1: {last1:.2f} | Bid {bid:.2f} / Ask {ask:.2f}")
    print(f"Spread: {spread_pts:.2f} pts")

    if "M15" in data:
        trend_label = "BULL" if last15 > ema200_15 else "BEAR"
        print(f"M15 trend: {trend_label} (vs EMA 200) | RSI: {rsi15:.1f} | ATR: {atr15:.2f}pts")
    if "M5" in data:
        print(f"M5 structure: voir swings | RSI: {rsi5:.1f} | ATR: {atr5:.2f}pts")
    if "M1" in data:
        entry_label = "BULL pullback EMA9/21" if last1 > ema9_1 else "BEAR pullback EMA9/21" if last1 < ema9_1 else "NEUTRE"
        print(f"M1 entry: {entry_label} | RSI: {rsi1:.1f} | ATR: {atr1:.2f}pts")

    if acc:
        spread_pct = (spread_pts * tick_value * 0.01 / acc.balance) * 100
        print(f"RISK: lot 0.01 max → spread = ${spread_pts*tick_value*0.01:.3f} = {spread_pct:.1f}% capital")
    if "M1" in data:
        print(f"SL/TP base: 0.5 ATR / 1.5 ATR = {atr1*0.5:.2f}pts / {atr1*1.5:.2f}pts")

    mt5.shutdown()


if __name__ == "__main__":
    main()
