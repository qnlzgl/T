Hi [Boss Name],

I wanted to give a quick update on the framework I’ve been testing for converting article-derived signals into a systematic trading strategy.

Overview of the approach

The idea is to treat each extracted research signal as a directional view with an explicit forecast horizon, and then aggregate all active views into a rolling position over time.

For each article, the LLM extracts:
- Asset (commodity / contract)
- Direction (bullish or bearish)
- Forecast horizon (start and end dates)

Rather than treating all signals equally on each day, I normalize their contribution by horizon length.

Signal construction

- Each signal is assigned a total unit directional weight (+1 for bullish, −1 for bearish).
- This unit weight is evenly distributed across the forecast horizon.
  - For example, a 20-day signal contributes +1/20 per day.
  - A 2-year signal contributes a much smaller daily weight, but for longer.
- This ensures that long-dated views do not mechanically dominate positioning simply due to their duration.

On any given day, the net position is the sum of all active signal contributions, with a simple cap applied to avoid excessive exposure. Execution assumptions are deliberately kept simple to isolate signal quality rather than trading optimization.

Key observations

Using this normalized rolling framework:
- Standalone PnL from article-derived signals is generally weak and noisy.
- Performance remains close to flat or negative after costs.
- The limitation appears structural: most research views are conditional and context-dependent, which does not translate well into direct directional execution.

Conclusion

This suggests that article-derived signals are unlikely to work well as a standalone trading strategy, even under conservative and transparent assumptions. However, they may still have value as contextual inputs (e.g. regime filters or confirmation layers) alongside existing systematic strategies.

Happy to walk through the details if helpful, but my recommendation would be not to invest significantly more time in pursuing this as a primary alpha source.

Best,  
Guanlun


Hi [Boss Name],

I wanted to share an updated summary of the horizon-normalized rolling signal framework and the results across commodities.

Method recap

As discussed, each article-derived signal is treated as a directional view with an explicit forecast horizon:
- Bullish signals contribute positive exposure, bearish signals negative exposure.
- Each signal is assigned a unit total weight (+1 / −1), evenly distributed across its forecast horizon.
- On any given day, net position is the sum of all active signal contributions, with a simple position cap applied.
- Execution assumptions are deliberately kept simple to focus on signal quality rather than optimization.

This setup avoids long-dated views mechanically dominating exposure and keeps the framework transparent and interpretable.

Results summary

Across the broader commodity universe, standalone performance from article-derived signals is generally weak and inconsistent.

However, there are a few cases where the framework shows limited but noticeable structure:
- Brent: relatively flat overall, with some clustering of positive PnL during specific macro periods.
- Natural Gas: modest improvement versus random, though still noisy and regime-dependent.
- Coffee and Cotton: small positive drift and slightly higher Sharpe than the rest of the universe, albeit with limited sample sizes.

Outside of these names, most commodities show no meaningful alpha and often deteriorate after costs.

Interpretation

The mixed results suggest that the limitation is structural rather than implementation-driven:
- Research articles often express conditional or narrative-driven views.
- Directional extraction alone loses important regime, timing, and context.
- Where signals appear to “work,” they seem tied to specific market structures rather than a broadly repeatable effect.

Conclusion and recommendation

Overall, article-derived signals do not appear suitable as a standalone systematic trading strategy. The small pockets of positive performance (e.g. NG, Coffee, Cotton) are interesting but likely insufficient to justify a dedicated strategy on their own.

My view is that this approach is best positioned as:
- a contextual or regime-filter input, or
- a confirmation layer alongside existing systematic frameworks,

rather than a primary alpha source. Unless we want to pursue it in that direction, I would not recommend investing significantly more time in expanding this as a standalone strategy.

Happy to discuss further or walk through the details if useful.

Best,  
Guanlun
