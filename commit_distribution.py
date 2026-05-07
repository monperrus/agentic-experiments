#!/usr/bin/env python3
"""
Compute distribution of number of commits per developer on GitHub
for 2023, 2024, and 2025 using GH Archive data.

GH Archive: https://www.gharchive.org/
Data URL: https://data.gharchive.org/YYYY-MM-DD-H.json.gz
"""

import gzip
import json
import requests
import statistics
from collections import defaultdict
from io import BytesIO

# Sample dates: 2 days per month spread across the year (1st and 15th)
# Using hour 12 (noon UTC) for each day
SAMPLE_DAYS = [
    (1, 1), (1, 15),
    (2, 1), (2, 15),
    (3, 1), (3, 15),
    (4, 1), (4, 15),
    (5, 1), (5, 15),
    (6, 1), (6, 15),
    (7, 1), (7, 15),
    (8, 1), (8, 15),
    (9, 1), (9, 15),
    (10, 1), (10, 15),
    (11, 1), (11, 15),
    (12, 1), (12, 15),
]
SAMPLE_HOUR = 12
YEARS = [2023, 2024, 2025]


def fetch_gharchive_hour(year, month, day, hour):
    """Fetch and parse a single GH Archive hour file."""
    url = f"https://data.gharchive.org/{year}-{month:02d}-{day:02d}-{hour}.json.gz"
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            print(f"  Skipping {url}: HTTP {resp.status_code}")
            return {}
        data = BytesIO(resp.content)
        commits_by_author = defaultdict(int)
        with gzip.open(data, 'rt', encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    event = json.loads(line)
                    if event.get('type') != 'PushEvent':
                        continue
                    actor = event.get('actor', {}).get('login', '')
                    if not actor:
                        continue
                    payload = event.get('payload', {})
                    n_commits = payload.get('size', 0)
                    if n_commits > 0:
                        commits_by_author[actor] += n_commits
                except (json.JSONDecodeError, KeyError):
                    continue
        print(f"  Processed {url}: {sum(commits_by_author.values())} commits, {len(commits_by_author)} devs")
        return dict(commits_by_author)
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return {}


def compute_stats(values):
    """Compute distribution stats for a list of integer values."""
    if not values:
        return {}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    total = sum(sorted_vals)
    mean_val = total / n
    median_val = statistics.median(sorted_vals)
    p90_idx = int(0.9 * n)
    p90_val = sorted_vals[min(p90_idx, n - 1)]
    p75_idx = int(0.75 * n)
    p75_val = sorted_vals[min(p75_idx, n - 1)]
    p99_idx = int(0.99 * n)
    p99_val = sorted_vals[min(p99_idx, n - 1)]

    # Histogram buckets
    buckets = [1, 2, 3, 5, 10, 20, 50, 100, 500, 1000, float('inf')]
    hist = defaultdict(int)
    for v in sorted_vals:
        for b in buckets:
            if v <= b:
                hist[b] += 1
                break

    return {
        'n': n,
        'total_commits': total,
        'mean': round(mean_val, 2),
        'median': median_val,
        'p75': p75_val,
        'p90': p90_val,
        'p99': p99_val,
        'min': sorted_vals[0],
        'max': sorted_vals[-1],
        'histogram': dict(hist),
    }


def main():
    results = {}

    for year in YEARS:
        print(f"\n=== Processing year {year} ===")
        all_commits = defaultdict(int)

        for month, day in SAMPLE_DAYS:
            # Skip future dates (2025 data - all should be available since current date is 2026)
            data = fetch_gharchive_hour(year, month, day, SAMPLE_HOUR)
            for author, count in data.items():
                all_commits[author] += count

        values = list(all_commits.values())
        stats = compute_stats(values)
        results[year] = stats
        print(f"\nYear {year} stats:")
        print(f"  Developers sampled: {stats['n']:,}")
        print(f"  Total commits in sample: {stats['total_commits']:,}")
        print(f"  Mean commits per dev: {stats['mean']}")
        print(f"  Median commits per dev: {stats['median']}")
        print(f"  75th percentile: {stats['p75']}")
        print(f"  90th percentile: {stats['p90']}")
        print(f"  99th percentile: {stats['p99']}")
        print(f"  Max: {stats['max']}")

    # Print summary table
    print("\n\n=== SUMMARY TABLE ===")
    print(f"{'Metric':<25} {'2023':>10} {'2024':>10} {'2025':>10}")
    print("-" * 55)
    for key, label in [
        ('n', 'Developers sampled'),
        ('total_commits', 'Total commits'),
        ('mean', 'Mean'),
        ('median', 'Median'),
        ('p75', '75th percentile'),
        ('p90', '90th percentile'),
        ('p99', '99th percentile'),
        ('max', 'Max'),
    ]:
        row = f"{label:<25}"
        for year in YEARS:
            val = results[year].get(key, 'N/A')
            if isinstance(val, float):
                row += f" {val:>10.1f}"
            elif isinstance(val, int):
                row += f" {val:>10,}"
            else:
                row += f" {str(val):>10}"
        print(row)

    # Histogram
    print("\n=== HISTOGRAM (commits per dev in sample) ===")
    bucket_labels = {
        1: '= 1', 2: '2', 3: '3', 5: '4-5', 10: '6-10',
        20: '11-20', 50: '21-50', 100: '51-100',
        500: '101-500', 1000: '501-1000', float('inf'): '1000+'
    }
    print(f"{'Bucket':<12} {'2023':>12} {'2024':>12} {'2025':>12}")
    print("-" * 50)
    for b in [1, 2, 3, 5, 10, 20, 50, 100, 500, 1000, float('inf')]:
        label = bucket_labels[b]
        row = f"{label:<12}"
        for year in YEARS:
            count = results[year]['histogram'].get(b, 0)
            total = results[year]['n']
            pct = 100.0 * count / total if total > 0 else 0
            row += f" {count:>6,} ({pct:4.1f}%)"
        print(row)

    return results


if __name__ == '__main__':
    main()
