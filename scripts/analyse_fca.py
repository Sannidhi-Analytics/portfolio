"""
Analyse FCA enforcement fines, 2023-2025.

Reads data/fca_fines.csv (transcribed from the FCA's published annual fines
pages) and writes data/fca_fines.json for the front end. Also prints a
validation check against the FCA's own published annual totals.

Usage: python scripts/analyse_fca.py
Source: https://www.fca.org.uk/news/news-stories/2025-fines (and 2024, 2023)
"""
import csv, json, collections, statistics, os

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, '..', 'data', 'fca_fines.csv')
OUT = os.path.join(HERE, '..', 'data', 'fca_fines.json')

# The FCA publishes an annual total on each fines page. Reconciling against
# these confirms the dataset is complete rather than a partial sample.
PUBLISHED_TOTALS = {'2023': 53_354_600, '2024': 176_045_385, '2025': 124_221_367}


def main():
    rows = list(csv.DictReader(open(SRC)))
    for r in rows:
        r['amount_gbp'] = float(r['amount_gbp'])

    json.dump(rows, open(OUT, 'w'))
    print(f'Wrote {OUT} — {len(rows)} enforcement actions\n')

    print('Validation against FCA published totals')
    by_year = collections.Counter()
    for r in rows:
        by_year[r['year']] += r['amount_gbp']
    for year in sorted(by_year):
        computed, published = by_year[year], PUBLISHED_TOTALS[year]
        status = 'MATCH' if abs(computed - published) < 1 else 'MISMATCH'
        print(f'  {year}: computed £{computed:>13,.0f} | published £{published:>13,.0f} | {status}')

    total = sum(r['amount_gbp'] for r in rows)
    firms = [r['amount_gbp'] for r in rows if r['type'] == 'Firm']
    individuals = [r['amount_gbp'] for r in rows if r['type'] == 'Individual']

    print(f'\nTotal: £{total/1e6:.1f}m across {len(rows)} actions')
    print(f'Firms: £{sum(firms)/1e6:.1f}m ({len(firms)} actions, '
          f'{sum(firms)/total*100:.1f}% of value)')
    print(f'Individuals: £{sum(individuals)/1e6:.1f}m ({len(individuals)} actions)')
    print(f'Median firm penalty: £{statistics.median(firms)/1e6:.2f}m | '
          f'mean £{statistics.mean(firms)/1e6:.2f}m')

    print('\nBy breach theme:')
    value = collections.Counter()
    count = collections.Counter()
    for r in rows:
        value[r['breach_theme']] += r['amount_gbp']
        count[r['breach_theme']] += 1
    for theme, v in value.most_common():
        print(f'  {theme:<40} £{v/1e6:>7.1f}m  ({count[theme]} actions)')

    print('\nBy sector:')
    sector = collections.Counter()
    for r in rows:
        sector[r['sector']] += r['amount_gbp']
    for s, v in sector.most_common(8):
        print(f'  {s:<40} £{v/1e6:>7.1f}m')


if __name__ == '__main__':
    main()
