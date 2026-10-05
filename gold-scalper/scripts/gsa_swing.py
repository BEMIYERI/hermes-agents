# -*- coding: utf-8 -*-
"""
gsa_swing.py v2 — EXECUTEUR SWING MULTI-MARCHE (activation par validation mecanique)
Lit gsa_swing_markets.json (produit par gsa_validator.py, cron hebdo) et ne trade
AUTO que les marches avec auto=true. Regles = backtest valide:
  signal: cloture > max(high P barres) ET > EMA200 -> BUY (inverse pour SELL)
  SL 1.5*ATR14(tf), TP 3xSL, time-exit 32 barres, AUCUN soft/trailing
  lot = volume_min broker (0.01), skip si risque > cap du marche
Garde-fous compte: 1 position GLOBALE simultanee, plancher solde 60$,
cooldown 1h apres sortie, dedup par marche+barre H1, magic 777201.
Cron Hermes no_agent 1x5min; stdout = carte (vide = rien).
"""
import json
import os
import time

import MetaTrader5 as mt5

XM = r"C:\Program Files\XM Global MT5\terminal64.exe"
BASE = os.path.dirname(os.path.abspath(__file__))
STATE_F = os.path.join(BASE, "gsa_swing_state.json")
MKTS_F = os.path.join(BASE, "gsa_swing_markets.json")
PAUSE_F = os.path.join(BASE, "gsa_swing_pause.txt")
LOCK = os.path.join(BASE, "gsa_slot_lock.json")
LOG_F = os.path.join(BASE, "gsa_swing.jsonl")

MAGIC = 777201
BAL_FLOOR = 10.0          # survie technique (decision humaine 02/10: plus de pause sur pertes)
COOLDOWN_AFTER_EXIT = 900  # 15 min (volume max autorise)
DRY = os.environ.get("GSA_SWING_DRY") == "1"


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_state(st):
    try:
        with open(STATE_F, "w", encoding="utf-8") as f:
            json.dump(st, f)
    except Exception:
        pass


def log(ev):
    try:
        ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        with open(LOG_F, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def ema(v, p):
    k = 2.0 / (p + 1.0)
    o = v[0]
    for x in v[1:]:
        o = x * k + o * (1.0 - k)
    return o


def evaluate(sym, cfg):
    """Retourne (dict signal, None) ou (None, motif)."""
    si = mt5.symbol_info(sym)
    if si is None:
        return None, "symbole absent"
    tf = mt5.TIMEFRAME_H1 if cfg.get("tf", "H1") == "H1" else mt5.TIMEFRAME_H4
    P = int(cfg.get("P", 48))
    cap = float(cfg.get("cap", 25.0))
    h1 = mt5.copy_rates_from_pos(sym, tf, 1, P + 260)
    if h1 is None or h1.shape[0] < 200 + P:
        return None, "historique insuffisant"
    c = [float(x) for x in h1["close"]]
    h = [float(x) for x in h1["high"]]
    l = [float(x) for x in h1["low"]]
    t = [int(x) for x in h1["time"]]
    m = len(c) - 1
    e200 = ema(c[:m + 1], 200)
    hi = max(h[m - P:m])
    lo = min(l[m - P:m])
    a = 0.0
    for z in range(1, 15):
        a += max(h[z] - l[z], abs(h[z] - c[z - 1]), abs(l[z] - c[z - 1])) / 14.0
    for z in range(15, m + 1):
        tr = max(h[z] - l[z], abs(h[z] - c[z - 1]), abs(l[z] - c[z - 1]))
        a = (a * 13.0 + tr) / 14.0
    lastc = c[m]
    sig = 1 if (lastc > hi and lastc > e200) else (-1 if (lastc < lo and lastc < e200) else 0)
    if sig == 0:
        return None, "attente"
    pt = si.point
    lot = si.volume_min
    u = si.trade_tick_value * pt / si.trade_tick_size * lot
    slp = 1.5 * a
    risk_usd = slp * u
    if risk_usd > cap:
        return None, "risque %.0f$ > cap %.0f$" % (risk_usd, cap)
    tick = mt5.symbol_info_tick(sym)
    entry_px = tick.ask if sig == 1 else tick.bid
    sl = entry_px - sig * slp
    tp = entry_px + sig * 3.0 * slp
    return {"sym": sym, "sig": sig, "bar": t[m], "px": lastc, "lot": lot,
            "sl": round(sl, si.digits), "tp": round(tp, si.digits),
            "risk": risk_usd, "atr": a, "channel": (lo, hi), "ema200": e200,
            "max_bars": int(cfg.get("max_bars", 32)), "tf_sec": 3600 if cfg.get("tf", "H1") == "H1" else 14400}, None


def try_enter(s):
    tick = mt5.symbol_info_tick(s["sym"])
    otype = mt5.ORDER_TYPE_BUY if s["sig"] == 1 else mt5.ORDER_TYPE_SELL
    pr = tick.ask if s["sig"] == 1 else tick.bid
    for filling in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC):
        req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": s["sym"], "volume": s["lot"],
               "type": otype, "price": pr, "sl": s["sl"], "tp": s["tp"], "deviation": 25,
               "magic": MAGIC, "comment": "GSAI-SWING", "type_time": mt5.ORDER_TIME_GTC,
               "type_filling": filling}
        if DRY:
            return {"retcode": 10009, "order": 0}, None
        chk = mt5.order_check(req)
        if chk is None:
            continue
        if chk.retcode not in (0, mt5.TRADE_RETCODE_DONE, 10009):
            if chk.retcode == 10019:
                return None, "marge insuffisante"
            continue
        r = mt5.order_send(req)
        if r is not None and r.retcode == mt5.TRADE_RETCODE_DONE:
            return r, None
    return None, "ordre refuse"


def send_close(p, why):
    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        return None
    otype = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    pr = tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask
    for filling in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC):
        r = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": p.symbol, "volume": p.volume,
                            "type": otype, "price": pr, "deviation": 30, "magic": MAGIC,
                            "comment": "GSAI-SW-" + why[:10], "position": p.ticket,
                            "type_filling": filling})
        if r is not None and r.retcode == mt5.TRADE_RETCODE_DONE:
            sign = 1 if p.type == mt5.POSITION_TYPE_BUY else -1
            return round((pr - p.price_open) * sign * p.volume * 100.0, 2)
    return None


def main():
    if os.path.exists(PAUSE_F):
        if time.time() - os.path.getmtime(PAUSE_F) < 7200:
            return
        try:
            os.unlink(PAUSE_F)
        except Exception:
            return

    mk_cfg = load_json(MKTS_F, {})
    active = {S: c for S, c in mk_cfg.get("markets", {}).items() if c.get("auto")}
    if not active:
        return

    if not mt5.initialize(path=XM):
        return
    out = []
    try:
        ai = mt5.account_info()
        if ai is None:
            return
        st = load_json(STATE_F, {})
        allpos = mt5.positions_get() or []
        mine = [p for p in allpos if p.magic == MAGIC]
        live_ids = {str(p.ticket) for p in allpos}

        # --- watchdog disparitions ---
        watches = st.get("watches", {})
        for tid in list(watches.keys()):
            if tid in live_ids:
                continue
            w = watches.pop(tid)
            sym = w.get("sym", "GOLD")
            pnl = None
            try:
                for dd in (mt5.history_deals_get(int(time.time()) - 86400 * 7, int(time.time()) + 60) or []):
                    if dd.magic == MAGIC and dd.entry == mt5.DEAL_ENTRY_OUT and str(dd.position) == tid:
                        pnl = round(dd.profit + dd.commission + dd.swap, 2)
                        break
            except Exception:
                pass
            if pnl is None and w.get("last_profit") is not None:
                pnl = w["last_profit"]
            if pnl is None:
                pnl = -w.get("risk", 20.0)  # ni deal ni profit connu: on comptabilise un SL (conservateur)
            led = st.setdefault("ledger", {})
            day = led.setdefault(time.strftime("%Y-%m-%d", time.gmtime()), {"pnl": 0.0, "n": 0})
            day["pnl"] = round(day["pnl"] + pnl, 2)
            day["n"] += 1
            lsym = st.setdefault("ledger_sym", {})
            msym = lsym.setdefault(time.strftime("%Y-%m", time.gmtime()), {})
            row = msym.setdefault(sym, {"pnl": 0.0, "n": 0})
            row["pnl"] = round(row["pnl"] + pnl, 2)
            row["n"] += 1
            st["last_exit_ts"] = time.time()
            st.pop("entry_bar_" + sym, None)
            log({"ev": "closed", "ticket": int(tid), "sym": sym, "pnl": round(pnl, 2)})
            out.append("SWING SORTIE #%d %s | PnL %+.2f$ | solde $%.2f | cumul jour %+.2f$ (x%d) | %s mois: %+.2f$ (x%d)" % (
                int(tid), sym, pnl, ai.balance, day["pnl"], day["n"], sym, row["pnl"], row["n"]))
        st["watches"] = watches
        save_state(st)

        # --- surveillance de MES positions (temps de detention par marche) ---
        for p in mine:
            if str(p.ticket) not in watches:
                eb = st.get("entry_bar_" + p.symbol)
                watches[str(p.ticket)] = {"risk": st.get("cur_risk", 21.0), "sym": p.symbol,
                                          "entry_bar": eb}
            watches[str(p.ticket)]["last_profit"] = round(p.profit, 2)
            cfg = active.get(p.symbol, {})
            max_bars = int(cfg.get("max_bars", 32))
            tf_sec = 3600 if cfg.get("tf", "H1") == "H1" else 14400
            tb = mt5.copy_rates_from_pos(p.symbol, mt5.TIMEFRAME_H1, 1, 2)
            eb = watches[str(p.ticket)].get("entry_bar") or st.get("entry_bar_" + p.symbol)
            if tb is not None and eb and (int(tb["time"][-1]) - eb) / tf_sec >= max_bars:
                pnl = send_close(p, "timeexit")
                if pnl is not None:
                    led = st.setdefault("ledger", {})
                    day = led.setdefault(time.strftime("%Y-%m-%d", time.gmtime()), {"pnl": 0.0, "n": 0})
                    day["pnl"] = round(day["pnl"] + pnl, 2)
                    day["n"] += 1
                    lsym = st.setdefault("ledger_sym", {})
                    msym = lsym.setdefault(time.strftime("%Y-%m", time.gmtime()), {})
                    row = msym.setdefault(p.symbol, {"pnl": 0.0, "n": 0})
                    row["pnl"] = round(row["pnl"] + pnl, 2)
                    row["n"] += 1
                    st["last_exit_ts"] = time.time()
                    st.pop("entry_bar_" + p.symbol, None)
                    watches.pop(str(p.ticket), None)
                    log({"ev": "closed", "ticket": p.ticket, "sym": p.symbol, "pnl": pnl, "why": "timeexit"})
                    out.append("SWING TIME-EXIT %dH #%d %s @ %.2f | PnL %+.2f$ | solde $%.2f" % (
                        max_bars, p.ticket, p.symbol, p.price_current, pnl, ai.balance))
        st["watches"] = watches
        save_state(st)

        # --- garde-fous compte ---
        if ai.balance < BAL_FLOOR:
            log({"ev": "refus", "why": "plancher %.2f" % ai.balance})
            if not st.get("floor_alerted"):
                st["floor_alerted"] = True
                save_state(st)
                print("STOP SYSTEME SWING: solde $%.2f < plancher $%.0f. Reconstruction du capital necessaire (decision humaine)." % (
                    ai.balance, BAL_FLOOR))
            return
        st["floor_alerted"] = False
        if time.time() - st.get("last_exit_ts", 0) < COOLDOWN_AFTER_EXIT:
            return
        # SLOTS (decision humaine 02/10): max 2 simultanees = 1 GOLD + 1 AUTRES.
        # Toute position (meme manuelle) occupe son couloir.
        busy_gold = any(p.symbol == "GOLD" for p in allpos)
        busy_other = any(p.symbol != "GOLD" for p in allpos)
        if len(allpos) >= 2:
            save_state(st)
            print("\n".join(out))
            return

        # --- scan des marches ACTIFS (validation mecanique) ---
        sigs = load_json(os.path.join(BASE, "gsa_swing_sigbars.json"), {})
        chosen = None
        refus = []
        for sym, cfg in active.items():
            if (sym == "GOLD" and busy_gold) or (sym != "GOLD" and busy_other):
                continue  # couloir occupe
            mt5.symbol_select(sym, True)
            s, why = evaluate(sym, cfg)
            if s is None:
                if why not in ("attente",):
                    refus.append("%s:%s" % (sym, why))
                continue
            if sigs.get(sym) == s["bar"]:
                continue  # deja trade sur cette barre
            chosen = s
            break
        if chosen is None:
            if refus:
                log({"ev": "refus", "why": ";".join(refus)[:180]})
            return
        # anti-course inter-moteurs (swing vs data peuvent viser le meme couloir AUTRES)
        try:
            lk = json.load(open(LOCK))
            if time.time() - lk.get("ts", 0) < 150 and lk.get("magic") != 777201:
                return  # autre moteur est en train d'ouvrir sur ce couloir
        except Exception:
            pass
        try:
            json.dump({"ts": time.time(), "magic": 777201, "sym": chosen["sym"]}, open(LOCK, "w"))
        except Exception:
            pass
        r, err = try_enter(chosen)
        if r is not None:
            sigs[chosen["sym"]] = chosen["bar"]
            try:
                json.dump(sigs, open(os.path.join(BASE, "gsa_swing_sigbars.json"), "w"))
            except Exception:
                pass
            st["entry_bar_" + chosen["sym"]] = chosen["bar"]
            st["cur_risk"] = round(chosen["risk"], 2)
            pos_now = [x for x in (mt5.positions_get(symbol=chosen["sym"]) or []) if x.magic == MAGIC]
            if pos_now:
                st.setdefault("watches", {})[str(pos_now[0].ticket)] = {"risk": chosen["risk"], "sym": chosen["sym"], "last_profit": 0.0}
            log({"ev": "entry", "sym": chosen["sym"], "dir": chosen["sig"], "px": chosen["px"],
                 "risk": round(chosen["risk"], 2)})
            side = "BUY" if chosen["sig"] == 1 else "SELL"
            out.append("POSITION SWING %s %s %.2f @ %.2f  [%s UTC]\n"
                       "SL %.2f (-$%.0f = %.0f%% solde)  TP %.2f (+$%.0f)  RR 1:3  |  canal %.0f-%.0f EMA200 %.0f\n"
                       "Solde $%.2f | 2 slots max (GOLD+autres) | time-exit %dH | plancher $10" % (
                           side, chosen["sym"], chosen["lot"], chosen["px"],
                           time.strftime("%H:%M", time.gmtime()),
                           chosen["sl"], chosen["risk"], 100.0 * chosen["risk"] / ai.balance,
                           chosen["tp"], 3 * chosen["risk"],
                           chosen["channel"][0], chosen["channel"][1], chosen["ema200"],
                           ai.balance, chosen["max_bars"]))
        else:
            log({"ev": "refus", "why": "enter:%s:%s" % (chosen["sym"], err)})
        save_state(st)
        print("\n".join(out))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
