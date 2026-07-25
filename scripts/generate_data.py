"""
Generate a synthetic GMP deviation dataset for the deviation dashboard.

No confidential or employer data is used. The generator models realistic
structure: severity mix, department distribution, a closure-time improvement
trend across the period, and recurrence probability conditioned on whether a
CAPA was raised.

Usage: python scripts/generate_data.py
Output: data/deviations.json
"""
import random, json, datetime, collections, os

random.seed(42)  # reproducible
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'deviations.json')

CATEGORIES = [('Documentation error', .26), ('Equipment failure', .16),
              ('Procedure not followed', .18), ('Material/component defect', .12),
              ('Environmental excursion', .09), ('Labelling error', .07),
              ('Calibration overdue', .06), ('Training gap', .06)]
DEPARTMENTS = ['Manufacturing', 'Quality Control', 'Packaging', 'Warehouse & Supply Chain']
SEVERITIES = [('Minor', .55), ('Major', .35), ('Critical', .10)]

# Target closure days by severity — used to flag overdue closures
TARGETS = {'Minor': 30, 'Major': 40, 'Critical': 30}
BASE_DAYS = {'Minor': 18, 'Major': 32, 'Critical': 45}

START = datetime.date(2024, 7, 1)
N = 240


def weighted_pick(pairs):
    r, cum = random.random(), 0
    for name, p in pairs:
        cum += p
        if r <= cum:
            return name
    return pairs[-1][0]


def main():
    rows = []
    for i in range(N):
        d = START + datetime.timedelta(days=random.randint(0, 729))
        severity = weighted_pick(SEVERITIES)
        category = weighted_pick(CATEGORIES)

        # Closure time improves across the period, modelling a process
        # improvement embedding over time rather than a step change.
        progress = (d - START).days / 730
        mean = BASE_DAYS[severity] * (1.25 - 0.55 * progress)
        closure = max(3, int(random.gauss(mean, BASE_DAYS[severity] * 0.28)))

        # CAPA always raised for Major/Critical; sometimes for Minor
        capa = severity != 'Minor' or random.random() < 0.35
        # Recurrence is markedly lower where a CAPA was raised
        recurred = random.random() < (0.055 if capa else 0.16)

        rows.append({'id': f'DEV-{d.year}-{i+1:03d}', 'date': d.isoformat(),
                     'dept': random.choice(DEPARTMENTS), 'category': category,
                     'severity': severity, 'closure_days': closure, 'capa': capa,
                     'recurred': recurred, 'overdue': closure > TARGETS[severity]})

    rows.sort(key=lambda r: r['date'])

    monthly = collections.defaultdict(lambda: {'n': 0, 'close': [], 'overdue': 0})
    for r in rows:
        m = monthly[r['date'][:7]]
        m['n'] += 1
        m['close'].append(r['closure_days'])
        m['overdue'] += r['overdue']

    with_capa = [r for r in rows if r['capa']]
    no_capa = [r for r in rows if not r['capa']]
    first = [r['closure_days'] for r in rows if r['date'] < '2025-01-01']
    last = [r['closure_days'] for r in rows if r['date'] >= '2026-01-01']

    agg = {
        'monthly': [{'m': m, 'n': v['n'],
                     'avg_close': round(sum(v['close']) / len(v['close']), 1),
                     'overdue': v['overdue']} for m, v in sorted(monthly.items())],
        'by_category': dict(collections.Counter(r['category'] for r in rows).most_common()),
        'by_dept': dict(collections.Counter(r['dept'] for r in rows).most_common()),
        'by_severity': dict(collections.Counter(r['severity'] for r in rows).most_common()),
        'capa_recur': {
            'with_capa': sum(r['recurred'] for r in with_capa) / len(with_capa),
            'no_capa': sum(r['recurred'] for r in no_capa) / len(no_capa)},
        'total': len(rows),
        'closure_first6': round(sum(first) / len(first), 1),
        'closure_last6': round(sum(last) / len(last), 1),
    }

    with open(OUT, 'w') as f:
        json.dump({'rows': rows, 'agg': agg}, f)

    print(f'Wrote {OUT} — {len(rows)} deviations')
    print(f"Closure time: {agg['closure_first6']} days -> {agg['closure_last6']} days")
    print(f"Recurrence with CAPA {agg['capa_recur']['with_capa']*100:.1f}% "
          f"vs without {agg['capa_recur']['no_capa']*100:.1f}%")


if __name__ == '__main__':
    main()
