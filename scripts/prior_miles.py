"""Load prior-year Geotab miles (Nov-Dec 2025) for rolling-12 per-mile maintenance rates.

Usage:
  python scripts/prior_miles.py MILES_NOV_2025.xlsx MILES_DEC_2025.xlsx
Each file is a Geotab trip summary export ("Report" sheet; Asset like "001-601002-pup", "Distance driven" in miles,
date range in the "Data" sheet). Writes data/prior_miles.json {unit: {"nov": mi, "dec": mi}}, then rerun build_data.py.
"""
import sys, json
from pathlib import Path
import pandas as pd

out = {}
for f in sys.argv[1:]:
    meta = pd.read_excel(f, 'Data', header=None)
    frm = pd.to_datetime(meta[meta[0] == 'FromDate'].iloc[0, 1])
    key = {11: 'nov', 12: 'dec'}[frm.month]
    R = pd.read_excel(f, 'Report')
    n = 0
    for a, d in zip(R['Asset'].astype(str), R['Distance driven']):
        parts = a.split('-')
        if len(parts) < 2 or not parts[1].strip().isdigit() or pd.isna(d): continue
        u = parts[1].strip().lstrip('0') or '0'
        o = out.setdefault(u, {'nov': 0.0, 'dec': 0.0}); o[key] = round(o[key] + float(d), 1); n += 1
    print(f'{frm:%b %Y}: {n} assets, {sum(v[key] for v in out.values()):,.0f} miles')
Path(__file__).resolve().parent.parent.joinpath('data', 'prior_miles.json').write_text(json.dumps(out, separators=(',', ':')))
