"""Load prior-year Fexa spend (Nov-Dec 2025) so unit-month maintenance runs on a rolling 12 months.

Usage:
  python scripts/prior_spend.py ASSET_SPEND_NOV_DEC_2025.xlsx
Writes data/prior_spend.json {unit: {"nov": $, "dec": $, "tmpl": template}}, then rerun build_data.py.
Same filtering as the CPM build: invoices split evenly across assets; registration/tax and non-fleet
categories and rows without a unit number removed; month = invoice transaction date.
"""
import sys, json
from pathlib import Path
import pandas as pd

SP = pd.read_excel(sys.argv[1]); amt = 'Subcontractor Invoice Total'
SP['dt'] = pd.to_datetime(SP['Subcontractor Invoice Transaction Date'], format='mixed')
SP = SP[(SP.dt.dt.year == 2025) & (SP.dt.dt.month >= 11)].copy(); SP['Month'] = SP.dt.dt.month
key = ['Subcontractor Invoice Reference Number', amt, 'Work Order ID']
SP['amt'] = SP[amt] / SP.groupby(key)['Asset Name'].transform('size')
SP['sub'] = SP['Work Order Category Full Path'].str.split(r' \| ').str[-1].str.split(' - ').str[-1]
SP['cat'] = SP['Work Order Category Full Path'].str.split(r' \| ').str[1]
SP['Unit'] = pd.to_numeric(SP['Asset Name'], errors='coerce')
keep = ~SP['sub'].isin({'Registration-Inspection', 'Personal Property Tax', 'Monthly Registration Invoice'}) \
       & ~SP['cat'].isin({'Insulation Blower', 'Holtec Saw', 'Ancillary Materials'}) & SP.Unit.notna()
K = SP[keep]; out = {}
for r in K.itertuples():
    u = str(int(r.Unit)); o = out.setdefault(u, {'nov': 0.0, 'dec': 0.0, 'tmpl': ''})
    o['nov' if r.Month == 11 else 'dec'] += r.amt
for u, t in K.groupby(K.Unit.astype(int).astype(str))['Asset Template Name'].first().items(): out[u]['tmpl'] = str(t)
for o in out.values(): o['nov'] = round(o['nov'], 2); o['dec'] = round(o['dec'], 2)
Path(__file__).resolve().parent.parent.joinpath('data', 'prior_spend.json').write_text(json.dumps(out, separators=(',', ':')))
print(f"Nov ${sum(o['nov'] for o in out.values()):,.0f}, Dec ${sum(o['dec'] for o in out.values()):,.0f}, {len(out)} units")
