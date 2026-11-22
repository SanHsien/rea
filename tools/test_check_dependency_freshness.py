"""Contract tests for tools/check_dependency_freshness.py."""

from __future__ import annotations

import io
import sys
import unittest
from unittest import mock

import json
import tempfile
from pathlib import Path

import check_dependency_freshness as freshness
from check_dependency_freshness import FreshnessError, classify, is_newer, load_deferrals, render


def outdated(pinned: str, latest: str) -> dict[str, dict]:
    return {"pkg": {"wanted": pinned, "latest": latest}}


class IsNewerTests(unittest.TestCase):
    def test_orders_numerically_not_lexically(self) -> None:
        self.assertTrue(is_newer("1.10.0", "1.9.0"))
        self.assertFalse(is_newer("1.9.0", "1.10.0"))

    def test_equal_is_not_newer(self) -> None:
        self.assertFalse(is_newer("2.0.0", "2.0.0"))

    def test_prerelease_latest_is_not_an_upgrade_target(self) -> None:
        self.assertFalse(is_newer("1.2.0-beta.18", "1.1.0"))

    def test_non_semver_is_never_newer(self) -> None:
        self.assertFalse(is_newer("latest", "1.0.0"))

    def test_stable_release_is_newer_than_prerelease_of_same_version(self) -> None:
        self.assertTrue(is_newer("1.0.0", "1.0.0-rc.1"))

    def test_prerelease_pin_behind_newer_stable_is_stale(self) -> None:
        self.assertTrue(is_newer("1.1.0", "1.0.0-rc.1"))


class ClassifyTests(unittest.TestCase):
    def test_current_pin_produces_no_row(self) -> None:
        self.assertEqual(classify(outdated("1.0.0", "1.0.0"), {}), [])

    def test_stale_pin_without_deferral_needs_evaluation(self) -> None:
        (row,) = classify(outdated("1.0.0", "1.1.0"), {})
        self.assertFalse(row["deferred"])

    def test_deferral_covers_up_to_deferred_latest(self) -> None:
        deferral = {"pkg": {"deferredLatest": "1.1.0", "reason": "follows upstream"}}
        (row,) = classify(outdated("1.0.0", "1.1.0"), deferral)
        self.assertTrue(row["deferred"])

    def test_deferral_lapses_when_registry_moves_past_it(self) -> None:
        deferral = {"pkg": {"deferredLatest": "1.1.0", "reason": "follows upstream"}}
        (row,) = classify(outdated("1.0.0", "1.2.0"), deferral)
        self.assertFalse(row["deferred"])

    def test_deferral_without_reason_is_ignored(self) -> None:
        deferral = {"pkg": {"deferredLatest": "1.1.0", "reason": "  "}}
        (row,) = classify(outdated("1.0.0", "1.1.0"), deferral)
        self.assertFalse(row["deferred"])


    def test_non_semver_deferred_latest_never_covers(self) -> None:
        deferral = {"pkg": {"deferredLatest": "latest", "reason": "follows upstream"}}
        (row,) = classify(outdated("1.0.0", "9.0.0"), deferral)
        self.assertFalse(row["deferred"])


class LoadDeferralsTests(unittest.TestCase):
    def load(self, payload: object) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deferrals.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_deferrals(path)

    def test_valid_entry_loads(self) -> None:
        entry = {"deferredLatest": "1.2.3", "reason": "x"}
        self.assertEqual(self.load({"pkg": entry}), {"pkg": entry})

    def test_non_object_entry_is_a_clean_error(self) -> None:
        with self.assertRaises(FreshnessError):
            self.load({"pkg": "oops"})

    def test_non_semver_deferred_latest_is_a_clean_error(self) -> None:
        with self.assertRaises(FreshnessError):
            self.load({"pkg": {"deferredLatest": "8.x", "reason": "x"}})


class RenderTests(unittest.TestCase):
    def test_empty_report_says_current(self) -> None:
        self.assertIn("all direct pins are current", render([]))


class MainTests(unittest.TestCase):
    def test_non_ascii_reason_does_not_crash_on_a_narrow_console(self) -> None:
        stale = {"pkg": {"wanted": "1.0.0", "latest": "1.1.0"}}
        deferral = {"pkg": {"deferredLatest": "1.1.0", "reason": "跟隨上游"}}
        raw = io.BytesIO()
        console = io.TextIOWrapper(raw, encoding="cp1252")
        with (
            mock.patch.object(freshness, "run_outdated", return_value=stale),
            mock.patch.object(freshness, "load_deferrals", return_value=deferral),
            mock.patch.object(sys, "stdout", console),
        ):
            self.assertEqual(freshness.main([]), 0)


# What `npm outdated --json` prints when the registry rate-limits it: exit 1 (the
# same code as "something is outdated") and an error object instead of rows.
E429_STDOUT = json.dumps(
    {
        "error": {
            "code": "E429",
            "summary": "429 Too Many Requests - GET https://registry.npmjs.org/pkg",
            "detail": "",
        }
    }
)


def npm_result(returncode: int, stdout: str, stderr: str = "") -> mock.Mock:
    return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)


class LookupFailureTests(unittest.TestCase):
    """A lookup that failed is unchecked. It must never be reported as current."""

    def run_main(self, npm: mock.Mock, argv: list[str]) -> tuple[int, str, str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.md"
            github_output = Path(tmp) / "github_output"
            github_output.write_text("", encoding="utf-8")
            stdout = io.StringIO()
            with (
                mock.patch.object(freshness.subprocess, "run", return_value=npm),
                mock.patch.object(freshness, "load_deferrals", return_value={}),
                mock.patch.dict("os.environ", {"GITHUB_OUTPUT": str(github_output)}),
                mock.patch.object(sys, "stdout", stdout),
            ):
                code = freshness.main([*argv, "--output", str(report_path)])
            written = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
            return code, stdout.getvalue(), written, github_output.read_text(encoding="utf-8")

    def test_rate_limited_lookup_raises_instead_of_returning_rows(self) -> None:
        with mock.patch.object(freshness.subprocess, "run", return_value=npm_result(1, E429_STDOUT)):
            with self.assertRaises(FreshnessError) as caught:
                freshness.run_outdated()
        self.assertIn("E429", str(caught.exception))

    def test_rate_limited_lookup_is_reported_check_failed_not_current(self) -> None:
        code, printed, written, _ = self.run_main(npm_result(1, E429_STDOUT), [])
        for report in (printed, written):
            self.assertIn("CHECK FAILED", report)
            self.assertIn("E429", report)
            self.assertNotIn("all direct pins are current", report)
        self.assertNotEqual(code, 0)

    def test_rate_limited_lookup_fails_under_strict(self) -> None:
        code, _, _, _ = self.run_main(npm_result(1, E429_STDOUT), ["--strict"])
        self.assertNotEqual(code, 0)

    def test_rate_limited_lookup_sets_the_workflow_attention_signal(self) -> None:
        _, _, _, outputs = self.run_main(npm_result(1, E429_STDOUT), ["--github-output"])
        self.assertIn("needs_attention=true", outputs.splitlines())
        self.assertIn("check_failed=true", outputs.splitlines())

    def test_non_zero_exit_with_stderr_only_is_check_failed(self) -> None:
        npm = npm_result(1, "", "npm error code E429")
        code, printed, _, outputs = self.run_main(npm, ["--strict", "--github-output"])
        self.assertIn("CHECK FAILED", printed)
        self.assertNotIn("all direct pins are current", printed)
        self.assertNotEqual(code, 0)
        self.assertIn("check_failed=true", outputs.splitlines())

    def test_row_without_a_registry_version_is_check_failed_for_that_package(self) -> None:
        rows = {"pkg": {"wanted": "1.0.0"}, "other": {"wanted": "1.0.0", "latest": "1.0.0"}}
        code, printed, _, outputs = self.run_main(npm_result(1, json.dumps(rows)), ["--github-output"])
        (line,) = [line for line in printed.splitlines() if "`pkg`" in line]
        self.assertIn("CHECK FAILED", line)
        self.assertNotIn("all direct pins are current", printed)
        self.assertNotEqual(code, 0)
        self.assertIn("check_failed=true", outputs.splitlines())

    def test_package_named_error_is_a_row_not_a_failure(self) -> None:
        rows = {"error": {"current": "1.0.0", "wanted": "1.0.0", "latest": "1.1.0"}}
        with mock.patch.object(freshness.subprocess, "run", return_value=npm_result(1, json.dumps(rows))):
            self.assertEqual(freshness.run_outdated(), rows)

    def test_clean_lookup_still_says_current_and_signals_nothing(self) -> None:
        code, printed, _, outputs = self.run_main(npm_result(0, ""), ["--strict", "--github-output"])
        self.assertIn("all direct pins are current", printed)
        self.assertEqual(code, 0)
        self.assertIn("needs_attention=false", outputs.splitlines())
        self.assertIn("check_failed=false", outputs.splitlines())

    def test_stale_pin_sets_attention_without_claiming_a_failed_check(self) -> None:
        rows = {"pkg": {"wanted": "1.0.0", "latest": "1.1.0"}}
        code, _, _, outputs = self.run_main(npm_result(1, json.dumps(rows)), ["--strict", "--github-output"])
        self.assertEqual(code, 1)
        self.assertIn("needs_attention=true", outputs.splitlines())
        self.assertIn("check_failed=false", outputs.splitlines())


if __name__ == "__main__":
    unittest.main()
