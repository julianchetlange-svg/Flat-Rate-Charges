"""Refresh Fexa maintenance in a copy of the CPM report's data from a newer Asset Spend export.

Usage:
  python scripts/refresh_fexa.py ASSET_SPEND.xlsx CPM_INDEX_HTML OUT_INDEX_HTML
  python scripts/build_data.py ASSET_LIST.xlsx OUT_INDEX_HTML
  python scripts/build_html.py

Same rules as the CPM build: invoices split evenly across the assets on them; registration/tax
sub-categories and non-fleet categories (Insulation Blower, Holtec Saw, Ancillary Materials) and rows
without a unit number removed; month = invoice transaction date, Jan-Oct 2026. Pickups and cargo vans
keep the CPM standard ($0.14 x miles).
"""
import sys, json
import pandas as pd

spend, src, out = sys.argv[1:4]
SP = pd.read_excel(spend)
amt = 'Subcontractor Invoice Total'
SP['dt'] = pd.to_datetime(SP['Subcontractor Invoice Transaction Date'], format='mixed')
SP = SP[(SP.dt.dt.year == 2026) & (SP.dt.dt.month <= 10)].copy(); SP['Month'] = SP.dt.dt.month
key = ['Subcontractor Invoice Reference Number', amt, 'Work Order ID']
SP['amt'] = SP[amt] / SP.groupby(key)['Asset Name'].transform('size')
SP['sub'] = SP['Work Order Category Full Path'].str.split(r' \| ').str[-1].str.split(' - ').str[-1]
SP['cat'] = SP['Work Order Category Full Path'].str.split(r' \| ').str[1]
SP['Unit'] = pd.to_numeric(SP['Asset Name'], errors='coerce')
keep = ~SP['sub'].isin({'Registration-Inspection', 'Personal Property Tax', 'Monthly Registration Invoice'}) \
       & ~SP['cat'].isin({'Insulation Blower', 'Holtec Saw', 'Ancillary Materials'}) & SP.Unit.notna()
new = {}
for r in SP[keep].itertuples():
    new.setdefault(str(int(r.Unit)), [0.0] * 10)[r.Month - 1] += r.amt

s = open(src).read(); tag = 'const DATA = '; i = s.index(tag) + len(tag)
D, end = json.JSONDecoder().raw_decode(s[i:]); end += i
ids = {a['id'] for a in D['assets']}; old = newt = 0
for a in D['assets']:
    if a.get('std'): continue
    old += sum(a['maint']); a['maint'] = [round(x, 2) for x in new.get(a['id'], [0] * 10)]; newt += sum(a['maint'])
miss = sum(sum(v) for k, v in new.items() if k not in ids)
D['fexa_refresh'] = spend.rsplit('/', 1)[-1]
open(out, 'w').write(s[:i] + json.dumps(D, separators=(',', ':')) + s[end:])
print(f'Fexa maintenance (excl. pickups/cargo vans): {old:,.0f} -> {newt:,.0f} ({newt-old:+,.0f}); spend on units not in CPM data: {miss:,.0f}')
