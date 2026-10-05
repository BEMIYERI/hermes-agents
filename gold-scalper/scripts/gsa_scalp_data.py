# -*- coding: utf-8 -*-
"""
gsa_scalp_data.py — SCALPING MULTI-MARCHE SANS SL, COLLECTE DE DONNEES
Marches: EURUSD GBPUSD USDJPY BTCUSD (GOLD excluded: son swing SL-valid est actif).
Demande utilisateur 2026-10-02: "active le scalping ... pour avoir des donnees
d'analyse. Annule le SL mais une position ne peut durer que 1h."

Sorties = SEULEMENT TP ou time-exit 60 min (substitut decide par l'humain).
Pas de soft stop, pas de trailing: maximiser la qualite des donnees brutes.
Chaque sortie est journalisee avec contexte complet + MFE/MAE (excursions
favorable/adverse) pour l'analyse ulterieure.

Mutual exclusion: ne trade pas si une position swing (777201) est ouverte;
le swing attend idem que le scalp soit fini -> 1 position totale.
Garde-fous survie: stop journalaire module -3$, plancher solde 60$,
max 8 trades/jour, cooldown 15 min par marche, spread cap par marche.
magic 777301, commentaire GSAI-DATA.
SL_MODE est un choix HUMAIN explicite (NONE ici); les alternatives PROTECT/WIDE
restent implantees pour basculer sans re-ecrire.
"""
import datetime
import json
import os
import time

import MetaTrader5 as mt5

XM = r"C:\Program Files\XM Global MT5\terminal64.exe"
BASE = os.path.dirname(os.path.abspath(__file__))
STATE_F = os.path.join(BASE, "gsa_scalp_data_state.json")
DATA_F = os.path.join(BASE, "gsa_scalp_dataset.jsonl")
PAUSE_F = os.path.join(BASE, "gsa_trade_pause.txt")  # shared kill-switch
LOCK = os.path.join(BASE, "gsa_slot_lock.json")

MAGIC = 777301
LOT = 0.01
SWING_MAGIC = 777201

SL_MODE = "NONE"            # NONE (choix humain) | PROTECT (1.2*ATR) | WIDE (3*ATR)
SL_MULT = {"PROTECT": 1.2, "WIDE": 3.0}
HOLD_MAX_MIN = 60           # regle humaine: 1h maximum, remplace le SL
BAL_FLOOR = 10.0            # survie technique seulement - PLUS de stop sur pertes (decision humaine 02/10)
MAX_TRADES_DAY = 24         # "maximum de trades possible" - borne de garde-fou accident, pas de rendement
COOLDOWN_S = 300
RSI_LO, RSI_HI = 25.0, 75.0
WHIP_ATR = 999.0   # NON bloquant: module de COLLECTE = mesurer, pas selectionner (rng10/atr est enregistre pour l'analyse)
MARKETS = {"EURUSD": 30, "GBPUSD": 35, "USDJPY": 35, "BTCUSD": 6000}  # cap spread pts
DRY = os.environ.get("GSA_SCALP_DRY") == "1"


def lj(path, dflt):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dflt


def sj(path, obj):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f)
    except Exception:
        pass


def ema(v, p):
    k = 2.0 / (p + 1.0)
    o = [v[0]]
    for x in v[1:]:
        o.append(x * k + o[-1] * (1.0 - k))
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


def atrv(h, l, c, period=14):
    trs = []
    for i in range(1, len(c)):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    if len(trs) < period:
        return 0.0
    a = sum(trs[:period]) / period
    for t in trs[period:]:
        a = (a * (period - 1) + t) / period
    return a


def dataset(rec):
    try:
        rec["ts"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        with open(DATA_F, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def compute_mfe_mae(sym, entry_ts_server, exit_ts_server, entry, sig, pt):
    """Excursions (base prix) sur les barres M1 entre entree et sortie (temps serveur -> UTC)."""
    try:
        off = mt5.symbol_info_tick(sym).time - int(time.time()) if mt5.symbol_info_tick(sym) else 0
        d_from = datetime.datetime.fromtimestamp(entry_ts_server - off - 60, datetime.UTC)
        d_to = datetime.datetime.fromtimestamp(exit_ts_server - off + 60, datetime.UTC)
        rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M1, d_from, d_to)
        if rates is None or len(rates) == 0:
            return None, None
        h = [float(x) for x in rates["high"]]
        l = [float(x) for x in rates["low"]]
        if sig == 1:
            return max(h) - entry, entry - min(l)
        return entry - min(l), max(h) - entry
    except Exception:
        return None, None


def evaluate(sym, maxspr):
    si = mt5.symbol_info(sym)
    tick = mt5.symbol_info_tick(sym)
    if si is None or tick is None or not si.visible:
        return None, "injoignable"
    pt = si.point
    u = si.trade_tick_value * pt / si.trade_tick_size * LOT
    spread_pts = int(round((tick.ask - tick.bid) / pt))
    if spread_pts > maxspr:
        return None, "spread %d" % spread_pts
    m1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 250)
    m15 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 120)
    if m1 is None or m1.shape[0] < 120 or m15 is None or m15.shape[0] < 60:
        return None, "histo"
    if tick.time - int(m1["time"][-1]) > 180:
        return None, "fige"
    c1 = [float(x) for x in m1["close"]][:-1]
    h1 = [float(x) for x in m1["high"]][:-1]
    l1 = [float(x) for x in m1["low"]][:-1]
    c15 = [float(x) for x in m15["close"]][:-1]
    px = c1[-1]
    e9 = ema(c1, 9)[-1]
    e21 = ema(c1, 21)[-1]
    E9 = ema(c15, 9)[-1]
    E21 = ema(c15, 21)[-1]
    rv = rsi(c1)
    ap = atrv(h1, l1, c1) / pt
    if ap <= 0:
        return None, "atr nul"
    sig = 1 if (px > e9 and px > e21 and E9 > E21) else (-1 if (px < e9 and px < e21 and E9 < E21) else 0)
    if sig == 0:
        return None, "pas de signal"
    if not (RSI_LO < rv < RSI_HI):
        return None, "RSI %.0f" % rv
    rng10 = (max(h1[-10:]) - min(l1[-10:])) / pt
    if rng10 > WHIP_ATR * ap:
        return None, "whipsaw"
    tp_pts = int(max(2 * spread_pts + 20, min(1.5 * ap, 4 * ap)))
    sl_pts = int(SL_MULT.get(SL_MODE, 0) * ap) if SL_MODE in SL_MULT else 0
    bar = int(m1["time"][-2])
    tpx = round(tick.ask + sig * tp_pts * pt, si.digits) if sig == 1 else round(tick.bid - sig * tp_pts * pt, si.digits)
    slx = round(tick.ask - sig * sl_pts * pt, si.digits) if sl_pts else 0
    if slx:
        slx = round(tick.bid - sig * sl_pts * pt, si.digits) if sig == -1 else slx
    return {"sym": sym, "sig": sig, "px": px, "bar": bar, "tp_pts": tp_pts, "tp": tpx,
            "sl": slx, "sl_pts": sl_pts, "spr": spread_pts, "rsi": round(rv, 1),
            "atr": round(ap, 1), "u": u, "m15": "BULL" if E9 > E21 else "BEAR",
            "d9": round((px - e9) / pt, 1), "d21": round((px - e21) / pt, 1),
            "whip_ratio": round(rng10 / max(ap, 0.5), 2)}, None


def main():
    if os.path.exists(PAUSE_F) and time.time() - os.path.getmtime(PAUSE_F) < 1800:
        return
    if not mt5.initialize(path=XM):
        return
    out = []
    try:
        ai = mt5.account_info()
        if ai is None:
            return
        st = lj(STATE_F, {})
        allpos = mt5.positions_get() or []
        mine = [p for p in allpos if p.magic == MAGIC]
        swing_open = [p for p in allpos if p.magic == SWING_MAGIC]
        live = {str(p.ticket) for p in allpos}
        today = time.strftime("%Y-%m-%d", time.gmtime())

        # --- clotures constees: enrichissement du dataset avec MFE/MAE ---
        watches = st.get("watches", {})
        for tid in list(watches.keys()):
            if tid in live:
                for p in allpos:
                    if str(p.ticket) == tid:
                        watches[tid]["last_profit"] = round(p.profit, 2)
                continue
            w = watches.pop(tid)
            sym = w.get("sym", "?")
            pnl = None
            try:
                for dd in (mt5.history_deals_get(int(time.time()) - 86400 * 2, int(time.time()) + 60) or []):
                    if dd.magic == MAGIC and dd.entry == mt5.DEAL_ENTRY_OUT and str(dd.position) == tid:
                        pnl = round(dd.profit + dd.commission + dd.swap, 2)
                        break
            except Exception:
                pass
            reason = w.get("reason", "?")
            if pnl is None:
                pnl = w.get("last_profit")
                if pnl is None:
                    pnl = 0.0
                    reason = "inconnu"
            mfe, mae = compute_mfe_mae(sym, w.get("open_server_ts", 0), int(time.time()),
                                       w.get("entry", 0.0), w.get("dir", 1), 1.0)
            rec = st.setdefault("dataset_close", {})
            lk = w.get("dataset_key", tid)
            dataset({"ev": "close", "key": lk, "ticket": int(tid), "sym": sym,
                     "dir": w.get("dir"), "pnl": pnl, "reason": reason,
                     "hold_min": round((time.time() - w.get("open_ts", time.time())) / 60.0, 1),
                     "mfe": round(mfe, 5) if mfe is not None else None,
                     "mae": round(mae, 5) if mae is not None else None,
                     "balance": round(ai.balance, 2)})
            led = st.setdefault("ledger", {}).setdefault(today, {"pnl": 0.0, "n": 0})
            led["pnl"] = round(led["pnl"] + pnl, 2)
            led["n"] += 1
            st["last_exit_" + sym] = time.time()
            out.append("DATA SORTIE %s #%d | PnL %+.2f$ (%s, %d min) | solde $%.2f | jour %+.2f$ (x%d)" % (
                sym, int(tid), pnl, reason, int((time.time() - w.get("open_ts", time.time())) / 60),
                ai.balance, led["pnl"], led["n"]))
        st["watches"] = watches
        sj(STATE_F, st)

        # --- gestion: time-exit 60 min (substitut du SL) ---
        for p in mine:
            if str(p.ticket) not in watches:
                tk = mt5.symbol_info_tick(p.symbol)
                watches[str(p.ticket)] = {"sym": p.symbol, "dir": 1 if p.type == mt5.POSITION_TYPE_BUY else -1,
                                          "entry": p.price_open, "open_ts": time.time(),
                                          "open_server_ts": int(tk.time) if tk else 0,
                                          "dataset_key": "re-attach-%d" % p.ticket, "last_profit": round(p.profit, 2)}
            tk2 = mt5.symbol_info_tick(p.symbol)
            if tk2 is not None and (tk2.time - p.time) / 60.0 >= HOLD_MAX_MIN and str(p.ticket) in watches:
                watches[str(p.ticket)]["reason"] = "time-exit 1h"
            age_min = (mt5.symbol_info_tick(p.symbol).time - p.time) / 60.0 if mt5.symbol_info_tick(p.symbol) else 0
            if age_min >= HOLD_MAX_MIN:
                tick = mt5.symbol_info_tick(p.symbol)
                otype = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                pr = tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask
                r = None
                for filling in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC):
                    r = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": p.symbol,
                                       "volume": p.volume, "type": otype, "price": pr,
                                       "deviation": 30, "magic": MAGIC, "comment": "GSAI-DATA-X",
                                       "position": p.ticket, "type_filling": filling})
                    if r is not None and r.retcode == mt5.TRADE_RETCODE_DONE:
                        break
                if r is not None and r.retcode == mt5.TRADE_RETCODE_DONE:
                    w = watches.get(str(p.ticket), {})
                    w["reason"] = "time-exit 1h"
                    # la prochaine passe constatera la disparition et ecrira le dataset
                    out.append("DATA TIME-EXIT %s #%d impose (1h, choix humain sans SL)" % (p.symbol, p.ticket))
                break
        sj(STATE_F, st)
        if mine:
            print("\n".join(out))
            return

        # --- garde-fous d'entree ---
        # SLOTS (decision humaine 02/10): 1 GOLD + 1 AUTRES max.
        # DATA vit dans le couloir AUTRES: libre seulement si AUCUNE position non-GOLD (y compris swing FX force ou manuel).
        if any(p.symbol != "GOLD" for p in allpos):
            return  # couloir AUTRES deja occupe (swing force, manuel ou autre data)
        led = st.setdefault("ledger", {}).get(today, {"pnl": 0.0, "n": 0})
        if ai.balance < BAL_FLOOR:
            log_ref = {"ev": "refus", "why": "plancher %.2f" % ai.balance}
            dataset(log_ref)
            if not st.get("floor_alerted"):
                st["floor_alerted"] = True
                sj(STATE_F, st)
                print("STOP MODULE DATA: solde $%.2f < plancher $%.0f." % (ai.balance, BAL_FLOOR))
            return
        st["floor_alerted"] = False
        if led["n"] >= MAX_TRADES_DAY:
            dataset({"ev": "refus", "why": "max %d trades" % MAX_TRADES_DAY})
            return

        for sym, maxspr in MARKETS.items():
            mt5.symbol_select(sym, True)
            s, why = evaluate(sym, maxspr)
            if s is None:
                continue
            if st.get("sigbar_" + sym) == s["bar"]:
                continue
            if time.time() - st.get("last_exit_" + sym, 0) < COOLDOWN_S:
                continue
            otype = mt5.ORDER_TYPE_BUY if s["sig"] == 1 else mt5.ORDER_TYPE_SELL
            tick = mt5.symbol_info_tick(sym)
            pr = tick.ask if s["sig"] == 1 else tick.bid
            req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": sym, "volume": LOT,
                   "type": otype, "price": pr, "tp": s["tp"], "deviation": 25,
                   "magic": MAGIC, "comment": "GSAI-DATA", "type_time": mt5.ORDER_TIME_GTC}
            if SL_MODE in SL_MULT and s["sl"]:
                req["sl"] = s["sl"]
            try:
                lk = json.load(open(LOCK)) if os.path.exists(LOCK) else None
                if lk and time.time() - lk.get("ts", 0) < 150 and lk.get("magic") not in (MAGIC,):
                    continue  # swing en train d'ouvrir sur le couloir AUTRES
            except Exception:
                pass
            try:
                json.dump({"ts": time.time(), "magic": MAGIC, "sym": sym}, open(LOCK, "w"))
            except Exception:
                pass
            if DRY:
                r = {"retcode": 10009, "order": 0}
            else:
                for filling in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC):
                    req["type_filling"] = filling
                    chk = mt5.order_check(req)
                    if chk is None or chk.retcode not in (0, mt5.TRADE_RETCODE_DONE, 10009):
                        r = None
                        continue
                    r = mt5.order_send(req)
                    if r is not None and r.retcode == mt5.TRADE_RETCODE_DONE:
                        break
                    r = None
            if not r:
                dataset({"ev": "refus", "why": "open %s" % sym})
                continue
            key = "%s-%d" % (sym, s["bar"])
            st["sigbar_" + sym] = s["bar"]
            pos_now = [x for x in (mt5.positions_get(symbol=sym) or []) if x.magic == MAGIC]
            if pos_now:
                watches[str(pos_now[0].ticket)] = {
                    "sym": sym, "dir": s["sig"], "entry": pos_now[0].price_open,
                    "open_ts": time.time(), "open_server_ts": int(tick.time),
                    "dataset_key": key, "last_profit": 0.0}
                st["watches"] = watches
            if not DRY:
                dataset({"ev": "open", "key": key, "sym": sym, "dir": s["sig"], "px": s["px"],
                     "tp_pts": s["tp_pts"], "sl_mode": SL_MODE, "spread": s["spr"],
                     "rsi": s["rsi"], "atr": s["atr"], "m15": s["m15"], "d9": s["d9"],
                         "d21": s["d21"], "whip": s["whip_ratio"], "balance": round(ai.balance, 2), "day_n": led["n"] + 1})
            out.append("DATA ENTREE %s %s %.2f @ %.5f | TP %.5f (+%.2f$) | SANS SL - sortie par TP ou 1h MAX\n"
                       "spread %d RSI %.0f ATR %.0f M15 %s | collecte %d/%d du jour | solde $%.2f" % (
                           "BUY" if s["sig"] == 1 else "SELL", sym, LOT, s["px"], s["tp"],
                           s["tp_pts"] * s["u"], s["spr"], s["rsi"], s["atr"], s["m15"],
                           led["n"] + 1, MAX_TRADES_DAY, ai.balance))
            break
        sj(STATE_F, st)
        print("\n".join(out))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
