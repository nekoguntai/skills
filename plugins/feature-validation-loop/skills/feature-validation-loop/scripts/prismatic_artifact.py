#!/usr/bin/env python3
"""Generate Prismatic Thread artifacts from the canonical validation ledger."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from ledger import REQUIRED_COLUMNS, read_rows, summarize_rows


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def yaml_scalar(value: object) -> str:
    text = str(value)
    if text == "":
        return '""'
    if all(char.isalnum() or char in "._-/:" for char in text):
        return text
    return json.dumps(text)


def yaml_list(values: list[str], indent: int = 0) -> str:
    prefix = " " * indent
    return "\n".join(f"{prefix}- {yaml_scalar(value)}" for value in values)


def markdown_cell(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = html.escape(text, quote=False)
    return text.replace("\\", "\\\\").replace("|", "\\|").strip()


def defect_is_closed(row: dict[str, str]) -> bool:
    if row.get("Current Status") == "waived" or row.get("Fix Status") == "waived":
        return True
    if row.get("Fix Status") == "fixed" and row.get("Current Status") in {"passed", "complete"}:
        return True
    return False


def parse_simple_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    config: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, config)]
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line or line.startswith("- "):
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = value.strip("'\"")
    return config


def artifact_paths(repo_root: Path, config: dict[str, Any], override: str | None) -> tuple[Path, Path]:
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    artifacts_dir = override or paths.get("artifacts") or "docs/artifacts"
    return repo_root / artifacts_dir, repo_root / "docs/feature-validation"


def front_matter(
    artifact_key: str,
    artifact_format: str,
    title: str,
    summary: str,
    ledger_relative: str,
    metrics: dict[str, Any],
    feature_view: str | None = None,
) -> str:
    body = [
        "---",
        "thread: feature-validation-loop",
        "threadTitle: Feature Validation Loop",
        "threadStatus: active",
        "artifactKey: " + artifact_key,
        "type: progress",
        "format: " + artifact_format,
        "title: " + yaml_scalar(title),
        "status: needs_review",
        "summary: " + yaml_scalar(summary),
        "tags:",
        "  - feature-validation",
        "  - qa",
        "relatedFiles:",
        "  - " + yaml_scalar(ledger_relative),
        "metadata:",
        "  workStatus: in_progress",
        "  disposition: committed",
        "  sourcePath: " + yaml_scalar(ledger_relative),
        "  featureValidation:",
        "    schemaVersion: 1",
        "    ledgerPath: " + yaml_scalar(ledger_relative),
    ]
    if feature_view:
        body.append("    view: " + yaml_scalar(feature_view))
    for key in [
        "totalFeatures",
        "discoveredFeatures",
        "testDesignedFeatures",
        "testedFeatures",
        "passedFeatures",
        "failedFeatures",
        "openDefects",
        "criticalDefects",
        "highDefects",
        "uxDefects",
        "waivedDefects",
        "confidenceScore",
    ]:
        body.append(f"    {key}: {int(metrics.get(key, 0) or 0)}")
    body.extend(
        [
            "    maxSeverity: " + yaml_scalar(metrics.get("maxSeverity", "none")),
            "    lastTestedAt: " + yaml_scalar(metrics.get("lastTestedAt", "")),
            "---",
            "",
        ]
    )
    return "\n".join(body)


def markdown_summary(rows: list[dict[str, str]], ledger_relative: str) -> str:
    metrics = summarize_rows(rows)
    summary = f"{metrics['testedFeatures']} of {metrics['totalFeatures']} features tested; {metrics['openDefects']} open defects."
    lines = [
        front_matter(
            "feature-validation-ledger",
            "markdown",
            "Feature Validation Ledger",
            summary,
            ledger_relative,
            metrics,
        ),
        "# Feature Validation Ledger",
        "",
        f"Canonical CSV: `{ledger_relative}`",
        "",
        "## Coverage Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    metric_labels = [
        ("Total features", "totalFeatures"),
        ("Discovered features", "discoveredFeatures"),
        ("Test-designed features", "testDesignedFeatures"),
        ("Tested features", "testedFeatures"),
        ("Passed features", "passedFeatures"),
        ("Failed features", "failedFeatures"),
        ("Open defects", "openDefects"),
        ("Critical defects", "criticalDefects"),
        ("High defects", "highDefects"),
        ("UX defects", "uxDefects"),
        ("Waived defects", "waivedDefects"),
        ("Confidence score", "confidenceScore"),
    ]
    for label, key in metric_labels:
        value = metrics[key]
        suffix = "%" if key == "confidenceScore" else ""
        lines.append(f"| {label} | {value}{suffix} |")
    lines.extend(
        [
            f"| Max severity | {metrics['maxSeverity']} |",
            f"| Last tested | {metrics['lastTestedAt'] or 'not recorded'} |",
            "",
            "## Open Critical Or High Items",
            "",
        ]
    )
    open_rows = [
        row
        for row in rows
        if row.get("Max Severity") in {"critical", "high"}
        and not defect_is_closed(row)
    ]
    if open_rows:
        lines.extend(["| Feature ID | Feature | Severity | Notes |", "| --- | --- | --- | --- |"])
        for row in open_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        markdown_cell(row.get("Feature ID", "")),
                        markdown_cell(row.get("Feature Name", "")),
                        markdown_cell(row.get("Max Severity", "")),
                        markdown_cell(row.get("Reproduction Notes") or row.get("Notes") or ""),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No open critical or high validation defects are recorded.")
    lines.extend(
        [
            "",
            "## Blind Spots",
            "",
            "Review rows with low confidence, blocked execution, waived tests, or missing runtime evidence before declaring broader coverage.",
        ]
    )
    return "\n".join(lines) + "\n"


def static_html_artifact(rows: list[dict[str, str]], ledger_relative: str) -> str:
    metrics = summarize_rows(rows)
    summary = f"{metrics['testedFeatures']} of {metrics['totalFeatures']} features tested; {metrics['openDefects']} open defects."
    metric_rows = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(metrics[key])}{'%' if key == 'confidenceScore' else ''}</td></tr>"
        for label, key in [
            ("Total features", "totalFeatures"),
            ("Tested features", "testedFeatures"),
            ("Passed features", "passedFeatures"),
            ("Failed features", "failedFeatures"),
            ("Open defects", "openDefects"),
            ("Critical defects", "criticalDefects"),
            ("High defects", "highDefects"),
            ("Confidence score", "confidenceScore"),
        ]
    )
    header = "".join(f"<th>{escape(column)}</th>" for column in REQUIRED_COLUMNS)
    table_rows = []
    for row in rows:
        cells = "".join(f"<td>{escape(row.get(column, ''))}</td>" for column in REQUIRED_COLUMNS)
        table_rows.append(f"<tr>{cells}</tr>")
    body = f"""
<section class="feature-validation-ledger">
  <h1>Feature Validation Ledger</h1>
  <p>Canonical CSV: <code>{escape(ledger_relative)}</code></p>
  <h2>Coverage Summary</h2>
  <table><tbody>{metric_rows}</tbody></table>
  <h2>Ledger Rows</h2>
  <table>
    <thead><tr>{header}</tr></thead>
    <tbody>{''.join(table_rows)}</tbody>
  </table>
</section>
"""
    return (
        front_matter(
            "feature-validation-ledger-html",
            "html",
            "Feature Validation Ledger HTML View",
            summary,
            ledger_relative,
            metrics,
            "html",
        )
        + body
    )


def contribution_payload(
    project_slug: str,
    repository_url: str | None,
    default_branch: str,
    ledger_relative: str,
    markdown_body: str,
    html_body: str | None,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    metrics = summarize_rows(rows)
    artifacts = [
        {
            "key": "feature-validation-ledger",
            "type": "progress",
            "format": "markdown",
            "title": "Feature Validation Ledger",
            "status": "needs_review",
            "summary": f"{metrics['testedFeatures']} of {metrics['totalFeatures']} features tested; {metrics['openDefects']} open defects.",
            "body": markdown_body.split("---\n", 2)[-1].strip(),
            "tags": ["feature-validation", "qa"],
            "relatedFiles": [ledger_relative],
            "metadata": {
                "workStatus": "in_progress",
                "disposition": "committed",
                "sourcePath": ledger_relative,
                "featureValidation": {
                    "schemaVersion": 1,
                    "ledgerPath": ledger_relative,
                    **metrics,
                },
            },
        }
    ]
    if html_body:
        artifacts.append(
            {
                "key": "feature-validation-ledger-html",
                "type": "progress",
                "format": "html",
                "title": "Feature Validation Ledger HTML View",
                "status": "needs_review",
                "summary": artifacts[0]["summary"],
                "body": html_body.split("---\n", 2)[-1].strip(),
                "tags": ["feature-validation", "qa"],
                "relatedFiles": [ledger_relative],
                "metadata": {
                    "workStatus": "in_progress",
                    "disposition": "committed",
                    "sourcePath": ledger_relative,
                    "featureValidation": {
                        "schemaVersion": 1,
                        "view": "html",
                        "ledgerPath": ledger_relative,
                        **metrics,
                    },
                },
            }
        )
    payload: dict[str, Any] = {
        "projectSlug": project_slug,
        "thread": {
            "key": "feature-validation-loop",
            "title": "Feature Validation Loop",
            "status": "active",
        },
        "artifacts": artifacts,
        "events": [
            {
                "kind": "artifact_submitted",
                "title": "Feature validation artifact generated",
                "message": "Feature validation artifacts were generated from the canonical CSV ledger.",
                "metadata": {"source": "feature-validation-loop"},
            }
        ],
    }
    if repository_url:
        payload["repository"] = {"url": repository_url, "branch": default_branch}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default="docs/feature-validation/feature-validation-ledger.csv")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--artifacts-dir")
    parser.add_argument("--write-html", action="store_true")
    parser.add_argument("--write-contribution", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    ledger_path = (repo_root / args.ledger).resolve() if not Path(args.ledger).is_absolute() else Path(args.ledger)
    ledger_relative = ledger_path.relative_to(repo_root).as_posix()
    rows = read_rows(ledger_path)
    config = parse_simple_config(repo_root / ".prismatic-thread.yaml")
    artifacts_dir, feature_dir = artifact_paths(repo_root, config, args.artifacts_dir)

    if config:
        output_dir = artifacts_dir
        markdown_path = output_dir / "feature-validation-loop.md"
    else:
        output_dir = feature_dir
        markdown_path = output_dir / "feature-validation-summary.md"

    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_body = markdown_summary(rows, ledger_relative)
    markdown_path.write_text(markdown_body, encoding="utf-8")
    print(f"Wrote Markdown artifact: {markdown_path}")

    html_body = None
    if args.write_html and config:
        html_body = static_html_artifact(rows, ledger_relative)
        html_path = artifacts_dir / "feature-validation-ledger.html"
        html_path.write_text(html_body, encoding="utf-8")
        print(f"Wrote HTML artifact: {html_path}")

    if args.write_contribution:
        project_slug = str(config.get("projectSlug") or repo_root.name)
        repository_url = str(config.get("repositoryUrl") or "") or None
        default_branch = str(config.get("defaultBranch") or "main")
        payload = contribution_payload(
            project_slug,
            repository_url,
            default_branch,
            ledger_relative,
            markdown_body,
            html_body,
            rows,
        )
        contribution_path = feature_dir / "prismatic-thread-contribution.json"
        feature_dir.mkdir(parents=True, exist_ok=True)
        contribution_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote contribution payload: {contribution_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
