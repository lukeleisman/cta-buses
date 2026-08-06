# CTA bus service — what is promised, what is scheduled, what is delivered

This repository exists to understand CTA bus service. It works outward through four questions:

1. **Claimed** — what CTA advertises. The Frequent Network page promises 10-minute-or-less
   waits on 20 routes.
2. **Scheduled** — what the timetable actually plans, which is not always what is advertised.
3. **Delivered** — what riders actually get, measured from vehicle positions rather than
   assumed from the schedule.
4. **Effect on ridership** — whether service changes move boardings, especially across the
   Frequent Network rollout.

Between March and December 2025 the CTA phased 20 bus routes into that Frequent Network. Can we
see it in the ridership data — and do the routes that gained the most service show the biggest
change? That is where the work started, and questions 2 and 3 are now in progress.

![CTA bus ridership by week, 2001–2026](docs/weekly_ridership.png)

Twenty-five years of weekly boardings: ~6M/week through the 2000s, a slow decline to ~5M by
2019, the 2020 collapse to 1.3M, and a recovery that has reached ~4.2M. The lower panel is the
number of routes reporting, which moves enough that no system total can be read without it.

## Status: in progress

The analysis is being rebuilt from the data up. An earlier agent-generated version
(`frequent_network_analysis.ipynb`) reached conclusions that have **not** been independently
verified and whose data selections were not all visible in the notebook — treat every number in
it as provisional. The rebuild starts with `exploration.ipynb`.

Ground rule for the rebuild: every filter or transformation happens in a visible cell and prints
what it did, and checks report their counts even when the count is zero.

## Layout

- **`exploration.ipynb`** — start here. System-wide exploration before any before/after design:
  integrity checks and cross-checks, corridors, total and per-route ridership, per-era statistics,
  and day-of-week structure. Writes `data/derived/` for the two notebooks below.
- `holidays.ipynb` — which days CTA actually runs a holiday schedule on, and how much ridership
  changes when it does. Needs `exploration.ipynb` to have run.
- `seasonality.ipynb` — the within-year profile, trend removed and holiday weeks held out, and
  whether it can be pooled across eras. Needs both of the above to have run.
- `frequent_network_analysis.ipynb` — the earlier route-level difference-in-differences writeup.
  Being replaced; kept for reference.
- `analyze.py`, `inference_proto.py`, `build_notebook.py` — supporting scripts for that earlier
  notebook.
- `fetch_stopwatch.py` — downloads the realised-service archive (below). Resumable;
  `--dry-run` sizes a pull before it moves any data.
- `docs/bus-tracker-data-plan.md` — the realised-frequency acquisition plan: source inventory,
  what to pull where, known hazards, and the calibration that comes before any claim.
- `docs/methods.md` — derivations and references. Currently headways and rider wait; other
  statistical methods get added here rather than expanded inline.
- `docs/` — figures referenced from this README.
- `output/` — CSV summaries and figures from `analyze.py`.

## Data

Neither dataset is committed (`data/` is gitignored). Both are public and regenerate from the
Chicago Data Portal.

**Daily totals by route** → `data/cta_bus_daily.csv` (47MB)
[CTA Ridership – Bus Routes – Daily Totals by Route](https://data.cityofchicago.org/Transportation/CTA-Ridership-Bus-Routes-Daily-Totals-by-Route/jyb9-n7fm/about_data)
(`jyb9-n7fm`). Columns `route`, `date`, `daytype` (`W` weekday, `A` Saturday, `U` Sunday/holiday),
`rides`. Covers 2001-01-01 to 2026-05-31, 188 routes.

```
curl "https://data.cityofchicago.org/resource/jyb9-n7fm.csv?\$limit=2000000" \
     -o data/cta_bus_daily.csv
```

**Monthly day-type averages, with route names** → `data/cta_bus_monthly.csv` (3MB)
[CTA Ridership – Bus Routes – Monthly Day-Type Averages & Totals](https://data.cityofchicago.org/Transportation/CTA-Ridership-Bus-Routes-Monthly-Day-Type-Averages/bynn-gwxy)
(`bynn-gwxy`). Supplies the route names the daily file lacks, and cross-checks our aggregation.

```
curl "https://data.cityofchicago.org/resource/bynn-gwxy.csv?\$limit=50000&\$order=route,month_beginning" \
     -o data/cta_bus_monthly.csv
```

**Route geometry** → `data/geo/` — downloaded by `exploration.ipynb` §4.a if missing, so no
manual step is needed. Two files, because routes move:

- [CTA - Bus Routes](https://data.cityofchicago.org/Transportation/CTA-Bus-Routes/6uva-a5ei/about_data)
  (`6uva-a5ei`), updated 2025-01-08 — 127 routes, the current network.
- [CTA - Bus Routes - KML](https://data.cityofchicago.org/Transportation/CTA-Bus-Routes-KML-Deprecated-February-2015-/atza-xq2n)
  (`atza-xq2n`), deprecated 2015-02 — 140 routes, the only historical geometry the portal keeps.
  Adds 22 discontinued routes the current file has dropped.

Together they cover 149 of the 188 routes in the ridership data. The 39 without geometry —
`R` shuttles, `X` expresses, special-event IDs — are 8.5% of summed mean riders/day, and are
absent from the map and the lifespan panels rather than placed on a guess.

### Realised service — Mansueto StopWatch

The ridership files carry no service measure, so *delivered* frequency comes from the
[Mansueto Institute's StopWatch](https://github.com/mansueto-institute/cta-stop-watch) archive,
which continues the [Chi Hack Night Ghost Buses](https://github.com/chihacknight/chn-ghost-buses)
scrape: CTA Bus Tracker polled every 5 minutes since 2022-05-19, interpolated to stop-level
arrivals, plus CTA's own GTFS accumulated into historic timetables.

| Product | `--what` | Size | Coverage |
|---|---|---|---|
| Actual arrivals, per pattern | `processed` | 34.4 GB | 886 patterns |
| Scheduled arrivals, per route | `timetables` | 13.8 GB | 124 routes |
| Their summary metrics | `metrics` | 357 MB | one file |
| Raw 5-minute pings | `raw` | 50.6 GB | 1529 days, no gaps |

Sizes measured 2026-08-05; the pipeline runs daily, so they grow. Requires `pyarrow`.

```
python fetch_stopwatch.py --what timetables --dest data/stopwatch --dry-run
python fetch_stopwatch.py --what processed  --dest <big-disk>
```

Read [`docs/bus-tracker-data-plan.md`](docs/bus-tracker-data-plan.md) before pulling — it
covers which products are actually needed, the pattern-churn hazard, and what has to be
calibrated on control routes before any number is quoted.

## Running

Use the `divvy-cta` conda environment (pandas 3.0.5) — base anaconda is two major versions
behind and is not what these notebooks were run against. Dependencies are not yet pinned.

```
conda activate divvy-cta
jupyter lab exploration.ipynb
```

The three notebooks run in order — `exploration.ipynb`, then `holidays.ipynb`, then
`seasonality.ipynb`. The first writes `data/derived/daily.csv` and `route_inventory.csv`; the
second writes `data/derived/holiday_calendar.csv`, which the third reads. `data/` is gitignored,
so these are local and regenerate by re-running the notebooks.

Notebook outputs are stripped on commit by [`nbstripout`](https://github.com/kynan/nbstripout),
configured in `.gitattributes`, so the repository stays small. Your working copy keeps its
figures; the committed version does not. After cloning, enable the filter once:

```
nbstripout --install --attributes .gitattributes
```

## Frequent Network rollout

Four phases, from [Streetsblog Chicago](https://chi.streetsblog.org/2025/03/05/10-minute-version-cta-promises-shorter-headways-on-20-bus-routes-there-are-a-bunch-of-reasons-riders-hope-the-plan-will-work-out)
and CTA press releases:

| Effective | Routes |
|---|---|
| 2025-03-23 | J14, 34, 47, 54, 60, 63, 79, 95 |
| 2025-06-15 | 4, 49, 66 |
| 2025-08-17 | 20, 53, 55, 77, 82 |
| 2025-12-21 | 9, 12, 72, 81 |

Sources conflict on whether #53 and #20 joined in June or August. Program definition — 10 minutes
or better, 6a–9p weekdays / 9a–9p weekends — is on the
[CTA Frequent Network page](https://www.transitchicago.com/frequent/).
