import { readFile } from "node:fs/promises";

import { describe, expect, it } from "vitest";

interface LockPackage {
  readonly version?: string;
  readonly dependencies?: Readonly<Record<string, string>>;
  readonly optionalDependencies?: Readonly<Record<string, string>>;
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

const installedEntries = (
  lock: Lockfile,
  name: string,
): (readonly [string, string])[] =>
  Object.entries(lock.packages)
    .filter(
      ([path]) =>
        path === `node_modules/${name}` ||
        path.endsWith(`/node_modules/${name}`),
    )
    .flatMap(([path, entry]) =>
      entry.version === undefined ? [] : [[path, entry.version] as const],
    );

const installedVersions = (lock: Lockfile, name: string): string[] =>
  installedEntries(lock, name).map(([, version]) => version);

/** Lock paths whose `name` dependency resolves to the copy at `target`. */
const dependentsOf = (lock: Lockfile, name: string, target: string): string[] =>
  Object.entries(lock.packages)
    .filter(
      ([, entry]) =>
        entry.dependencies?.[name] !== undefined ||
        entry.optionalDependencies?.[name] !== undefined,
    )
    .map(([path]) => path)
    .filter((path) => {
      // Node resolution: the nearest node_modules/<name> at or above the dependent.
      for (let base = path; ;) {
        const candidate = `${base === "" ? "" : `${base}/`}node_modules/${name}`;
        if (lock.packages[candidate] !== undefined) return candidate === target;
        if (base === "") return false;
        const index = base.lastIndexOf("/node_modules/");
        base = index === -1 ? "" : base.slice(0, index);
      }
    })
    .sort();

/**
 * Advisory ranges that npm audit reported on 2026-11-06 (GHSA-g3hv-75wg-m249
 * for minimatch 7.0.0 through 11.0.0, GHSA-3g3m-2fjr-6pw4 for glob 9.0.0
 * through 14.0.1). The fork pins development copies with package.json
 * overrides.
 */
const vulnerableRanges = [
  { name: "minimatch", from: "7.0.0", through: "11.0.0" },
  { name: "glob", from: "9.0.0", through: "14.0.1" },
] as const;

/**
 * Accepted exception (docs/DECISIONS.md 2026-11-24): GHSA-g3hv-75wg-m249 in the
 * minimatch copy that only frida uses. frida (optional runtime dependency, still
 * `minimatch ^10.0.1` in 17.27.5) calls minimatch only in Device.getProcess(name),
 * and src never calls getProcess. A runtime override cannot fix it because
 * scripts/lib/plugin-package.mjs rejects runtime overrides. The exception holds
 * only while frida is the sole dependent of that copy, and must be removed once
 * frida no longer needs minimatch 10 (ROADMAP.md).
 */
const acceptedExceptions = [
  {
    name: "minimatch",
    path: "node_modules/minimatch",
    dependents: ["node_modules/frida"],
  },
] as const;

const isAccepted = (name: string, path: string): boolean =>
  acceptedExceptions.some(
    (exception) => exception.name === name && exception.path === path,
  );

describe("dependency advisories", () => {
  it.each(vulnerableRanges)(
    "keeps every locked $name outside the advisory range $from to $through",
    async ({ name, from, through }) => {
      const lock = JSON.parse(
        await readFile("package-lock.json", "utf8"),
      ) as Lockfile;
      const entries = installedEntries(lock, name);

      expect(entries.length).toBeGreaterThan(0);
      const vulnerable = entries.filter(
        ([path, version]) =>
          compareVersions(version, from) >= 0 &&
          compareVersions(version, through) <= 0 &&
          !isAccepted(name, path),
      );
      expect(vulnerable).toEqual([]);
    },
  );

  it.each(acceptedExceptions)(
    "limits the accepted $name exception at $path to $dependents and expires it once unneeded",
    async ({ name, path, dependents }) => {
      const lock = JSON.parse(
        await readFile("package-lock.json", "utf8"),
      ) as Lockfile;
      const range = vulnerableRanges.find((entry) => entry.name === name)!;
      const version = lock.packages[path]?.version;

      // Still needed: the copy exists and is inside the advisory range.
      expect(version).toBeDefined();
      expect(
        compareVersions(version!, range.from) >= 0 &&
          compareVersions(version!, range.through) <= 0,
      ).toBe(true);
      // Still contained: nothing besides the recorded dependents reaches it.
      expect(dependentsOf(lock, name, path)).toEqual([...dependents]);
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
