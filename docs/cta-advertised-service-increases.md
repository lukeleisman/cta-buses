# CTA advertised service increases, verbatim from transitchicago.com/frequent/
# Pasted by Luke 2026-08-05. This is the source for hypothesis 2 (dose-response).

| Route | Weekday | Saturday | Sunday/Hol | Non-frequency changes in the same text |
|---|---|---|---|---|
| 4 Cottage Grove | — | — | 20% | Owl extended 63rd → 95th/Dan Ryan |
| 9 Ashland | 10% | — | — | |
| 12 Roosevelt | — | 15% | 25% | |
| J14 Jeffery Jump | 20% | 35% (weekends) | 35% (weekends) | hours of service increased wkdy + Sun |
| 20 Madison | 10% | 10% | 25% | |
| 34 South Michigan | every 6-10 vs 8-16 min | — | — | stated as headway, not % |
| 47 47th | doubled **Kedzie↔Midway only** | — | — | segment-only dose |
| 49 Western | 10% | 10% | 25% | |
| 53 Pulaski | 25% | 10% | 25% | **extended** 31st → 76th/Ford City; owl extended |
| 54 Cicero | — | — | 30% | |
| 55 Garfield | 20% | 30% | 30% | |
| 60 Blue Island/26th | — | 45% (weekends) | 45% (weekends) | |
| 63 63rd | 40% **Midway↔Kedzie/63rd only** | — | — | segment-only dose |
| 66 Chicago | 10% | — | — | Owl extended Pulaski → Austin |
| 72 North | 10% | 10% | 25% | |
| 77 Belmont | — | 10% | 20% | |
| 79 79th | 50% **Western↔Ford City only** | 20% **same segment** | — | segment-only dose |
| 81 Lawrence | — | 10% | 25% | |
| 82 Kimball/Homan | 15% | 45% | 60% | **extended** Central Park/31st → 31st/Pulaski |
| 95 95th | 20% | >30% (weekends) | >30% (weekends) | |

## Structure worth exploiting

- **Zero advertised weekday dose:** 4, 12, 54, 60, 77, 81. Six built-in within-network
  placebos for the weekday test.
- **Zero advertised Saturday dose:** 4, 9, 34, 47, 54, 63, 66. 
- **Sunday is the largest dose almost everywhere** — consistent with the old notebook's
  Sunday finding, but that finding was selected after the fact; here it is predicted in advance.
- **Dose varies WITHIN route across day types** → route fixed effects are available.

## Caveats this table forces

1. **Segment-only doses (47, 63, 79):** route-total ridership dilutes a segment increase by
   the share of riders on that segment. Expected effect is attenuated by an unknown factor.
2. **Route extensions (53, 82):** new territory adds riders mechanically. This is a coverage
   effect, not a frequency effect, and it biases those two routes UP. 53 also confounds with
   the 53A curtailment the old notebook found.
3. **Owl extensions (4, 53, 66):** small rider counts, but same coverage-vs-frequency issue.
4. **34 is a headway range, not a percent** — needs a conversion decision (mean headway
   8→12min midpoint vs 6→10 implies ~+33%) or exclusion from the quantitative dose fit.
5. **"weekends" (J14, 60, 95)** does not separate Sat from Sun; those three cannot enter a
   Sat-vs-Sun contrast, only a pooled weekend one.
6. Advertised ≠ delivered. This is scheduled service as marketed; whether it was operated is
   the GTFS question deferred to the future notebook.
