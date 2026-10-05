# -*- coding: utf-8 -*-
"""
gsa_trade.py v3 — EXECUTEUR MULTI-MARCHE 24H/7 (GOLD SCALPER AI / Hermes)
Cron Hermes no_agent, 1x/min. stdout = carte Telegram (vide = rien).

Rotation automatique par heure UTC (jours de semaine):
  00-07  Asie   : USDJPY, EURUSD, GBPUSD, GOLD
  07-16  Londres: EURUSD, GOLD, GBPUSD, USDJPY
  16-21  NY     : GOLD, EURUSD, GBPUSD, USDJPY
  21-24  soir   : BTCUSD
  week-end      : BTCUSD (seul marche 24/7)
1 position a la fois TOUS marches confondus.

Risque dimensionne en DOLLARS puis converti en points PAR MARCHE:
  SL$ cible 0.90 (clamp 2*spread+15 <= SL <= 4*ATR, plafond dur 1.60$)
  TP = 2 x SL (RR 1:2)
order_check() AVANT chaque envoi: marge insuffisante = refus (pas de reject serveur).
Ledger local, stop journee -1.50$, plancher solde 15$, cooldown 900s, max 6/j.
"""
import datetime
import json
import os
import time

import MetaTrader5 as mt5

XM_PATH = r"C:\Program Files\XM Global MT5\terminal64.exe"
BASE = os.path.dirname(os.path.abspath(__file__))
STATE_F = os.path.join(BASE, "gsa_trade_state.json")
PAUSE_F = os.path.join(BASE, "gsa_trade_pause.txt")
LOG_F = os.path.join(BASE, "gsa_trades.jsonl")

MAGIC = 777101

def sizing(balance):
    """(lot, risque$) adaptatifs au solde. <80$: 0.01/1$; 80-149$: 0.02; >=150$: 0.03.
    Risque = 1% du solde borne [1.00, 2.50]$. Distance de SL = risk$/ (upp*lot)
    -> a lot double, meme distance de prix que 0.01 a $1 (le risque $ reste 1%)."""
    lot = 0.01 if balance < 80 else (0.02 if balance < 150 else 0.03)
    risk = min(max(1.0, round(balance * 0.01, 2)), 2.5)
    return lot, risk

LOT = 0.01               # remplace par sizing() a l'entree
RISK_USD = 1.00          # remplace par sizing() a l'entree
RISK_MAX_USD = 1.60      # remplace par risk*1.6 a l'entree
DAILY_LOSS_STOP = 1.50   # remplace par risk*1.5 a l'entree
BAL_FLOOR = 15.0
COOLDOWN_S = 900
MAX_TRADES_DAY = 6
SL_MAX_SPREAD_FRAC = 0.50   # spread <= 50% du SL (0.35 rendait GOLD/BTC injouables)
RSI_LO, RSI_HI = 25.0, 75.0
ATR_MIN = 1.0               # ATR mini en points
TIME_EXIT_MIN = 60
TRAIL_ARM_MULT = 1.0        # trail quand profit >= 1 x SL
TRAIL_LOCK_MULT = 0.15      # verrouille 15% du SL en profit
SOFT_LOSS_FRAC = 0.80       # stop doux a 80% du SL risque

POOLS = {
    "weekday": {
        range(0, 7):   ["USDJPY", "EURUSD", "GBPUSD", "GOLD"],
        range(7, 16):  ["EURUSD", "GOLD", "GBPUSD", "USDJPY"],
        range(16, 21): ["GOLD", "EURUSD", "GBPUSD", "USDJPY"],
        range(21, 22): ["BTCUSD"],                 # pause quotidienne FX (21-22 UTC)
        range(22, 24): ["USDJPY", "EURUSD", "GBPUSD", "GOLD", "BTCUSD"],  # Asie reprend 22 UTC
    },
    "weekend": {
        range(0, 24): ["BTCUSD"],
    },
}
# plafond de spread acceptable par marche (points) — au-dela, refus
MAX_SPREAD = {"GOLD": 65, "EURUSD": 30, "GBPUSD": 35, "USDJPY": 35, "BTCUSD": 6000}
WHIP_ATR_MULT = 5.0   # 4.0 = fausses alertes whipsaw a l'ouverture de session (ATR fige pendant la pause)


def day_key():
    return time.strftime("%Y-%m-%d", time.gmtime())


def load_state():
    try:
        with open(STATE_F, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st):
    try:
        with open(STATE_F, "w", encoding="utf-8") as f:
            json.dump(st, f)
    except Exception:
        pass


def log_event(ev):
    try:
        with open(LOG_F, "a", encoding="utf-8") as f:
            ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def ledger_add(st, pnl, reason):
    led = st.setdefault("ledger", {})
    d = led.setdefault(day_key(), {"pnl": 0.0, "n": 0})
    d["pnl"] = round(d["pnl"] + pnl, 2)
    d["n"] += 1


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


def atr(highs, lows, closes, period=14):
    trs = []
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    if len(trs) < period:
        return 0.0
    a = sum(trs[:period]) / period
    for t in trs[period:]:
        a = (a * (period - 1) + t) / period
    return a


def pick_pool(now_utc):
    key = "weekend" if now_utc.weekday() >= 5 else "weekday"
    for rng, pool in POOLS[key].items():
        if now_utc.hour in rng:
            return list(pool)
    return POOLS[key][max(POOLS[key].keys(), key=lambda r: r[0])]


def eval_symbol(sym, max_lot, risk_usd, risk_max_usd):
    """Retourne dict signal/risque (avec lot choisi par marche) ou (None, motif).
    Le lot est le PLUS GRAND <= max_lot dont le SL faisable reste dans risk_max_usd
    et <= 4*ATR: FX typiquement 0.02, GOLD/BTC restent a 0.01 (spread large)."""
    si = mt5.symbol_info(sym)
    tick = mt5.symbol_info_tick(sym)
    if si is None or tick is None or not si.visible:
        return None, "injoignable"
    pt = si.point
    upp01 = si.trade_tick_value * pt / si.trade_tick_size * 0.01  # $ par point au lot 0.01
    if upp01 <= 0:
        return None, "tick_value nul"
    spread = tick.ask - tick.bid
    spread_pts = int(round(spread / pt))
    if spread_pts > MAX_SPREAD.get(sym, 60):
        return None, "spread %d>%d" % (spread_pts, MAX_SPREAD.get(sym, 60))

    m1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 250)
    m15 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 120)
    if m1 is None or m1.shape[0] < 120 or m15 is None or m15.shape[0] < 60:
        return None, "historique insuffisant"
    c1 = [float(x) for x in m1["close"]][:-1]
    h1 = [float(x) for x in m1["high"]][:-1]
    l1 = [float(x) for x in m1["low"]][:-1]
    c15 = [float(x) for x in m15["close"]][:-1]
    # fraicheur: les temps MT5 sont en HEURE SERVEUR (decale de UTC).
    # On estime le decalage avec le tick du symbole lui-meme (aussi serveur).
    last_t = int(m1["time"][-1])
    tick_age = tick.time - last_t          # secondes entre tick serveur et ouverture de la bougie courante
    if tick_age > 180:
        return None, "fige (%ds)" % int(tick_age)

    px = c1[-1]
    e9 = ema(c1, 9)[-1]; e21 = ema(c1, 21)[-1]
    E9 = ema(c15, 9)[-1]; E21 = ema(c15, 21)[-1]
    rv = rsi(c1)
    a_pts = atr(h1, l1, c1) / pt
    if a_pts < ATR_MIN:
        return None, "ATR trop bas"
    sig = 1 if (px > e9 and px > e21 and E9 > E21) else (-1 if (px < e9 and px < e21 and E9 < E21) else 0)
    if sig == 0:
        return None, "pas de signal"
    if not (RSI_LO < rv < RSI_HI):
        return None, "RSI %.0f hors bande" % rv
    rng10 = (max(h1[-10:]) - min(l1[-10:])) / pt
    if rng10 > WHIP_ATR_MULT * max(a_pts, 0.5):
        return None, "whipsaw rng=%d atr=%.0f" % (int(rng10), a_pts)

    # dimensionnement: choisir le lot max faisable, puis la distance SL
    sl_min = int(2 * spread_pts + 15)
    sl_cap_pts = int(4 * a_pts)
    chosen_lot, sl, upp = None, 0, 0.0
    for L in sorted({max_lot, 0.02, 0.01}, reverse=True):
        if L > max_lot:
            continue
        u = upp01 * (L / 0.01)
        # distance cible = risque$, plafonnee a 4*ATR; mais le plancher
        # '2*spread+15' prime sur le plafond ATR (sinon FX calme = jamais tradable)
        d = max(sl_min, min(int(risk_usd / u), sl_cap_pts))
        if d * u > risk_max_usd:
            continue
        chosen_lot, sl, upp = L, d, u
        break
    if chosen_lot is None:
        return None, "SL faisable inexistant (lot %s spr %d atr %.0f)" % (max_lot, spread_pts, a_pts)
    if spread_pts > SL_MAX_SPREAD_FRAC * sl:
        return None, "spread vs SL"
    tp = sl * 2
    slp = round(tick.ask - sl * pt, si.digits) if sig == 1 else round(tick.bid + sl * pt, si.digits)
    tpp = round(tick.ask + tp * pt, si.digits) if sig == 1 else round(tick.bid - tp * pt, si.digits)
    return {"sym": sym, "sig": sig, "px": px, "sl_pts": sl, "tp_pts": tp, "slp": slp, "tpp": tpp,
            "spread": spread_pts, "rsi": rv, "atr": round(a_pts, 1), "upp": upp, "lot": chosen_lot}, None


def margin_ok(s, ai):
    """order_check en mode verification pure; True si la marge passe."""
    si = mt5.symbol_info(s["sym"])
    tick = mt5.symbol_info_tick(s["sym"])
    if si is None or tick is None or ai is None:
        return False
    otype = mt5.ORDER_TYPE_BUY if s["sig"] == 1 else mt5.ORDER_TYPE_SELL
    pr = tick.ask if s["sig"] == 1 else tick.bid
    for filling in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC):
        chk = mt5.order_check({"action": mt5.TRADE_ACTION_DEAL, "symbol": s["sym"], "volume": s["lot"],
                               "type": otype, "price": pr, "sl": s["slp"], "tp": s["tpp"],
                               "deviation": 20, "magic": MAGIC, "type_time": mt5.ORDER_TIME_GTC,
                               "type_filling": filling})
        if chk is None:
            continue
        if chk.retcode in (0, mt5.TRADE_RETCODE_DONE, 10009):
            return chk.margin < ai.margin_free * 0.9
        if chk.retcode == 10019:
            return False
    return False

def try_open(s):
    si = mt5.symbol_info(s["sym"])
    tick = mt5.symbol_info_tick(s["sym"])
    otype = mt5.ORDER_TYPE_BUY if s["sig"] == 1 else mt5.ORDER_TYPE_SELL
    side = "BUY" if s["sig"] == 1 else "SELL"
    pr = tick.ask if s["sig"] == 1 else tick.bid
    for filling in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC):
        req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": s["sym"], "volume": s["lot"],
               "type": otype, "price": pr, "sl": s["slp"], "tp": s["tpp"], "deviation": 20,
               "magic": MAGIC, "comment": "GSAI-PY", "type_time": mt5.ORDER_TIME_GTC,
               "type_filling": filling}
        chk = mt5.order_check(req)
        if chk is None:
            continue
        if chk.retcode not in (0, mt5.TRADE_RETCODE_DONE, 10009):
            if chk.retcode == 10019:   # not enough margin
                return None, "marge insuffisante (%s)" % s["sym"]
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
                            "comment": "GSAI-" + why[:12], "position": p.ticket, "type_filling": filling})
        if r is not None and r.retcode == mt5.TRADE_RETCODE_DONE:
            sign = 1 if p.type == mt5.POSITION_TYPE_BUY else -1
            pnl = (pr - p.price_open) * sign * p.volume * 100.0
            return ("POSITION FERMEE #%d %s (%s) %s @ %.2f | PnL %+.2f$" % (
                p.ticket, p.symbol, "BUY" if p.type == 0 else "SELL", why, pr, pnl), pnl)
    return None


def main():
    if os.path.exists(PAUSE_F):
        try:
            if time.time() - os.path.getmtime(PAUSE_F) < 1800:
                return
            os.unlink(PAUSE_F)
        except Exception:
            return

    if not mt5.initialize(path=XM_PATH):
        return
    out = []
    try:
        ai = mt5.account_info()
        if ai is None:
            return
        max_lot, risk_usd = sizing(ai.balance)
        risk_max_usd = round(risk_usd * 1.6, 2)
        daily_stop = round(risk_usd * 1.5, 2)
        st = load_state()
        poss = mt5.positions_get() or []
        mine = [p for p in poss if p.magic == MAGIC]
        foreign = [p for p in poss if p.magic != MAGIC]
        live_ids = {str(p.ticket) for p in poss}

        # --- watchdog sorties ---
        watches = st.get("watches", {})
        changed = False
        for tid in list(watches.keys()):
            if tid in live_ids:
                continue
            w = watches.pop(tid)
            changed = True
            pnl = None
            try:
                dh = mt5.history_deals_get(w["ts"] - 5, time.time() + 120)
                for dd in (dh or []):
                    if dd.magic == MAGIC and dd.entry == mt5.DEAL_ENTRY_OUT and dd.position == int(tid):
                        pnl = dd.profit + dd.commission + dd.swap
                        break
            except Exception:
                pass
            sym = w.get("sym", "?")
            if pnl is None and w.get("last_profit") is not None:
                pnl = w["last_profit"] - (w.get("spread", 0) * w.get("upp", 0.01))
            if pnl is None:
                px = mt5.symbol_info_tick(sym).bid if mt5.symbol_info_tick(sym) else 0
                if w["dir"] == 1:
                    pnl = w["tp_pts"] * w["upp"] if px >= w["tp"] else -(w["sl_pts"] * w["upp"] + 0.3)
                else:
                    pnl = w["tp_pts"] * w["upp"] if px <= w["tp"] else -(w["sl_pts"] * w["upp"] + 0.3)
                out.append("SORTIE #%d (%s) constatee | PnL estime %+.2f$" % (int(tid), sym, pnl))
            else:
                out.append("SORTIE #%d (%s) confirmee | PnL %+.2f$" % (int(tid), sym, pnl))
            ledger_add(st, pnl, "watchdog")
            log_event({"ev": "closed", "ticket": int(tid), "sym": sym, "pnl": round(pnl, 2)})
        if changed:
            st["watches"] = watches
            save_state(st)

        # --- gestion position ouverte ---
        if mine:
            p = mine[0]
            pt = 0.0001
            try:
                si = mt5.symbol_info(p.symbol)
                pt = si.point if si and si.point > 0 else 0.0001
                upp = si.trade_tick_value * pt / si.trade_tick_size * p.volume
            except Exception:
                upp = 0.01
            if str(p.ticket) not in watches:
                watches[str(p.ticket)] = {"dir": 1 if p.type == 0 else -1, "order": getattr(p, "order", 0),
                                          "ts": time.time(), "tp": p.tp, "sl": p.sl, "sym": p.symbol,
                                          "sl_pts": 0, "tp_pts": 0, "upp": upp}
            watches[str(p.ticket)]["last_profit"] = round(p.profit, 2)
            st["watches"] = watches
            save_state(st)
            # stop doux: 80% du risque
            if p.sl > 0:
                risk_pts = abs(p.price_open - p.sl) / pt
                if p.profit <= -(risk_pts * upp * SOFT_LOSS_FRAC):
                    r = send_close(p, "softstop")
                    if r:
                        msg, pnl = r
                        ledger_add(st, pnl, "soft")
                        watches.pop(str(p.ticket), None)
                        st["watches"] = watches
                        st["last_entry_ts"] = time.time()
                        save_state(st)
                        out.append(msg + "  [STOP DOUX]")
                    print("\n".join(out))
                    return
            if (time.time() - p.time) / 60.0 >= TIME_EXIT_MIN:
                r = send_close(p, "timeexit")
                if r:
                    msg, pnl = r
                    ledger_add(st, pnl, "time")
                    watches.pop(str(p.ticket), None)
                    st["watches"] = watches
                    st["last_entry_ts"] = time.time()
                    save_state(st)
                    out.append(msg + "  [time-exit 60min]")
                print("\n".join(out))
                return
            # trailing
            gain = (p.price_current - p.price_open) if p.type == 0 else (p.price_open - p.price_current)
            gain_pts = gain / pt
            arm_pts = (p.sl and abs(p.price_open - p.sl) / pt * TRAIL_ARM_MULT) or 100
            lock_pts = arm_pts * TRAIL_LOCK_MULT
            if gain_pts >= arm_pts:
                if p.type == mt5.POSITION_TYPE_BUY:
                    nsl = round(p.price_open + lock_pts * pt, si.digits)
                    if p.sl == 0 or p.sl < nsl:
                        mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": nsl, "tp": p.tp})
                else:
                    nsl = round(p.price_open - lock_pts * pt, si.digits)
                    if p.sl == 0 or p.sl > nsl:
                        mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": nsl, "tp": p.tp})
            return

        if foreign:
            # v3.4 cohabitation: les trades manuels (magic 0) ne GELENT plus les
            # entrees; l'executeur garde SA position unique (magic 777101).
            # Garde-fou: total <= 2 positions ET chaque etrangere protegee (SL>0).
            unprotected = [p for p in foreign if p.sl == 0]
            if len(poss) > 2 or unprotected:
                st["last_entry_ts"] = time.time()
                save_state(st)
                out.append("ALERTE survol: %d etrangeres (%d sans SL) - entrees gelees." % (
                    len(foreign), len(unprotected)))
                print(chr(10).join(out))
                return

        # --- garde-fous globaux ---
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        led = st.get("ledger", {}).get(day_key(), {"pnl": 0.0, "n": 0})
        if ai.balance < BAL_FLOOR:
            log_event({"ev": "refus", "why": "plancher %.2f" % ai.balance}); return
        if led["pnl"] <= -daily_stop:
            log_event({"ev": "refus", "why": "stop journee %.2f" % led["pnl"]}); return
        if led["n"] >= MAX_TRADES_DAY:
            log_event({"ev": "refus", "why": "max trades"}); return
        if time.time() - st.get("last_entry_ts", 0) < COOLDOWN_S:
            return
        # weekend: FX fermees, BTC ouvert (géré par le pool)

        # --- rotation des marches ---
        pool = pick_pool(now_utc)
        refusals = []
        chosen = None
        ai_chk = mt5.account_info()
        for sym in pool:
            s, why = eval_symbol(sym, max_lot, risk_usd, risk_max_usd)
            if not s:
                if why and why != "pas de signal":
                    refusals.append("%s:%s" % (sym, why))
                continue
            # pre-vol: ordre de marge (order_check sans envoi) -> si insuffisant, marche suivant
            if not margin_ok(s, ai_chk):
                refusals.append("%s:marge" % sym)
                log_event({"ev": "refus", "why": "marge %s (libre %.2f)" % (sym, ai_chk.margin_free if ai_chk else -1)})
                continue
            chosen = s
            break
        if chosen is None:
            if refusals:
                log_event({"ev": "refus", "why": ";".join(refusals)[:180]})
            save_state(st)
            return

        r, err = try_open(chosen)
        if r is not None:
            st["last_entry_ts"] = time.time()
            st["fails"] = 0
            led_now = st.get("ledger", {}).get(day_key(), {"pnl": 0.0, "n": 0})
            pos_now = [x for x in (mt5.positions_get(symbol=chosen["sym"]) or []) if x.magic == MAGIC]
            if pos_now:
                watches[str(pos_now[0].ticket)] = {"dir": chosen["sig"], "order": r.order, "ts": time.time(),
                                                   "tp": chosen["tpp"], "sl": chosen["slp"], "sym": chosen["sym"],
                                                   "sl_pts": chosen["sl_pts"], "tp_pts": chosen["tp_pts"],
                                                   "spread": chosen["spread"], "upp": chosen["upp"]}
                st["watches"] = watches
            log_event({"ev": "entry", "dir": chosen["sig"], "sym": chosen["sym"], "price": chosen["px"]})
            usd_sl = chosen["sl_pts"] * chosen["upp"]
            usd_tp = chosen["tp_pts"] * chosen["upp"]
            pool_say = ",".join(pool)
            out.append("POSITION OUVERTE %s %s %.2f @ %.2f  [%s UTC]" % (
                "BUY" if chosen["sig"] == 1 else "SELL", chosen["sym"], chosen["lot"], chosen["px"],
                time.strftime("%H:%M", time.gmtime())))
            out.append("SL %.2f (-$%.2f)  TP %.2f (+$%.2f)  RR 1:2  |  spread %d  RSI %.0f  ATR %.0f  |  risque %.2f$" % (
                chosen["slp"], usd_sl, chosen["tpp"], usd_tp,
                chosen["spread"], chosen["rsi"], chosen["atr"], usd_sl))
            out.append("Solde $%.2f | trade %d/%d du jour | PnL jour %+.2f$ | pool: %s" % (
                ai.balance, led_now["n"] + 1, MAX_TRADES_DAY, led_now["pnl"], pool_say))
        else:
            st["fails"] = st.get("fails", 0) + 1
            if st["fails"] >= 3:
                try:
                    open(PAUSE_F, "w").write("3 echecs\n")
                except Exception:
                    pass
            log_event({"ev": "refus", "why": "open:%s:%s" % (chosen["sym"], err)})
        save_state(st)
        print("\n".join(out))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
