"""Load the 2026 monthly flat-rate billing files (as sent to accounting) for the back-test.

Usage:
  python scripts/build_old_billing.py FILE_JAN.xlsx FILE_FEB.xlsx ...   (any order; month read from the file title)

Each file needs sheets 'Flat Rate Fixed Variable' (pivot by store: asset-class base rates, 'Variable Charge',
'Camera Monthly Fee', 'DAMAGES - ...' lines) and 'Data Detail' (one row per asset with Charge).
Writes data/old_billing_2026.json.
"""
import sys, re, json, collections
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']


def norm(a):
    if isinstance(a, (int, float)): return str(int(a))
    s = str(a).strip()
    return s.lstrip('0') or '0' if re.fullmatch(r'0*\d+[A-Za-z]*', s) else None


def load(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['Flat Rate Fixed Variable']
    rows = list(ws.iter_rows(values_only=True))
    title = str(rows[0][0])
    m = next(i for i, n in enumerate(MONTHS) if n in title)
    hi = next(i for i, r in enumerate(rows) if r[0] == 'Row Labels'); hdr = rows[hi]
    ci = hdr.index('Sum of Charge'); ni = hdr.index('Count of Asset Number')
    stores = collections.defaultdict(collections.Counter); cur = None; total = None; dmg_lines = []
    for r in rows[hi + 1:]:
        a = r[0]
        if a is None: continue
        n = norm(a)
        if n is not None: cur = n; continue
        s = str(a)
        if s == 'Grand Total': total = r[ci]; break
        if s.endswith(' Total'): continue
        v = r[ci]
        if not isinstance(v, (int, float)): continue
        if s == 'Variable Charge': k = 'variable'
        elif 'Camera' in s: k = 'camera'
        elif 'DAMAGE' in s.upper(): k = 'damages'; dmg_lines.append([cur, s, round(v, 2)])
        else:
            k = 'base'
            if isinstance(r[ni], (int, float)): stores[cur]['units'] += r[ni]
        stores[cur][k] += v
    dd = list(wb['Data Detail'].iter_rows(values_only=True)); h = [str(x).strip() if x else x for x in dd[0]]
    iS, iA, iC, iF, iCh, iMi = (h.index(x) for x in ('Store', 'Asset Number', 'Asset Class', 'Function', 'Charge', 'Miles'))
    assets = []
    for r in dd[1:]:
        if r[iC] == 'Variable Charge' and r[iS] is not None and isinstance(r[iMi], (int, float)):
            stores[norm(r[iS]) or str(r[iS])]['miles'] += r[iMi]
        if r[iA] is None or r[iS] is None or not isinstance(r[iCh], (int, float)): continue
        if 'DAMAGE' in str(r[iC]).upper(): continue
        assets.append([norm(r[iS]) or str(r[iS]), str(r[iA]).split('.')[0], r[iC], r[iF], round(r[iCh], 2)])
    return m, total, stores, assets, dmg_lines


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    loaded = {}
    for p in sys.argv[1:]:
        m, total, stores, assets, dmg = load(p)
        loaded[m] = (total, stores, assets, dmg)
        print(f'{MONTHS[m]}: total {total:,.0f}, {len(stores)} locations, {len(assets)} assets')
    months = sorted(loaded)
    out = {'months': [MONTHS[m][:3] for m in months], 'totals': [round(loaded[m][0], 2) for m in months], 'stores': {}, 'assets': {}, 'damages': []}
    n = len(months)
    for j, m in enumerate(months):
        total, stores, assets, dmg = loaded[m]
        for s, c in stores.items():
            d = out['stores'].setdefault(s, {k: [0] * n for k in ('base', 'variable', 'camera', 'damages', 'units', 'miles')})
            for k in d: d[k][j] = round(c.get(k, 0), 2)
        for s, a, cls, fn, ch in assets:
            e = out['assets'].setdefault(a, [s, cls, fn, [0] * n])
            e[0], e[1], e[2] = s, cls, fn
            e[3][j] = round(e[3][j] + ch, 2)
        out['damages'] += [[out['months'][j]] + x for x in dmg]
    (ROOT / 'data' / 'old_billing_2026.json').write_text(json.dumps(out, separators=(',', ':')))
