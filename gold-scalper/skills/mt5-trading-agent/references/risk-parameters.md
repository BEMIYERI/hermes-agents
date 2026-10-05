# MT5 Agent Risk Parameters

## Parameter Reference

| Parameter | Default | Description | Adjustment Rules |
|-----------|---------|-------------|------------------|
| `RISK_PER_TRADE` | 0.10 | % of capital risked per trade | Never exceed 0.20; lower for small accounts |
| `SL_ATR_MULTIPLIER` | 1.0 | SL distance in ATR units | Floor = spread × 2; cap at 200 points |
| `TAKE_PROFIT_RATIO` | 2.0 | TP/SL ratio | Maintain ≥ 1.5; 2.0 is optimal for scalping |
| `MAX_DAILY_LOSS` | 0.50 | Daily loss limit (% of starting capital) | Hard stop; agent pauses when hit |
| `MAX_TIME_EXIT_MINUTES` | 60 | Max position lifetime | Exit stale trades; prevents capital lock-up |
| `TRAILING_STOP_POINTS` | 15 | Profit lock distance | Activate after 20pts profit |
| `MIN_CAPITAL` | 3.0 | Minimum capital to trade | Below this, cannot cover spread cost |

## Capital Thresholds for GOLD (XM Global)

| Capital Range | Max Lot | Notes |
|---------------|---------|-------|
| < $3 | Cannot trade | Spread aller-retour ($0.55/0.01 lot) is a large share of the account |
| $3 – $70 | 0.01 | Risk 10% = $0.30 – $7 per trade |
| $70 – $120 | 0.02 | Step up allowed after first threshold |
| > $120 | 0.03 | Full sizing available |

## Lot Calculation

```python
def calc_lot(capital, sl_points, symbol_info):
    risk_dollar = capital * RISK_PER_TRADE
    sl_distance = sl_points * symbol_info.point
    risk_per_lot = sl_distance * symbol_info.trade_tick_value
    lot = risk_dollar / risk_per_lot if risk_per_lot > 0 else symbol_info.volume_min
    
    # Round to volume step
    volume_step = symbol_info.volume_step or 0.01
    lot = round(lot / volume_step) * volume_step
    
    # Apply bounds
    lot = max(lot, symbol_info.volume_min)
    lot = min(lot, symbol_info.volume_max or 10.0)
    lot = min(lot, 0.1)  # Cap at 0.1 for safety
    
    # Margin check
    if lot * (symbol_info.margin_initial or 500) > mt5.account_info().margin_free:
        lot = max(symbol_info.volume_min,
                  round(mt5.account_info().margin_free / (symbol_info.margin_initial or 500) / volume_step) * volume_step)
        lot = min(lot, 0.1)
    
    return lot
```

## Spread Awareness

**GOLD on XM Global typical spread: 50–60 points**

Le coût du spread, c'est `spread_pts × point_value` où `point_value =
trade_tick_value × lot`. Sur GOLD, `trade_tick_value = 1.0` **par point par
lot** — donc à 0.01 lot un point vaut $0.01 :

- aller-retour 55 pts à 0.01 lot = **$0.55** (et non $5.50 — erreur d'un facteur
  100 qui circule dans d'anciens documents)
- avec $20 de capital, le spread aller-retour = **2.75%** du capital par entrée,
  pas 27.5%
- avec $100, ce même aller-retour = 0.55% du capital

**Rule:** avant toute entrée, vérifier
`capital > spread_pts * trade_tick_value * lot * min_lot`. Le seuil de
rentabilité qui en découle est
`WR = (SL + spread_trip) / (TP + SL + spread_trip)` — et il ne dépend pas du
capital. Voir `references/edge-validation.md` pour le protocole complet.
