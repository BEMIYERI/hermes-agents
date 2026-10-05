# MT5 Visual EA Deployment Patterns

## Visual EA Architecture

A visual trading EA for MT5 displays real-time signals and market state directly on the chart. This reference covers the standard components and patterns.

## Component Checklist

Every visual EA should include these elements:

### 1. Expert Panel (OBJ_RECTANGLE_LABEL + OBJ_LABEL)
```mql5
// Panel background
ObjectCreate(0, "PANEL_BG", OBJ_RECTANGLE_LABEL, 0, 0, 0);
ObjectSetInteger(0, "PANEL_BG", OBJPROP_XDISTANCE, 10);
ObjectSetInteger(0, "PANEL_BG", OBJPROP_YDISTANCE, 10);
ObjectSetInteger(0, "PANEL_BG", OBJPROP_XSIZE, 280);
ObjectSetInteger(0, "PANEL_BG", OBJPROP_YSIZE, 300);
ObjectSetInteger(0, "PANEL_BG", OBJPROP_BGCOLOR, clrBlack);
ObjectSetInteger(0, "PANEL_BG", OBJPROP_COLOR, clrGray);

// Text labels inside panel
ObjectCreate(0, "LABEL_ACCOUNT", OBJ_LABEL, 0, 0, 0);
ObjectSetInteger(0, "LABEL_ACCOUNT", OBJPROP_COLOR, clrWhite);
ObjectSetInteger(0, "LABEL_ACCOUNT", OBJPROP_FONTSIZE, 9);
```

Panel contents typically:
- Account: Equity, Balance, Margin Free
- Position: type, entry price, TP, P&L, time elapsed
- Statistics: total trades, wins, losses, winrate, total profit
- Market: phase, trend, RSI, ATR, contraction
- Signal: status + condition
- Learning: winrate, adaptation status

### 2. Signal Arrows (OBJ_ARROW)
```mql5
// BUY arrow (green, up)
ObjectCreate(0, "ARROW_BUY_1", OBJ_ARROW, 0, time, price);
ObjectSetInteger(0, "ARROW_BUY_1", OBJPROP_ARROWCODE, 233);  // Up arrow
ObjectSetInteger(0, "ARROW_BUY_1", OBJPROP_COLOR, clrLime);   // Green
ObjectSetInteger(0, "ARROW_BUY_1", OBJPROP_WIDTH, 3);
ObjectSetInteger(0, "ARROW_BUY_1", OBJPROP_SELECTABLE, false);

// SELL arrow (red, down)
ObjectCreate(0, "ARROW_SELL_1", OBJ_ARROW, 0, time, price);
ObjectSetInteger(0, "ARROW_SELL_1", OBJPROP_ARROWCODE, 234);  // Down arrow
ObjectSetInteger(0, "ARROW_SELL_1", OBJPROP_COLOR, clrRed);    // Red
ObjectSetInteger(0, "ARROW_SELL_1", OBJPROP_WIDTH, 3);

// EXIT arrow (orange)
ObjectCreate(0, "ARROW_EXIT_1", OBJ_ARROW, 0, time, price);
ObjectSetInteger(0, "ARROW_EXIT_1", OBJPROP_ARROWCODE, 234);
ObjectSetInteger(0, "ARROW_EXIT_1", OBJPROP_COLOR, clrOrange);
ObjectSetInteger(0, "ARROW_EXIT_1", OBJPROP_WIDTH, 3);
```

Arrow codes reference:
- 233 = Up arrow (BUY)
- 234 = Down arrow (SELL/EXIT)
- 168 = Circle
- 236 = Square

### 3. Technical Lines (OBJ_HLINE)
```mql5
// Fibonacci levels
ObjectCreate(0, "FIB_618", OBJ_HLINE, 0, 0, fib618_price);
ObjectSetInteger(0, "FIB_618", OBJPROP_COLOR, clrOrange);
ObjectSetInteger(0, "FIB_618", OBJPROP_WIDTH, 1);
ObjectSetInteger(0, "FIB_618", OBJPROP_STYLE, STYLE_DASH);

// EMA lines
ObjectCreate(0, "EMA20", OBJ_HLINE, 0, 0, ema20_value);
ObjectSetInteger(0, "EMA20", OBJPROP_COLOR, clrLime);
ObjectSetInteger(0, "EMA20", OBJPROP_WIDTH, 2);

// Swing High/Low
ObjectCreate(0, "SWING_HIGH", OBJ_HLINE, 0, 0, swing_high);
ObjectSetInteger(0, "SWING_HIGH", OBJPROP_COLOR, clrRed);
ObjectSetInteger(0, "SWING_HIGH", OBJPROP_WIDTH, 2);
ObjectSetInteger(0, "SWING_HIGH", OBJPROP_STYLE, STYLE_SOLID);
```

### 4. Zone Rectangles (OBJ_RECTANGLE)
```mql5
// Entry zone
ObjectCreate(0, "ZONE_ENTRY", OBJ_RECTANGLE, 0, time1, top_price, time2, bottom_price);
ObjectSetInteger(0, "ZONE_ENTRY", OBJPROP_COLOR, clrLime);
ObjectSetInteger(0, "ZONE_ENTRY", OBJPROP_STYLE, STYLE_SOLID);
ObjectSetInteger(0, "ZONE_ENTRY", OBJPROP_FILL, true);
ObjectSetInteger(0, "ZONE_ENTRY", OBJPROP_BACK, true);
```

### 5. Text Labels (OBJ_TEXT)
```mql5
// Real-time label (updated on each tick)
ObjectCreate(0, "LABEL_RSI", OBJ_TEXT, 0, time, price_levels[0]);
ObjectSetString(0, "LABEL_RSI", OBJPROP_TEXT, "RSI: " + DoubleToString(rsi, 1));
ObjectSetInteger(0, "LABEL_RSI", OBJPROP_COLOR, clrCyan);
ObjectSetInteger(0, "LABEL_RSI", OBJPROP_FONTSIZE, 11);
ObjectSetInteger(0, "LABEL_RSI", OBJPROP_FONT, "Arial");
```

## Panel Text Format Template

Standard panel layout (multi-line text via OBJ_LABEL):

```
=== GOLD TRADER PRO v6 ===

[PRIX]        $XXXX.XX
[STATUT]      AUTO TRADING ON

📊 POSITION:
  Type:        BUY / SELL
  Entry:       $XXXX.XX
  TP:          $XXXX.XX
  P&L:         +$XX.XX / -$X.XX
  Time:        XX min
  % to TP:    XX%

📈 STATS:
  Trades:      XX
  Wins:        XX  Losses: XX
  WinRate:     XX%
  Total PnL:   +$XX.XX

📉 MARKET:
  Phase:       CONSOLIDATION/BREAKOUT/IMPULSE
  Trend:       UP/DOWN/INDETERMINE
  RSI:         XX.X
  ATR:         XX.XX pt
  Contraction: XX%

🎯 SIGNAL:     BUY/SELL/WAITING
  Condition:   EMA cross / RSI / BB / FIB

🧠 LEARNING:
  WinRate:     XX%
  Adaptation:  Active

📋 PARAMÈTRES:
  Lot:         0.01
  TP:          $X.XX
  Time Exit:   XX min
  Trailing:    X pts
  SL:          DÉSACTIVÉ
```

## EA Input Parameters (from reference EA)

When user provides a reference EA, extract and mirror these inputs:

```mql5
input int    SwingPeriod      = 25;      // Swing detection period
input double FibLevel1       = 0.618;   // Fibonacci 61.8%
input double FibLevel2       = 0.786;   // Fibonacci 78.6%
input int    ATRPeriod        = 14;      // ATR calculation period
input double ContractionRatio = 0.65;    // Market contraction threshold
input bool   ShowPanel        = true;    // Show Expert panel
input bool   ShowFibZones     = true;    // Show Fibonacci zones
input bool   EnableLearning   = true;    // Enable learning system

// Auto trading
input bool   EnableAutoTrading = true;   // Enable/disable auto trading
input double LotSize         = 0.01;    // Default lot size
input double TakeProfitUSD   = 2.0;     // TP in USD (2-5 USD)
input bool   CloseAllOnSignal = false;   // Close on new signal

// Risk management
input int    TimeExitMinutes  = 60;     // Auto exit after X minutes
input int    TrailingPts     = 15;      // Trailing stop points
input int    PauseBars       = 60;      // Bars to wait after signal
input int    MinBarsBetweenTrades = 30; // Minimum bars between trades
input int    MaxConsecutiveTrades = 2;  // Max consecutive trades
```

## Auto-Attachment Workflow

When user requires autonomous deployment (no manual drag-and-drop):

### Prerequisites
1. MT5 terminal must be running
2. EA file must be in `%APPDATA%/MetaQuotes/Terminal/<InstanceID>/MQL5/Experts/`
3. COM must be registered (check with `reg query HKCR /f MetaTrader5.Application`)

### Auto-Attach via COM (Python)
```python
import win32com.client

mt5 = win32com.client.Dispatch("MetaTrader5.Application")

# Find GOLD M1 chart
for i in range(mt5.ChartsTotal()):
    chart = mt5.ChartGet(i, 0)
    if chart.Symbol() == "GOLD" and chart.Period() == 1:
        gold_chart = chart
        break

# Create if not found
if gold_chart is None:
    gold_chart = mt5.ChartCreate("GOLD", 1)

mt5.ChartActivate(gold_chart)
result = mt5.ChartApplyExpert(gold_chart, ea_path, [])
```

### Known COM Failure Recovery

If COM returns `(-2147221005, 'Chaîne de classe incorrecte')`:
1. Verify MT5 is running: `tasklist | findstr terminal64`
2. Check COM registration: `reg query HKCR /f MetaTrader5.Application`
3. Restart MT5 and retry
4. If still failing, COM class is not registered — this is an environment issue

### Fallback When COM Fails

If COM fails and user requires autonomous operation:
- Document the limitation explicitly
- Present the manual attach steps as a fallback
- Do not pretend auto-attachment works when it doesn't
- Consider MQL5 script as alternative (requires MT5 UI to execute)

## Verification Checklist

Before declaring visual EA deployment complete:

- [ ] EA file exists in MQL5/Experts/
- [ ] EA compiles without errors in MetaEditor
- [ ] EA is attached to GOLD M1 chart (verify via MT5 UI or COM)
- [ ] GREEN arrows appear when BUY signal triggers
- [ ] RED arrows appear when SELL signal triggers
- [ ] ORANGE arrows appear when position exits
- [ ] Expert panel shows real-time data (equity, positions, stats)
- [ ] Technical lines visible (Fib, EMA, Swing, Support/Resist)
- [ ] Panel updates on each tick (not static)

## Color Convention (Standard)

| Element | Condition | Color |
|---------|-----------|-------|
| BUY arrow | Long signal/entry | Green (clrLime) |
| SELL arrow | Short signal/entry | Red (clrRed) |
| EXIT arrow | Position close | Orange (clrOrange) |
| Panel BG | Always visible | Black with gray border |
| Fib 61.8 | Support/resistance | Orange |
| Fib 78.6 | Support/resistance | Yellow |
| EMA20 | Trend filter | Lime green |
| EMA50 | Trend filter | Yellow |
| Swing High | Resistance | Red |
| Swing Low | Support | Green |
| Buy zone | Entry area | Green (semi-transparent) |
| Sell zone | Entry area | Red (semi-transparent) |
| Phase zone | Market state | Yellow/Green/Blue/White |
| RSI label | Indicator | Cyan |
| ATR label | Indicator | White |
| Phase label | Market state | Yellow/Green/Blue |

## Common Object Naming Conventions

Use prefixed names to avoid collisions with other EAs/indicators:
- Panel: `GTP_PANEL_BG`, `GTP_TITLE`, `GTP_INFO`  (GTP = Gold Trader Pro)
- Arrows: `GTP_ARROW_BUY_N`, `GTP_ARROW_SELL_N`, `GTP_ARROW_EXIT_N`
- Lines: `GTP_FIB618`, `GTP_EMA20`, `GTP_SWING_HIGH`
- Zones: `GTP_ZONE_ENTRY`, `GTP_ZONE_PHASE`
- Labels: `GTP_LABEL_RSI`, `GTP_LABEL_PRICE`

Prefixing ensures `ObjectsDeleteAll(0, "GTP_")` removes all EA objects cleanly on detach.
