#!/usr/bin/env python3
"""Manually flag catalog changes for official-source review."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SKIP_CATEGORIES = frozenset({89})


def escaped(value):
    return str(value).replace('|', r'\|').replace('\n', ' ').replace('\r', ' ')


def cells(line):
    # Split only unescaped table separators.
    import re
    return [part.strip() for part in re.split(r'(?<!\\)\|', line.strip())[1:-1]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--news-log', type=Path, default=Path('/workspace/iron-steel/social/news-log.md'))
    parser.add_argument('--append', action='store_true')
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--today', type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args()
    data = json.loads((ROOT / 'data/release-calendar.json').read_text())
    items = []
    try:
        for game, category in data['categories'].items():
            if int(category) in SKIP_CATEGORIES:
                continue
            url = f'https://tcgcsv.com/tcgplayer/{category}/groups'
            if args.fixture:
                response = json.loads((args.fixture / f'{category}.json').read_text())
            else:
                request = urllib.request.Request(url, headers={'User-Agent': 'iron-steel-binder'})
                with urllib.request.urlopen(request, timeout=60) as stream:
                    response = json.load(stream)
            groups = {int(g['groupId']): g for g in response['results']}
            tracked = {int(r['tcgcsv_group']): r for r in data['rows'] if r['game'] == game and r.get('tcgcsv_group') is not None}
            for gid, row in tracked.items():
                group = groups.get(gid)
                catalog = (group.get('publishedOn') or '')[:10] if group else row['catalog_date']
                if group is None or catalog != row['catalog_date']:
                    items.append([catalog, game, group['name'] if group else row['product'], row['type'], 'Catalog change (needs official source)', url, args.today.isoformat(), f'previous: {row["catalog_date"]}' if group else 'Group disappeared; date is the last tracked catalog date'])
            for gid, group in groups.items():
                catalog = (group.get('publishedOn') or '')[:10]
                if gid not in tracked and gid not in data['ignore_groups']['ids'] and data['window']['from'] <= catalog <= data['window']['to']:
                    items.append([catalog, game, group['name'], 'Unknown', 'New catalog entry (needs official source)', url, args.today.isoformat(), 'New group'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Fetch error: {exc}', file=sys.stderr)
        return 2
    report = args.report or Path(f'/workspace/release-calendar/tmp/release-date-diff-{args.today.isoformat()}.md')
    text = f'# Release date diff — {args.today.isoformat()}\n\n'
    if items:
        text += '| date | game | product | type | status | source URL | date checked | detail |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n'
        text += ''.join('| ' + ' | '.join(map(escaped, item)) + ' |\n' for item in items)
    else:
        text += 'No changes\n'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(text)
    print(f'{len(items)} flagged item(s); report: {report}')
    if args.append:
        if not args.news_log.is_file():
            print(f'News log missing; skipping append: {args.news_log}')
        else:
            existing = args.news_log.read_text()
            keys = {(c[0], c[2], c[4]) for line in existing.splitlines() if len(c := cells(line)) == 7}
            additions = []
            for item in items:
                values = list(map(escaped, item[:7]))
                key = (values[0], values[2], values[4])
                if key not in keys:
                    additions.append('| ' + ' | '.join(values) + ' |\n')
                    keys.add(key)
            if additions:
                with args.news_log.open('a') as stream:
                    if existing and not existing.endswith('\n'):
                        stream.write('\n')
                    stream.writelines(additions)
            print(f'Appended {len(additions)} row(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
