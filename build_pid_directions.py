"""Build the pattern -> direction reference table, once, for every route.

Which way a bus is going is not recorded in the arrival files, but it is a
property of the pattern (`pid`), and CTA publishes it. Working it out means
joining StopWatch's 13 GB of timetables to the GTFS feeds, which takes about a
minute and a half for the whole network -- so it is done here once and written
to a small CSV that the notebooks read instead.

    python build_pid_directions.py

Writes `data/derived/pid_directions.csv`, one row per (route, pid):

    route, pid, direction, n_trips, n_directions

`n_directions` is the number of distinct directions the matched trips gave.
**It should always be 1.** Anything else means the pattern is not consistent and
the label should not be used; the script prints a count and exits non-zero if any
appear, rather than writing a file that quietly contains them.

`direction` is empty when no scheduled trip for that pattern matched a GTFS feed.
That happens for patterns retired before the earliest feed on disk. Most such
patterns have no arrival file either, so they never reach an analysis -- but not
all of them do, and the summary printed at the end says how many are affected.

Re-run this after adding GTFS feeds to `data/gtfs/` or refreshing the timetables.
"""
import glob
import os
import re
import sys
import time

import pandas as pd

import ctabus as cta

OUT_PATH = f'{cta.DERIVED}/pid_directions.csv'


def routes_on_disk():
    """Every route that has a cleaned timetable, read off the filenames."""
    names = glob.glob(f'{cta.TIMETABLES_DIR}/rt*_timetable.parquet')
    found = []
    for path in names:
        match = re.match(r'rt(.+)_timetable\.parquet', os.path.basename(path))
        if match:
            found.append(match.group(1))
    return sorted(found)


def main():
    routes = routes_on_disk()
    if not routes:
        sys.exit(f'no timetables found in {cta.TIMETABLES_DIR}')
    print(f'{len(routes)} routes with timetables')

    cta.gtfs_trips()          # load the GTFS feeds once, not once per route
    print(f'GTFS trips loaded: {len(cta.gtfs_trips()):,} distinct trip_id\n')

    frames = []
    started = time.time()
    for i, route in enumerate(routes, 1):
        table = cta.pattern_directions(route)
        table.insert(0, 'route', route)
        frames.append(table)
        print(f'  [{i:>3}/{len(routes)}] rt{route:<5} '
              f'{int((table.n_directions == 1).sum()):>3} of {len(table):>3} patterns labelled',
              flush=True)

    everything = pd.concat(frames, ignore_index=True)

    conflicting = everything[everything.n_directions > 1]
    if len(conflicting):
        print(f'\nFAILED: {len(conflicting)} patterns have trips in more than one '
              f'direction. Not writing {OUT_PATH}.')
        print(conflicting.to_string(index=False))
        sys.exit(1)

    os.makedirs(cta.DERIVED, exist_ok=True)
    everything.to_csv(OUT_PATH, index=False)

    labelled = everything.direction.notna()
    print(f'\nwrote {OUT_PATH}  ({time.time() - started:.0f}s)')
    print(f'  patterns          : {len(everything):,}')
    print(f'  with a direction  : {labelled.sum():,} ({labelled.mean():.1%})')
    print(f'  without           : {(~labelled).sum():,}  '
          f'(no scheduled trip matched a GTFS feed on disk)')
    print(f'  conflicting       : 0')

    # The unlabelled patterns only matter if an arrivals file exists for them,
    # so say how many do -- that is the number an analysis would actually hit.
    have = {cta.norm_pid(os.path.basename(p).replace('trips_', '').replace('_full.parquet', ''))
            for p in glob.glob(f'{cta.ACTUALS_DIR}/*.parquet')}
    unlabelled_with_data = everything[~labelled & everything.pid.isin(have)]
    print(f'\n  of the unlabelled, {len(unlabelled_with_data)} DO have an arrivals file '
          f'and so would be met by an analysis:')
    for route, group in unlabelled_with_data.groupby('route'):
        print(f'    rt{route:<5} {sorted(group.pid)}')


if __name__ == '__main__':
    main()
