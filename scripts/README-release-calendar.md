# Release calendar maintenance

Run manually weekly; there is no automation. Website Ops runs the script, Researchy verifies official dates on flagged rows, and the Social Media Manager owns news-log.md. Catalog dates are review signals, not official release announcements.

From the repository root, run a dry run (does not write the news log):

```sh
python3 scripts/release_date_diff.py --report tmp/live-report.md
```

The default report is `/workspace/release-calendar/tmp/release-date-diff-<YYYY-MM-DD>.md`. `--report PATH` overrides it. Fetch errors exit 2; successful runs exit 0.

To append reviewed signals to an existing log, use:

```sh
python3 scripts/release_date_diff.py --append --news-log PATH --report tmp/report.md
```

The default log is `/workspace/iron-steel/social/news-log.md`. A missing log is never created. Without `--append`, the log is never written. Duplicate date, product and status combinations are skipped. A disappeared group uses its last tracked catalog date and is identified in the report.

Offline checks use one response JSON file per category (3.json, 68.json, 71.json, 93.json), each containing a `results` list:

```sh
python3 scripts/release_date_diff.py --fixture tmp/tests/fixtures --today 2026-10-15 --report tmp/tests/report.md --append --news-log tmp/tests/news-log.copy.md
```

Category 89 is always skipped, even if configured. `publishedOn` supplies the date; `modifiedOn` is not used.

After Researchy verifies official sources, update `data/release-calendar.json`, including review_date, dates, precision, source details, checked dates and catalog_date as appropriate. Preserve month precision when no exact day is announced. Then run:

```sh
python3 scripts/build_release_calendar.py
```

The builder writes the static HTML and prints the computed `Next:` text, selecting the first exact date on or after the day following review_date. Refresh that line in the homepage release calendar card and update the calendar sitemap lastmod to the review date. Review the resulting diff before publication.
