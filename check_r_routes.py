"""Evidence for how the R routes are treated in exploration.ipynb section 2.

The R-prefixed routes are the 2013 Red Line South reconstruction shuttles. Two choices are
made about them in the notebook, and this script is what backs them up:

  1. They are given no corridor. Their number is the STATION they served, not the street they
     ran on, so the numeric-root rule files them under corridors they never touched.
  2. They are NOT dropped -- their rides stay in every ridership total, including the
     day-of-week section. This quantifies what that costs.

Reads the raw portal file directly, so it does not depend on the notebook having been run.

    python check_r_routes.py
"""
import pandas as pd

DAILY   = 'data/cta_bus_daily.csv'
MONTHLY = 'data/cta_bus_monthly.csv'
DOW     = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# The 20 Frequent Network routes, as CTA labels them.
FREQ = ['J14', '4', '9', '12', '20', '34', '47', '49', '53', '54',
        '55', '60', '63', '66', '72', '77', '79', '81', '82', '95']


def numeric_root(route):
    """The corridor rule used in the notebook: X49 -> 49, J14 -> 14, R95 -> 95."""
    import re
    m = re.search(r'\d+', route)
    return m.group() if m else route


d = pd.read_csv(DAILY, dtype={'route': str}, parse_dates=['date'])
mon = pd.read_csv(MONTHLY, dtype={'route': str}, parse_dates=['month_beginning'])
names = mon.sort_values('month_beginning').groupby('route').routename.last()

is_r = d.route.str.match(r'^R\d', na=False)
print(f'rows {len(d):,}   R-route rows {int(is_r.sum()):,}\n')

# ---------------------------------------------------------------------------
# 1. What they are, and which corridors the numeric-root rule would give them
# ---------------------------------------------------------------------------
inv = (d[is_r].groupby('route')
         .agg(first=('date', 'min'), last=('date', 'max'),
              days=('date', 'nunique'), rides_per_day=('rides', 'mean')))
inv['name'] = names.reindex(inv.index)
inv['would_join_corridor'] = [numeric_root(r) for r in inv.index]
inv['frequent_network'] = inv.would_join_corridor.isin(FREQ)
for c in ('first', 'last'):
    inv[c] = inv[c].dt.strftime('%Y-%m-%d')

print('R routes and the corridor each would have joined:')
print(inv[['name', 'first', 'last', 'days', 'rides_per_day',
           'would_join_corridor', 'frequent_network']].round(0).to_string())
print(f'\n  routes: {len(inv)}   '
      f'landing in a Frequent Network corridor: {int(inv.frequent_network.sum())} '
      f'({", ".join(inv.index[inv.frequent_network])})')
print(f'  years they ran: {sorted(d.loc[is_r, "date"].dt.year.unique())}\n')

# ---------------------------------------------------------------------------
# 2. Cost of leaving them in the day-of-week shape (notebook section 5)
# ---------------------------------------------------------------------------
yr13  = d.date.dt.year == 2013            # the only year they ran
sys13 = d[yr13].groupby('date').rides.sum()
r13   = d[yr13 & is_r].groupby('date').rides.sum()


def dow_shape(s):
    """Mean rides by day of week, divided by the period's own overall mean."""
    m = s.groupby(s.index.dayofweek).mean()
    return m / m.mean()


shape = pd.DataFrame({'with R': dow_shape(sys13),
                      'without R': dow_shape(sys13.sub(r13, fill_value=0))})
shape['diff']   = shape['with R'] - shape['without R']
shape['diff %'] = (shape['with R'] / shape['without R'] - 1) * 100
shape.index = DOW

print('2013 day-of-week shape, each column normalised by its own 2013 mean:')
print(shape.round(4).to_string())

worst = shape['diff %'].abs()
window = (d.date >= r13.index.min()) & (d.date <= r13.index.max())
print(f'\n  largest shift from keeping them in : {worst.max():.2f}%  ({worst.idxmax()})')
print(f'  R share of 2013 ridership          : {r13.sum() / sys13.sum() * 100:.2f}%')
print(f'  R share during the shutdown window : '
      f'{r13.sum() / d[window].rides.sum() * 100:.2f}%')
print(f'\n  Their own week is flatter than the system\'s:')
print('   ', dow_shape(r13).round(3).to_numpy(), '(R routes)')
print('   ', dow_shape(sys13).round(3).to_numpy(), '(system, 2013)')
