# -*- coding: utf-8 -*-
"""
gsa_agents.py v2 — CHAINE MULTI-AGENTS, SCALPING SUR TOUS LES MARCHES
(decision humaine 02/10: scalping tous marches, TP ~1.5-2$, positions rapides,
analyse M1/M5/M15/H1, pas d'arret tant qu'il y a des opportunites).

Agents par marche (EURUSD GBPUSD USDJPY GOLD BTCUSD):
 1 COLLECTEUR   : temps reel MT5 (M1/M5/M15/H1, ticks, spread, volumes) + RSS actus
 2 ANALYSTE     : etat par timeframe (EMA9/21, RSI, ATR, pente) + vote de tendance
 3 SYNTHETISEUR : decision ecrite = score 0..100, sens, TP vise ~1.5-2$ (borne ATR/spread)
 4 DECIDEUR/EXECUTEUR + CHEF RISQUE (politique verrouillee): trade ou passe
 5 SUPERVISEUR  : ages, time-exit DUR 35min + filet 60min, closes -> dataset MFE/MAE
 6 APPRENANT    : wr / TP-hit / MFE-MAE par marche -> regle tp_usd et score_min bornes

Politique verrouillee humain: JAMAIS de pause pertes; plancher 10$ = marge technique;
1 scalp par marche; swing GOLD (magic 777201) coexiste sans conflit (verrou 150s).
Cron Hermes no_agent 1x2min; stdout = cartes (vide = rien).
"""
import datetime
import json
import os
import re
import time
import urllib.request

import MetaTrader5 as mt5

XM = r"C:\Program Files\XM Global MT5\terminal64.exe"
BASE = os.path.dirname(os.path.abspath(__file__))
STATE_F = os.path.join(BASE, "gsa_agents_state.json")
OLD_STATE_F = os.path.join(BASE, "gsa_scalp_data_state.json")
TUNE_F = os.path.join(BASE, "gsa_agents_tuning.json")
LOG_F = os.path.join(BASE, "gsa_agents_log.jsonl")
DATA_F = os.path.join(BASE, "gsa_scalp_dataset.jsonl")
PAUSE_F = os.path.join(BASE, "gsa_trade_pause.txt")
LOCK = os.path.join(BASE, "gsa_slot_lock.json")
NEWS_F = os.path.join(BASE, "gsa_news_cache.json")

MAGIC = 777301
LOT = 0.01
MARKETS = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "BTCUSD"]
MAX_SPREAD = {"EURUSD": 30, "GBPUSD": 35, "USDJPY": 35, "GOLD": 65, "BTCUSD": 6000}
HOLD_MAX_MIN = 35          # "positions rapides" (consigne humaine 02/10)
FILET_MIN = 60             # plafond absolu herite de la regle "1h max"
BAL_FLOOR = 10.0           # marge technique uniquement — jamais une pause pertes
MAX_CONCURRENT = 6
COOLDOWN_S = 60
HARD_CAP_DAY = 48
TP_USD_DEF = 1.8           # 1.5-2$ vise (apprenant: 1.2..2.5)
SCORE_MIN_DEF = 55.0
RSI_LO, RSI_HI = 25.0, 75.0
IMPACT_WORDS = ("nfp", "non-farm", "cpi", "ppi", "fomc", "rate decision", "interest rate",
                "gdp", "unemployment", "inflation", "fed", "bce", "boe", "boj", "taux", "chomage")
DRY = os.environ.get("GSA_AGENTS_DRY") == "1"
_MEM = {}


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


def think(agent, market, obs, why, action=""):
    try:
        with open(LOG_F, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%H:%M:%S", time.gmtime()),
                                "agent": agent, "mkt": market, "obs": str(obs)[:200],
                                "why": str(why)[:160], "act": action}, ensure_ascii=False) + "\n")
    except Exception:
        pass


def dataset(rec):
    try:
        rec["ts"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        with open(DATA_F, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
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


def med(v):
    return round(sorted(v)[len(v) // 2], 5) if v else None


# ---------------- 1. COLLECTEUR ----------------
def collect_news():
    cache = lj(NEWS_F, {"ts": 0, "items": []})
    if time.time() - cache.get("ts", 0) < 900:
        return cache["items"]
    items = []
    try:
        req = urllib.request.Request("https://www.fxstreet.com/rss/news",
                                     headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=8).read(220000).decode("utf-8", "ignore")
        titles = re.findall(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", raw)
        dates = re.findall(r"<pubDate>(.*?)</pubDate>", raw)
        for i, t in enumerate(titles[1:13]):
            t = (t or "").strip()
            if len(t) > 8:
                items.append({"t": t[:160], "d": (dates[i] if i < len(dates) else "")[:40]})
    except Exception as e:
        think("COLLECTEUR", "NEWS", "flux indisponible", str(e)[:70], "")
    sj(NEWS_F, {"ts": time.time(), "items": items})
    return items


def news_impact_minutes():
    now = time.time()
    worst = 999
    for it in collect_news():
        low = it["t"].lower()
        if any(k in low for k in IMPACT_WORDS):
            try:
                dt = datetime.datetime.strptime(it["d"][:25].strip(), "%a, %d %b %Y %H:%M:%S")
                worst = min(worst, max(0, int((now - dt.timestamp()) / 60)))
            except Exception:
                worst = min(worst, 20)
    return worst


def collector(sym):
    si = mt5.symbol_info(sym)
    tick = mt5.symbol_info_tick(sym)
    if si is None or tick is None or not si.visible:
        return None, "injoignable"
    pt = si.point
    rates = {}
    for tf in ("M1", "M5", "M15", "H1"):
        r = mt5.copy_rates_from_pos(sym, getattr(mt5, "TIMEFRAME_" + tf), 0, 250)
        if r is None or r.shape[0] < 80:
            return None, "histo %s" % tf
        rates[tf] = r
    if tick.time - int(rates["M1"]["time"][-1]) > 180:
        return None, "fige"
    col = {"si": si, "tick": tick, "pt": pt, "rates": rates,
           "u": si.trade_tick_value * pt / si.trade_tick_size * LOT,
           "spread_pts": int(round((tick.ask - tick.bid) / pt)),
           "digits": si.digits, "bar_m1": int(rates["M1"]["time"][-2]),
           "vol_med": med([int(x) for x in rates["M1"]["tick_volume"][-60:-1]]) or 1,
           "vol_now": int(rates["M1"]["tick_volume"][-2])}
    return col, None


# ---------------- 2. ANALYSTE (M1/M5/M15/H1) ----------------
def analyst(sym, col):
    if col is None:
        return None, "sans collecte"
    pt = col["pt"]
    tfs = {}
    for tf in ("M1", "M5", "M15", "H1"):
        r = col["rates"][tf]
        c = [float(x) for x in r["close"]][:-1]
        h = [float(x) for x in r["high"]][:-1]
        l = [float(x) for x in r["low"]][:-1]
        px = c[-1]
        e9s, e21s = ema(c, 9), ema(c, 21)
        if px > e9s[-1] > e21s[-1]:
            vote = 1
        elif px < e9s[-1] < e21s[-1]:
            vote = -1
        elif e9s[-1] > e21s[-1]:
            vote = 1
        elif e9s[-1] < e21s[-1]:
            vote = -1
        else:
            vote = 0
        tfs[tf] = {"px": px, "e9": e9s[-1], "e21": e21s[-1], "rsi": rsi(c),
                   "atr": atrv(h, l, c) / pt, "vote": vote,
                   "slope": (e21s[-1] - e21s[-4]) / pt if len(c) > 24 else 0.0}
    votes = [tfs[t]["vote"] for t in ("M1", "M5", "M15", "H1")]
    cnt = {1: votes.count(1), -1: votes.count(-1)}
    if cnt[1] >= cnt[-1] and cnt[1] >= 3:
        direction = 1
    elif cnt[-1] > cnt[1] and cnt[-1] >= 3:
        direction = -1
    else:
        direction = 0
    agree = max(cnt.values()) if direction else 0
    st = dict(tfs["M1"])
    st.update({"votes": votes, "dir": direction, "agree": agree,
               "m5": tfs["M5"], "m15": tfs["M15"], "h1": tfs["H1"],
               "spread_pts": col["spread_pts"], "u": col["u"], "pt": pt,
               "digits": col["digits"], "bar_m1": col["bar_m1"],
               "ask": col["tick"].ask, "bid": col["tick"].bid,
               "vol_ratio": (col["vol_now"] / col["vol_med"]) if col["vol_med"] else 1.0})
    key = (direction, st["bar_m1"] // 5)
    memk = "a_" + sym
    if _MEM.get(memk) != key:
        think("ANALYSTE", sym, "votes M1/M5/M15/H1=%s dir=%s rsi=%.0f atr=%.0f spr=%d" % (
              votes, direction, st["rsi"], st["atr"], st["spread_pts"]),
              "confluence %d/4" % agree)
        _MEM[memk] = key
    return st, None


# ---------------- 3. SYNTHETISEUR ----------------
def synthetizer(sym, ast, tun, news_min):
    if ast is None:
        return None, "sans analyse"
    if ast["dir"] == 0:
        return None, "divergent %s" % ast["votes"]
    if ast["spread_pts"] > MAX_SPREAD[sym]:
        return None, "spread %d>%d" % (ast["spread_pts"], MAX_SPREAD[sym])
    if not (RSI_LO < ast["rsi"] < RSI_HI):
        return None, "RSI %.0f" % ast["rsi"]
    tp_usd = min(2.5, max(1.2, float(tun.get(sym, {}).get("tp_usd", TP_USD_DEF))))
    tp_by_usd = int(tp_usd / ast["u"]) if ast["u"] > 0 else 0
    tp_pts = max(2 * ast["spread_pts"] + 12, min(tp_by_usd, int(6 * max(ast["atr"], 1.0))))
    if tp_pts * ast["u"] < ast["spread_pts"] * ast["u"] * 2.2:
        return None, "TP %.2f$ couvert par le spread" % (tp_pts * ast["u"])
    score = 42.0
    score += 8.0 * (ast["agree"] - 2)
    if ast["m5"]["vote"] == ast["dir"]:
        score += 6
    if ast["m15"]["vote"] == ast["dir"]:
        score += 8
    if ast["h1"]["vote"] == ast["dir"]:
        score += 6
    score += min(12.0, ast["atr"] * (0.5 if sym in ("GOLD", "BTCUSD") else 1.0))
    score += max(0.0, 10.0 - ast["spread_pts"] / 3.0)
    if ast["vol_ratio"] > 1.2:
        score += 5
    if news_min < 45:
        score -= 35
    score = round(score, 1)
    thr = float(tun.get(sym, {}).get("score_min", SCORE_MIN_DEF))
    side = "BUY" if ast["dir"] == 1 else "SELL"
    tp_px = round((ast["ask"] if ast["dir"] == 1 else ast["bid"]) + ast["dir"] * tp_pts * ast["pt"], ast["digits"])
    think("SYNTHETISEUR", sym, "%s score=%.0f/%.0f TP %dpt=%.2f$ news=%s" % (
          side, score, thr, tp_pts, tp_pts * ast["u"],
          ("%dm" % news_min) if news_min < 900 else "calme"),
          "confluence %d/4 M15=%s H1=%s spr=%d vol=%.1fx" % (
              ast["agree"], ast["m15"]["vote"], ast["h1"]["vote"], ast["spread_pts"], ast["vol_ratio"]),
          "VALIDE" if score >= thr else "REFUSE")
    if score < thr:
        return None, "score %.0f<%.0f" % (score, thr)
    return {"sym": sym, "dir": ast["dir"], "px": ast["px"], "tp": tp_px, "tp_pts": tp_pts,
            "score": score, "entry": ast["ask"] if ast["dir"] == 1 else ast["bid"],
            "bar": ast["bar_m1"], "spread": ast["spread_pts"], "rsi": round(ast["rsi"], 1),
            "atr": round(ast["atr"], 1), "u": ast["u"], "votes": ast["votes"],
            "news_min": news_min, "vol_ratio": round(ast["vol_ratio"], 2)}, None


# ---------------- CHEF RISQUE ----------------
def risk_block(st, allpos, ai, today):
    led = st.setdefault("ledger", {}).get(today, {"pnl": 0.0, "n": 0})
    if ai.balance < BAL_FLOOR:
        return "plancher marge %.2f$ < %.0f$" % (ai.balance, BAL_FLOOR)
    if len(allpos) >= MAX_CONCURRENT:
        return "couloirs pleins (%d positions)" % len(allpos)
    if led["n"] >= HARD_CAP_DAY:
        return "plafond accident %d/j" % HARD_CAP_DAY
    return None


# ---------------- 4. EXECUTEUR ----------------
def executor(op, st):
    if st.get("sigbar_" + op["sym"]) == op["bar"]:
        return None, "deja pris sur cette barre"
    if time.time() - st.get("last_exit_" + op["sym"], 0) < COOLDOWN_S:
        return None, "cooldown marche"
    try:
        lk = lj(LOCK, None)
        if lk and time.time() - lk.get("ts", 0) < 150 and lk.get("magic") != MAGIC:
            return None, "verrou swing 150s"
    except Exception:
        pass
    sj(LOCK, {"ts": time.time(), "magic": MAGIC, "sym": op["sym"]})
    req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": op["sym"], "volume": LOT,
           "type": mt5.ORDER_TYPE_BUY if op["dir"] == 1 else mt5.ORDER_TYPE_SELL,
           "price": op["entry"], "tp": op["tp"], "deviation": 25, "magic": MAGIC,
           "comment": "GSAI-AGT2", "type_time": mt5.ORDER_TIME_GTC}
    if DRY:
        think("EXECUTEUR", op["sym"], "DRY ordre simule score=%.0f" % op["score"], "test", "SIMULE")
        return {"retcode": 10009, "order": 0}, None
    for filling in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC):
        req["type_filling"] = filling
        chk = mt5.order_check(req)
        if chk is None or chk.retcode not in (0, 10009, mt5.TRADE_RETCODE_DONE):
            if chk is not None and chk.retcode == 10019:
                return None, "marge insuffisante"
            continue
        r = mt5.order_send(req)
        if r is not None and r.retcode == mt5.TRADE_RETCODE_DONE:
            think("EXECUTEUR", op["sym"], "TRADE %s @%.5f TP +%.2f$ score=%.0f" % (
                  "BUY" if op["dir"] == 1 else "SELL", op["entry"],
                  op["tp_pts"] * op["u"], op["score"]),
                  "collecte>analyse(M1/M5/M15/H1)>synthese>decision OK", "POSITION")
            return r, None
    return None, "ordre refuse"


# ---------------- 5. SUPERVISEUR ----------------
def mfe_mae(sym, entry_ts_server, entry, sig):
    try:
        tk = mt5.symbol_info_tick(sym)
        off = (tk.time - int(time.time())) if tk else 0
        d_from = datetime.datetime.fromtimestamp(entry_ts_server - off - 90, datetime.UTC)
        rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M1, d_from, datetime.datetime.now(datetime.UTC))
        if rates is None or len(rates) == 0:
            return None, None
        h = [float(x) for x in rates["high"]]
        l = [float(x) for x in rates["low"]]
        if sig == 1:
            return max(h) - entry, entry - min(l)
        return entry - min(l), max(h) - entry
    except Exception:
        return None, None


def _close_position(p, comment):
    tk = mt5.symbol_info_tick(p.symbol)
    if tk is None:
        return False
    otype = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    pr = tk.bid if p.type == mt5.POSITION_TYPE_BUY else tk.ask
    for filling in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC):
        r = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": p.symbol,
                            "volume": p.volume, "type": otype, "price": pr, "deviation": 40,
                            "magic": MAGIC, "comment": comment, "position": p.ticket,
                            "type_filling": filling})
        if r is not None and r.retcode == mt5.TRADE_RETCODE_DONE:
            return True
    return False


def supervisor(st, allpos, live, ai, out):
    watches = st.setdefault("watches", {})
    mine = [p for p in allpos if p.magic == MAGIC]
    for p in mine:
        tid = str(p.ticket)
        if tid not in watches:
            tk = mt5.symbol_info_tick(p.symbol)
            watches[tid] = {"sym": p.symbol, "dir": 1 if p.type == mt5.POSITION_TYPE_BUY else -1,
                            "entry": p.price_open, "open_ts": time.time(),
                            "open_server_ts": int(tk.time) if tk else 0,
                            "dataset_key": "adopt-%d" % p.ticket,
                            "last_profit": round(p.profit, 2)}
            think("SUPERVISEUR", p.symbol, "adoption #%d" % p.ticket, "position heritagee", "")
        w = watches[tid]
        w["last_profit"] = round(p.profit, 2)
        tk = mt5.symbol_info_tick(p.symbol)
        age_min = ((tk.time - w.get("open_server_ts", tk.time)) / 60.0) if tk else 0
        if not w.get("closing") and age_min >= HOLD_MAX_MIN:
            w["closing"] = True
            w["reason"] = "time-exit %dmin" % HOLD_MAX_MIN
            think("SUPERVISEUR", p.symbol, "TIME-EXIT #%d age=%.0fmin pnl=%+.2f$" % (
                  p.ticket, age_min, p.profit), "position rapide (consigne humaine)", "CLOSE")
            if not DRY:
                _close_position(p, "GSAI-AGT-X")
        if not w.get("closing") and age_min >= FILET_MIN:
            w["closing"] = True
            w["reason"] = "filet %dmin" % FILET_MIN
            think("SUPERVISEUR", p.symbol, "FILET #%d age=%.0fmin" % (p.ticket, age_min),
                  "plafond humain absolu 1h", "CLOSE")
            if not DRY:
                _close_position(p, "GSAI-AGT-X")
    for tid in list(watches.keys()):
        if tid in live:
            continue
        w = watches.pop(tid)
        sym = w.get("sym", "?")
        pnl = None
        reason = w.get("reason", "TP serveur")
        if not DRY:
            try:
                for dd in (mt5.history_deals_get(int(time.time()) - 86400 * 2, int(time.time()) + 60) or []):
                    if dd.entry == mt5.DEAL_ENTRY_OUT and str(dd.position) == tid:  # le deal de cloture serveur porte magic=0
                        pnl = round(dd.profit + dd.commission + dd.swap, 2)
                        if dd.comment and "AGT-X" in dd.comment:
                            reason = w.get("reason", "time-exit")
                        break
            except Exception:
                pass
        if pnl is None:
            pnl = w.get("last_profit")
            if pnl is None:
                pnl = 0.0
                reason = "inconnu"
        mfe, mae = mfe_mae(sym, w.get("open_server_ts", 0), w.get("entry", 0.0), w.get("dir", 1))
        dataset({"ev": "close", "key": w.get("dataset_key", tid), "ticket": int(tid), "sym": sym,
                 "dir": w.get("dir"), "pnl": round(pnl, 2), "reason": reason,
                 "hold_min": round((time.time() - w.get("open_ts", time.time())) / 60.0, 1),
                 "mfe": round(mfe, 5) if mfe is not None else None,
                 "mae": round(mae, 5) if mae is not None else None,
                 "balance": round(ai.balance, 2)})
        led = st.setdefault("ledger", {}).setdefault(time.strftime("%Y-%m-%d", time.gmtime()),
                                                     {"pnl": 0.0, "n": 0})
        led["pnl"] = round(led["pnl"] + pnl, 2)
        led["n"] += 1
        st["last_exit_" + sym] = time.time()
        think("SUPERVISEUR", sym, "CLOSE #%d %+.2f$ (%s)" % (int(tid), pnl, reason),
              "dataset MFE/MAE enrichi", "")
        out.append("AGT SORTIE %s #%d | %+.2f$ (%s) | jour %+.2f$ (x%d) | solde $%.2f" % (
            sym, int(tid), pnl, reason, led["pnl"], led["n"], ai.balance))
    st["watches"] = watches


# ---------------- 6. APPRENANT ----------------
def learner(st, out):
    if not os.path.exists(DATA_F):
        return
    if time.time() - st.get("last_learn", 0) < 900:
        return
    st["last_learn"] = time.time()
    opens = {}
    closes = []
    try:
        for line in open(DATA_F, encoding="utf-8"):
            r = json.loads(line)
            if r["ev"] == "open":
                opens[r.get("key")] = r
            elif r["ev"] == "close":
                closes.append(r)
    except Exception:
        return
    tun = lj(TUNE_F, {})
    by_sym = {}
    for c in closes:
        try:
            ts = time.mktime(time.strptime(c["ts"], "%Y-%m-%d %H:%M:%S"))
        except Exception:
            continue
        if ts > time.time() - 10 * 86400:
            by_sym.setdefault(c["sym"], []).append(c)
    for sym, rows in by_sym.items():
        if len(rows) < 8:
            continue
        pnls = [r["pnl"] for r in rows]
        tp_hits = len([r for r in rows if "TP" in str(r.get("reason", "")).upper()])
        tp_rate = 100.0 * tp_hits / len(rows)
        wr = 100.0 * len([p for p in pnls if p > 0]) / len(rows)
        cur_tp = float(tun.get(sym, {}).get("tp_usd", TP_USD_DEF))
        cur_sc = float(tun.get(sym, {}).get("score_min", SCORE_MIN_DEF))
        new_tp, new_sc = cur_tp, cur_sc
        if tp_rate < 20 and cur_tp > 1.3:
            new_tp = round(cur_tp - 0.2, 2)
        elif tp_rate > 60 and cur_tp < 2.3:
            new_tp = round(cur_tp + 0.2, 2)
        if wr < 35 and cur_sc < 70:
            new_sc = round(cur_sc + 4)
        elif wr > 55 and cur_sc > 48:
            new_sc = round(cur_sc - 3)
        changed = []
        if new_tp != cur_tp:
            tun.setdefault(sym, {})["tp_usd"] = new_tp
            changed.append("tp_usd %.1f->%.1f (TP-hit %.0f%%)" % (cur_tp, new_tp, tp_rate))
        if new_sc != cur_sc:
            tun.setdefault(sym, {})["score_min"] = new_sc
            changed.append("score_min %.0f->%.0f (wr %.0f%%)" % (cur_sc, new_sc, wr))
        if changed:
            think("APPRENANT", sym, "; ".join(changed), "bornes tp 1.2..2.5 / score 48..70", "TUNE")
            out.append("AGT APPRENANT %s: %s (n=%d)" % (sym, "; ".join(changed), len(rows)))
    sj(TUNE_F, tun)


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
        st = lj(STATE_F, None)
        if st is None and os.path.exists(OLD_STATE_F):
            st = lj(OLD_STATE_F, {})
            st["migrated"] = "gsa_scalp_data"
            think("SYSTEM", "-", "etat repris de gsa_scalp_data", "continuite position en cours", "")
        st = st or {}
        allpos = mt5.positions_get() or []
        live = {str(p.ticket) for p in allpos}
        today = time.strftime("%Y-%m-%d", time.gmtime())

        supervisor(st, allpos, live, ai, out)
        sj(STATE_F, st)
        allpos = mt5.positions_get() or []

        block = risk_block(st, allpos, ai, today)
        if block:
            think("DECIDEUR", "-", "frein: " + block, "politique verrouillee (jamais pour pertes)", "")
            if block.startswith("plancher"):
                if not st.get("floor_alerted"):
                    st["floor_alerted"] = True
                    sj(STATE_F, st)
                    print("STOP TECHNIQUE AGENTS: solde $%.2f sous marge min $%.0f — la marge ne couvre plus un ordre (ce n'est pas une pause pertes)." % (
                        ai.balance, BAL_FLOOR))
                return
            sj(STATE_F, st)
            print("\n".join(out))
            return
        st["floor_alerted"] = False

        tun = lj(TUNE_F, {})
        news_min = news_impact_minutes()
        opened = 0
        for sym in MARKETS:
            mt5.symbol_select(sym, True)
            if opened:
                continue
            if any(p.symbol == sym and p.magic == MAGIC for p in allpos):
                continue
            col, cerr = collector(sym)
            if col is None:
                if cerr not in ("fige",):
                    think("COLLECTEUR", sym, "hors jeu", cerr, "")
                continue
            ast, _ = analyst(sym, col)
            op, _ = synthetizer(sym, ast, tun, news_min)
            if op is None:
                continue
            r, err = executor(op, st)
            if r is None:
                think("EXECUTEUR", sym, "non passe", err, "RIEN")
                continue
            opened += 1
            st["sigbar_" + sym] = op["bar"]
            pos_now = [x for x in (mt5.positions_get(symbol=sym) or []) if x.magic == MAGIC]
            if pos_now and not DRY:
                tk = mt5.symbol_info_tick(sym)
                st.setdefault("watches", {})[str(pos_now[0].ticket)] = {
                    "sym": sym, "dir": op["dir"], "entry": pos_now[0].price_open,
                    "open_ts": time.time(), "open_server_ts": int(tk.time) if tk else 0,
                    "dataset_key": "%s-%d" % (sym, op["bar"]), "last_profit": 0.0}
            dataset({"ev": "open", "key": "%s-%d" % (sym, op["bar"]), "sym": sym,
                     "dir": op["dir"], "px": op["px"], "tp_pts": op["tp_pts"],
                     "sl_mode": "NONE", "spread": op["spread"], "rsi": op["rsi"],
                     "atr": op["atr"], "score": op["score"], "votes": op["votes"],
                     "news_min": op["news_min"], "vol_ratio": op["vol_ratio"],
                     "hold_max_min": HOLD_MAX_MIN, "balance": round(ai.balance, 2),
                     "chain": "collecte>analyse(M1/M5/M15/H1)>synthese>decision>exec"})
            led = st.setdefault("ledger", {}).setdefault(today, {"pnl": 0.0, "n": 0})
            led["n"] += 1
            n_agree = sum(1 for v in op["votes"] if v == op["dir"])
            out.append("AGT ENTREE %s %s 0.01 @ %.5f | TP %.5f (+%.2f$) | score %.0f | confluence %d/4\n"
                       "SANS SL -> time-exit %dmin (filet 60) | spr %d RSI %.0f ATR %.0f vol x%.1f | news %s\n"
                       "collecte %d/48 du jour | solde $%.2f" % (
                           "BUY" if op["dir"] == 1 else "SELL", sym, op["px"], op["tp"],
                           op["tp_pts"] * op["u"], op["score"], n_agree, HOLD_MAX_MIN,
                           op["spread"], op["rsi"], op["atr"], op["vol_ratio"],
                           ("%dm" % news_min) if news_min < 900 else "calme",
                           led["n"], ai.balance))
        learner(st, out)
        sj(STATE_F, st)
        print("\n".join(out))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
