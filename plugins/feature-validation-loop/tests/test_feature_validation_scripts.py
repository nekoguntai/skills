#!/usr/bin/env python3
"""Regression tests for feature-validation-loop helper scripts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PLUGIN_ROOT / "skills" / "feature-validation-loop" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import ledger  # noqa: E402
import prismatic_artifact  # noqa: E402


def base_row(**overrides: str) -> dict[str, str]:
    row = {column: "" for column in ledger.REQUIRED_COLUMNS}
    row.update(
        {
            "Feature ID": "FEAT-WEB-001",
            "Feature Name": "Project validation summary",
            "Surface": "web project detail",
            "Source Paths": "apps/web/app/project-detail.tsx",
            "Execution Status": "not_run",
            "Current Status": "discovered",
            "Defect Count": "0",
            "Max Severity": "none",
            "Fix Status": "none",
            "Confidence": "medium",
        }
    )
    row.update(overrides)
    return row


class FeatureValidationScriptTests(unittest.TestCase):
    def test_markdown_artifact_escapes_cells_and_counts_pending_retest_defects(self) -> None:
        row = base_row()
        row["Feature Name"] = "Bad | <script>alert(1)</script>"
        row["Execution Status"] = "failed"
        row["Current Status"] = "fixed_pending_retest"
        row["Defect IDs"] = "DEF-FEAT-WEB-001-001"
        row["Defect Count"] = "1"
        row["Max Severity"] = "high"
        row["Reproduction Notes"] = "Pipe | <b>raw</b>"
        row["Fix Status"] = "fixed"
        rows = [row]

        metrics = ledger.summarize_rows(rows)
        self.assertEqual(metrics["openDefects"], 1)

        markdown = prismatic_artifact.markdown_summary(rows, "qa/custom-ledger.csv")
        self.assertIn("Bad \\| &lt;script&gt;alert(1)&lt;/script&gt;", markdown)
        self.assertIn("Pipe \\| &lt;b&gt;raw&lt;/b&gt;", markdown)
        self.assertNotIn("<script>alert(1)</script>", markdown)

    def test_contribution_payload_uses_custom_ledger_path(self) -> None:
        rows = [base_row()]
        markdown = prismatic_artifact.markdown_summary(rows, "qa/custom-ledger.csv")
        payload = prismatic_artifact.contribution_payload(
            "fixture-project",
            "https://example.invalid/repo.git",
            "main",
            "qa/custom-ledger.csv",
            markdown,
            None,
            rows,
        )
        artifact = payload["artifacts"][0]
        self.assertEqual(artifact["relatedFiles"], ["qa/custom-ledger.csv"])
        self.assertEqual(artifact["metadata"]["sourcePath"], "qa/custom-ledger.csv")
        self.assertEqual(
            artifact["metadata"]["featureValidation"]["ledgerPath"],
            "qa/custom-ledger.csv",
        )

    def test_validate_requires_defect_count_consistency_and_block_reasons(self) -> None:
        mismatch = base_row(
            **{
                "Defect IDs": "DEF-FEAT-WEB-001-001; DEF-FEAT-WEB-001-002",
                "Defect Count": "1",
            }
        )
        blocked = base_row(
            **{
                "Feature ID": "FEAT-WEB-002",
                "Execution Status": "blocked",
                "Current Status": "blocked",
            }
        )
        waived = base_row(
            **{
                "Feature ID": "FEAT-WEB-003",
                "Execution Status": "waived",
                "Current Status": "waived",
                "Fix Status": "waived",
            }
        )

        errors = ledger.validate_rows([mismatch, blocked, waived], ledger.REQUIRED_COLUMNS)
        combined = "\n".join(errors)
        self.assertIn("does not match 2 Defect IDs", combined)
        self.assertIn("blocked rows require Reproduction Notes or Notes", combined)
        self.assertIn("waived rows require Reproduction Notes or Notes", combined)


if __name__ == "__main__":
    unittest.main()
