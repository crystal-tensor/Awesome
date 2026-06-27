# Design System

## Overview

FinTerra is a research-grade financial intelligence product with two visual modes: a dark command-center cockpit for live news simulation, and a light institutional analytics workspace for model validation. The layout uses dense sidebars, floating panels, metric cards, market maps, chart canvases, and table-driven evidence. The identity should feel like a serious quant lab: precise, data-rich, restrained, and cinematic only when showing the map or model engine.

## Colors

- **Lab Surface**: `#0b111c` - near-black shell for the financial intelligence lab.
- **Sidebar Navy**: `#102033` - deep blue navigation and strategy workbench sidebars.
- **Content Surface**: `#f4f7fb` - light analytics surface used by the model overview.
- **Primary Blue**: `#2f6df6` - selected controls, run buttons, and standard strategy curve.
- **Cyan Signal**: `#52d7f7` - map nodes, graph highlights, and live-generation accents.
- **Quantum Rose**: `#e11d48` - PT / quantum result emphasis.
- **Model Teal**: `#0f766e` - model summary evidence and positive improvement.
- **Text Dark**: `#18212f` - primary text on light surfaces.
- **Muted Text**: `#64748b` - labels, captions, and secondary notes.
- **Border Soft**: `#d9e3ef` - light-surface card borders.

## Typography

- **Primary UI**: Barlow Condensed with generic sans-serif fallback. The source product uses dense Chinese financial UI patterns; the video keeps compact, high-contrast typography for reliable rendering.
- **Video Display**: Barlow Condensed. Used for giant titles and numeric callouts to avoid a generic web-page feel while keeping a modern financial register.
- **Data Voice**: JetBrains Mono. Used for timestamps, ratios, ticker codes, and technical labels.
- **Scale**: Hero statements 78-118px, scene headings 52-72px, body/captions 30-42px, data labels 18-24px.

## Elevation

The product uses thin borders, translucent dark overlays, and compact metric panels rather than heavy drop shadows. Dark scenes should use glows behind important graph nodes and soft panel outlines. Light scenes should use crisp card borders, small radius corners, and restrained shadows only for lifted screenshot panels.

## Components

- **Financial Map Cockpit**: A global map with glowing market nodes, dotted relationship lines, a left news sidebar, and floating ask/graph panels.
- **MiroFish Process Stream**: A live log panel showing role generation, multi-round discussion, and graph focus states during simulation.
- **Strategy Workbench**: Dark sidebar plus wide chart workspace with two metric cards for classic 5-20 and quantum 5-20 backtests.
- **Model Market Cards**: Four market cards comparing average improvement across return, annual return, Sharpe, and drawdown.
- **Single Stock Detail**: Table row selection flows into a single-stock backtest panel with paired metric cards and a two-line return curve.

## Do's and Don'ts

### Do's

- Use real captured screenshots as the hero proof in every product scene.
- Keep financial numbers large, tabular, and visibly grounded in the source UI.
- Use cyan for live intelligence and rose for PT / quantum uplift.
- Use thin dividing rules and compact panels to preserve the institutional product feel.
- Show risk disclaimers as research framing, not as decorative fine print.

### Don'ts

- Do not turn this into a generic AI promo with abstract gradients.
- Do not invent performance metrics beyond the captured page data.
- Do not hide the actual product UI behind dark overlays.
- Do not use playful rounded marketing cards; keep the frame serious and evidence-led.
- Do not imply investment advice, guaranteed returns, or automatic trading.
