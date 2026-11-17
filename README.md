# Fleet Flat Rate Charges

Interactive calculator for McCoy's annual flat monthly fleet rate. Stores pay a flat monthly rate per asset instead of taking fleet costs directly on their P&L, so repair decisions aren't made to protect a store's P&L and fleet expense is smoothed over each asset's life. **Fuel is not in the rate**; it is billed separately at actual.

Open `index.html` in a browser (or enable GitHub Pages: Settings → Pages → Deploy from branch `main`, `/root`). Settings you change are kept in that browser. **Download Excel** exports the store summary, rate by asset type, maintenance per mile/hour, asset detail, excluded locations, flags and assumptions.

## Phases
1. **Rate build** – done.
2. **Monthly processing** – the **2026 Back-test** tab bills each unit Jan–Oct 2026 at the new rates (fixed charge + type $/mile or $/hour × that month's miles/hours; flat maintenance for trailers etc.; months with no reading use the unit's average month) and compares it by store and month with accounting's old flat-rate allocation and actual expense. The same logic will run each month on new miles/hours for the accounting charge report.

## How the rate is built
Each asset type (template) gets one monthly rate: the simple average of the individual rates of its units at flat-rate locations. Combined types: *24' TA Flatbed & Slide*, *Truck Mounted Forklift & 4-Way*, *Tractor (TA & SA)*.

Individual rate per unit:
| Component | Calculation |
|---|---|
| Delivered cost | equipment cost with tax + aftermarket (wrap / rolling tarp, TMFL kit / lift gate) |
| Base rate | `PMT(funding rate/12, life months, −delivered cost, residual, 1)` – paid in advance down to residual |
| Ad valorem | 0.8% × delivered cost ÷ 12 |
| Registration | 0.6% ÷ 12 trucks/tractors; 0.2% ÷ 12 light-duty and trailers; none for forklifts/TMFL |
| GPS / Lytx | $26 / $36 per month, road units only |
| Maintenance | Fexa work-order history only (see below) |

**Maintenance** (from the YTD Cost per Mile / Hour analysis, Jan–Oct 2026):
- Trucks, tractors, light-duty: type's total Fexa spend ÷ total miles × average monthly miles per unit.
- Forklifts and TMFLs: total Fexa spend ÷ total hours × average monthly hours per unit.
- Trailers, carts, sweeper, reach truck, scissor lifts: Fexa spend per active unit-month.
- Locked: pickups $0.14/mile, cars $0.09/mile (incomplete Fexa data).
- Units with missing telematics/hour months are left out of the per-mile/hour rates.

**2027 rate-year assumptions (built from 2026 data):** funding rate 6.00%; life/residual – forklift 96 mo/15%, TMFL 96/20%, light-duty 72/20%, truck 96/15%, tractor 120/15%, trailer 180/5%, specialty trailer 180/0%.

**Aftermarket:** wraps ($3,825 trucks/tractors, $4,625 van bodies) and TMFL kits ($3,825 on 24' TA trucks) are added to delivered cost only for units **36 months or older**; newer units (and planned 2027 units) already carry an all-in delivered cost.

**Missing costs:** assets with no Asset Original Value use a placeholder cost – the average of the 3 same-template units closest in origination date – applied as the cost (marked "est", info note "Estimated cost") until the next asset upload carries the real value.

**Locations:** 353, 355, 355CD, 356, 359, 450, 489 and 950 are not on flat rate. Their assets are kept and priced for reference but left out of totals. All other locations, including offices (730, 735, 761–767, 900), are charged.

**Planned 2027 change:** 10 new Tractor TAs (Jan 2027) replace the 10 oldest store tractors. Replaced units drop out of the averages; cost per new unit and the replaced unit numbers are editable on the Assumptions tab.

## Repo layout
```
index.html               built calculator (open this)
src/template.html        calculator source; data tokens are injected at build
data/assets.json         asset list (Current_Assets_11_13_2026.xlsx)
data/maint_rates.json    Fexa maintenance per mile / hour by template
data/unitmonth.json      Fexa maintenance per unit-month by template
data/tractor_units.json  per-unit tractor data for planned replacements
data/usage_2026.json     Jan–Oct 2026 miles/hours and in-service months by unit (from the CPM report)
data/acct_2026.json      accounting's old flat-rate allocation by store/month and actual expense (through Sep)
data/logo.b64           McCoy's logo (base64 PNG) for the header
data/cost_estimates.json placeholder cost for assets missing Asset Original Value (avg of 3 same-type units nearest in age)
scripts/build_data.py    rebuild data/ from an asset list export + the CPM report's index.html
scripts/build_html.py    inject data/ into src/template.html -> index.html
```

## Rebuilding
```
pip install pandas openpyxl
python scripts/build_data.py Current_Assets.xlsx path/to/Fleet-CMP-HOUR-Analysis/index.html
python scripts/build_usage.py path/to/Fleet-CMP-HOUR-Analysis/index.html Sep26_Finals_YTD_Total_Vehicle_Expenses_Ops.xlsx
python scripts/build_html.py
```

## 2026 old billing (back-test)

`data/old_billing_2026.json` holds what the 2026 monthly flat-rate files billed (base by asset class, $0.42 per store mile, $36 Lytx cameras, damages) by store and month, plus base charge by asset. Rebuild it from the monthly files:

```
python scripts/build_old_billing.py Flat_Rate_January_2026.xlsx ... Flat_Rate_October_2026.xlsx
python scripts/build_html.py
```

The back-test compares new rates with old billing excluding damages and excluded locations (450 Millworks was billed Jan–Aug). Per-asset mileage and camera fees are estimated from Geotab miles because the old method billed them by store.
