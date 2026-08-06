# Realised bus frequency — data acquisition plan

The ridership files carry no service measure. Everything so far treats the Frequent Network
as a date on which a route was *declared* frequent; nothing tests whether 10-minute service
actually appeared. The Mansueto Institute's **StopWatch** archive closes that gap, and it is
the only public source that does.

Sizes and coverage below were measured by HEAD sweep on 2026-08-05. The pipeline runs daily,
so they grow.

## Source

StopWatch continues the Chi Hack Night [Ghost Buses](https://github.com/chihacknight/chn-ghost-buses)
scrape: CTA Bus Tracker `getvehicles` polled **every 5 minutes since 2022-05-19**, interpolated
to a stop-level record of when each bus passed each stop. Repo:
[mansueto-institute/cta-stop-watch](https://github.com/mansueto-institute/cta-stop-watch),
served from `https://d2v7z51jmtm0iq.cloudfront.net/cta-stop-watch`.

Published analysis covers June 2022 – July 2024 only; everything after that is the automated
pipeline running unattended and is not covered by their report.

| Product | Path | Size | Units | Content |
|---|---|---|---|---|
| Actual arrivals | `processed_by_pid/trips_{pid}_full.parquet` | **34.4 GB** | 886 patterns | one row per trip × stop, interpolated |
| Scheduled arrivals | `clean_timetables/rt{rt}_timetable.parquet` | **13.8 GB** | 124 routes | one row per trip × stop × date |
| Summary metrics | `metrics/stop_metrics_df_latest.parquet` | 357 MB | 1 file | their aggregation |
| Raw pings | `full_day_data/{date}.csv` | 50.6 GB | 1529 days | unprocessed, 5-min |
| Crosswalk | `rt_to_pid.csv` | 12 KB | 940 rows | route → pattern |

Restricted to the 20 Frequent Network routes: actuals 11.7 GB, timetables 4.74 GB.

**Raw coverage is complete.** All 1,529 dates from 2022-05-19 to 2026-07-25 return 200 — no
missing days. The only partial is 2022-05-19 itself (1.1 MB against a 30 MB weekday median),
the day the scrape started. Weekday file size grows 30.2 → 44.2 MB median from 2022 to 2026;
whether that is more service or more scraping is unresolved and is checked once the data is
local, not before.

## The two sides line up

Actual (`trips_{pid}_full.parquet`) and scheduled (`rt{rt}_timetable.parquet`) both give one
row per stop visit with a `bus_stop_time` datetime, on the same pattern and stop keys:

```
actual     seg_combined  typ  stop_sequence  bus_stop_time  speed_mph
           unique_trip_vehicle_day  stpid  p_stp_id  vid  rt  pid

scheduled  route_id  pid  schd_trip_id  stop_id  stop_sequence
           service_id  trip_id  bus_stop_time
```

So a headway is a sort-and-diff within (route, stop, direction) on **either** side, computed
the same way on both, and realised-vs-scheduled is a join. Headways are not stored — which is
better than inheriting theirs, because we choose the windows rather than adopt their 6am–8pm
filter, which does not match the Frequent Network's 6a–9p weekday / 9a–9p weekend promise.

No transit.land needed. `clean_timetables` is CTA's own published GTFS accumulated and
deduped over time by their pipeline, so the 500-download free tier stays unspent.

## What to pull, and where

**On the other computer — 48.2 GB.** `processed` (34.4) + `timetables` (13.8), all routes.
Not just the Frequent Network: controls carry the calibration and the counterfactual, so
scoping to the 20 treated routes now would have to be undone later.

```
python fetch_stopwatch.py --what processed  --dest <big-disk> --dry-run   # confirm footprint
python fetch_stopwatch.py --what processed  --dest <big-disk>
python fetch_stopwatch.py --what timetables --dest <big-disk>
```

Resumable — size-checked against the server, `.part` until verified, safe to re-issue.

**Locally — small.** The metrics file (357 MB) as an independent cross-check on our own
aggregation, and a few dozen raw days for the interpolation check:

```
python fetch_stopwatch.py --what metrics --dest data/stopwatch
python fetch_stopwatch.py --what raw --start 2024-04-01 --end 2024-04-30 --dest data/stopwatch
```

**Skip** the full 50.6 GB raw archive. It is only needed to audit the interpolation, and a
sample of days answers that.

## What this can answer

1. **Is the 10-minute promise met?** Distribution of realised headways on Frequent Network
   routes inside the promised windows, and the fraction exceeding 10 minutes. The 5-minute
   figure is the *sampling* interval on vehicle positions, not the uncertainty on a headway —
   see below.
2. **Realised against scheduled.** Same computation both sides, joined. Independent of whether
   CTA's advertised headway was ever run.
3. **Did frequency change at the phase dates?** The four phases against control routes —
   the ridership event-study design, with service on the left-hand side instead of assumed.
4. **Does realised service explain the ridership response better than scheduled?** Only after
   1–3 stand up.

## Why 5-minute polling is enough

A 5-minute sampling interval does **not** imply 5-minute uncertainty on a headway. Two
reasons, and they compound:

**Interpolation is well constrained.** A bus moves along a fixed path at a measured speed. At
~10 mph it covers ~0.8 miles between pings, spanning several stops at typical CTA spacing, and
its distance along the pattern is recorded at each ping (`pdist` raw, `speed_mph` and
`seg_combined` processed). Placing a stop crossing between two pings is therefore an
interpolation on a known arc with known endpoints and a known speed — not a guess across an
unobserved gap. The residual error comes from *within-interval* speed variation (dwell time,
signals), not from the sampling interval, and is plausibly tens of seconds rather than minutes.

**The quantity we want is a difference at a fixed stop.** A headway is `t₂ − t₁` for
successive buses at the *same* stop, both interpolated by the same procedure over the same
geometry. Whatever that procedure gets systematically wrong there — a slow corner, an
unmodelled dwell, a consistently late-firing ping — enters both terms and cancels in the
difference. What survives is the difference of two independent within-interval deviations,
which is small against a 10-minute threshold.

So the plan is a real distribution of headways, not a bound. Calibration's job is to *size the
residual*, not to establish whether the instrument works.

## What "headway" means here

**Headway is the time between one bus and the next bus behind it, measured at a fixed place on
the route.** Stand at a corner, watch a 66 go by, start a stopwatch, stop it when the next 66
going the same way passes: that interval is a headway. It is a property of the *service at a
place*, not of any one bus.

There is a real ambiguity worth killing off, because the other reading — how much progress a
bus makes as it moves from stop to stop — names a different quantity, usually called **running
time** or **trip duration**. The two are independent: a route can run slowly and evenly (long
running time, steady headways) or quickly and erratically (short running time, bunched
headways). The insights index computes both, side by side and separately, from the same GTFS
trips:

- headway — `scripts/fetch-gtfs.js:463-464`, the median of gaps between successive trip
  departures.
- duration — `scripts/fetch-gtfs.js:446`, `(lastArrival − firstDeparture) / 60` for one trip.

Only the first is what the 10-minute promise is about. The second is what `speed_mph` in the
StopWatch actuals speaks to, and it is a separate question we are not asking yet.

The standard definition agrees, and pins the measurement to a stop. GTFS
[`frequencies.txt`](https://gtfs.org/documentation/schedule/reference/#frequenciestxt) defines
`headway_secs` as:

> "Time interval (in seconds) between departures from the same stop (same stop_sequence) for
> the same trip pattern (same trip_id) during this time period."

### Three ways it gets operationalised — we use the third

The word survives three different measurements, which give different numbers, and mixing them
is how the confusion starts:

| Where measured | How | Source |
|---|---|---|
| At the origin terminal | median gap between successive trip *departures* | `fetch-gtfs.js:442-464` |
| Between two vehicles, in space | `(pdist₂ − pdist₁) / 880 ft-per-min` | `src/bus/gaps.js:4,39-40` |
| **At a named stop, in time** | **gap between successive passings of that stop** | **ours** |

The first is what CTA's own "every 10 minutes" is built from, but spacing drifts as buses run,
so terminal headway and mid-route headway diverge — that divergence is a large part of what we
want to measure. The second is a live proxy the bot needs because it has only a snapshot of
positions; its own code calls it "crude... only used as a ratio, not an absolute ETA"
(`gaps.js:2-3`). We need neither approximation: the StopWatch actuals give the times buses
actually passed each stop, so we measure the rider's interval directly.

### How we compute it

At one stop, in one direction, collect the times buses passed it and sort them. The differences
between consecutive times are the headways — a list of minute values, one per gap. Everything
downstream is a statistic of that list. The identical computation on `clean_timetables` gives
the scheduled headways at the same stop, which is what makes realised-vs-scheduled a
like-for-like comparison rather than a comparison against CTA's terminal-based advertisement.

Four rules decide which passings count:

- **Buses in service only.** Layovers, parked vehicles and deadheads are dropped, or a bus
  sitting at a terminal counts as an arrival nobody could board. The insights code excludes a
  terminal zone for exactly this reason (`gaps.js:42-45`).
- **Pooled across patterns, split by direction.** A rider boards whatever comes going their
  way, so every pattern serving that stop in that direction contributes to one list. Direction
  never pools. This is also what neutralises pattern churn: renumbering moves trips between
  pattern IDs, but the stop still sees the same buses. (Right for boarding; looser for a rider
  whose destination a short-turn never reaches.)
- **Both ends inside the window.** For 6a–9p, a gap counts only if both passings fall inside
  it — otherwise the overnight hole enters as a single 540-minute headway.
- **No headway for the first bus of a window.** Nothing precedes it.

## What to report, and why the mean headway is not enough

Derivations, worked example and references: **[methods.md — Headways and rider wait](methods.md#headways-and-rider-wait)**.

"Every 10 minutes" can be true on average while most riders wait longer than 10 minutes,
because riders do not arrive when the buses do. A rider lands in a gap with probability
proportional to that gap's length, so long gaps catch more people than a per-gap average
suggests. Bunching moves mass into the long gaps **without changing the mean headway at all**:
three buses arriving together on a 10-minute route leave a 30-minute hole, and the mean is
still 10. The insights bot documents the same limitation of its own effective-headway number
(`docs/GHOSTING.md`): "if the surviving buses clump together, the mean gap is unchanged but
riders in the resulting hole wait longer than the mean implies."

Writing the observed headways at a stop as `h`, the whole rider-facing object is one survival
curve — the share of riders waiting longer than `w`, equivalently the share of the time the
next bus is more than `w` minutes away:

```
S(w) = Σ max(hᵢ − w, 0) / Σ hᵢ
```

Report **`S(w)` as a curve**, plus two headline numbers:

- **Service experienced** — `S(10)`, the share of riders waiting over 10 minutes.
- **Service delivered** — `count(hᵢ > 10) / n`, the share of gaps over 10 minutes.

Mean headway never appears without `CV` beside it, since mean rider wait is
`(mean headway / 2) · (1 + CV²)`.

This sharpens the event study too: a phase could add bus-hours, hold the mean headway at 10,
and leave `S(10)` flat or worse if the added service bunches. That is a finding, not a failure.

**The tracker does not rescue this.** The derivation only needs the moment of consultation to
be independent of the buses, not the rider to be standing at the stop — so it applies unchanged
to someone checking an app, and `S(w)` is exactly the distribution of the wait the app reveals.
A rider who sees 18 minutes and takes another mode has absorbed the failure as a fare or an
abandoned trip rather than as waiting time. The tracker changes the *response* to a failure,
not its incidence, which is why the service is measured through headways rather than through
observed waits.

## Method notes worth borrowing

From the `chicago-transit-insights` detector docs — their real-time methods differ from ours
(we have interpolated stop arrivals; they estimate from live spacing), but their failure modes
were learned the expensive way and transfer directly.

- **Exclude terminal zones.** Buses near the pattern start/end are on layover, not running
  headways. They gate on a route-length-scaled buffer, and at post time drop anything whose
  nearest stop *is* the first or last named stop. Without this, layovers read as arrivals.
- **Exclude parked buses.** A vehicle that has barely moved for ~5 minutes is not providing
  service even while it broadcasts on the route. `speed_mph` and `pdist` let us apply this.
- **Never use `duration / headway` for expected vehicle count.** They tried it; it overestimates
  by 3–5× during ramp-up and ramp-down hours, where the headway comes from a few clustered trip
  starts. Use area-under-curve instead — for each scheduled trip add the fraction of each hour
  it is in progress, giving the mean number simultaneously running.
- **Different filters for different questions.** Rider-facing headway wants the dominant
  `service_id` and dominant origin terminal, or garage pullouts and short-turns corrupt the
  median. Counts of vehicles on the street want *every* revenue trip. Inheriting the first set
  into the second made route 79 eastbound — a Frequent Network route — read 6 expected against
  ~17 observed.
- **`pdist` and GTFS shapes are different coordinate systems.** Join actuals to schedule on
  lat/lon or stop id, never on distance-along-pattern.

**One thing we cannot borrow.** Their schedule adherence uses `stst`/`stsd`, the scheduled trip
start each bus self-reports, which pins a vehicle to an exact GTFS trip with no guessing. The
StopWatch scrape does **not** capture those fields — it has `tatripid` and `origtatripno`,
which StopWatch itself says are not unique, hence their synthetic trip id. So per-vehicle
schedule adherence is not available to us retrospectively; we compare *distributions* of
realised and scheduled headway at a stop, not trip-to-trip deviations.

## Calibrate before any of it

Standing rule: no difference-statistic without a null. Before any
number is quoted, on **control routes only** — never the 20 — establish:

- **Residual size.** Reconstruct headways from processed arrivals; compare against raw pings
  for the same days. How much does interpolation move a *gap*, as opposed to an arrival time?
  The cancellation argument above predicts the first is much smaller than the second — check it.
- **Residual near the threshold.** The fraction exceeding 10 minutes depends on error at 10
  minutes specifically, not on average error. Bias there is what matters.
- **Asymmetries that do not cancel.** A dropped poll and a genuinely absent bus look alike;
  a ghost bus is a real signal, not noise. Where the two terms come from different regimes
  the cancellation argument weakens, and those cases need naming.
- **A null.** What does this pipeline report for a route whose schedule did *not* change over
  a phase boundary? That is the noise floor every treated-route estimate is read against.

## Quirks to handle when they surface, not before

- **Pattern churn at service changes.** CTA renumbers patterns when it reworks a schedule, so
  a route's service migrates across pattern IDs. Pattern 20426 on route 66 runs 2023-06-05 to
  2025-03-21 and stops — two days before phase 1. Anything left at pattern level will show
  phantom service collapses on exactly the dates of interest. Roll up to route × stop.
- **54 of 940 crosswalk entries have no file** (404), and route 19's timetable is missing.
  Likely the same churn; unconfirmed. The fetch script lists them rather than failing.
- **Join hygiene.** Stop id is `stpid` in actuals, `stop_id` in schedules; `pid` is
  zero-padded (`06672`) in schedules and float-like (`20426.0`) in actuals.
- **A sampled file?** The one pattern inspected returned exactly 12,000 rows with dates out of
  order — suspiciously round. Check row counts against date span once local.
- **Schedule dedup method.** `update_schedule.py` keeps "trips from a schedule in which there
  was not an update", and the pre-pipeline backfill came from transit.land. Read it before
  trusting the early period.

## Prerequisite

`divvy-cta` has pandas 3.0.5 but **no pyarrow**, so it cannot read any of this. Base has
pyarrow 14.0.2 but pandas 2.1.4, which is not what the notebooks were run against.

```
conda install -n divvy-cta pyarrow
```

## Not used: chicago-transit-alerts

[cailinpitt/chicago-transit-alerts](https://github.com/cailinpitt/chicago-transit-alerts)
publishes CTA disruption incidents, and led here, but cannot answer these questions. Its
`history.sqlite` has **90-day retention**, so it is a rolling window rather than an archive —
`data_start_ts` is 2026-04-26 and will keep advancing. Coverage begins four months after the
final Frequent Network phase, so there is no pre-period. And it is a thresholded event log:
448 bus incidents over three months across 125 routes, with firings further suppressed by
cooldown. A rate needs the ordinary headways too, and those were never recorded. Useful only
for naming a specific incident, with a permalink.
