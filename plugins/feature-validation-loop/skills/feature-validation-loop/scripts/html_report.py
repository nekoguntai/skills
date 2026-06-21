#!/usr/bin/env python3
"""Generate a deterministic standalone HTML report from the canonical ledger."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from urllib.parse import quote

from ledger import REQUIRED_COLUMNS, read_rows, summarize_rows


def safe_text(value: object) -> str:
    return html.escape(str(value), quote=True)


def source_links(value: str) -> str:
    links: list[str] = []
    for raw_part in value.split(";"):
        part = raw_part.strip()
        if not part:
            continue
        lower = part.casefold()
        safe_label = safe_text(part)
        if lower.startswith(("javascript:", "data:", "vbscript:", "file:", "/")) or "://" in lower:
            links.append(f"<span>{safe_label}</span>")
            continue
        if not re.fullmatch(r"[A-Za-z0-9._/@#:+%=-]+", part):
            links.append(f"<span>{safe_label}</span>")
            continue
        href = quote(part, safe="/#?=&%._-:+@")
        links.append(f'<a href="{safe_text(href)}">{safe_label}</a>')
    return "<br>".join(links)


def metric_cards(summary: dict[str, object]) -> str:
    metrics = [
        ("Features", "totalFeatures"),
        ("Tested", "testedFeatures"),
        ("Passed", "passedFeatures"),
        ("Failed", "failedFeatures"),
        ("Open defects", "openDefects"),
        ("Critical", "criticalDefects"),
        ("High", "highDefects"),
        ("Confidence", "confidenceScore"),
    ]
    cards = []
    for label, key in metrics:
        value = summary.get(key, 0)
        suffix = "%" if key == "confidenceScore" else ""
        cards.append(
            '<section class="metric">'
            f"<span>{safe_text(label)}</span>"
            f"<strong>{safe_text(value)}{suffix}</strong>"
            "</section>"
        )
    return "\n".join(cards)


def table(rows: list[dict[str, str]]) -> str:
    header = "".join(f"<th>{safe_text(column)}</th>" for column in REQUIRED_COLUMNS)
    body_rows = []
    for row in rows:
        status = safe_text(row.get("Current Status", ""))
        severity = safe_text(row.get("Max Severity", ""))
        cells = []
        for column in REQUIRED_COLUMNS:
            value = row.get(column, "")
            content = source_links(value) if column == "Source Paths" else safe_text(value)
            cells.append(f"<td>{content}</td>")
        body_rows.append(
            f'<tr data-status="{status}" data-severity="{severity}">'
            + "".join(cells)
            + "</tr>"
        )
    return (
        '<table id="ledger-table">\n'
        f"<thead><tr>{header}</tr></thead>\n"
        f"<tbody>{''.join(body_rows)}</tbody>\n"
        "</table>"
    )


def render_html(rows: list[dict[str, str]], ledger_path: Path) -> str:
    summary = summarize_rows(rows)
    statuses = sorted({row.get("Current Status", "") for row in rows if row.get("Current Status")})
    severities = sorted({row.get("Max Severity", "") for row in rows if row.get("Max Severity")})
    status_options = '<option value="">All statuses</option>' + "".join(
        f'<option value="{safe_text(status)}">{safe_text(status)}</option>' for status in statuses
    )
    severity_options = '<option value="">All severities</option>' + "".join(
        f'<option value="{safe_text(severity)}">{safe_text(severity)}</option>' for severity in severities
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Feature Validation Ledger</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: Canvas; color: CanvasText; }}
    main {{ padding: 24px; }}
    h1 {{ margin: 0 0 6px; font-size: 1.7rem; }}
    .source {{ margin: 0 0 20px; color: color-mix(in srgb, CanvasText 70%, Canvas 30%); }}
    .metrics {{ display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); margin: 20px 0; }}
    .metric {{ border: 1px solid color-mix(in srgb, CanvasText 18%, Canvas 82%); border-radius: 8px; padding: 12px; }}
    .metric span {{ display: block; font-size: .78rem; color: color-mix(in srgb, CanvasText 65%, Canvas 35%); }}
    .metric strong {{ display: block; margin-top: 4px; font-size: 1.35rem; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0; }}
    input, select {{ min-height: 36px; padding: 6px 9px; font: inherit; }}
    input {{ min-width: min(420px, 100%); flex: 1; }}
    .table-wrap {{ overflow: auto; border: 1px solid color-mix(in srgb, CanvasText 18%, Canvas 82%); border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid color-mix(in srgb, CanvasText 14%, Canvas 86%); text-align: left; vertical-align: top; }}
    th {{ position: sticky; top: 0; background: Canvas; z-index: 1; white-space: nowrap; }}
    td {{ min-width: 130px; max-width: 360px; }}
    td:nth-child(1), td:nth-child(3), td:nth-child(12), td:nth-child(13), td:nth-child(16), td:nth-child(18), td:nth-child(20), td:nth-child(21), td:nth-child(22) {{ white-space: nowrap; }}
    a {{ color: LinkText; }}
    .empty {{ padding: 20px; }}
  </style>
</head>
<body>
<main>
  <h1>Feature Validation Ledger</h1>
  <p class="source">Canonical source: <code>{safe_text(ledger_path.as_posix())}</code></p>
  <section class="metrics" aria-label="Ledger metrics">
    {metric_cards(summary)}
  </section>
  <section class="toolbar" aria-label="Filters">
    <input id="search" type="search" placeholder="Search ledger" aria-label="Search ledger">
    <select id="status" aria-label="Filter by status">{status_options}</select>
    <select id="severity" aria-label="Filter by severity">{severity_options}</select>
  </section>
  <section class="table-wrap">
    {table(rows) if rows else '<p class="empty">No feature rows have been recorded yet.</p>'}
  </section>
</main>
<script>
(() => {{
  const search = document.getElementById("search");
  const status = document.getElementById("status");
  const severity = document.getElementById("severity");
  const rows = Array.from(document.querySelectorAll("#ledger-table tbody tr"));
  function applyFilters() {{
    const query = search.value.trim().toLowerCase();
    const selectedStatus = status.value;
    const selectedSeverity = severity.value;
    for (const row of rows) {{
      const matchesQuery = !query || row.textContent.toLowerCase().includes(query);
      const matchesStatus = !selectedStatus || row.dataset.status === selectedStatus;
      const matchesSeverity = !selectedSeverity || row.dataset.severity === selectedSeverity;
      row.hidden = !(matchesQuery && matchesStatus && matchesSeverity);
    }}
  }}
  search?.addEventListener("input", applyFilters);
  status?.addEventListener("change", applyFilters);
  severity?.addEventListener("change", applyFilters);
}})();
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default="docs/feature-validation/feature-validation-ledger.csv")
    parser.add_argument("--output", default="docs/feature-validation/feature-validation-ledger.html")
    args = parser.parse_args()

    ledger_path = Path(args.ledger)
    output_path = Path(args.output)
    rows = read_rows(ledger_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(rows, ledger_path), encoding="utf-8")
    print(f"Wrote HTML report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
