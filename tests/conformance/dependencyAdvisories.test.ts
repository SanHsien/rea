import { readFile } from "node:fs/promises";

import { describe, expect, it } from "vitest";

interface LockPackage {
  readonly version?: string;
}

interface Lockfile {
  readonly packages: Readonly<Record<string, LockPackage>>;
}

const parseVersion = (version: string): readonly [number, number, number] => {
  const [major = 0, minor = 0, patch = 0] = version
    .split("-")[0]!
    .split(".")
    .map((part) => Number.parseInt(part, 10));
  return [major, minor, patch];
};

const compareVersions = (left: string, right: string): number => {
  const a = parseVersion(left);
  const b = parseVersion(right);
  for (const index of [0, 1, 2] as const) {
    const difference = a[index] - b[index];
    if (difference !== 0) {
      return difference;
    }
  }
  return 0;
};

const installedVersions = (lock: Lockfile, name: string): string[] =>
  Object.entries(lock.packages)
    .filter(
      ([path]) =>
        path === `node_modules/${name}` ||
        path.endsWith(`/node_modules/${name}`),
    )
    .flatMap(([, entry]) =>
      entry.version === undefined ? [] : [entry.version],
    );

/**
 * Advisory ranges that npm audit reported on 2026-11-06 (GHSA-g3hv-75wg-m249
 * for minimatch 7.0.0 through 11.0.0, GHSA-3g3m-2fjr-6pw4 for glob 9.0.0
 * through 14.0.1). The fork pins them with package.json overrides because the
 * newest frida still asks for minimatch ^10.
 */
const vulnerableRanges = [
  { name: "minimatch", from: "7.0.0", through: "11.0.0" },
  { name: "glob", from: "9.0.0", through: "14.0.1" },
] as const;

describe("dependency advisories", () => {
  it.each(vulnerableRanges)(
    "keeps every locked $name outside the advisory range $from to $through",
    async ({ name, from, through }) => {
      const lock = JSON.parse(
        await readFile("package-lock.json", "utf8"),
      ) as Lockfile;
      const versions = installedVersions(lock, name);

      expect(versions.length).toBeGreaterThan(0);
      const vulnerable = versions.filter(
        (version) =>
          compareVersions(version, from) >= 0 &&
          compareVersions(version, through) <= 0,
      );
      expect(vulnerable).toEqual([]);
    },
  );

  it("keeps every locked @isaacs/nonrecursive-glob-match within what minimatch 11.0.1 accepts (^1.0.1)", async () => {
    const lock = JSON.parse(
      await readFile("package-lock.json", "utf8"),
    ) as Lockfile;
    const versions = installedVersions(lock, "@isaacs/nonrecursive-glob-match");

    expect(versions.length).toBeGreaterThan(0);
    const outOfRange = versions.filter(
      (version) =>
        compareVersions(version, "1.0.1") < 0 ||
        compareVersions(version, "2.0.0") >= 0,
    );
    expect(outOfRange).toEqual([]);
  });
});
