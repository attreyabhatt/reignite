"""Build a private, offline SEO dashboard from baseline data and optional GSC Pages CSVs.

Use ordinary, un-compared exports with Top pages, Clicks, Impressions, CTR, Position.
python scripts/seo_report.py --current pages.csv --previous prior-pages.csv
"""
import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]


def aggregate(path):
    grouped = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            url = row.get("Top pages") or row.get("Page") or row.get("URL")
            if not url:
                raise ValueError("Use a Pages CSV with a Top pages, Page or URL column")
            parsed = urlsplit(url)
            if parsed.hostname not in {"tryagaintext.com", "www.tryagaintext.com"}:
                raise ValueError("Only TryAgainText page exports are supported")
            key = parsed.path
            if key == '/situations/what-to-text-after-a-date/':
                key = '/situations/what-to-text-after-first-date/'
            item = grouped.setdefault(key, {"path": key, "clicks": 0, "impressions": 0, "position_sum": 0})
            clicks = float(row["Clicks"].replace(",", ""))
            impressions = float(row["Impressions"].replace(",", ""))
            item["clicks"] += clicks
            item["impressions"] += impressions
            item["position_sum"] += float(row["Position"]) * impressions
    for item in grouped.values():
        item["position"] = round(item.pop("position_sum") / max(item["impressions"], 1), 2)
    return grouped


def build(current=None, previous=None):
    baseline = json.loads((ROOT / 'marketing/seo-baseline-2026-10-27.json').read_text())
    if current:
        latest = aggregate(current)
        prior = aggregate(previous) if previous else {}
        baseline['pages'] = [{**latest.get(key, {"path": key, "clicks": 0, "impressions": 0, "position": 0}),
                              "previous_clicks": prior.get(key, {}).get('clicks', 0),
                              "previous_impressions": prior.get(key, {}).get('impressions', 0)}
                             for key in latest.keys() | prior.keys()]
        baseline['page_export'] = str(current.name)
    template = (ROOT / 'scripts/seo_dashboard.html').read_text(encoding='utf-8')
    return template.replace('__DATA__', json.dumps(baseline).replace('<', '\\u003c'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current', type=Path)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / '.seo-audit/dashboard.html')
    args = parser.parse_args()
    if args.previous and not args.current:
        parser.error('--previous requires --current')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build(args.current, args.previous), encoding='utf-8')
    print(args.output.resolve())
