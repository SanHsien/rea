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


if __name__ == "__main__":
    unittest.main()
