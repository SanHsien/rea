#!/usr/bin/env python3
"""Compare the exact versions pinned in package.json with the npm registry.

``package.json`` pins every direct dependency to one version, so "declared floor"
and "installed version" are the same thing here. A row is *stale* when the registry
``latest`` is newer than that pin. A stale row is acceptable only when
``.github/dependency-deferrals.json`` records an evaluated reason and a
``deferredLatest``; the deferral lapses as soon as the registry moves past it.

Raising a pin to silence this report is not an exit: the pins follow upstream
(morluto/rea) and change when an upstream sync brings them.

A lookup that failed is *unchecked*, never *current*. ``npm outdated --json`` exits 1
both when a pin is stale and when the registry refuses the request (E429), so the exit
code alone cannot tell them apart; the payload is inspected instead.

Exit codes: 0 every pin was checked and is current or deferred; 1 a pin needs
evaluation; 2 the check is incomplete (lookup failed, or a row has no usable version).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFERRALS_PATH = REPO_ROOT / ".github" / "dependency-deferrals.json"
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+.*)?$")


class FreshnessError(RuntimeError):
    """Raised when the registry state or the deferral file cannot be read."""


def parse_version(text: str) -> tuple[int, int, int, bool] | None:
    """Return (major, minor, patch, is_release); ``None`` when not plain semver."""
    match = _SEMVER_RE.match(text.strip())
    if not match:
        return None
    major, minor, patch, pre = match.groups()
    return int(major), int(minor), int(patch), pre is None


def is_newer(candidate: str, base: str) -> bool:
    """True when ``candidate`` is a newer stable release than ``base``.

    A prerelease ``latest`` (a dist-tag pointing at a beta) is not an upgrade target.
    A stable release is newer than a prerelease of the same ``major.minor.patch``.
    """
    new, old = parse_version(candidate), parse_version(base)
    if new is None or old is None or not new[3]:
        return False
    return new > old


def load_deferrals(path: Path = DEFERRALS_PATH) -> dict[str, dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FreshnessError(f"invalid deferrals file: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FreshnessError(f"deferrals file must be an object: {path}")
    for name, entry in data.items():
        if not isinstance(entry, dict):
            raise FreshnessError(f"deferral for {name} must be an object: {path}")
        if parse_version(str(entry.get("deferredLatest", ""))) is None:
            raise FreshnessError(f"deferral for {name} needs a plain semver deferredLatest: {path}")
    return data


def classify(outdated: dict[str, dict], deferrals: dict[str, dict]) -> list[dict]:
    """One row per direct dependency whose pin is behind the registry."""
    rows = []
    for name, info in sorted(outdated.items()):
        details = info if isinstance(info, dict) else {}
        pinned, latest = str(details.get("wanted") or ""), str(details.get("latest") or "")
        if parse_version(pinned) is None or parse_version(latest) is None:
            # No comparable version came back for this package: unchecked, not current.
            rows.append(
                {
                    "name": name,
                    "pinned": pinned or "?",
                    "latest": latest or "?",
                    "deferred": False,
                    "reason": "",
                    "check_failed": True,
                }
            )
            continue
        if not is_newer(latest, pinned):
            continue
        deferral = deferrals.get(name) or {}
        reason = str(deferral.get("reason", "")).strip()
        deferred_to = str(deferral.get("deferredLatest", ""))
        covered = (
            bool(reason)
            and parse_version(deferred_to) is not None
            and not is_newer(latest, deferred_to)
        )
        rows.append(
            {
                "name": name,
                "pinned": pinned,
                "latest": latest,
                "deferred": covered,
                "reason": reason if covered else "",
                "check_failed": False,
            }
        )
    return rows


def payload_error(payload: object) -> str:
    """Return npm's own failure text when the payload is an error, not a set of rows."""
    if not isinstance(payload, dict) or "error" not in payload:
        return ""
    error = payload["error"]
    if isinstance(error, dict):
        # The payload is keyed by package name and a package can be called "error";
        # its row carries version fields, a failure does not.
        if {"current", "wanted", "latest"} & set(error):
            return ""
        parts = [error.get("code"), error.get("summary"), error.get("detail")]
    else:
        parts = [error, payload.get("message")]
    text = "; ".join(str(part).strip() for part in parts if part and str(part).strip())
    return text or "npm reported an error without details"


def run_outdated(cwd: Path = REPO_ROOT) -> dict[str, dict]:
    result = subprocess.run(
        ["npm", "outdated", "--json", "--all=false"],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=sys.platform == "win32",
        check=False,
    )
    # npm outdated exits 1 when anything is outdated; other codes are real failures.
    if result.returncode not in (0, 1):
        raise FreshnessError(f"npm outdated exited {result.returncode}: {result.stderr.strip()}")
    if not result.stdout.strip():
        if result.returncode != 0:
            # Exit 1 means "outdated rows follow". With no rows it is a failure.
            raise FreshnessError(
                f"npm outdated exited {result.returncode} without a report: {result.stderr.strip()}"
            )
        return {}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise FreshnessError(f"cannot parse npm outdated output: {exc}") from exc
    if not isinstance(payload, dict):
        raise FreshnessError(f"npm outdated returned {type(payload).__name__}, expected an object")
    error = payload_error(payload)
    if error:
        # A registry failure (E429 included) shares exit 1 with "something is outdated".
        raise FreshnessError(f"npm outdated could not read the registry: {error}")
    return payload


def write_github_output(needs_attention: bool, check_failed: bool) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"needs_attention={'true' if needs_attention else 'false'}\n")
        handle.write(f"check_failed={'true' if check_failed else 'false'}\n")


def render(rows: list[dict], check_error: str = "") -> str:
    lines = [
        "# Dependency freshness",
        "",
        "| Package | Pinned | Registry latest | Status |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        if row.get("check_failed"):
            status = "CHECK FAILED: no comparable version from the registry"
        elif row["deferred"]:
            status = f"deferred: {row['reason']}"
        else:
            status = "needs evaluation"
        lines.append(f"| `{row['name']}` | `{row['pinned']}` | `{row['latest']}` | {status} |")
    if check_error:
        # Nothing was compared. Saying "current" here would report a failed lookup as a pass.
        cell = " ".join(check_error.replace("|", "/").split())
        lines.append(f"| (all) | ? | ? | CHECK FAILED: {cell} |")
    elif not rows:
        lines.append("| - | - | - | all direct pins are current |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="also write the report to this file")
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="append needs_attention and check_failed to $GITHUB_OUTPUT",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fleet-wide spelling of the default: this checker always exits non-zero "
        "when a pin needs evaluation (1) or the check is incomplete (2)",
    )
    args = parser.parse_args(argv)
    # Deferral reasons are free text; a narrow console codec must not abort the run.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    rows: list[dict] = []
    check_error = ""
    try:
        rows = classify(run_outdated(), load_deferrals())
    except FreshnessError as exc:
        check_error = str(exc)
        print(f"::error::{exc}")
    report = render(rows, check_error)
    sys.stdout.write(report)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    check_failed = bool(check_error) or any(row.get("check_failed") for row in rows)
    stale = any(not row["deferred"] for row in rows)
    if args.github_output:
        write_github_output(check_failed or stale, check_failed)
    if check_failed:
        return 2
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
