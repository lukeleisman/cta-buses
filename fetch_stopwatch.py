"""Download the Mansueto Institute StopWatch archive of CTA bus service.

StopWatch continues the Chi Hack Night Ghost Buses scrape: CTA Bus Tracker
`getvehicles` polled every 5 minutes since 2022-05-19, interpolated to a stop-level
record of when each bus actually passed each stop, plus CTA's own published GTFS
accumulated into historic timetables. It is the only public source of *realised*
CTA bus frequency -- the ridership portal files carry no service measure at all.

Four products, selected with --what:

  processed   trips_{pid}_full.parquet   34.4 GB   886 patterns   ACTUAL arrivals
  timetables  rt{rt}_timetable.parquet   13.8 GB   124 routes     SCHEDULED arrivals
  metrics     stop_metrics_df_latest     357 MB    1 file         their aggregation
  raw         {date}.csv                 50.6 GB   1529 days      unprocessed pings

`processed` and `timetables` are the pair the analysis needs: both are one row per
stop visit with a `bus_stop_time`, so a headway is a sort-and-diff on either side
and the two are directly comparable. `raw` is only needed to check how far the
interpolation moved things, and a few dozen days is enough for that.

Resumes by comparing local size against the server's content-length, so an
interrupted run can be re-issued unchanged. Nothing is overwritten once complete.

    python fetch_stopwatch.py --what timetables --dest data/stopwatch --dry-run
    python fetch_stopwatch.py --what processed --dest /Volumes/big/stopwatch
    python fetch_stopwatch.py --what raw --start 2025-03-01 --end 2025-03-31 --dest .

Sizes above are as measured 2026-08-05; the pipeline runs daily, so they grow.
"""
import argparse
import csv
import datetime as dt
import io
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = 'https://d2v7z51jmtm0iq.cloudfront.net/cta-stop-watch'
XWALK = f'{BASE}/rt_to_pid.csv'

# Coverage as measured 2026-08-05. First day is a partial -- the scrape started midday.
RAW_FIRST = dt.date(2022, 5, 19)

# The 20 Frequent Network routes, as CTA labels them. Same list as check_r_routes.py.
FREQ = ['J14', '4', '9', '12', '20', '34', '47', '49', '53', '54',
        '55', '60', '63', '66', '72', '77', '79', '81', '82', '95']


def human(n):
    """Bytes at a readable scale -- these files span 8 KB to 400 MB."""
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(n) < 1000 or unit == 'GB':
            return f'{n:.1f} {unit}' if unit != 'B' else f'{n:.0f} B'
        n /= 1000
    return f'{n:.1f} GB'


def read_xwalk():
    """Route -> pattern crosswalk, fetched fresh. 940 rows, ~125 routes."""
    with urllib.request.urlopen(XWALK, timeout=60) as r:
        text = r.read().decode()
    rows = list(csv.DictReader(io.StringIO(text)))
    return [(x['rt'].strip(), x['pid'].strip()) for x in rows]


def remote_size(url):
    """content-length via HEAD, or None if the file is not there (404)."""
    req = urllib.request.Request(url, method='HEAD')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return int(r.headers['content-length'])
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def targets(what, routes, start, end):
    """[(url, relative path)] for the requested product."""
    if what == 'metrics':
        name = 'stop_metrics_df_latest.parquet'
        return [(f'{BASE}/metrics/{name}', f'metrics/{name}')]

    if what == 'raw':
        out, d = [], start
        while d <= end:
            out.append((f'{BASE}/full_day_data/{d}.csv', f'full_day_data/{d}.csv'))
            d += dt.timedelta(days=1)
        return out

    if what == 'timetables':
        rts = routes or sorted({rt for rt, _ in read_xwalk()})
        return [(f'{BASE}/clean_timetables/rt{rt}_timetable.parquet',
                 f'clean_timetables/rt{rt}_timetable.parquet') for rt in rts]

    if what == 'processed':
        pairs = read_xwalk()
        if routes:
            pairs = [(rt, pid) for rt, pid in pairs if rt in routes]
        return [(f'{BASE}/processed_by_pid/trips_{pid}_full.parquet',
                 f'processed_by_pid/trips_{pid}_full.parquet') for _, pid in pairs]

    raise ValueError(what)


def fetch(url, path, size):
    """Download to a .part file then rename, so a partial never looks complete."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size == size:
        return 'have', size
    part = path.with_suffix(path.suffix + '.part')
    with urllib.request.urlopen(url, timeout=300) as r, open(part, 'wb') as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    got = part.stat().st_size
    if size is not None and got != size:
        part.unlink()
        return 'size-mismatch', got
    part.rename(path)
    return 'got', got


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--what', required=True,
                   choices=['processed', 'timetables', 'metrics', 'raw'])
    p.add_argument('--dest', required=True, help='root directory to write under')
    p.add_argument('--routes', help='comma-separated routes, or "freq" for the 20')
    p.add_argument('--start', help='raw only, YYYY-MM-DD')
    p.add_argument('--end', help='raw only, YYYY-MM-DD')
    p.add_argument('--workers', type=int, default=6)
    p.add_argument('--dry-run', action='store_true',
                   help='size everything with HEAD and print the total, download nothing')
    a = p.parse_args()

    routes = None
    if a.routes:
        routes = FREQ if a.routes == 'freq' else [r.strip() for r in a.routes.split(',')]

    start = dt.date.fromisoformat(a.start) if a.start else RAW_FIRST
    end = dt.date.fromisoformat(a.end) if a.end else dt.date.today()
    if a.what == 'raw' and not (a.start and a.end):
        print('raw: --start and --end are required (the full archive is 50.6 GB)')
        return 1

    dest = Path(a.dest)
    tgts = targets(a.what, routes, start, end)
    print(f'{a.what}: {len(tgts)} files'
          + (f'   routes: {len(routes)}' if routes else '') + '\n')

    # Size first, always. Tells us the footprint before a byte of payload moves,
    # and catches the files that are in the index but not on the server.
    sizes, missing = {}, []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(remote_size, u): (u, rel) for u, rel in tgts}
        for i, f in enumerate(as_completed(futs), 1):
            u, rel = futs[f]
            s = f.result()
            if s is None:
                missing.append(rel)
            else:
                sizes[(u, rel)] = s
            if i % 100 == 0:
                print(f'  sized {i}/{len(tgts)}', file=sys.stderr)

    total = sum(sizes.values())
    have = sum(s for (u, rel), s in sizes.items()
               if (dest / rel).exists() and (dest / rel).stat().st_size == s)
    print(f'  on server : {len(sizes)} files, {human(total)}')
    print(f'  missing   : {len(missing)}' + (f'  {missing[:8]}' if missing else ''))
    print(f'  already   : {human(have)} local and complete')
    print(f'  to fetch  : {human(total - have)}\n')
    if a.dry_run:
        return 0

    done = failed = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(fetch, u, dest / rel, s): rel
                for (u, rel), s in sizes.items()}
        for i, f in enumerate(as_completed(futs), 1):
            rel = futs[f]
            try:
                status, n = f.result()
                done += 1
                if status != 'have':
                    print(f'  [{i}/{len(futs)}] {status:14s} {n / 1e6:8.1f} MB  {rel}')
            except Exception as e:
                failed += 1
                print(f'  [{i}/{len(futs)}] FAILED {rel}: {e}')

    print(f'\ncomplete: {done}   failed: {failed}')
    if missing:
        print(f'not on server: {len(missing)}')
        for rel in missing:
            print(f'  {rel}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
