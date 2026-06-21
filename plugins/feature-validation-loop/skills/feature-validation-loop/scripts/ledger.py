#!/usr/bin/env python3
"""Create, validate, summarize, and upsert the feature validation ledger."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

REQUIRED_COLUMNS = [
    "Feature ID",
    "Feature Name",
    "Surface",
    "Source Paths",
    "User Story",
    "Expected Behavior",
    "Edge Cases",
    "Validation Rules",
    "Dependencies",
    "Assumptions",
    "Test Cases",
    "Execution Status",
    "Current Status",
    "Defect IDs",
    "Defect Count",
    "Max Severity",
    "Reproduction Notes",
    "Fix Status",
    "Verification Notes",
    "Last Tested Date",
    "Last Source Commit",
    "Confidence",
    "Notes",
]

EXECUTION_STATUSES = {"", "not_run", "running", "passed", "failed", "blocked", "waived"}
CURRENT_STATUSES = {
    "",
    "discovered",
    "test_designed",
    "testing",
    "passed",
    "failed",
    "fixing",
    "fixed_pending_retest",
    "waived",
    "blocked",
    "complete",
}
SEVERITIES = {"", "critical", "high", "medium", "low", "ux", "none"}
FIX_STATUSES = {"", "none", "planned", "in_progress", "fixed", "deferred", "waived"}
CONFIDENCES = {"", "high", "medium", "low"}

SEVERITY_RANK = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "ux": 2,
    "low": 1,
    "none": 0,
    "": 0,
}

SURFACE_PREFIXES = [
    (("web", "ui", "screen", "route", "page", "form"), "WEB"),
    (("api", "endpoint", "server", "http", "rpc"), "API"),
    (("cli", "command", "terminal"), "CLI"),
    (("config", "env", "setting", "flag", "option"), "CFG"),
    (("job", "worker", "cron", "queue", "background"), "JOB"),
    (("integration", "external", "webhook", "import", "export"), "INT"),
    (("workflow", "business", "process"), "WF"),
]


class LedgerError(Exception):
    """Raised when ledger validation or mutation fails."""


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise LedgerError(f"Ledger does not exist: {path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise LedgerError(f"Ledger has no header: {path}")
        rows = []
        for row in reader:
            rows.append({column: (row.get(column) or "") for column in reader.fieldnames})
        return rows


def write_rows(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [normalize_row(row) for row in rows]
    normalized.sort(key=sort_key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(normalized)


def normalize_row(row: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for column in REQUIRED_COLUMNS:
        value = row.get(column, "")
        if value is None:
            normalized[column] = ""
        elif isinstance(value, (list, tuple)):
            normalized[column] = "; ".join(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, dict):
            normalized[column] = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            normalized[column] = str(value).strip()
    return normalized


def sort_key(row: dict[str, str]) -> tuple[str, tuple[str, int], str]:
    return (
        row.get("Surface", "").casefold(),
        feature_id_sort(row.get("Feature ID", "")),
        row.get("Feature Name", "").casefold(),
    )


def feature_id_sort(feature_id: str) -> tuple[str, int]:
    match = re.fullmatch(r"FEAT-([A-Z0-9]+)-(\d+)", feature_id.strip())
    if match:
        return (match.group(1), int(match.group(2)))
    return (feature_id.casefold(), 0)


def validate_rows(rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> list[str]:
    errors: list[str] = []
    header = fieldnames if fieldnames is not None else REQUIRED_COLUMNS
    missing = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")

    seen: dict[str, int] = {}
    for index, raw_row in enumerate(rows, start=2):
        row = normalize_row(raw_row)
        feature_id = row["Feature ID"]
        if not feature_id:
            errors.append(f"Row {index}: Feature ID is required")
        elif feature_id in seen:
            errors.append(f"Row {index}: duplicate Feature ID {feature_id} also appears on row {seen[feature_id]}")
        else:
            seen[feature_id] = index

        if row["Execution Status"] not in EXECUTION_STATUSES:
            errors.append(f"Row {index}: invalid Execution Status {row['Execution Status']!r}")
        if row["Current Status"] not in CURRENT_STATUSES:
            errors.append(f"Row {index}: invalid Current Status {row['Current Status']!r}")
        if row["Max Severity"] not in SEVERITIES:
            errors.append(f"Row {index}: invalid Max Severity {row['Max Severity']!r}")
        if row["Fix Status"] not in FIX_STATUSES:
            errors.append(f"Row {index}: invalid Fix Status {row['Fix Status']!r}")
        if row["Confidence"] not in CONFIDENCES:
            errors.append(f"Row {index}: invalid Confidence {row['Confidence']!r}")
        defect_count = 0
        if row["Defect Count"]:
            try:
                defect_count = int(row["Defect Count"])
            except ValueError:
                errors.append(f"Row {index}: Defect Count must be an integer")
            else:
                if defect_count < 0:
                    errors.append(f"Row {index}: Defect Count must be non-negative")
        defect_ids = split_defect_ids(row["Defect IDs"])
        if defect_ids and defect_count != len(defect_ids):
            errors.append(
                f"Row {index}: Defect Count {defect_count} does not match {len(defect_ids)} Defect IDs"
            )
        if defect_count > 0 and not defect_ids:
            errors.append(f"Row {index}: Defect Count is positive but Defect IDs is empty")
        if has_status(row, "blocked") and not row["Reproduction Notes"] and not row["Notes"]:
            errors.append(f"Row {index}: blocked rows require Reproduction Notes or Notes")
        if has_status(row, "waived") and not row["Reproduction Notes"] and not row["Notes"]:
            errors.append(f"Row {index}: waived rows require Reproduction Notes or Notes")
    return errors


def split_defect_ids(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;,\n]+", value) if part.strip()]


def has_status(row: dict[str, str], status: str) -> bool:
    return status in {row["Execution Status"], row["Current Status"], row["Fix Status"]}


def defect_is_closed(row: dict[str, str]) -> bool:
    if row["Current Status"] == "waived" or row["Fix Status"] == "waived":
        return True
    if row["Fix Status"] == "fixed" and row["Current Status"] in {"passed", "complete"}:
        return True
    return False


def load_with_header(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        raise LedgerError(f"Ledger does not exist: {path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def surface_prefix(surface: str) -> str:
    surface_key = surface.casefold()
    for needles, prefix in SURFACE_PREFIXES:
        if any(needle in surface_key for needle in needles):
            return prefix
    return "GEN"


def allocate_feature_id(rows: Iterable[dict[str, str]], surface: str) -> str:
    prefix = surface_prefix(surface)
    max_number = 0
    pattern = re.compile(rf"^FEAT-{re.escape(prefix)}-(\d+)$")
    for row in rows:
        match = pattern.fullmatch((row.get("Feature ID") or "").strip())
        if match:
            max_number = max(max_number, int(match.group(1)))
    return f"FEAT-{prefix}-{max_number + 1:03d}"


def parse_row_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        rows = payload["rows"]
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        raise LedgerError("Row JSON must be an object, an array, or an object with a rows array.")
    if not all(isinstance(row, dict) for row in rows):
        raise LedgerError("Every row JSON item must be an object.")
    return rows


def merge_row(existing: dict[str, str] | None, incoming: dict[str, Any], source_commit: str | None) -> dict[str, str]:
    base = normalize_row(existing or {})
    incoming_row = normalize_row(incoming)

    if not incoming_row["Feature ID"]:
        incoming_row["Feature ID"] = base["Feature ID"]

    for column in REQUIRED_COLUMNS:
        new_value = incoming_row[column]
        if new_value:
            base[column] = new_value

    if source_commit and not incoming_row["Last Source Commit"]:
        base["Last Source Commit"] = source_commit

    if (existing or {}).get("Current Status") == "waived" and not incoming_row["Current Status"]:
        base["Current Status"] = "waived"
    if (existing or {}).get("Execution Status") == "waived" and not incoming_row["Execution Status"]:
        base["Execution Status"] = "waived"
    if (existing or {}).get("Fix Status") == "waived" and not incoming_row["Fix Status"]:
        base["Fix Status"] = "waived"

    if not base["Execution Status"]:
        base["Execution Status"] = "not_run"
    if not base["Current Status"]:
        base["Current Status"] = "discovered"
    if not base["Max Severity"]:
        base["Max Severity"] = "none"
    if not base["Defect Count"]:
        base["Defect Count"] = "0"
    if not base["Fix Status"]:
        base["Fix Status"] = "none"
    if not base["Confidence"]:
        base["Confidence"] = "low"

    return base


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    normalized = [normalize_row(row) for row in rows]
    total = len(normalized)
    tested = sum(1 for row in normalized if row["Execution Status"] in {"passed", "failed"})
    passed = sum(1 for row in normalized if row["Execution Status"] == "passed" or row["Current Status"] in {"passed", "complete"})
    failed = sum(1 for row in normalized if row["Execution Status"] == "failed" or row["Current Status"] == "failed")
    test_designed = sum(1 for row in normalized if row["Test Cases"] or row["Current Status"] in {"test_designed", "testing", "passed", "failed", "complete"})
    discovered = sum(1 for row in normalized if row["Feature ID"])
    waived = sum(1 for row in normalized if row["Current Status"] == "waived" or row["Execution Status"] == "waived" or row["Fix Status"] == "waived")
    critical = sum(1 for row in normalized if row["Max Severity"] == "critical")
    high = sum(1 for row in normalized if row["Max Severity"] == "high")
    ux = sum(1 for row in normalized if row["Max Severity"] == "ux")
    open_defects = 0
    for row in normalized:
        defect_count = int(row["Defect Count"] or "0")
        if defect_count > 0 and not defect_is_closed(row):
            open_defects += defect_count

    max_severity = "none"
    for row in normalized:
        severity = row["Max Severity"]
        if SEVERITY_RANK[severity] > SEVERITY_RANK[max_severity]:
            max_severity = severity

    last_tested = ""
    for row in normalized:
        last_tested = max(last_tested, row["Last Tested Date"])

    if total == 0:
        confidence_score = 0
    else:
        confidence_score = round((passed / total) * 70 + (test_designed / total) * 20 + (tested / total) * 10)
        confidence_score -= critical * 15 + high * 8 + max(0, open_defects - critical - high) * 2
        confidence_score = max(0, min(100, confidence_score))

    return {
        "totalFeatures": total,
        "discoveredFeatures": discovered,
        "testDesignedFeatures": test_designed,
        "testedFeatures": tested,
        "passedFeatures": passed,
        "failedFeatures": failed,
        "openDefects": open_defects,
        "criticalDefects": critical,
        "highDefects": high,
        "uxDefects": ux,
        "waivedDefects": waived,
        "maxSeverity": max_severity,
        "confidenceScore": confidence_score,
        "lastTestedAt": last_tested,
    }


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.ledger)
    if path.exists() and not args.force:
        rows, header = load_with_header(path)
        errors = validate_rows(rows, header)
        if errors:
            raise LedgerError("\n".join(errors))
        print(f"Ledger already exists and validates: {path}")
        return 0
    write_rows(path, [])
    print(f"Created ledger: {path}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    rows, header = load_with_header(Path(args.ledger))
    errors = validate_rows(rows, header)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Ledger validates: {args.ledger} ({len(rows)} rows)")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    rows = read_rows(Path(args.ledger))
    summary = summarize_rows(rows)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        for key, value in summary.items():
            print(f"{key}: {value}")
    return 0


def cmd_allocate_id(args: argparse.Namespace) -> int:
    rows = read_rows(Path(args.ledger)) if Path(args.ledger).exists() else []
    print(allocate_feature_id(rows, args.surface))
    return 0


def cmd_upsert(args: argparse.Namespace) -> int:
    path = Path(args.ledger)
    existing_rows = read_rows(path) if path.exists() else []
    by_id = {row["Feature ID"]: normalize_row(row) for row in existing_rows if row.get("Feature ID")}
    pending_rows = parse_row_json(Path(args.row_json))

    for pending in pending_rows:
        normalized_pending = normalize_row(pending)
        feature_id = normalized_pending["Feature ID"]
        if not feature_id:
            feature_id = allocate_feature_id(by_id.values(), normalized_pending["Surface"])
            pending["Feature ID"] = feature_id
        by_id[feature_id] = merge_row(by_id.get(feature_id), pending, args.source_commit)

    rows = list(by_id.values())
    errors = validate_rows(rows, REQUIRED_COLUMNS)
    if errors:
        raise LedgerError("\n".join(errors))
    write_rows(path, rows)
    print(f"Upserted {len(pending_rows)} row(s) into {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create the canonical ledger if needed")
    init_parser.add_argument("--ledger", default="docs/feature-validation/feature-validation-ledger.csv")
    init_parser.add_argument("--force", action="store_true", help="replace an existing ledger with an empty one")
    init_parser.set_defaults(func=cmd_init)

    validate_parser = subparsers.add_parser("validate", help="validate ledger structure and statuses")
    validate_parser.add_argument("--ledger", default="docs/feature-validation/feature-validation-ledger.csv")
    validate_parser.set_defaults(func=cmd_validate)

    summary_parser = subparsers.add_parser("summary", help="print ledger metrics")
    summary_parser.add_argument("--ledger", default="docs/feature-validation/feature-validation-ledger.csv")
    summary_parser.add_argument("--json", action="store_true")
    summary_parser.set_defaults(func=cmd_summary)

    allocate_parser = subparsers.add_parser("allocate-id", help="print the next stable feature ID for a surface")
    allocate_parser.add_argument("--ledger", default="docs/feature-validation/feature-validation-ledger.csv")
    allocate_parser.add_argument("--surface", required=True)
    allocate_parser.set_defaults(func=cmd_allocate_id)

    upsert_parser = subparsers.add_parser("upsert", help="upsert rows from JSON by Feature ID")
    upsert_parser.add_argument("--ledger", default="docs/feature-validation/feature-validation-ledger.csv")
    upsert_parser.add_argument("--row-json", required=True)
    upsert_parser.add_argument("--source-commit")
    upsert_parser.set_defaults(func=cmd_upsert)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except LedgerError as exc:
        print(f"ledger.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
