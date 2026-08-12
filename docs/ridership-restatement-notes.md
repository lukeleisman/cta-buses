# 2025 ridership restatement — notes

Source: `docs/CTA_MEMO_Ridership_Update_2026-03-20.pdf` (CTA Planning & Innovation, dated 3.17.2026, effective 3.20.2026).

## Which method our data is

New. Our 2025 bus total is 198.6M in both `data/cta_bus_daily.csv` and `data/cta_bus_monthly.csv`, matching the restated 199.6M system figure. Original was 184.0M. Both files pulled after the 3.20.2026 effective date.

## What changed

Restated back to 2025-01-01 only; 2024 and earlier remain on the old method.

- Actual Scheidt & Bachmann farebox counts replaced the placeholder estimates used during 2025.
- APC-based undercount factors replaced video-based factors. APC totals run ~10% above fare-collection totals; a 0.5 factor now applies to cash farebox counts.
- Bus 2025: 184.0M → 199.6M (+15.7M, +8.5%). Rail: 135.2M → 138.4M (+2.4%), separate change, station-level underpaid counts.

Undercount corrections are not new — the memo confirms adjustment factors were historically derived from video observations. This is a change in how the factor is derived.

## Caveats for the analysis

- 2025 growth over 2024 is bounded, not point-identified. The old method held evasion at 2023–24 rates while actual evasion grew, so a new-method 2024 would also exceed 180.4M by an unknown amount. True growth sits between +2% and +10%; the reported +10.1% is not like-for-like.
- Route-level increases were proportional to recorded farebox counts, so they track evasion by route (~66 routes 0–10%, ~30 at 10–20%, ~18 above 20%, a few negative). Not a common time shift for route-vs-route comparisons crossing 2024-12-31. Within-2025 comparisons unaffected.
