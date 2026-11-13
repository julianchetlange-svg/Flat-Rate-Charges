"""Build monthly usage and accounting comparison data for the 2026 back-test.

Usage:
  python scripts/build_usage.py CPM_INDEX_HTML [ACCOUNTING_XLSX]

  CPM_INDEX_HTML   index.html from julianchetlange-svg/Fleet-CMP-HOUR-Analysis (monthly miles/hours by asset)
  ACCOUNTING_XLSX  accounting's YTD vehicle expense file (sheets 'Ops' and 'Ops Veh Exp Alloc'), optional

Writes data/usage_2026.json (and data/acct_2026.json when the accounting file is given).
Units are billed to their store on data/assets.json (current list); disposed units use their CPM store.
"""
import sys, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
EX = {'353', '355', '355CD', '356', '359', '489', '450', '950'}


def sc(v):
    s = str(v).strip().split(' ')[0].split('_')[0]
    s = s.split('.')[0] if re.fullmatch(r'\d+\.0', s) else s
    return s.lstrip('0') or '0'


def usage(cpm_path):
    s = Path(cpm_path).read_text()
    i = s.index('const DATA = ') + len('const DATA = ')
    d, _ = json.JSONDecoder().raw_decode(s[i:])
    months = d['months']
    A = {r[3]: r for r in json.loads((DATA / 'assets.json').read_text())}
    out, seen = [], set()
    for a in d['assets']:
        store = A[a['id']][0] if a['id'] in A else a['s']
        if store in EX: continue
        tmpl = A[a['id']][4] if a['id'] in A else (a['t'] or '')
        if a['c'] in ('Truck', 'LD Vehicle'): use = a['mi']
        elif a['c'] in ('Forklift', 'TMFL'): use = a['hr']
        else: use = None
        out.append([a['id'], store, tmpl, ''.join('1' if x else '0' for x in a['act']),
                    [round(x, 1) for x in use] if use is not None else None, 0 if a['id'] in A else 1])
        seen.add(a['id'])
    # current units with no CPM record: active from origination month, no usage
    n = len(months)
    for k, r in A.items():
        if k in seen or r[0] in EX: continue
        o = str(r[9] or '')
        start = int(o[5:7]) if o.startswith('2026') else 1
        out.append([k, r[0], r[4], ''.join('1' if m + 1 >= start else '0' for m in range(n)), None, 0])
    (DATA / 'usage_2026.json').write_text(json.dumps({'months': months, 'units': out}, separators=(',', ':')))
    return len(out), months


def acct(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    actual = {}
    for r in list(wb['Ops'].iter_rows(values_only=True))[1:]:
        if r[0] and str(r[0]).strip() != 'Total' and r[2] is not None:
            actual[sc(r[0])] = round(float(r[2]), 2)
    ws = wb['Ops Veh Exp Alloc']; rows = list(ws.iter_rows(values_only=True)); hdr = rows[0]
    month_of = []
    for h in hdr[1:-2]:
        m = re.search(r'(\d{2})/\d{2}/2026', str(h))
        month_of.append(int(m.group(1)) - 1 if m else None)
    alloc = {}
    for r in rows[1:]:
        if not r[0] or str(r[0]).strip() == 'Total': continue
        v = [0.0] * 12
        for mi, x in zip(month_of, r[1:-2]):
            if mi is not None and x: v[mi] += float(x)
        alloc[sc(r[0])] = [round(x, 2) for x in v]
    names = {sc(r[0]): str(r[0]).split(' ', 1)[1] for r in rows[1:] if r[0] and str(r[0]).strip() != 'Total'}
    out = {'through': 'Sep', 'alloc': alloc, 'actual': actual, 'names': names}
    old = DATA / 'acct_2026.json'
    if old.exists():   # keep monthly totals entered by hand (old flat-rate charges incl. HQ assets)
        prev = json.loads(old.read_text())
        for k in ('totalInclHQ', 'totalInclHQThrough'):
            if k in prev: out[k] = prev[k]
    (DATA / 'acct_2026.json').write_text(json.dumps(out, separators=(',', ':')))
    return len(alloc)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    n, months = usage(sys.argv[1])
    print(f'{n} unit records, months {months[0]}–{months[-1]}')
    if len(sys.argv) > 2:
        print(f'{acct(sys.argv[2])} stores in accounting file')
