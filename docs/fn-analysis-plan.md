# Rebuild plan — `frequent_network_analysis.ipynb`

Draft for Luke's approval, 2026-08-05. **Nothing in this plan has been executed against
ridership outcomes.** The old notebook is untouched.

## Provenance note — read this first

An earlier draft of this plan contained per-route and pooled before/after ridership results
that I computed while planning. That was a mistake: the design was not fixed yet, so looking at
outcomes first is the pre-registration violation §1 exists to prevent. **Those numbers are void
and are not carried into this document.** Any design choice below that was reached after seeing
them is flagged `[POST-HOC — re-derive]` and must be re-established from control routes before
it is accepted.

The distinction being applied throughout:

- **Outcome data = ridership.** Do not look at it for the 20 treated corridors until the design
  is fixed and approved. Feasibility questions (how wide is the null, does the window have
  power) are answerable on **control routes only**, and that is how they will be answered.
- **Treatment data = scheduled service (GTFS).** Measuring what CTA actually ran is not an
  outcome and does not bias the test — it is reading the intervention protocol. It is used
  freely below.

---

## 1. Hypotheses, fixed before outcomes are examined

Goes in the notebook first, and fixes statistic, windows, null and decision rule.

- **H1 — network level.** Pooled across the 20 corridors, ridership rises modestly after
  rollout, relative to its own history and to the rest of the system. Direction predicted,
  magnitude small.
- **H2 — dose-response.** The change in a route's ridership on a given day type increases with
  the service actually added *for that day type*. Estimated as an elasticity β, **predicted in
  advance at β ≈ 0.3–0.6** from the transit literature (§5). H2 is the primary test.

H2 is primary because the dose varies **within route across day types**, so route fixed effects
absorb every route-level confounder — construction, neighbourhood trend, the route extensions,
and the selection effect that CTA chose growing corridors. Frequent-vs-control cannot do that.

Multiplicity: with H2 pre-specified as a single slope, the three-day-type multiple-comparisons
problem in `NOTES.md` #1 largely dissolves. Where day types are still tested separately (H1),
report Holm or Bonferroni explicitly. This is the direct fix for the old notebook calling Sunday
"the strongest causal evidence" after it was the one that passed.

---

## 2. Design parameters — Luke's corrected definition

The 1-month-before / 2-months-after span is an **exclusion window (washout)**, not the
measurement window. Rollout timing is uncertain and riders take time to notice, so that span is
discarded. PRE and POST are everything available outside it.

```
        PRE (length TBD)          [ washout: -4wk .. +8wk ]        POST (all available)
   ────────────────────────────|═══════════╪═══════════════|────────────────────────────►
                                        rollout
```

POST length available per cohort, given data ends 2026-05-31 (arithmetic only, no ridership
touched):

| Cohort | Washout ends | POST weeks available |
|---|---|---|
| 2025-03-23 | 2025-05-12 | 54 |
| 2025-06-15 | 2025-08-04 | 42 |
| 2025-08-17 | 2025-10-06 | 33 |
| 2025-12-21 | 2026-02-09 | 15 |

This unevenness is itself a design decision (§8, decision 2): phase 1 gets more than a full
year, so seasonality largely self-cancels within its POST; phase 4 gets 15 weeks of late winter
and spring, so it does not. Truncating all four to a common 15 weeks buys comparability at the
cost of most of the phase-1 sample.

**Open:** how far back PRE reaches. A fixed 52 weeks, a length matched to POST, or a fixed
calendar start. Not decided.

### Unit and panel

- **Corridors, not routes**, per `exploration.ipynb` §2 — R shuttles carry no corridor and are
  excluded from the panel; `X49`/`49B` fold into 49, `J14` into 14. §5's GTFS evidence now
  supports this independently.
- **Day groups derived from `date`**: `W` = Mon–Fri, `A` = Sat, `U` = Sun. `daytype` is used
  only to identify schedule types run.
- **Recommended unit:** mean **riders/day within each day group**, presented as a
  week-equivalent (`5·W̄ + 1·Ā + 1·Ū`). Gives the riders/week figure Luke asked for while making
  holiday removal, partial weeks and unequal window lengths harmless. Decision 1 in §8.
- **Checks that print even at zero:** corridor membership identical in PRE and POST (a route
  appearing or vanishing mid-window would fake an effect); complete weeks; holiday days per
  window; corridors missing weeks.

---

## 3. Feasibility calibration — control routes only

*Replaces the section that contained the voided numbers.*

Before any treated-route outcome is examined, establish on the ~110 **non-Frequent** corridors:

1. **Null width.** Run the exact PRE/POST statistic on control corridors across untreated years
   (candidate placebo years 2015–2019, 2023, 2024; 2020–22 excluded for the pandemic). The
   spread is how much this statistic moves with no treatment.
2. **Trend vs season decomposition.** At 52-week PRE and 15–54-week POST, pre→post spans well
   over a year, so the placebo distribution mixes pre-2020 decline (−2–3%/yr) with 2023–24
   recovery (+10–15%/yr). **Quantify how much of the null is trend and how much is season.**
   This determines whether own-history placebo windows can serve as the seasonal correction at
   all, or whether trend must be removed first.
3. **Power.** Given the null width, what effect size is detectable per route, and pooled over
   20? Report it before looking, so "underpowered" is a finding rather than an excuse.
4. **Placebo DiD.** Run the full estimator on control-vs-control splits in untreated years. It
   must come out near zero. If it does not, the estimator is broken and the design changes.

Nothing here touches the 20 treated corridors. Results go in a visible cell.

---

## 4. Correction layers

Each correction reports: value before, value after, how much it moved, and an explicit line
saying **what it removed and what it did not** — so §6 can show the layers do not overlap.

**4a — Corridors vs routes.** Show the route-level version alongside so transfer effects are
visible. Re-derive rather than inherit the old notebook's numbers.

**4b — Holidays.** Drop holiday dates from both windows. The effect is large (0.26×–0.53× of a
normal weekday) and route-dependent, so this matters. Removing them also makes `U` pure Sundays.
Report days dropped per window per cohort.

> **Needs a second holiday list, built here — not a change to `holidays.ipynb`.**
>
> `data/derived/holiday_calendar.csv` is CTA's **operational** holiday list: dates where
> `daytype` disagrees with the real day of week, i.e. days CTA ran a *different schedule* than
> the weekday implies. `holidays.ipynb` computes that correctly and states its limitation in the
> notebook ("Only weekday occurrences are detectable: a holiday falling on a weekend already
> runs the Saturday or Sunday schedule, so there is no label to disagree with"), and it prints
> the weekend cases as their own counter. Nothing upstream needs fixing.
>
> But this notebook needs a **different object**: calendar holidays, i.e. low-ridership days.
> Christmas depresses ridership whether or not the schedule shifted, and a weekend-dated
> Christmas is invisible to the operational list — verified: Christmas 2021 and 2022, July 4
> 2020 and 2021, New Year's 2022 all unflagged. Only 4 of the 152 operational flags fall on a
> weekend, and those are the anomalies where CTA ran a Sunday schedule on a Saturday.
>
> **Build here:** the six CTA-observed holidays by calendar date — New Year's, Memorial,
> Independence, Labor, Thanksgiving, Christmas — regardless of day of week. Which six is itself
> a finding from `holidays.ipynb` §1 (CTA never observes MLK, Presidents, Juneteenth, Columbus
> or Veterans). Carry the operational flag alongside as a separate column, since "Christmas run
> on a Sunday schedule" and "Christmas run on a Saturday schedule" are different days.
>
> **This matters most for §3, not §4b.** The 2025–26 windows contain mostly weekday holidays,
> which the operational list would catch anyway. The placebo years used for the null calibration
> are full of weekend-dated holidays — so the gap sits under the step the rest of the design
> rests on.

**4c — Secular trend.** Fit in **log space** per corridor and system-wide, excluding each
route's own washout. Log because `seasonality.ipynb` §5.b established a log fit is exactly
invariant to growth while a level fit leaves up to 0.0175 behind — that note explicitly says
"use log if a fitted growth curve is wanted in the FN notebook."

**4d — Seasonality.** Two candidates, and §3.2 decides between them:
- *Own-history placebo windows* — same ISO weeks in untreated years, per corridor. Route-
  specific, needs no extrapolation, generates its own null. Risk: at long windows it may be
  measuring trend rather than season.
- *The pooled seasonal index* from `seasonality.ipynb`. Problem: it **ends 2025-11-17 and 2026
  contributes nothing**, so every POST window extending into 2026 is extrapolated — and under
  the washout design all four do. It is also system-wide, and 32 of 136 routes correlate below
  0.5 with it.

**4e — Contemporaneous control.** Route change minus control change over identical windows.

`[POST-HOC — re-derive]` I came to think this should be **primary** rather than a final layer,
because differencing against a contemporaneous control cancels the common trend directly, which
matters most exactly when POST is long. That conclusion was reached after seeing voided numbers.
It is a property of window length and the 2023–26 recovery slope rather than of the treated
routes, so it should survive re-derivation from §3 — but it must actually be re-derived.

**The double-counting trap.** 4c and 4d overlap: a placebo window contains that year's trend as
well as its season. They must be applied to observed *and* placebo windows in the same order, or
one term is removed twice. §6 makes this auditable.

**Control contamination.** The same schedule changes altered service on non-FN routes. Build the
control as a **parameter** and report at least three: all non-FN corridors; non-FN corridors
minus any with a measured service change (§5 now makes this identifiable rather than guesswork);
and a size-matched subset.

The old notebook's version of this step was not clean, and the notebook should say why: it
subtracted a mean pre-trend gap computed from year-pairs that themselves contained treatment
(`NOTES.md` #2 — the 2024→2025 growth term is inflated for the eight phase-1 corridors by their
own partial rollout).

---

## 5. The dose — measured, not advertised

### What CTA advertised

Luke's verbatim transcription of `transitchicago.com/frequent/` is in
`scratchpad/advertised_dose.md`. Structure: six routes have no advertised weekday increase
(4, 12, 54, 60, 77, 81), seven no Saturday increase, and Sunday carries the largest dose almost
everywhere (20–60%).

Known defects: segment-only doses (47, 63, 79), route extensions that add riders mechanically
(53, 82), owl extensions (4, 53, 66), "weekends" not split Sat/Sun (J14, 60, 95), and 34 quoted
as a headway range rather than a percent.

### What CTA actually scheduled

Measured from archived GTFS: scheduled trips per route per representative service day, winter
2024-25 feed (2025-02-01, pre-phase-1) vs winter 2025-26 feed (2026-01-28, post-phase-4).
Treatment-side measurement — no ridership involved.

**Not established — do not rely on any of it.** A first pass this session suggested advertised
and scheduled service diverge, on some routes sharply and in both directions. Luke did not
review it and the numbers rest on unchecked assumptions (see the caveats below). They are
deliberately not reproduced here. Redo the comparison properly before drawing anything from it.

There are **three distinct things** and this plan should not blur them:

1. **Advertised** — `docs/cta-advertised-service-increases.md`, the CTA page. A marketing claim.
2. **Scheduled** — GTFS `trips.txt`, the published timetable.
3. **Actually run** — real-time bus positions (Ghost Bus / `cta-stop-watch`), the separate
   notebook noted as a future project.

Which of these H2's dose should be built on is an open decision, not something this plan settles.
Luke's standing caution applies regardless: advertised service may not have been delivered, and
there may be unadvertised changes — so the six routes with no advertised weekday increase are at
best a soft placebo. That is measurement error in the regressor, which attenuates β toward zero,
making any estimate a lower bound.

### Caveats on the measured dose, all to be fixed before it is used

1. **Rail routes are in the GTFS route list** and must be filtered out.
2. **Trips/day counts owl service**, so the owl extensions on 4, 53 and 66 inflate their dose
   without changing frequency in the program window. Needs trips restricted to the program
   hours (6a–9p weekdays, 9a–9p weekends), which requires first-departure times from
   `stop_times.txt`.
3. **Trips/day is not headway.** The program is defined on headway; trips/day is a proxy.
4. **Only two feeds so far**, giving a whole-program change rather than per-phase changes.
   Per-phase requires feeds bracketing each rollout (§7).

### Why β is an elasticity

Estimating `Δlog(riders)_{r,g} = α_r + β·log(1 + dose_{r,g}) + ε` with route fixed effects makes
β a **service elasticity of ridership**, comparable to published values rather than a bare
effect size. [TCRP Report 95, Ch. 9](https://www.trb.org/publications/tcrp/tcrp_rpt_95c9.pdf)
puts the average response to frequency changes at **+0.5** in service-quantity terms;
multi-year national studies give **+0.54 to +0.57 short-run** (UK) and **+0.29 short-run**
(France). Hence the pre-registered β ≈ 0.3–0.6.

**Inference with 20 clusters:** cluster-robust SEs are unreliable at this cluster count. Primary
= **permutation test** permuting the dose vector across routes. Cross-check = **wild cluster
bootstrap** ([Cameron, Gelbach & Miller 2008](https://direct.mit.edu/rest/article/90/3/414/57731)),
the standard remedy for few clusters.

**Aggregate to one PRE and one POST value per corridor before doing inference across corridors.**
This is the standard fix for serial correlation in DiD
([Bertrand, Duflo & Mullainathan 2004, QJE](https://academic.oup.com/qje/article-abstract/119/1/249/1876068)),
which found conventional DiD standard errors so understated that up to **45% of placebo
interventions** came out significant at 5%. Week-level t-tests inside a window would fall
straight into this and must not be used.

A related trap to avoid explicitly: pooling corridors and taking a standard error *across
corridors* does not capture trend uncertainty, because all corridors share the same
2025–26 recovery trend. Such a standard error will look impressively small and mean nothing.
The trend uncertainty has to come from the placebo years or the control group.

---

## 6. One cell stating the accounting identity

To make "no double correction" checkable rather than asserted:

```
log(riders_{r,g,t}) = trend_r(t) + season_r(week-of-year) + level_{r,g} + τ_{r,g}·post + ε
```

§4's layers are then visibly successive removals of distinct terms, and the cell prints residual
variance after each — an over-correction shows up as variance going *up*.

---

## 7. Schedule data — status and what is still needed

- **Have:** four archived CTA feeds from the Wayback Machine (2025-02-01, 2025-04-06,
  2026-01-28, 2026-03-02), in `data/gtfs/` (gitignored). These bracket phase 1 and sit after
  phase 4. Wayback has **no snapshots between Apr 2025 and Jan 2026**, so phases 2 and 3 are
  not bracketed.
- **Transitland** holds **~181 CTA feed versions back to 2016-02-13**, including versions
  bracketing every rollout date. Metadata queries work with the current key. **Bulk downloads
  require applying for a 500-download allowance, which we do not have yet** — the download
  endpoint returns 401.
- **TransitFeeds** (2014–Feb 2024) returns 403; deprecated Dec 2025. Unusable.
- **`mansueto-institute/cta-stop-watch`** is alive (last push 2026-06-10) and publishes
  scheduled-vs-actual headway metrics, but documented coverage is Jun 2022 – Jul 2024, which
  misses the rollout.

**Storage plan once the allowance arrives.** Full zips are 48–96 MB each, of which ~98.5% is
`stop_times.txt` (343 MB uncompressed) and `shapes.txt` (55 MB). The files needed for
trips-per-route-per-day are `trips.txt` (5.7 MB) plus `calendar`, `calendar_dates` and `routes`
(~18 KB) — so a slim derivative of all 181 versions is ~200–300 MB against ~12 GB raw.

**Download the full zips and extract afterwards** (Luke's call, 2026-08-05). The download
allowance is the scarce resource and disk is not; slimming at acquisition would risk burning
one-shot downloads on a buggy extractor with no second pass. Keep the raw zips, derive the slim
files locally, and re-derive freely as the extraction changes — which it will, since
program-hours filtering needs `stop_times.txt` and that requirement was only discovered after
the first extraction was written.

A ten-year slim archive also supports the placebo years in §3 directly — service history for
control routes is what distinguishes "this route was quiet" from "this route was also changed."

---

## 8. Decisions needed before any cell is written

1. **Unit** — mean riders/day per day group shown as a week-equivalent, or literal riders/week?
2. **POST length** — leave uneven (54/42/33/15 weeks), or truncate to a common 15?
3. **PRE length** — fixed 52 weeks, matched to POST, or a fixed calendar start?
4. **Primary seasonal correction** — own-history placebo or the pooled index? §3.2 informs this;
   it should not be settled before that runs.
5. **Estimator ordering** — is contemporaneous control primary (the `[POST-HOC]` item in 4e), or
   a final layer? Needs re-derivation from §3 first.
6. **Transitland allowance** — apply for the 500 downloads, or proceed on the four Wayback feeds?
7. **Old files** — `analyze.py`, `inference_proto.py`, `build_notebook.py` and the old notebook
   all feed the superseded design. Delete, or keep for reference?

---

## 9. Work order once approved

1. **§3 feasibility calibration on control routes only.** Everything downstream depends on what
   it says about trend vs season, and it is the step that re-derives the `[POST-HOC]` items.
2. Resolve the phase map: the #53/#20 June-vs-August conflict, and whether 49/53/82/95 received
   a second bump in December (CTA's December release quotes increases for all four, though they
   rolled out in March/June/August). Per-phase GTFS settles this if the allowance arrives.
3. Restatement check: look for a step **inside** 2025 from the placeholder→actual farebox
   replacement. `ridership-break-2025` establishes that within-2025 comparisons are unaffected,
   but that assumes the new method is uniform across 2025 and nobody has tested it. Cheap, and
   if it fails the design changes — so do it before building on the windows.
4. §1–§2: hypotheses, dose table, panel, checks.
5. Raw before/after, with the §3 null shown beside it so the calendar's contribution is visible.
6. §4 correction layers, then §6 identity.
7. H1 pooled, H2 dose-response, cohort views.
8. Robustness: window sensitivity grid, extensions (53, 82), segment-only doses (47, 63, 79),
   single-week weather outliers — with only ~52 PRE weeks, `seasonality.ipynb`'s left-skew
   finding (−0.51, storms push weeks down and nothing pushes them up) argues for reporting
   median as well as mean.
9. README: status, layout, the future frequency-vs-ridership project, dose-table provenance.
10. Retire superseded scripts per decision 7.
