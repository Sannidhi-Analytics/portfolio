"""
Fetch and analyse FDA drug enforcement (recall) data from the openFDA API.
Outputs data/fda_summary.json consumed by fda-recalls.html

Usage:  python scripts/fetch_fda.py
Source: https://open.fda.gov/apis/drug/enforcement/
"""
import urllib.request, json, collections, re, os

BASE = 'https://api.fda.gov/drug/enforcement.json'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'fda_summary.json')

# Recall reasons are free text. These patterns are applied in order; each record
# is assigned to the first category that matches. Order matters: CGMP is checked
# first because CGMP notices often also mention contamination as the symptom.
CATEGORIES = {
    'CGMP deviations':                   r'cgmp|current good manufacturing',
    'Contamination (microbial/foreign)':  r'contaminat|microbial|sterility|particulate|foreign (material|matter)|mold|bacteria',
    'Impurities (incl. nitrosamines)':    r'impurit|nitrosamine|ndma|nitroso',
    'Labelling/packaging errors':         r'label|packag|carton|mispr',
    'Potency/specification failures':     r'potency|subpotent|superpotent|out of specification|oos|assay|dissolution|specification',
    'Stability failures':                 r'stability|expir',
    'Mix-ups/wrong product':              r'mix.?up|incorrect (product|tablet|drug)|wrong',
    'Presence of undeclared ingredient':  r'undeclared|unapproved',
}


def get(url):
    with urllib.request.urlopen(url, timeout=25) as r:
        return json.load(r)


def main():
    out = {}

    # Aggregate counts across the entire dataset via the API's count endpoint
    out['classification'] = get(f'{BASE}?count=classification.exact')['results']
    out['voluntary']      = get(f'{BASE}?count=voluntary_mandated.exact')['results']
    out['status']         = get(f'{BASE}?count=status.exact')['results']

    # Recalls per year, aggregated from daily initiation-date counts
    daily = get(f'{BASE}?count=recall_initiation_date')['results']
    yearly = collections.Counter()
    for d in daily:
        yearly[d['time'][:4]] += d['count']
    out['yearly'] = {y: yearly[y] for y in sorted(yearly) if '2015' <= y <= '2026'}

    # Pull individual records from 2021 onward for root cause categorisation.
    # openFDA caps limit at 1000 per request, so page through with skip.
    records = []
    for skip in range(0, 3000, 1000):
        page = get(f'{BASE}?search=recall_initiation_date:[20210101+TO+20261231]'
                   f'&limit=1000&skip={skip}')
        records += page['results']
        if len(page['results']) < 1000:
            break
    print(f'Fetched {len(records)} individual recall records')

    counts = collections.Counter()
    yearly_class = collections.defaultdict(collections.Counter)
    for r in records:
        reason = (r.get('reason_for_recall') or '').lower()
        for name, pattern in CATEGORIES.items():
            if re.search(pattern, reason):
                counts[name] += 1
                break
        else:
            counts['Other'] += 1
        year = r.get('recall_initiation_date', '')[:4]
        if year:
            yearly_class[year][r.get('classification', 'Unknown')] += 1

    out['reason_categories'] = dict(counts.most_common())
    out['yearly_class'] = {y: dict(yearly_class[y]) for y in sorted(yearly_class)}
    out['top_firms'] = collections.Counter(
        (r.get('recalling_firm') or 'Unknown').strip() for r in records).most_common(10)
    out['records_analysed'] = len(records)
    out['total_recalls_all_time'] = sum(c['count'] for c in out['classification'])

    with open(OUT, 'w') as f:
        json.dump(out, f, indent=1)
    print(f'Wrote {OUT}')
    print(f"Total recalls in dataset: {out['total_recalls_all_time']:,}")
    for name, n in out['reason_categories'].items():
        print(f'  {name}: {n} ({n/len(records)*100:.1f}%)')


if __name__ == '__main__':
    main()
