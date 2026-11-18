"""Rebuild the calculator's data files.

Usage:
  python scripts/build_data.py ASSET_LIST.xlsx CPM_INDEX_HTML

  ASSET_LIST.xlsx  current asset list export (Store Number, Store Name, Store District, Asset Name,
                   Asset Template Name, Asset Manufacturer Name, Asset Serial Number, Asset Ownership,
                   Asset Status, Asset Date of Origination, Asset Original Value)
  CPM_INDEX_HTML   index.html from julianchetlange-svg/Fleet-CMP-HOUR-Analysis (the YTD cost per mile /
                   hour report, which embeds the Fexa maintenance, miles and hours by asset)

Uses data/prior_spend.json (scripts/prior_spend.py) for rolling-12 unit-month maintenance when present.
Writes data/assets.json, data/maint_rates.json, data/unitmonth.json, data/tractor_units.json and
data/cost_estimates.json.
Then run scripts/build_html.py.
"""
import sys, json, math, collections, statistics as st
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
# locations not on flat rate (maintenance averages use the other locations first)
EX = {'353', '355', '355CD', '356', '359', '489', '450', '950'}
# CPM templates that are not rated per mile / hour
SKIP = {'(blank)', 'Sub / rental unit', 'Electric Pallet Jack', 'Mobile Generator Trailer', 'Scissor Lift'}
# units left out of the per-mile/hour rates as anomalies
#   694028  24' Van Body, 068 Plainview, disposed: $7,155 Fexa on 3,918 miles Jan-May (11/17/2026: keep 24' Van Body at $0.468)
MAINT_EXCLUDE = {'694028'}


def assets(path):
    df = pd.read_excel(path, dtype={'Store Number': str, 'Asset Serial Number': str})
    v = lambda x: None if (x is None or (isinstance(x, float) and math.isnan(x))) else x
    cols = ['Store Number', 'Store Name', 'Store District', 'Asset Name', 'Asset Template Name', 'Asset Manufacturer Name',
            'Asset Serial Number', 'Asset Ownership', 'Asset Status', 'Asset Date of Origination', 'Asset Original Value']
    loc = 'Asset Location' if 'Asset Location' in df.columns else None   # physical location / billing guidance (11/18/2026 file on)
    rows = []
    for _, r in df.iterrows():
        row = [str(r[cols[0]])] + [v(r[c]) for c in cols[1:3]] + [str(r[cols[3]]).split('.')[0]] + [v(r[c]) for c in cols[4:]]
        if row[10] is not None and row[10] <= 0: row[10] = None          # a zero cost is a missing cost
        row.append(v(r[loc]) if loc else None)
        rows.append(row)
    (DATA / 'assets.json').write_text(json.dumps(rows, separators=(',', ':')))
    return len(rows)


def cost_estimates():
    """Placeholder cost for assets with no Asset Original Value: average of the 3 same-template units with a cost
    whose origination date is closest (all same-template units if the asset has no date)."""
    import datetime as dt
    A = json.loads((DATA / 'assets.json').read_text())
    def d(x):
        try: return dt.date.fromisoformat(str(x)[:10])
        except Exception: return None
    out = {}
    for r in A:
        if r[10] is not None: continue
        o = d(r[9])
        peers = [p for p in A if p[4] == r[4] and p[10] and p[10] > 0 and d(p[9])]
        if not peers: continue
        near = sorted(peers, key=lambda p: abs((d(p[9]) - o).days))[:3] if o else peers
        out[r[3]] = dict(cost=round(sum(p[10] for p in near) / len(near), 2),
                         basis=f"avg of {len(near)} {r[4]} unit(s) " + (f"originated nearest {r[9]}" if o else "(no origination date)") + ": " +
                               ", ".join(f"{p[3]} ({p[9]}, ${p[10]:,.0f})" for p in near[:3]))
    (DATA / 'cost_estimates.json').write_text(json.dumps(out, separators=(',', ':')))
    return len(out)


def cpm(path):
    s = Path(path).read_text()
    i = s.index('const DATA = ') + len('const DATA = ')
    d, _ = json.JSONDecoder().raw_decode(s[i:])
    return d


def usage(a):
    if a['c'] in ('Truck', 'LD Vehicle'): return a['mi'], 'mile'
    if a['c'] in ('Forklift', 'TMFL'): return a['hr'], 'hour'
    return None, None


def maint_rates(d):
    """Fexa maintenance ÷ miles or hours by template. Units with an active month lacking usage are left out."""
    blank = lambda: dict(units=0, m=0, u=0, am=0, rates=[], gap=0)
    g = collections.defaultdict(lambda: {'all': blank(), 'ch': blank(), 'n': 0, 'he': 0})
    anym = collections.defaultdict(lambda: {'ch': [0, 0], 'all': [0, 0]})
    for a in d['assets']:
        t = a['t'] or '(blank)'
        arr, meas = usage(a)
        if arr is None or t in SKIP or a['id'] in MAINT_EXCLUDE: continue
        o = g[t]; o['c'] = a['c']; o['meas'] = meas; o['n'] += 1
        use = sum(arr)
        if use <= 0: continue
        ks = ['all', 'ch'] if a['s'] not in EX else ['all']
        nmo = sum(1 for x in arr if x > 0)
        for k in ks: anym[t][k][0] += use; anym[t][k][1] += nmo
        if any(a['act'][i] and arr[i] <= 0 for i in range(len(arr))):
            for k in ks: o[k]['gap'] += 1
            continue
        if meas == 'hour' and a.get('he') == 1: o['he'] += 1
        m = sum(a['mrec']) if a.get('mrec') is not None else sum(a['maint'])  # recorded Fexa spend only
        am = sum(a['act']) or len(arr)
        for k in ks:
            b = o[k]; b['units'] += 1; b['m'] += m; b['u'] += use; b['am'] += am; b['rates'].append(m / use)
    out = []
    for t, o in g.items():
        row = dict(t=t, c=o['c'], meas=o['meas'], n=o['n'], std=0, he=o['he'])
        for k in ('all', 'ch'):
            b = o[k]
            row[k] = dict(units=b['units'], gap=b['gap'], maint=round(b['m'], 2), use=round(b['u'], 1), am=b['am'],
                          rate=round(b['m'] / b['u'], 4) if b['u'] else None,
                          mean=round(sum(b['rates']) / len(b['rates']), 4) if b['rates'] else None,
                          med=round(st.median(b['rates']), 4) if b['rates'] else None,
                          mo=round(b['u'] / b['am'], 1) if b['am'] else None)
        x = anym.get(t)
        if x and (x['ch'][1] or x['all'][1]):
            row['moAny'] = round(x['ch'][0] / x['ch'][1] if x['ch'][1] else x['all'][0] / x['all'][1], 1)
        out.append(row)
    out.sort(key=lambda r: (r['c'], r['t']))
    (DATA / 'maint_rates.json').write_text(json.dumps(out, separators=(',', ':')))


def unit_month(d):
    """Fexa maintenance per active unit-month by template, on a rolling 12 months when data/prior_spend.json
    (Nov-Dec of the prior year) is present. A unit counts as active in Nov/Dec if it had spend that month, or was
    in service in January and originated by the end of that month."""
    pf = DATA / 'prior_spend.json'
    P = json.loads(pf.read_text()) if pf.exists() else {}
    g = collections.defaultdict(lambda: {'ch': [], 'all': []})
    for a in d['assets']:
        if not a['t'] or a['t'] == 'Sub / rental unit': continue
        am = sum(a['act'])
        if am <= 0: continue
        m = sum(a['maint'])
        if P and not a.get('std'):
            p = P.get(a['id'], {}); o = a.get('o') or ''; jan = bool(a['act'][0])
            for k, end in (('nov', '2025-11-30'), ('dec', '2025-12-31')):
                sp = p.get(k, 0)
                if sp or (jan and (not o or o <= end)): am += 1
                m += sp
        rec = (m, am)
        g[a['t']]['all'].append(rec)
        if a['r'] and a['s'] not in EX: g[a['t']]['ch'].append(rec)
    out = {}
    for t, o in g.items():
        row = {}
        for k, v in o.items():
            if not v: row[k] = None; continue
            M = sum(x[0] for x in v); A = sum(x[1] for x in v)
            row[k] = dict(units=len(v), maint=round(M, 2), am=A, rate=round(M / A, 2), mean=round(sum(x[0] / x[1] for x in v) / len(v), 2))
        out[t] = row
    (DATA / 'unitmonth.json').write_text(json.dumps(out, separators=(',', ':')))


def tractor_units(d):
    """Per-unit tractor data, so planned replacements can drop specific units from the averages."""
    out = []
    for a in d['assets']:
        if a['t'] not in ('Tractor TA', 'Tractor SA'): continue
        arr = a['mi']; use = sum(arr)
        ok = use > 0 and not any(a['act'][i] and arr[i] <= 0 for i in range(len(arr)))
        out.append([a['id'], a['s'], round(sum(a['maint']), 2), round(use, 1), sum(a['act']), 1 if ok else 0, a['o'] or '', a['t']])
    (DATA / 'tractor_units.json').write_text(json.dumps(out, separators=(',', ':')))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    DATA.mkdir(exist_ok=True)
    n = assets(sys.argv[1])
    ne = cost_estimates()
    d = cpm(sys.argv[2])
    maint_rates(d); unit_month(d); tractor_units(d)
    print(f'{n} assets ({ne} with estimated cost); CPM data built {d.get("built")}')
