# Methods and derivations

Supporting derivations for the CTA analyses. Statistical methods used elsewhere in the repo
get added here rather than expanded inline in a notebook or plan.

Contents:
- [Headways and rider wait](#headways-and-rider-wait)

---

# Headways and rider wait

Used by `docs/bus-tracker-data-plan.md`. The question is whether the Frequent Network's
"every 10 minutes" is delivered, and what fraction of the time it is not.

## Setup

At one stop, in one direction, buses pass at times `t₀ < t₁ < … < tₙ`. The gaps

```
hᵢ = tᵢ − tᵢ₋₁          i = 1 … n
T  = Σ hᵢ               total observed time
```

are the headways. Everything below is a statistic of the observed list `h`. **No assumption is
made about how headways are distributed** — not Poisson buses, not exponential gaps, nothing.
The single assumption is about riders:

> **Uniform arrivals.** Riders arrive at the stop at a constant rate λ, at instants independent
> of the bus process, and each boards the next bus.

This is most defensible on exactly the service we are studying — a route advertising 10-minute
headways, where people turn up rather than consult a timetable — and least defensible late at
night or on a 30-minute route, where riders time their arrival to the schedule.

## Step 1 — where a random rider lands

The number of riders arriving during gap `i` is `λhᵢ` in expectation, and `λT` in total. So

```
P(a randomly chosen rider arrived during gap i) = λhᵢ / λT = hᵢ / T
```

λ cancels: the result is independent of how busy the stop is. Two consequences:

- This is **not** `1/n`. Gaps are sampled in proportion to their own length — a 20-minute gap
  catches twice as many riders as a 10-minute one. Averaging over *gaps* and averaging over
  *riders* are different operations, and the gap between them is the entire subject.
- Standard names: length-biased sampling; the inspection paradox; "random incidence" in
  Larson & Odoni.

## Step 2 — the wait distribution

Condition on landing in gap `i`. Uniform arrivals restricted to an interval are still uniform,
so the arrival instant sits `u ~ Uniform[0, hᵢ]` after the previous bus, and the rider waits

```
W = hᵢ − u  ~  Uniform[0, hᵢ]
```

Hence `P(W > w | gap i) = max(hᵢ − w, 0) / hᵢ`. Multiplying by the landing probability from
step 1 and summing, the `hᵢ` cancels:

```
                    Σᵢ max(hᵢ − w, 0)
S(w) = P(W > w) =  ───────────────────
                          Σᵢ hᵢ
```

**`S(w)` is the whole object.** Every rider-facing statistic below is a reading of this one
curve, and plotting it for `w = 0…30` says more than any single number.

### The second reading of the numerator

`Σ max(hᵢ − w, 0)` is the **number of minutes during which the next bus is more than `w`
minutes away** — inside a gap of length `hᵢ`, those are exactly its first `hᵢ − w` minutes.

So `S(w)` is simultaneously *the share of riders who wait longer than `w`* and *the share of
the time the service is failing a `w`-minute promise*. Under uniform arrivals the two
questions have one answer.

### Who counts as consulting the service

The derivation never used the fact that the rider is standing at the stop — only that the
instant of consultation is independent of the bus process. So it applies unchanged to someone
checking a tracker app. If tracker checks are uniform in time, the "time until next bus" the
app reveals has exactly the distribution `S(w)`.

This matters for interpretation. A rider who sees an 18-minute gap and takes a different mode
has not been served any better than one who waits 18 minutes — they have absorbed the failure
as a fare, a walk, or an abandoned trip. **The tracker changes the response to a service
failure, not its incidence.** `S(10)` is therefore not an upper bound on the failure rate; it
is the failure rate, and it is robust to what riders do next. What the tracker (and balking)
*does* disturb is the distribution of realised waiting time at the stop, which is censored —
which is a reason to measure the service via headways rather than via observed waits.

## Step 3 — the four statistics

Two different distributions are in play, and the first statistic comes from a different one
than the rest.

**Over gaps** — unweighted, one vote per gap. Describes service *delivered*:

```
share of gaps over 10 min = count(hᵢ > 10) / n
```

**Over riders** — length-weighted, via step 1. Describes service *experienced*:

```
share of riders whose gap    Σ_{hᵢ>10} hᵢ
exceeds 10 min            =  ──────────────
                                  Σ hᵢ

share of riders who wait     Σᵢ max(hᵢ − 10, 0)
more than 10 min          =  ────────────────────  =  S(10)      <- the rider-facing answer
                                    Σ hᵢ

mean rider wait           =  Σ hᵢ² / (2 Σ hᵢ)
```

The mean follows from `E[W | gap i] = hᵢ/2` weighted by step 1. It is also the area under the
survival curve, which is a useful internal check on any implementation:

```
∫₀^∞ S(w) dw  =  Σᵢ ∫₀^{hᵢ} (hᵢ − w) dw / Σh  =  Σᵢ (hᵢ²/2) / Σh  =  Σhᵢ² / (2Σhᵢ)   ✓
```

### The coefficient-of-variation form

Dividing through by `n` and substituting `E[h²] = Var(h) + E[h]²`:

```
E[W] = E[h²] / (2E[h]) = (E[h]/2) · (1 + CV²),      CV = sd(h)/mean(h)
```

Perfectly even service has `CV = 0`, and mean wait is half the headway. Every departure from
evenness adds wait **with the mean headway unchanged**. This is the standard transit-planning
form of the result.

## Why this is the whole point

Bunching moves probability mass into long gaps without touching `E[h]`. Two routes, both
truthfully advertising "every 10 minutes":

| | even: 10, 10, 10 … | bunched: 2, 18, 2, 18 … |
|---|---|---|
| mean headway | 10.0 min | 10.0 min |
| share of gaps > 10 min | 0% | 50% |
| share of riders whose gap > 10 min | 0% | 90% |
| **share of riders waiting > 10 min — `S(10)`** | **0%** | **40%** |
| mean rider wait | 5.0 min | 8.2 min |
| CV | 0 | 0.8 |

Check on the last row via the CV form: `(10/2)·(1 + 0.64) = 8.2` ✓.

A phase of the Frequent Network could add bus-hours, hold the mean headway at 10, and leave
`S(10)` unmoved or worse if the added service bunches. That is a finding, not a failure of the
method — and it is invisible to any analysis that reports mean headway alone.

## What to report

`S(w)` as a curve, plus `S(10)` and the share of gaps over 10 as the two headline numbers —
service experienced and service delivered. Mean headway alone is not sufficient and should
never appear without `CV` beside it.

## References

The derivation above is self-contained — each step is checkable without any of these. The
citations below are marked with what was actually verified, and what each one does and does not
support.

### Covers the whole derivation

**Larson & Odoni, *Urban Operations Research*, §2.13 "Random Incidence."** Free and readable at
<http://web.mit.edu/urban_or_book/www/book/chapter2/2.13.html>. Verified: this section covers
steps 1, 2 and 4 above. It defines the problem as

> "An individual … starts observing the process at a *random time*, and he or she wishes to
> obtain the probability law (or at least the mean) of the time he or she must wait until the
> *next* arrival occurs … This is said to be a problem of *random incidence*."

states that the density of the entered gap "incorporates both the frequency of gaps of length
`w` and their duration" (our step 1, length-biasing); that "given entry into a gap of length
`w`, the remaining time until the next event follows a uniform distribution (0 to `w`)" (our
step 2); and that "the *mean time from random incidence until the next event depends only on
the mean and variance of the inter-event time Y*" — which is the `(1 + CV²)` result. The
formulas themselves are served as images, so they are not quoted here verbatim.

### Real, but about bunching — not about the wait formula

**Welding (1957), "The Instability of a Close-Interval Service," *Operational Research
Quarterly* 8(3), 133–148.** Verified to exist with those details; the author was at the London
Transport Executive. It is the early account of bunching as a *dynamic instability* — why
headways fail to stay even. Cite it for why `CV` is nonzero in the first place, not for the
waiting-time mathematics.

**Osuna & Newell (1972), "Control Strategies for an Idealized Public Transportation System,"
*Transportation Science* 6(1), 52–72.** Verified to exist. It formulates *holding control* as a
dynamic program — when to hold a vehicle at a terminal — with passengers arriving at a uniform
rate and average wait per passenger as the objective. Relevant to what an operator can do about
bunching; it is not the source of the formulas above.

### Not verified — do not cite until checked

- ***Transit Capacity and Quality of Service Manual*** for `E[W] = (E[H]/2)(1 + CV²)`.
  Secondary sources state this formula and report that the TCQSM tracks the coefficient of
  variation of headways, but the primary text could not be reached (the National Academies
  reader serves page images). Treat as unconfirmed.
- **Feller, *Probability Theory*, Vol. II** for the inspection paradox. Cited from memory in an
  earlier draft, never checked. Chapter number unconfirmed.

A better freely-readable second source, if one is wanted, is likely TCRP Report 113, *Using
Archived AVL-APC Data to Improve Transit Performance and Management*, ch. 6 "Tools for
Analyzing Waiting Time" — also unverified, same page-image problem.
