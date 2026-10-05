# MT5 Agent Common Errors

## Connection Failures

### "Terminal: Invalid params" on mt5.initialize()

This occurs when:
- MT5 terminal is not running
- Wrong server name specified
- Account doesn't exist on that server

**Fix:**
1. Start MT5 terminal manually first
2. Verify server name: check MT5 toolbar → Tools → Options → Server
3. Ensure account is logged in on that server

### "No connection" errors

MT5 must be running and connected before agent starts.

**Fix:** Check `mt5.terminal_info().connected` before trading loop.

---

## Order Execution Failures

### OrderSend returns None

Usually means MT5 API is not initialized or connection lost.

**Fix:**
```python
if not mt5.terminal_info().connected:
    mt5.initialize()  # or restart
```

### retcode != TRADE_RETCODE_DONE

Common retcodes and meanings:
- `TRADE_RETCODE_REQUOTE` — Price changed, retry with current price
- `TRADE_RETCODE_LIMIT_ORDER` — Price not reached, adjust price
- `TRADE_RETCODE_MARKET_CLOSED` — Market closed for symbol
- `TRADE_RETCODE_ZEROVOLUME` — Invalid volume
- `TRADE_RETCODE_NOT_ENOUGH_MONEY` — Insufficient margin
- `TRADE_RETCODE_TARGET_FINISHED` — Order filled (actually success)

**Fix:** Log retcode and comment; adjust parameters accordingly.

---

## Data Issues

### copy_rates_from_pos returns None

- Symbol not available on account
- Invalid timeframe

**Fix:**
```python
symbol_info = mt5.symbol_info("GOLD")
if symbol_info is None:
    print("GOLD not available on this account")
```

---

## DataFrame vs ndarray Confusion

**Pitfall:** `mt5.copy_rates_from_pos()` returns a **numpy ndarray**, not a DataFrame.

```python
# WRONG - will fail
candles = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M1, 0, 200)
atr = get_atr(candles)  # get_atr uses .values which doesn't exist on ndarray

# CORRECT
candles = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M1, 0, 200)
candles_df = pd.DataFrame(candles)
atr = get_atr(candles_df)  # convert to DataFrame first
```

**Rule:** Always convert MT5 rate arrays to DataFrame before passing to pandas-based functions.

---

## Symbol Confusion

**Pitfall:** Using `XAUUSD` when broker expects `GOLD`.

XM Global uses `GOLD` as the symbol name. Always verify:

```python
symbol_info = mt5.symbol_info("GOLD")
if symbol_info is None:
    # Try alternative names
    for name in ["GOLD", "XAUUSD", "GOLD.us"]:
        if mt5.symbol_info(name):
            SYMBOL = name
            break
```

---

## Lot/Sizing Math Errors

**Pitfall:** Dividing by zero when `tick_value` is 0 or None.

```python
# WRONG
risk_per_lot = sl_distance * symbol_info.trade_tick_value  # crash if tick_value is 0
lot = risk_dollar / risk_per_lot  # ZeroDivisionError

# CORRECT
tick_value = symbol_info.trade_tick_value or 1.0
risk_per_lot = sl_distance * tick_value
lot = risk_dollar / risk_per_lot if risk_per_lot > 0 else symbol_info.volume_min
```

**Pitfall:** Not checking margin before ordering.

Always verify `lot * margin_per_lot <= margin_free` before sending order, or reduce lot to fit.

---

## Timezone & Timestamps

**Pitfall:** `mt5.copy_rates_from_pos()` returns timestamps as Unix seconds (`r.time` is an integer). Converting with `pd.to_datetime(df['time'], unit='s')` works. Do NOT pass a Series of timestamps to `.strftime()` — extract scalar first.

```python
# WRONG
print(f"Time: {df.index[-1].strftime('%H:%M:%S')}")  # fails if index[-1] is a Series

# CORRECT
last_time = df.index[-1]
print(f"Time: {last_time.strftime('%H:%M:%S')}")
```

---

## Multi-Timeframe Analysis Pitfalls

**Pitfall:** When combining multiple timeframes (M15 + M5 + M1), verify each timeframe's candle count independently — a shorter timeframe with fewer candles returns `None` from `copy_rates_from_pos` and propagates `None` through your analysis chain. Guard every timeframe block separately.

```python
# WRONG — assumes all TFs return data
m15 = get_candles(mt5.TIMEFRAME_M15, 300)
m5 = get_candles(mt5.TIMEFRAME_M5, 300)
m1 = get_candles(mt5.TIMEFRAME_M1, 300)

# ... later, m1 is None → AttributeError on m1['close']

# CORRECT — guard each
if m15 is not None and len(m15) > 50:
    # M15 analysis
if m5 is not None and len(m5) > 100:
    # M5 analysis
if m1 is not None and len(m1) > 50:
    # M1 analysis
```

**Pitfall:** EMA/SMA crossover logic on the entry timeframe must compare against the **same** timeframe's EMAs, not higher timeframe EMAs. Using M15 EMA values for M1 entry triggers produces whipsaw entries.

**Pitfall:** RSI on different timeframes has different "normal" ranges — M1 RSI of 70+ can be normal in a strong trend; M15 RSI of 70+ is more meaningful. Do not apply the same threshold rigidly across all timeframes without context.
