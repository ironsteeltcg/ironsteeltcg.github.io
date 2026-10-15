#!/usr/bin/env python3
"""Rebuild the static calendar using the shared tracker components."""
import argparse
import datetime as dt
import html
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://ironsteeltcg.github.io/tcg-release-calendar/'
TITLE = 'TCG Release & Restock Calendar | Iron & Steel TCG'
DESCRIPTION = 'Upcoming Pokémon, One Piece, Disney Lorcana and Naruto TCG releases and sourced restocks. Check dates, sources and buying links. Updated weekly.'
FAQ = [
    ('When does Hyperia City release?', 'Hobby stores Oct 16, 2026; wide retail Oct 23, 2026, per Ravensburger, checked Oct 15, 2026.'),
    ('When do One Piece EB05 and OP18 release?', 'EB05 Oct 30, 2026; OP18 Nov 20, 2026, per Bandai; OP18 release event cards have no official date yet.'),
    ("When does Bandai's Naruto TCG launch?", "June 2027 worldwide, per Bandai's Oct 10, 2026 announcement; no exact day announced."),
    ('When is the next Pokémon restock?', 'No verified restock date listed; restocks are listed only with a retailer notice and check time.'),
    ('How often is this calendar updated?', 'Weekly, and whenever a sourced date changes.'),
]
e = html.escape


# Reuse the guide palette, table rules and floating panel depth.
CALENDAR_CSS = """
.calendar-panel{background:var(--sheet);border:1px solid var(--line);border-radius:20px;box-shadow:var(--sh-1);padding:20px;margin:14px 0}
.calendar-panel>h2:first-child{margin-top:0}
.status{display:inline-flex;padding:3px 8px;border-radius:999px;font-size:11px;font-weight:800;background:var(--mint);color:var(--ink)}
.status.unv{background:var(--panel);color:var(--ink-2);border:1px solid var(--line);margin:0;text-transform:none;letter-spacing:normal}
.tw table td:nth-child(5){color:var(--ink-2);font-weight:400}
"""

def day(value, full=False):
    d = dt.date.fromisoformat(value)
    return f'{d.strftime("%B" if full else "%b")} {d.day}, {d.year}'


def date_text(value):
    if value['precision'] == 'month':
        return dt.date.fromisoformat(value['date'] + '-01').strftime('%B %Y')
    if value['precision'] == 'day':
        return day(value['date'])
    return value.get('text', 'No official date')


def real_buy_link(row):
    return row.get('stocked') is True and isinstance(row.get('store_url'), str) and bool(row['store_url'])


def build(data_path=ROOT / 'data/release-calendar.json', output=ROOT / 'tcg-release-calendar/index.html'):
    data = json.loads(data_path.read_text())
    show_buy = any(real_buy_link(row) for row in data['rows'])
    review = dt.date.fromisoformat(data['review_date'])
    template = (ROOT / 'free-pokemon-collection-tracker-no-app/index.html').read_text()
    head = template.split('<script type="application/ld+json">')[0]
    old_title = re.search(r'<title>(.*?)</title>', head).group(1)
    old_desc = re.search(r'<meta name="description" content="(.*?)">', head).group(1)
    head = head.replace(old_title, e(TITLE)).replace(old_desc, e(DESCRIPTION))
    head = head.replace('https://ironsteeltcg.github.io/free-pokemon-collection-tracker-no-app/', URL)
    graph = [
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Pokémon TCG binders', 'item': 'https://ironsteeltcg.github.io/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'TCG release calendar', 'item': URL}]},
        {'@type': 'WebPage', 'name': TITLE, 'url': URL, 'dateModified': data['review_date'], 'publisher': {'@id': 'https://ironsteeltcg.github.io/#org'}},
        {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in FAQ]},
    ]
    head += '<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False) + '</script>\n'
    head += '<style>' + template.split('<style>')[1].split('</style>')[0] + CALENDAR_CSS + '</style></head><body><main>\n'
    top = template.split('<div class="top">')[1].split('</div>')[0]
    body = '<div class="top">' + top.replace('Free collection trackers', 'TCG release calendar') + '</div>\n'
    body += '<h1>TCG release and restock calendar</h1><p class="answer">This calendar tracks upcoming Pokémon, One Piece TCG, Disney Lorcana and Bandai Naruto TCG releases and retailer restocks, with sources and dates checked.</p>'
    body += f'<p>Last updated: {day(data["review_date"], True)}</p><p>Bookmark this page and check back weekly.</p>\n<h2>Next 30 days</h2><ul>'
    exact = sorted((dt.date.fromisoformat(d['date']), i, j, r, d) for i, r in enumerate(data['rows']) if r['status'] != 'Unconfirmed' for j, d in enumerate(r['dates']) if d['precision'] == 'day')
    for date, _, _, row, label in exact:
        if review <= date <= review + dt.timedelta(days=30):
            body += f'<li>{day(date.isoformat())}: {e(row["product"])} ({e(row["game"])}) — {e(label["label"])}</li>'
    body += '</ul><h2>Monthly releases by game</h2>'
    columns = ['Date', 'Product', 'Type', 'Status', 'Source']
    if show_buy:
        columns.append('Where to buy')
    for game in ('Pokémon', 'One Piece', 'Lorcana', 'Naruto'):
        body += f'<h3>{game}</h3><div class="tw"><table class="cmp"><thead><tr>' + ''.join(f'<th scope="col">{c}</th>' for c in columns) + '</tr></thead><tbody>'
        for row in data['rows']:
            if row['game'] != game:
                continue
            dates = '<br>'.join((e(d['label']) + ': ' if len(row['dates']) > 1 else '') + e(date_text(d)) + (' (released)' if d['precision'] == 'day' and dt.date.fromisoformat(d['date']) < review else '') for d in row['dates'])
            source = f'<span class="srcs"><a href="{e(row["source_url"])}" rel="nofollow noopener" data-gc-event="out-source/{e(row["id"])}" data-gc-title="{e(row["product"])} source">{e(row["source_name"])}</a> · checked {day(row["checked"])}</span>'
            buy = 'Not in our stock' if show_buy else ''
            if real_buy_link(row):
                host = urlparse(row['store_url']).hostname or ''
                event = 'out-tcgplayer-store' if host == 'tcgplayer.com' or host.endswith('.tcgplayer.com') else 'out-store'
                buy = f'<a href="{e(row["store_url"])}" rel="noopener" data-gc-event="{event}/{e(row["id"])}" data-gc-title="{e(row["product"])} (release calendar)">In our stock</a>'
            values = [dates, e(row['product']) + '<small class="srcs">' + e(row['region']) + '</small>', e(row['type']), f'<span class="status{" unv" if row["status"] == "Unconfirmed" else ""}">{e(row["status"])}</span>', source, buy]
            body += '<tr>' + ''.join(f'<td data-l="{c}">{v}</td>' for c, v in zip(columns, values)) + '</tr>'
        body += '</tbody></table></div>'
    body += '<h2>Restocks</h2><p>No sourced retailer restocks right now. We only list a restock with the retailer\'s own notice and the time we checked it.</p>'
    body += '<h2>What changed this week</h2><p>First edition of this calendar (Oct 15, 2026). Hyperia City now lists hobby-store and wide-retail dates separately; Into the Inkdark lists prerelease and release separately.</p>'
    body += '<h2>How dates are verified</h2><p>Dates come from official publisher pages and press releases, with the checked date shown. TCGplayer catalog dates (via TCGCSV) are only used to spot changes. Month-only announcements stay month-only; anything without an official date is labeled Unconfirmed.</p><h2>FAQ</h2>'
    body += ''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in FAQ)
    body += '<p class="cta"><a href="../">Pokémon TCG binders</a> · <a href="../cheapest-pokemon-sets-to-complete/">Compare the cheapest Pokémon sets to complete</a></p>\n</main>\n'
    # Wrap each content section without altering its text or heading order.
    content, end = body.split('</main>', 1)
    intro, *sections = content.split('<h2>')
    top_end = intro.index('</div>') + len('</div>')
    intro = intro[:top_end] + '<section class="calendar-panel">' + intro[top_end:] + '</section>'
    body = intro + ''.join('<section class="calendar-panel"><h2>' + section + '</section>' for section in sections) + '</main>' + end
    footer = '<footer>' + template.split('<footer>')[1].split('</footer>')[0]
    body += footer + ' Not affiliated with Bandai, Shueisha, Toei Animation, Disney or Ravensburger. One Piece, Naruto and Disney Lorcana names belong to their owners. Iron &amp; Steel TCG is an unofficial fan site.</footer>\n</body></html>\n'
    tabbar = re.search(r'<nav class="tabbar".*?</nav>', template, re.S).group()
    tabbar = re.sub(r' aria-current="page"', '', tabbar)
    body = body.replace('</body>', tabbar + '\n</body>')
    output.parent.mkdir(exist_ok=True)
    output.write_text(head + body)
    upcoming = next((item for item in exact if item[0] >= review + dt.timedelta(days=1)), None)
    if upcoming:
        date, _, _, row, label = upcoming
        print(f'Next: {row["product"]} ({row["game"]}), {label["label"].lower()} {day(date.isoformat())}')
    else:
        print('Next: No confirmed upcoming date')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data/release-calendar.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'tcg-release-calendar/index.html')
    args = parser.parse_args()
    build(args.data, args.out)
