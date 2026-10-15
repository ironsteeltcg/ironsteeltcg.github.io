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

GRID_CSS = r"""
[hidden]{display:none!important}
#calendar-ui,.release-wrap{--gold-600:#e9a800;--flare-500:#ff5d8f}
#calendar-ui{margin-top:12px}.month-tools{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.month-tools h3{flex:1;margin:0;font-size:19px}.month-tools button,.date-strip{min-height:44px;border:1px solid var(--line);border-radius:12px;background:var(--sheet);color:var(--ink);font:inherit;padding:6px 12px;cursor:pointer}.month-tools button:disabled{color:var(--ink-2);cursor:default;background:var(--panel)}
.month-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));margin:14px 0}.weekday{text-align:center;font-size:12px;padding:8px 0;color:var(--ink-2)}.day{min-width:44px;min-height:48px;border:0;border-radius:12px;background:var(--sheet);color:var(--ink);font:inherit;cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px}.day:hover{background:var(--panel)}.day{position:relative}.day.today{box-shadow:0 0 0 2px var(--sheet),0 0 0 4px var(--mint);z-index:1}.day.release{background:var(--game-color);color:#fff}.day.release.two-games{background:linear-gradient(135deg,var(--game-color) 50%,var(--second-color) 50%)}.day:focus-visible{outline:3px solid var(--ink);outline-offset:4px;z-index:2}.release-count{position:absolute;right:2px;top:1px;min-width:16px;height:16px;border-radius:6px;background:var(--ink);color:#fff;font-size:11px;line-height:16px}.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--game-color)}.pokemon{--game-color:color-mix(in srgb, var(--gold-600), #000 38%)}.one-piece{--game-color:color-mix(in srgb, var(--flare-500), #000 27%)}.lorcana{--game-color:color-mix(in srgb, var(--lav), #000 36%)}.naruto{--game-color:var(--price)}.legend .swatch{display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--game-color)}.legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:12px;margin:12px 0}.legend span{display:inline-flex;gap:6px;align-items:center}.date-strip{display:block;width:100%;text-align:left;margin:10px 0;background:var(--surface)}
.release-wrap{position:fixed;inset:0;z-index:30;display:grid;place-items:center}.release-backdrop{position:absolute;inset:0;background:#ecececd9;backdrop-filter:blur(8px) saturate(0) brightness(1.05)}.release-sheet{position:relative;background:var(--sheet);color:var(--ink);border-radius:22px;box-shadow:var(--sh-2);padding:24px;width:min(720px,calc(100% - 32px));max-height:90dvh;overflow:auto;touch-action:pan-x;animation:sheet-in .2s ease-out}.release-sheet h3{font-size:20px;margin:4px 52px 20px 0}.release-sheet .x{position:absolute;right:12px;top:12px;width:48px;height:48px;border:0;border-radius:50%;background:var(--sheet);box-shadow:var(--sh-1);color:var(--ink);font-size:24px;cursor:pointer}.release-item{border-top:1px solid var(--line);padding:16px 0}.release-item h4{font-size:18px;margin:8px 0}.release-item p{margin:8px 0}.release-item .srcs{font-size:13px}body.sheet-open{overflow:hidden}body.sheet-open .tabbar{display:none}
@keyframes sheet-in{from{transform:translateY(20px);opacity:0}to{transform:none;opacity:1}}
@media(max-width:600px){#calendar-ui{margin-left:-12px;margin-right:-12px}.release-wrap{place-items:end center}.release-sheet{width:calc(100% - 16px);margin-bottom:8px;padding:20px;border-radius:22px}.day{min-height:48px}.month-tools h3{font-size:17px}}
@media(prefers-reduced-motion:reduce){.release-sheet{animation:none;transition:none}}
"""
GRID_JS = r"""
(()=>{'use strict';
const data=JSON.parse(document.getElementById('calendar-data').textContent),ui=document.getElementById('calendar-ui'),grid=document.getElementById('month-grid'),title=document.getElementById('month-title'),wrap=document.getElementById('release-wrap'),sheet=document.getElementById('release-sheet'),items=document.getElementById('release-items'),heading=document.getElementById('release-heading');
const today=new Date(),pad=n=>String(n).padStart(2,'0'),key=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`,todayKey=key(today),min=data.window.from.slice(0,7),max=data.window.to.slice(0,7),games={'Pokémon':'pokemon','One Piece':'one-piece','Lorcana':'lorcana','Naruto':'naruto'},fmt=new Intl.DateTimeFormat('en-US',{month:'long',day:'numeric',year:'numeric'}),monthFmt=new Intl.DateTimeFormat('en-US',{month:'long',year:'numeric'}),date=k=>new Date(k+'T12:00:00');
let month=todayKey.slice(0,7),trigger=null;const clamp=m=>m<min?min:m>max?max:m;month=clamp(month);
const matches=k=>data.rows.flatMap(r=>r.dates.filter(d=>k==='undated'?d.precision==='none':k.endsWith('-tba')?d.precision==='month'&&d.date===k.slice(0,7):d.precision==='day'&&d.date===k).map(d=>({r,d})));
const hash=k=>history.replaceState(null,'','#'+k),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function close(update=true){wrap.hidden=true;document.body.classList.remove('sheet-open');document.querySelector('main').inert=false;document.querySelector('footer').inert=false;if(update)hash(month);if(trigger?.isConnected)trigger.focus({preventScroll:true})}
function open(k,from){const rows=matches(k);if(!rows.length)return;trigger=from||document.querySelector(`[data-date="${k}"]`)||document.getElementById(k==='undated'?'undated-strip':'tba-strip');heading.textContent=k==='undated'?'Date not announced':k.endsWith('-tba')?monthFmt.format(date(k.slice(0,7)+'-01'))+' · date TBA':fmt.format(date(k));items.innerHTML=rows.map(({r,d})=>`<article class="release-item"><span><i class="dot ${games[r.game]}" aria-hidden="true"></i> ${esc(r.game)}</span><h4>${esc(r.product)}</h4><p>${esc(r.type)}</p><span class="status${r.status==='Unconfirmed'?' unv':''}">${esc(r.status)}</span><p>${esc(d.label)}: ${d.precision==='day'?fmt.format(date(d.date)):d.precision==='month'?'Date TBA':'No official date'}</p><span class="srcs"><a href="${esc(r.source_url)}" rel="nofollow noopener" data-gc-event="out-source/${esc(r.id)}" data-gc-title="${esc(r.product)} source">${esc(r.source_name)}</a> · checked ${new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric'}).format(date(r.checked))}</span></article>`).join('');wrap.hidden=false;document.body.classList.add('sheet-open');document.querySelector('main').inert=true;document.querySelector('footer').inert=true;hash(k);document.getElementById('release-close').focus();}
function render(){title.textContent=monthFmt.format(date(month+'-01'));document.getElementById('month-prev').disabled=month===min;document.getElementById('month-next').disabled=month===max;grid.innerHTML=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(x=>`<div role="columnheader" class="weekday">${x}</div>`).join('');const first=date(month+'-01'),count=new Date(first.getFullYear(),first.getMonth()+1,0).getDate();for(let i=0;i<first.getDay();i++)grid.insertAdjacentHTML('beforeend','<div aria-hidden="true"></div>');for(let n=1;n<=count;n++){let k=month+'-'+pad(n),rows=matches(k),b=document.createElement('button');b.className='day'+(k===todayKey?' today':'');b.dataset.date=k;b.setAttribute('aria-label',fmt.format(date(k))+', '+(rows.length?rows.length+' release'+(rows.length===1?'':'s'):'no releases'));if(k===todayKey)b.setAttribute('aria-current','date');b.tabIndex=k===(month===todayKey.slice(0,7)?todayKey:month+'-01')?0:-1;const releaseGames=[...new Set(rows.map(x=>games[x.r.game]))];if(rows.length){b.classList.add("release",releaseGames[0]);if(releaseGames.length>1){b.classList.add("two-games");const swatch=document.querySelector(".legend ."+releaseGames[1]);b.style.setProperty("--second-color",getComputedStyle(swatch).backgroundColor)}}b.innerHTML=`<span class="date-number">${n}</span>${rows.length>1?`<span class="release-count" aria-hidden="true">${rows.length}</span>`:""}`;b.onclick=()=>open(k,b);b.onfocus=()=>grid.querySelectorAll('button').forEach(x=>x.tabIndex=x===b?0:-1);b.onkeydown=e=>{let step={ArrowRight:1,ArrowLeft:-1,ArrowDown:7,ArrowUp:-7}[e.key];if(!step)return;e.preventDefault();let next=date(k);next.setDate(next.getDate()+step);let nk=key(next);if(nk.slice(0,7)<min||nk.slice(0,7)>max)return;if(nk.slice(0,7)!==month){month=nk.slice(0,7);render();hash(month)}grid.querySelector(`[data-date="${nk}"]`)?.focus()};grid.append(b)}const cells=[...grid.children];grid.replaceChildren();for(let i=0;i<cells.length;i+=7){let row=document.createElement('div');row.setAttribute('role','row');row.style.display='contents';cells.slice(i,i+7).forEach(c=>{if(c.classList.contains('weekday'))row.append(c);else{let cell=document.createElement('div');cell.setAttribute('role','gridcell');cell.style.display='contents';cell.append(c);row.append(cell)}});grid.append(row)}let tba=matches(month+'-tba'),t=document.getElementById('tba-strip');t.hidden=!tba.length;t.textContent='This month, date TBA · '+tba.map(x=>x.r.game+' — '+x.r.product).join(' · ');t.onclick=()=>open(month+'-tba',t);}
function move(n){let d=date(month+'-01');d.setMonth(d.getMonth()+n);month=clamp(key(d).slice(0,7));render();hash(month)}
document.getElementById('month-prev').onclick=()=>move(-1);document.getElementById('month-next').onclick=()=>move(1);document.getElementById('month-today').onclick=()=>{month=clamp(todayKey.slice(0,7));render();hash(month)};document.getElementById('undated-strip').onclick=e=>open('undated',e.currentTarget);document.getElementById('release-close').onclick=()=>close();document.querySelector('.release-backdrop').onclick=()=>close();
document.addEventListener('keydown',e=>{if(wrap.hidden)return;if(e.key==='Escape'){e.preventDefault();close()}if(e.key==='Tab'){let a=[...sheet.querySelectorAll('button,a[href]')],i=a.indexOf(document.activeElement);e.preventDefault();a[(i+(e.shiftKey?-1:1)+a.length)%a.length].focus()}});
let start=null;sheet.addEventListener('pointerdown',e=>{if(e.target.closest('button,a'))return;start=e.clientY;sheet.setPointerCapture(e.pointerId)});sheet.addEventListener('pointerup',e=>{if(start!==null&&e.clientY-start>80)close();start=null});sheet.addEventListener('pointercancel',()=>start=null);
function restore(){if(!wrap.hidden)close(false);let k=location.hash.slice(1);if(/^\d{4}-\d{2}(?:-\d{2}|-tba)?$/.test(k))month=clamp(k.slice(0,7));render();if(k==='undated'||/^\d{4}-\d{2}-(?:\d{2}|tba)$/.test(k))open(k);else hash(month)}ui.parentElement.hidden=false;restore();addEventListener('hashchange',restore);
})();
"""
GRID_MARKUP = r"""<h2>Calendar</h2><div id="calendar-ui"><div class="month-tools"><h3 id="month-title" aria-live="polite"></h3><button id="month-prev" aria-label="Previous month">&lt;</button><button id="month-today">Today</button><button id="month-next" aria-label="Next month">&gt;</button></div><div class="legend" aria-label="Games"><span><i class="swatch pokemon" aria-hidden="true"></i>Pokémon</span><span><i class="swatch one-piece" aria-hidden="true"></i>One Piece</span><span><i class="swatch lorcana" aria-hidden="true"></i>Lorcana</span><span><i class="swatch naruto" aria-hidden="true"></i>Naruto</span></div><button class="date-strip" id="tba-strip" hidden></button><div id="month-grid" class="month-grid" role="grid" aria-labelledby="month-title"></div><button class="date-strip" id="undated-strip">Date not announced · One Piece — OP18 release event cards</button></div>"""
GRID_MODAL = r"""<div id="release-wrap" class="release-wrap" hidden><div class="release-backdrop"></div><section id="release-sheet" class="release-sheet" role="dialog" aria-modal="true" aria-labelledby="release-heading"><button class="x" id="release-close" aria-label="Close">×</button><h3 id="release-heading"></h3><div id="release-items"></div></section></div>"""

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
    head += '<style>' + template.split('<style>')[1].split('</style>')[0] + CALENDAR_CSS + GRID_CSS + '</style></head><body><main>\n'
    top = template.split('<div class="top">')[1].split('</div>')[0]
    body = '<div class="top">' + top.replace('Free collection trackers', 'TCG release calendar') + '</div>\n'
    body += '<h1>TCG release and restock calendar</h1><p class="answer">This calendar tracks upcoming Pokémon, One Piece TCG, Disney Lorcana and Bandai Naruto TCG releases and retailer restocks, with sources and dates checked.</p>'
    body += f'<p>Last updated: {day(data["review_date"], True)}</p><p>Bookmark this page and check back weekly.</p>\n<h2>Next 30 days</h2><ul>'
    exact = sorted((dt.date.fromisoformat(d['date']), i, j, r, d) for i, r in enumerate(data['rows']) if r['status'] != 'Unconfirmed' for j, d in enumerate(r['dates']) if d['precision'] == 'day')
    for date, _, _, row, label in exact:
        if review <= date <= review + dt.timedelta(days=30):
            body += f'<li>{day(date.isoformat())}: {e(row["product"])} ({e(row["game"])}) — {e(label["label"])}</li>'
    body += '</ul><h2>All releases</h2>'
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
    body = body.replace('<section class="calendar-panel"><h2>Next 30 days', '<section class="calendar-panel" hidden>' + GRID_MARKUP + '</section><section class="calendar-panel"><h2>Next 30 days')
    embedded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    body = body.replace('</body>', tabbar + GRID_MODAL + '<script type="application/json" id="calendar-data">' + embedded + '</script><script>' + GRID_JS + '</script>\n</body>')
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
