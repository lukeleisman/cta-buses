"""Shared helpers for the CTA bus notebooks.

Anything more than one notebook needs lives here, so the copies cannot drift
apart: the plotting style, the paths into `data/`, the file-inspection
helpers, and the loaders for route shapes and stop locations.

Use it from a notebook running at the repo root:

    import ctabus as cta
    cta.apply_style()
    stops = cta.route_stops('66')

Nothing in this module writes to disk. Notebooks do their own writing, so it
is always visible in the notebook that produced the file.

Two things worth knowing before reading further:

* `data/` is a symlink out of the repo to /media/work/data/cta. It is not
  version controlled, and it holds ~47 GB, so several helpers here are built
  to read schemas and samples rather than whole files.
* Stop arrival times in `processed_by_pid/` are *estimated*, not observed.
  They come from interpolating between vehicle pings taken every 5 minutes.
  `data_inventory.ipynb` §2a quotes the upstream code that does it.
"""
import glob
import os
from datetime import datetime

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# --- where the data lives ----------------------------------------------------
DATA = 'data'                              # symlink -> /media/work/data/cta
STOPWATCH = f'{DATA}/stopwatch'
ACTUALS_DIR = f'{STOPWATCH}/processed_by_pid'    # when buses ACTUALLY passed stops
TIMETABLES_DIR = f'{STOPWATCH}/clean_timetables'  # when they were SCHEDULED to
RAW_DIR = f'{STOPWATCH}/full_day_data'           # the raw 5-minute pings
METRICS_DIR = f'{STOPWATCH}/metrics'             # StopWatch's own aggregation
GEO = f'{DATA}/geo'                              # route line shapes
GTFS = f'{DATA}/gtfs'                            # CTA schedule feeds
DERIVED = f'{DATA}/derived'                      # written by our own notebooks

# The 20 routes CTA phased into the Frequent Network during 2025, spelled the
# way CTA spells them. Kept identical to the list in fetch_stopwatch.py and
# check_r_routes.py -- if one changes, change all three.
FREQ = ['J14', '4', '9', '12', '20', '34', '47', '49', '53', '54',
        '55', '60', '63', '66', '72', '77', '79', '81', '82', '95']

# --- colours -----------------------------------------------------------------
# One palette for every notebook, so the figures read as a single set. Tested
# for contrast on the light surface below; if you change one, re-check it.
SURFACE, INK, INK2, MUTED = '#fcfcfb', '#0b0b0b', '#52514e', '#898781'
GRID, AXIS = '#e1e0d9', '#c3c2b7'
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
BLUE_L = '#b7d3f6'

CHICAGO_LAT = 41.9      # used to set the aspect of un-projected lat/lon maps


def apply_style():
    """Apply the shared matplotlib settings. Call once, near the top of a notebook.

    Sets the palette, turns off the top and right spines, left-aligns titles,
    and puts gridlines behind the data. Changes global matplotlib state, so it
    affects every figure drawn afterwards in that kernel.
    """
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
        'savefig.facecolor': SURFACE,
        'axes.edgecolor': AXIS, 'axes.labelcolor': INK2, 'text.color': INK,
        'xtick.color': MUTED, 'ytick.color': MUTED,
        'grid.color': GRID, 'grid.linewidth': 0.8,
        'axes.spines.top': False, 'axes.spines.right': False,
        'font.family': 'sans-serif', 'font.size': 10, 'figure.dpi': 110,
        'axes.titlesize': 12, 'axes.titleweight': 'bold',
        'axes.titlelocation': 'left', 'axes.titlepad': 10,
        'legend.frameon': False,
    })


def style(ax, ylab=None, axis='y'):
    """Tidy up one set of axes: grid behind the data, no tick marks, optional y label.

    Args:
        ax: the axes to change, modified in place.
        ylab: y-axis label. Left alone if None.
        axis: which gridlines to draw -- 'y' (default), 'x', or 'both'.

    Returns the same axes, so it can be chained.
    """
    ax.grid(axis=axis, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    if ylab:
        ax.set_ylabel(ylab, color=INK2)
    return ax


def map_aspect(ax, lat=CHICAGO_LAT):
    """Stop a lat/lon scatter plot from looking stretched.

    A degree of longitude is shorter than a degree of latitude, and the gap
    grows with distance from the equator. Plotting raw lat/lon on equal axes
    squashes the map east-west. This sets the aspect so shapes come out right
    at Chicago's latitude. Only needed for un-projected coordinates -- data
    already in a projected CRS does not want this.
    """
    ax.set_aspect(1 / np.cos(np.radians(lat)))
    return ax


# --- looking at files --------------------------------------------------------
def human(n_bytes):
    """Format a byte count at a readable scale, e.g. 47110722 -> '44.9 MB'."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n_bytes < 1024 or unit == 'TB':
            return f'{n_bytes:,.0f} {unit}' if unit == 'B' else f'{n_bytes:,.1f} {unit}'
        n_bytes /= 1024


def count_csv_rows(path, chunk=1 << 22):
    """Count data rows in a CSV by counting newlines, without loading it.

    Reads in 4 MB blocks, so it works on files far larger than memory.
    Subtracts one for the header. A file whose last line has no trailing
    newline will be undercounted by one.
    """
    with open(path, 'rb') as f:
        n = sum(buf.count(b'\n') for buf in iter(lambda: f.read(chunk), b''))
    return n - 1


def census(root=DATA):
    """Summarise every directory under `root`: how many files, how big, how old.

    Walks the tree and returns one row per directory that directly contains
    files, sorted largest first. Reads file metadata only -- no file contents
    are opened, so this is fast even over the 47 GB tree.

    Columns: directory, files, bytes, size (human-readable), ext (the
    extensions present), newest_file_mtime.

    Note `newest_file_mtime` is when the file last changed on *this* machine,
    which for a download is when we fetched it -- not when the publisher made
    it.
    """
    rows = []
    for dirpath, _, filenames in os.walk(root):
        if not filenames:
            continue
        sizes = [os.path.getsize(os.path.join(dirpath, f)) for f in filenames]
        mtimes = [os.path.getmtime(os.path.join(dirpath, f)) for f in filenames]
        exts = sorted({os.path.splitext(f)[1] or '(none)' for f in filenames})
        rows.append({
            'directory': os.path.relpath(dirpath, root) if dirpath != root else '.',
            'files': len(filenames),
            'bytes': sum(sizes),
            'size': human(sum(sizes)),
            'ext': ' '.join(exts),
            'newest_file_mtime': datetime.fromtimestamp(max(mtimes)).strftime('%Y-%m-%d'),
        })
    return pd.DataFrame(rows).sort_values('bytes', ascending=False).reset_index(drop=True)


def peek(path, n=4, note=None):
    """Show what is in one data file: its size, row count, columns, and first rows.

    Handles parquet and CSV. For parquet it reads the schema and a single row
    group, so a 400 MB file costs about as much as a small one -- the whole
    file is never loaded. For CSV it reads `n` rows for the preview and
    another 2000 to guess dtypes, plus a newline count for the row total.

    Args:
        path: the file to inspect.
        n: how many rows to show.
        note: an optional line printed under the filename, for context.

    Prints a dtype table and a preview, and returns the preview DataFrame.

    The dtype table is built from the parquet schema rather than the resulting
    DataFrame: pandas turns a `__index_level_0__` column into the index, so the
    two do not always have the same number of columns.
    """
    from IPython.display import display
    print(f'\033[1m{path}\033[0m   {human(os.path.getsize(path))}')
    if note:
        print(note)

    if os.path.splitext(path)[1] == '.parquet':
        pf = pq.ParquetFile(path)
        schema = pf.schema_arrow
        print(f'rows: {pf.metadata.num_rows:,}   columns: {len(schema.names)}   '
              f'row groups: {pf.metadata.num_row_groups}')
        head = pf.read_row_group(0).slice(0, n).to_pandas()
        cols = pd.DataFrame({'column': schema.names,
                             'dtype': [str(t) for t in schema.types]})
    else:
        head = pd.read_csv(path, nrows=n)
        print(f'rows: {count_csv_rows(path):,}   columns: {head.shape[1]}')
        sniff = pd.read_csv(path, nrows=2000)
        cols = pd.DataFrame({'column': list(sniff.columns),
                             'dtype': [str(d) for d in sniff.dtypes]})

    display(cols.set_index('column').T)
    display(head)
    return head


# --- route shapes ------------------------------------------------------------
# Four files describe the shape of CTA bus routes. data_inventory.ipynb §3
# compares them: the first, second and fourth all carry the current network
# and agree to within a foot on 126 of 127 routes; the KML is the 2015 network
# and is genuinely different.
GEO_SOURCES = {
    'geojson_local_0803':  f'{GEO}/cta_routes_current.geojson',
    'geojson_portal_0812': f'{GEO}/portal_6uva-a5ei_busroutes.geojson',
    'kml_atza-xq2n':       f'{GEO}/cta_routes_2015.kml',
    'shp_d5bx-dr8z':       f'{GEO}/d5bx-dr8z_shapefile/CTA_BusRoutes.shp',
}

# The default when a caller just wants "the current route shapes".
CURRENT_GEOMETRY = 'geojson_portal_0812'


def _route_ids(gdf, key):
    """Pull the route number out of whichever column this file happens to use.

    The GeoJSON calls it `route`, the shapefile `ROUTE`, and the KML puts it in
    `Name` with the readable name buried in an HTML `description` blob.
    Returned as strings, because route ids are not all numeric -- J14, X49, 8A.
    """
    if key.startswith('kml'):
        return gdf['Name'].astype(str)
    col = 'route' if 'route' in gdf.columns else 'ROUTE'
    return gdf[col].astype(str)


def load_geometry(keys=None):
    """Load the route-shape files into GeoDataFrames.

    Args:
        keys: which sources to load, as keys of GEO_SOURCES. Loads all four
            if omitted.

    Returns {key: GeoDataFrame}. Each frame gets a `route_id` column so the
    four can be compared despite their different column names. Files are left
    in whatever CRS they ship in -- the GeoJSONs and KML are EPSG:4326
    (lat/lon), the shapefile EPSG:3435 (Illinois East, feet) -- so reproject
    before measuring anything.
    """
    import geopandas as gpd
    out = {}
    for key in (keys or GEO_SOURCES):
        g = gpd.read_file(GEO_SOURCES[key])
        g['route_id'] = _route_ids(g, key)
        out[key] = g
    return out


def route_line(route, source=CURRENT_GEOMETRY):
    """The line shape of one route, as a one-or-few-row GeoDataFrame.

    Returns an empty frame if the route is not in that source -- the 2015 KML
    and the current file disagree about 31 routes, so this happens for real.
    """
    g = load_geometry([source])[source]
    return g[g.route_id == str(route)]


# --- stops -------------------------------------------------------------------
def pattern_files(route, xwalk_path=f'{DATA}/rt_to_pid.csv'):
    """Find the arrival files for a route, and note which ones are absent.

    A "pattern" is one path a bus can take along a route: the full run, a
    short-turn, a variant that skips a segment. StopWatch stores one file per
    pattern. `rt_to_pid.csv` maps routes to patterns, but it lists patterns
    that are not on the server -- 54 of 940 overall, and 6 of route 66's 19.
    See docs/bus-tracker-data-plan.md.

    Returns (paths, missing_pids): existing file paths, and the pattern ids
    that had no file.
    """
    xwalk = pd.read_csv(xwalk_path, dtype=str)
    pids = xwalk.loc[xwalk.rt == str(route), 'pid'].tolist()
    paths, missing = [], []
    for p in pids:
        path = f'{ACTUALS_DIR}/trips_{p}_full.parquet'
        if os.path.exists(path):
            paths.append(path)
        else:
            missing.append(p)
    return paths, missing


def gtfs_stops(gtfs_dir=GTFS):
    """Stop locations from the GTFS feed: stop_id, stop_name, stop_lat, stop_lon.

    The arrival files carry a stop id but no coordinates, so this is what puts
    stops on a map. Note the feed is a single snapshot while the arrivals span
    2022 onwards, so stops retired before the snapshot will not be found.
    """
    stops = pd.read_csv(f'{gtfs_dir}/stops.txt', dtype={'stop_id': str})
    return stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']]


def route_stops(route, with_coords=True):
    """Every (pattern, stop) pair on a route, with coordinates attached.

    Reads only three columns from each pattern file and drops duplicates
    straight away, so the result is a few hundred rows even though the files
    behind it are gigabytes.

    Args:
        route: route id, e.g. '66'.
        with_coords: join GTFS coordinates. Set False to skip the join.

    Returns a DataFrame of pid, stpid, stop_sequence and -- when joined --
    stop_id, stop_name, stop_lat, stop_lon.

    Stops with no GTFS match keep NaN coordinates rather than being dropped,
    so the caller can see how many there are and decide. For route 66 that is
    17 of 168 stops.
    """
    paths, _ = pattern_files(route)
    frames = [pq.read_table(p, columns=['stpid', 'stop_sequence', 'pid'])
              .to_pandas().drop_duplicates(['pid', 'stpid', 'stop_sequence'])
              for p in paths]
    stops = pd.concat(frames, ignore_index=True).drop_duplicates()
    stops['stpid'] = stops.stpid.astype(str)
    if not with_coords:
        return stops
    return stops.merge(gtfs_stops(), left_on='stpid', right_on='stop_id', how='left')


# --- route plots -------------------------------------------------------------
def plot_route_overview(stops, route, source=CURRENT_GEOMETRY, ax=None):
    """Plot a route's stops on top of its line, with the end points labelled.

    Args:
        stops: the output of route_stops(). Rows without coordinates are
            skipped, and stops shared by several patterns are drawn once.
        route: route id, used for the line shape and the title.
        source: which geometry file to draw the line from.
        ax: draw into existing axes, or make a new figure if None.

    There is no basemap, so the west and east end stops are labelled to make
    the map orientable.
    """
    import matplotlib.pyplot as plt
    located = stops[stops.stop_lat.notna()].drop_duplicates('stpid')
    if ax is None:
        _, ax = plt.subplots(figsize=(13, 4.2))

    line = route_line(route, source)
    if len(line):
        line.plot(ax=ax, color=BLUE_L, lw=3, zorder=1)
    ax.scatter(located.stop_lon, located.stop_lat, s=16, color=BLUE, zorder=3,
               edgecolor=SURFACE, linewidth=0.4)

    for _, r in located.nsmallest(1, 'stop_lon').iterrows():
        ax.annotate(f'  west\n  {r.stop_name}', (r.stop_lon, r.stop_lat),
                    fontsize=8, color=INK2, va='center')
    for _, r in located.nlargest(1, 'stop_lon').iterrows():
        ax.annotate(f'{r.stop_name}  \neast  ', (r.stop_lon, r.stop_lat),
                    fontsize=8, color=INK2, va='center', ha='right')

    ax.set_title(f'Route {route}: {len(located)} distinct stops with GTFS coordinates')
    ax.set_xlabel('longitude')
    ax.set_ylabel('latitude', color=INK2)
    map_aspect(ax)
    ax.grid(alpha=.4)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    return ax


def plot_pattern_panels(stops, route, ncols=3):
    """One small map per pattern, with stops shaded by their order along it.

    Each panel shows every stop on the route in grey, and that pattern's own
    stops shaded dark-to-light by `stop_sequence`. Which end is dark tells you
    which way the pattern runs, and how far along the route it reaches shows
    whether it is a full run or a short-turn. No external direction label is
    used, so this is a way of seeing direction rather than trusting a field.

    Args:
        stops: output of route_stops().
        route: route id, for the title.
        ncols: panels per row.

    Returns the figure.
    """
    import matplotlib.pyplot as plt
    located = stops[stops.stop_lat.notna()]
    all_stops = located.drop_duplicates('stpid')
    pids = located.groupby('pid').stpid.nunique().sort_values(ascending=False).index.tolist()
    nrows = int(np.ceil(len(pids) / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 2.1 * nrows), squeeze=False)
    for ax, pid in zip(axes.ravel(), pids):
        d = located[located.pid == pid].sort_values('stop_sequence')
        ax.scatter(all_stops.stop_lon, all_stops.stop_lat, s=3, color=GRID, zorder=1)
        ax.scatter(d.stop_lon, d.stop_lat, c=d.stop_sequence, cmap='viridis',
                   s=14, zorder=3, edgecolor='none')
        ax.set_title(f'pid {pid}   {d.stpid.nunique()} stops   '
                     f'seq {d.stop_sequence.min():g}-{d.stop_sequence.max():g}', fontsize=9)
        map_aspect(ax)
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ax.spines.values():
            side.set_visible(False)
    for ax in axes.ravel()[len(pids):]:
        ax.set_visible(False)

    fig.suptitle(f'Route {route}: each pattern, dark-to-light by stop_sequence',
                 x=0.01, ha='left', fontweight='bold', fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    return fig


def plot_sequence_vs_longitude(stops, route, ax=None):
    """Plot each pattern's stop order against longitude, to separate the directions.

    For an east-west route, a pattern heading east has a stop_sequence that
    rises with longitude, and one heading west has a sequence that falls. The
    two directions therefore appear as two fans of lines with opposite slopes,
    and short-turns show up as lines that cover only part of the width.

    This is a look at the data, not a direction assignment -- it will be
    uninformative for a north-south route, where latitude is the axis that
    matters.

    Args:
        stops: output of route_stops().
        route: route id, for the title.
        ax: draw into existing axes, or make a new figure if None.
    """
    import matplotlib.pyplot as plt
    located = stops[stops.stop_lat.notna()]
    pids = located.groupby('pid').stpid.nunique().sort_values(ascending=False).index.tolist()
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 4.4))

    palette = plt.cm.tab20(np.linspace(0, 1, len(pids)))
    for colour, pid in zip(palette, pids):
        d = located[located.pid == pid].sort_values('stop_sequence')
        ax.plot(d.stop_lon, d.stop_sequence, marker='o', ms=3, lw=1,
                color=colour, label=str(pid))
    ax.set_xlabel('longitude  (west <-- --> east)')
    ax.legend(title='pid', ncols=7, fontsize=8, title_fontsize=8,
              loc='upper center', bbox_to_anchor=(0.5, -0.16))
    ax.set_title(f'Route {route}: stop_sequence vs longitude, one line per pattern')
    style(ax, 'stop_sequence')
    return ax
