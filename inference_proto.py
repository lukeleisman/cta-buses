import pandas as pd, numpy as np, re
from scipy import stats

d = pd.read_csv('data/cta_bus_daily.csv', dtype={'route': str}, parse_dates=['date'])
d['route'] = d.route.str.strip(); d['year'] = d.date.dt.year; d['month'] = d.date.dt.month
def corridor(r):
    if re.fullmatch(r'X\d+', r): return r[1:]
    m = re.fullmatch(r'(\d+)[A-Z]+', r)
    return m.group(1) if m else r
d['corridor'] = d.route.map(corridor)

FREQ = ['J14','4','9','12','20','34','47','49','53','54','55','60','63','66','72','77','79','81','82','95']
YEARS = [2022,2023,2024,2025,2026]
def panel(y):
    s = d[(d.year==y)&(d.month<=5)]
    return s.groupby(['corridor','route','daytype']).rides.mean().groupby(['corridor','daytype']).sum().unstack()
P = {y: panel(y) for y in YEARS}
common = set.intersection(*(set(p.index) for p in P.values()))
keep = sorted(r for r in common if P[2025].loc[r,'W'] >= 500)
F = [r for r in keep if r in FREQ]; C = [r for r in keep if r not in FREQ]

rng = np.random.default_rng(0)

def devs(dt):
    """Per-corridor: log-growth in post year minus that corridor's mean pre-year log-growth.
    Restricted to corridors that actually run on this day type in every year."""
    ok = [r for r in keep
          if all(np.isfinite(P[y].loc[r,dt]) and P[y].loc[r,dt] > 0 for y in YEARS)]
    g = {}
    for a,b in zip(YEARS, YEARS[1:]):
        g[b] = np.log(P[b].loc[ok,dt].values / P[a].loc[ok,dt].values)
    pre = np.mean([g[y] for y in [2023,2024,2025]], axis=0)
    return pd.Series(g[2026] - pre, index=ok)

print(f"{'':<16}{'Freq mean':>10}{'Ctrl mean':>10}{'diff(pp)':>10}{'95% CI':>18}{'perm p':>9}{'t p':>8}")
for dt, nm in [('W','Weekday'), ('A','Saturday'), ('U','Sunday/Hol')]:
    v = devs(dt)
    fi=[r for r in F if r in v.index]; ci=[r for r in C if r in v.index]
    f = v[fi].values; c = v[ci].values
    D = (f.mean() - c.mean())*100

    # permutation: shuffle which corridors are labelled Frequent
    allv = np.concatenate([f,c]); n = len(f)
    null = np.empty(20000)
    for i in range(20000):
        p = rng.permutation(allv)
        null[i] = p[:n].mean() - p[n:].mean()
    pperm = (np.abs(null*100) >= abs(D)).mean()

    # bootstrap CI: resample corridors within each group
    bs = np.empty(20000)
    for i in range(20000):
        bs[i] = (rng.choice(f, n, True).mean() - rng.choice(c, len(c), True).mean())*100
    lo, hi = np.percentile(bs, [2.5, 97.5])

    pt = stats.ttest_ind(f, c, equal_var=False).pvalue
    print(f'{nm:<16}{f.mean()*100:>9.1f}%{c.mean()*100:>9.1f}%{D:>9.1f} [{lo:>6.1f},{hi:>6.1f}]{pperm:>9.4f}{pt:>8.4f}')

# dose-response: within Frequent corridors, Sunday deviation vs weekday deviation
dw,du=devs('W'),devs('U')
_f=[r for r in F if r in dw.index and r in du.index]
w,u = dw[_f].values, du[_f].values
print(f'\nDose-response (within the 20 Frequent corridors), Sunday dev - weekday dev:')
print(f'  n={len(_f)} | mean {np.mean(u-w)*100:+.1f}pp | positive on {(u>w).sum()}/{len(_f)}')
print(f'  Wilcoxon signed-rank p = {stats.wilcoxon(u, w).pvalue:.5f}')
print(f'  paired t-test p        = {stats.ttest_rel(u, w).pvalue:.5f}')
# same contrast among control corridors, as a placebo
_c=[r for r in C if r in dw.index and r in du.index]
wc,uc = dw[_c].values, du[_c].values
print(f'  same contrast in control corridors: mean {np.mean(uc-wc)*100:+.1f}pp, '
      f'positive on {(uc>wc).sum()}/{len(_c)}, Wilcoxon p = {stats.wilcoxon(uc, wc).pvalue:.5f}')
