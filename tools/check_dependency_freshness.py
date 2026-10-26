#!/usr/bin/env python3
"""Compare the exact versions pinned in package.json with the npm registry.

``package.json`` pins every direct dependency to one version, so "declared floor"
and "installed version" are the same thing here. A row is *stale* when the registry
``latest`` is newer than that pin. A stale row is acceptable only when
``.github/dependency-deferrals.json`` records an evaluated reason and a
``deferredLatest``; the deferral lapses as soon as the registry moves past it.

Raising a pin to silence this report is not an exit: the pins follow upstream
(morluto/rea) and change when an upstream sync brings them.
"""

from __future__ import annotations

import argparse
import json
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
        pinned, latest = info.get("wanted", ""), info.get("latest", "")
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
            }
        )
    return rows


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
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise FreshnessError(f"cannot parse npm outdated output: {exc}") from exc


def render(rows: list[dict]) -> str:
    lines = [
        "# Dependency freshness",
        "",
        "| Package | Pinned | Registry latest | Status |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        status = f"deferred: {row['reason']}" if row["deferred"] else "needs evaluation"
        lines.append(f"| `{row['name']}` | `{row['pinned']}` | `{row['latest']}` | {status} |")
    if not rows:
        lines.append("| - | - | - | all direct pins are current |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="also write the report to this file")
    args = parser.parse_args(argv)
    # Deferral reasons are free text; a narrow console codec must not abort the run.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        rows = classify(run_outdated(), load_deferrals())
    except FreshnessError as exc:
        print(f"::error::{exc}")
        return 2
    report = render(rows)
    sys.stdout.write(report)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    return 1 if any(not row["deferred"] for row in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
