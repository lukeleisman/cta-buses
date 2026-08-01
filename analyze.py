"""
Did the CTA Frequent Network gain ridership after its 2025 service increase?

Design
------
The rollout was staggered across four 2025 schedule changes (Mar/Jun/Aug/Dec).
Rather than lean on exact rollout dates, we use a buffered pre/post design:

    PRE   = Jan-May 2025  (only phase-1 routes treated, and only from Mar 23)
    PRE2  = Jan-May 2024  (nothing treated)
    POST  = Jan-May 2026  (all 20 routes fully treated)
    BUFFER= Jun 2025 - Dec 2025 excluded entirely (rollout in progress)

Comparing the same calendar months (Jan-May) across years holds seasonality
fixed by construction. A control group of non-Frequent routes then absorbs
system-wide trend, giving a difference-in-differences estimate.
"""

import pandas as pd
import numpy as np

FREQ = ['J14', '4', '9', '12', '20', '34', '47', '49', '53', '54',
        '55', '60', '63', '66', '72', '77', '79', '81', '82', '95']

# Express / branch variants of Frequent routes. Excluded from the control group
# because service changes on the trunk route spill into them.
VARIANTS = ['X4', 'X9', 'X49', '49B', '53A', '54A', '54B', '55A', '55N',
            '63W', '81W', '8A', '52A', '62H', '111A', '85A']

PHASE = {  # approximate service-change date each route joined
    '2025-03-23': ['J14', '34', '47', '54', '60', '63', '79', '95'],
    '2025-06-15': ['4', '49', '66'],
    '2025-08-17': ['20', '53', '55', '77', '82'],
    '2025-12-21': ['9', '12', '72', '81'],
}

DAYNAME = {'W': 'Weekday', 'A': 'Saturday', 'U': 'Sunday/Holiday'}


def load():
    d = pd.read_csv('data/cta_bus_daily.csv', dtype={'route': str},
                    parse_dates=['date'])
    d['route'] = d.route.str.strip()
    d['year'] = d.date.dt.year
    d['month'] = d.date.dt.month
    return d


def window(d, year, months=(1, 2, 3, 4, 5)):
    return d[(d.year == year) & (d.month.isin(months))]


def avg_daily(d):
    """Mean daily rides per route per daytype -> avoids month-length and
    weekday-count composition effects."""
    return d.groupby(['route', 'daytype']).rides.mean().unstack()


def pct(a, b):
    return (b - a) / a * 100


def main():
    d = load()
    freq = set(FREQ)
    variants = set(VARIANTS)

    # ---- route-level: Jan-May 2025 -> Jan-May 2026 -------------------------
    p25 = avg_daily(window(d, 2025))
    p26 = avg_daily(window(d, 2026))
    p24 = avg_daily(window(d, 2024))

    common = p25.index.intersection(p26.index).intersection(p24.index)
    # drop tiny routes: unstable percentages
    keep = [r for r in common if p25.loc[r, 'W'] >= 500]
    p24, p25, p26 = p24.loc[keep], p25.loc[keep], p26.loc[keep]

    grp = pd.Series(['Frequent' if r in freq else
                     ('Variant' if r in variants else 'Control')
                     for r in keep], index=keep)

    print('=' * 74)
    print('CTA FREQUENT NETWORK — RIDERSHIP CHANGE')
    print('Jan–May windows, average daily boardings by day type')
    print('=' * 74)

    rows = []
    for dt in ['W', 'A', 'U']:
        for g in ['Frequent', 'Control']:
            idx = grp[grp == g].index
            # aggregate = total rides across group (weights by route size)
            a24, a25, a26 = (x.loc[idx, dt].sum() for x in (p24, p25, p26))
            rows.append({
                'Day type': DAYNAME[dt], 'Group': g, 'n routes': len(idx),
                '2024': round(a24), '2025': round(a25), '2026': round(a26),
                '%chg 25→26': round(pct(a25, a26), 1),
                '%chg 24→26': round(pct(a24, a26), 1),
            })
    agg = pd.DataFrame(rows)

    print('\n--- Aggregate boardings (sum of average weekday/Sat/Sun rides) ---')
    print(agg.to_string(index=False))

    print('\n--- Difference-in-differences (Frequent minus Control) ---')
    did = []
    for dt in ['W', 'A', 'U']:
        s = agg[agg['Day type'] == DAYNAME[dt]].set_index('Group')
        did.append({
            'Day type': DAYNAME[dt],
            'Frequent %chg 25→26': s.loc['Frequent', '%chg 25→26'],
            'Control %chg 25→26': s.loc['Control', '%chg 25→26'],
            'DiD 25→26 (pp)': round(s.loc['Frequent', '%chg 25→26']
                                    - s.loc['Control', '%chg 25→26'], 1),
            'DiD 24→26 (pp)': round(s.loc['Frequent', '%chg 24→26']
                                    - s.loc['Control', '%chg 24→26'], 1),
        })
    print(pd.DataFrame(did).to_string(index=False))

    # ---- per-route detail --------------------------------------------------
    phase_of = {r: dt for dt, rs in PHASE.items() for r in rs}
    per = pd.DataFrame({
        'route': FREQ,
        'phase': [phase_of[r] for r in FREQ],
        'wkdy 2025': [round(p25.loc[r, 'W']) if r in p25.index else np.nan
                      for r in FREQ],
        'wkdy 2026': [round(p26.loc[r, 'W']) if r in p26.index else np.nan
                      for r in FREQ],
    })
    per['wkdy %'] = (pct(per['wkdy 2025'], per['wkdy 2026'])).round(1)
    per['sun %'] = [round(pct(p25.loc[r, 'U'], p26.loc[r, 'U']), 1)
                    if r in p25.index else np.nan for r in FREQ]
    per['sat %'] = [round(pct(p25.loc[r, 'A'], p26.loc[r, 'A']), 1)
                    if r in p25.index else np.nan for r in FREQ]
    per = per.sort_values(['phase', 'wkdy %'], ascending=[True, False])

    ctrl_w = pct(p25.loc[grp[grp == 'Control'].index, 'W'].sum(),
                 p26.loc[grp[grp == 'Control'].index, 'W'].sum())
    per['wkdy % vs ctrl'] = (per['wkdy %'] - ctrl_w).round(1)

    print('\n--- Per-route change, Jan–May 2025 → Jan–May 2026 ---')
    print(f'(control-group weekday change was {ctrl_w:+.1f}%)')
    print(per.to_string(index=False))

    # ---- distribution check: is the gain broad or driven by outliers? ------
    fr = per['wkdy %'].dropna()
    ct = pct(p25.loc[grp[grp == 'Control'].index, 'W'],
             p26.loc[grp[grp == 'Control'].index, 'W']).dropna()
    print('\n--- Median route-level weekday %chg (unweighted) ---')
    print(f'  Frequent (n={len(fr)}): median {fr.median():+.1f}%  '
          f'mean {fr.mean():+.1f}%  beat control median: '
          f'{(fr > ct.median()).sum()}/{len(fr)} routes')
    print(f'  Control  (n={len(ct)}): median {ct.median():+.1f}%  '
          f'mean {ct.mean():+.1f}%')

    # ---- PARALLEL-TRENDS TEST ---------------------------------------------
    # A DiD is only credible if Frequent routes were NOT already outgrowing
    # the control group before treatment. Run the same Jan–May comparison on
    # pre-treatment year pairs as a placebo.
    print('\n' + '=' * 74)
    print('PARALLEL-TRENDS / PLACEBO TEST — same Jan–May design, pre years')
    print('=' * 74)
    yrs = [2022, 2023, 2024, 2025, 2026]
    panels = {y: avg_daily(window(d, y)) for y in yrs}
    fidx = grp[grp == 'Frequent'].index
    cidx = grp[grp == 'Control'].index
    pt = []
    for dt in ['W', 'A', 'U']:
        for a, b in zip(yrs, yrs[1:]):
            if not all(set(fidx) <= set(panels[y].index) for y in (a, b)):
                continue
            f = pct(panels[a].loc[fidx, dt].sum(), panels[b].loc[fidx, dt].sum())
            c = pct(panels[a].loc[cidx, dt].sum(), panels[b].loc[cidx, dt].sum())
            pt.append({'Day type': DAYNAME[dt], 'Period': f'{a}→{b}',
                       'Frequent %': round(f, 1), 'Control %': round(c, 1),
                       'Gap (pp)': round(f - c, 1),
                       'Treated?': 'POST' if b == 2026 else 'pre'})
    pt = pd.DataFrame(pt)
    print(pt.to_string(index=False))

    print('\n--- Pre-trend-adjusted effect (post gap minus mean pre gap) ---')
    adj = []
    for dt in ['W', 'A', 'U']:
        s = pt[pt['Day type'] == DAYNAME[dt]]
        pre = s[s['Treated?'] == 'pre']['Gap (pp)'].mean()
        post = s[s['Treated?'] == 'POST']['Gap (pp)'].iloc[0]
        adj.append({'Day type': DAYNAME[dt],
                    'Mean pre-period gap (pp)': round(pre, 1),
                    'Post-period gap (pp)': round(post, 1),
                    'Adjusted effect (pp)': round(post - pre, 1)})
    print(pd.DataFrame(adj).to_string(index=False))

    # ---- longest-running cohort: phase 1, two full post years -------------
    print('\n--- Phase-1 routes (treated Mar 2025): Jun–Dec windows ---')
    ph1 = PHASE['2025-03-23']
    for yr in (2023, 2024, 2025):
        pass
    jd = {yr: avg_daily(window(d, yr, months=(6, 7, 8, 9, 10, 11, 12)))
          for yr in (2023, 2024, 2025)}
    idx1 = [r for r in ph1 if all(r in jd[y].index for y in jd)]
    ctrl_idx = [r for r in grp[grp == 'Control'].index
                if all(r in jd[y].index for y in jd)]
    out = []
    for label, idx in [('Phase-1 Frequent', idx1), ('Control', ctrl_idx)]:
        v = [jd[y].loc[idx, 'W'].sum() for y in (2023, 2024, 2025)]
        out.append({'Group': label, 'n': len(idx),
                    '2023': round(v[0]), '2024': round(v[1]),
                    '2025': round(v[2]),
                    '%chg 23→24 (pre)': round(pct(v[0], v[1]), 1),
                    '%chg 24→25 (post)': round(pct(v[1], v[2]), 1)})
    print(pd.DataFrame(out).to_string(index=False))

    per.to_csv('output/per_route_change.csv', index=False)
    agg.to_csv('output/aggregate_change.csv', index=False)
    print('\nWrote output/per_route_change.csv, output/aggregate_change.csv')


if __name__ == '__main__':
    main()
