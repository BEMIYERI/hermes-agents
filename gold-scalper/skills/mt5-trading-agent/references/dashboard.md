# MT5 Trading Agent Dashboard Generation

## Pattern Overview

A self-refreshing HTML dashboard provides external monitoring of the agent's state without requiring MT5 UI access. The pattern: Python polls MT5 via the `MetaTrader5` pip package every N seconds, renders a dark-themed HTML file, and the browser auto-refreshes.

## File Structure

```
agent/
├── generate_dashboard.py      # Dashboard generator script
├── dashboard.html             # Generated output (committed or ignored)
└── skill references/          # This file
```

## Generator Script Structure

```python
import MetaTrader5 as mt5
import os
from datetime import datetime

OUTPUT_FILE = "dashboard.html"

def get_mt5_data():
    """Poll MT5 for current state."""
    data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'account': {},
        'symbol': {},
        'positions': [],
        'chart_data': []
    }
    
    if not mt5.initialize():
        return data
    
    # Account info
    acc = mt5.account_info()
    data['account'] = {
        'login': acc.login,
        'balance': f"{acc.balance:.2f}",
        'equity': f"{acc.equity:.2f}",
        'margin_free': f"{acc.margin_free:.2f}",
    }
    
    # Symbol info (e.g., GOLD)
    sym = mt5.symbol_info("GOLD")
    if sym:
        tick = mt5.symbol_info_tick("GOLD")
        data['symbol'] = {
            'bid': f"{tick.bid:.2f}",
            'ask': f"{tick.ask:.2f}",
            'spread_pts': f"{(tick.ask - tick.bid) / sym.point:.0f}",
        }
    
    # Open positions
    positions = mt5.positions_get()
    if positions:
        for pos in positions:
            data['positions'].append({
                'ticket': pos.ticket,
                'type': "ACHAT" if pos.type == 0 else "VENTE",
                'volume': f"{pos.volume:.2f}",
                'open_price': f"{pos.open_price:.2f}",
                'profit': f"{pos.profit:.2f}",
            })
    
    # Recent candles for mini chart
    rates = mt5.copy_rates_from("GOLD", mt5.TIMEFRAME_M1, time.time() - 3600, 50)
    if rates is not None and len(rates) > 0:
        data['chart_data'] = [
            {'time': datetime.fromtimestamp(r['time']).strftime('%H:%M'),
             'open': f"{r['open']:.2f}", 'high': f"{r['high']:.2f}",
             'low': f"{r['low']:.2f}", 'close': f"{r['close']:.2f}"}
            for r in rates[-30:]
        ]
    
    mt5.shutdown()
    return data

def render_html(data):
    """Generate dark-themed HTML with auto-refresh."""
    # Build candlestick visual elements (div-based, no GDI+)
    candles_html = ""
    for c in data['chart_data'][-15:]:
        oc, cc = float(c['open']), float(c['close'])
        color = "#22c55e" if cc >= oc else "#ef4444"
        # Simple height-based visualization, no GDI+ dependency
        candles_html += f'<div style="display:inline-block;width:6px;height:100px;">'
        candles_html += f'<div style="background:{color};opacity:0.7;height:{abs(cc-oc)*25}px;'
        candles_html += f'position:relative;bottom:{min(oc,cc)*25}px;"></div></div>'
    
    # Progress bar toward target
    equity = float(data['account'].get('equity', 0))
    progress = min(equity / 200, 1)  # 200 = target
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="15">
    <title>GOLD TRADER PRO - Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: #e5e7eb; }}
        .card {{ background: #1a1a2e; border-radius: 10px; padding: 15px; margin: 10px 0; }}
        .value {{ font-size: 24px; font-weight: bold; color: #22c55e; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ color: #6b7280; text-transform: uppercase; }}
        th, td {{ padding: 8px; border-bottom: 1px solid #2d3561; }}
    </style>
</head>
<body>
    <div class="card">
        <h3>Equity: <span class="value">${{data['account'].get('equity', '0')}}</span></h3>
        <p>Balance: ${data['account'].get('balance', '0')} | Spread: {data['symbol'].get('spread_pts', '0')} pts</p>
    </div>
    
    <div class="card">
        <h3>Positions ({len(data['positions'])})</h3>
        <table>
            <tr><th>Ticket</th><th>Type</th><th>Volume</th><th>Entry</th><th>P&L</th></tr>
            {''.join(f'<tr><td>{p["ticket"]}</td><td style="color:{"#22c55e" if p["type"]=="ACHAT" else "#ef4444"}">{p["type"]}</td><td>{p["volume"]}</td><td>${p["open_price"]}</td><td>${p["profit"]}</td></tr>' for p in data['positions']) if data['positions'] else '<tr><td colspan="5" style="text-align:center;color:#6b7280">Aucune position</td></tr>'}
        </table>
    </div>
    
    <div class="card">
        <h3>GOLD M1 (last 15 candles)</h3>
        <div style="display:flex;gap:1px;overflow-x:auto">{candles_html}</div>
    </div>
    
    <div style="text-align:center;color:#6b7280;padding:20px;font-size:12px">
        <p>Dernière mise à jour: {data['timestamp']}</p>
        <p>Objectif: $200 | Progression: {progress*100:.1f}%</p>
    </div>
</body>
</html>"""
    return html

def main():
    data = get_mt5_data()
    html = render_html(data)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Dashboard: {OUTPUT_FILE} ({os.path.getsize(OUTPUT_FILE)} octets)")

if __name__ == '__main__':
    main()
```

## CSS Guidelines

- Use `#0a0a0f` background, `#1a1a2e` cards, `#2d3561` borders
- Colors: green `#22c55e` (positives), red `#ef4444` (negatives), gold `#ffd700` (accent)
- Font: system sans-serif stack (Segoe UI on Windows)
- No external dependencies — no CDN, no JS frameworks
- Auto-refresh via `<meta http-equiv="refresh" content="15">` (15 seconds)

## Candlestick Rendering

**Pitfall:** Avoid GDI+ or canvas-based rendering in the HTML generator — GDI+ object creation fails with "Nom de fichier ou extension trop long" on some Windows configurations when called from a long-running Python process. Use pure-CSS div-based rendering instead.

```python
# WRONG - may fail with GDI+ errors
from PIL import Image, ImageDraw  # or matplotlib, or cairo

# CORRECT - pure CSS, no native rendering
candle_html = f'<div style="height:{abs(close-open)*scale}px;background:{color}"></div>'
```

## Refresh Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Refresh interval | 15 seconds | Balance between freshness and MT5 API load |
| Data poll interval | Every generation | No separate caching layer needed |
| Candle window | 15-30 candles | Enough context without overwhelming |

## Pitfalls

**GDI+ failures in chart rendering:** When generating chart images (PNG) using PIL/ImageDraw or matplotlib from a Python process that has been running for hours, GDI+ can fail with "Nom de fichier ou extension trop long" (WinError 206) even for in-memory operations. This is a process-lifetime GDI+ resource issue, not a path-length issue. Prefer CSS-based rendering for HTML dashboards and limit image generation to short-lived processes.

**MT5 initialization overhead:** Each dashboard generation calls `mt5.initialize()` and `mt5.shutdown()`. At 15-second refresh, this is acceptable. For sub-second refresh, keep a persistent MT5 connection and only refresh the HTML.

**Position list empty state:** Always handle the case where `positions_get()` returns None or an empty list — show a clear "Aucune position" message rather than an empty table.

**Number formatting:** Use f-strings with explicit formatting (`{value:.2f}`) rather than `str()` — MT5 returns floats that may show many decimal places from floating-point artifacts.

## Embedding in Agent Workflow

```bash
# Run as part of agent startup sequence
python3 generate_dashboard.py

# Or as a scheduled refresh alongside the trading loop
# (separate thread or cron every 15s)
```

The generated `dashboard.html` can be opened in any browser. For Hermes desktop, deliver via `MEDIA:` path.
