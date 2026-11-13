"""Inject the data files into src/template.html and write index.html."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / 'data'
html = (ROOT / 'src' / 'template.html').read_text()
for token, name in [('__ASSETS__', 'assets.json'), ('__MAINT__', 'maint_rates.json'),
                    ('__UNITMO__', 'unitmonth.json'), ('__TUNITS__', 'tractor_units.json'), ('__COSTEST__', 'cost_estimates.json'),
                    ('__USAGE__', 'usage_2026.json'), ('__ACCT__', 'acct_2026.json')]:
    html = html.replace(token, (D / name).read_text().replace('</', '<\\/'))
logo = (D / 'logo.b64').read_text().strip()
html = html.replace('__LOGO__', 'data:image/png;base64,' + logo)
(ROOT / 'index.html').write_text(html)
print(f'index.html: {len(html):,} bytes')
