import { readFile } from "node:fs/promises";
import { matchesGlob } from "node:path";
import { expect, it } from "vitest";
import { parse } from "yaml";
import { z } from "zod";
import {
  CODEQL_LANGUAGES,
  planCodeqlLanguages,
} from "../../../scripts/ci/codeql-scope.mjs";

const github = new URL("../../../.github/", import.meta.url);
const configuration = z
  .strictObject({
    name: z.string(),
    "threat-models": z.array(z.string()),
    paths: z.array(z.string()),
    "paths-ignore": z.array(z.string()),
  })
  .parse(
    parse(await readFile(new URL("codeql/production.yml", github), "utf8")),
  );

// Fork: SanHsien/rea keeps its own `.github/workflows/codeql.yml` (one scan of
// every shipped language, uploaded on main), so the code-scanning triage in
// docs/DECISIONS.md stays comparable. Upstream's production workflow, gated on
// REA_CODEQL_ADVANCED and scoped by scripts/ci/codeql-scope.mjs, is not used here;
// the scope script and .github/codeql/production.yml keep their upstream tests.
const workflowDocument = z
  .object({
    on: z.object({
      push: z.object({ branches: z.array(z.string()) }),
      pull_request: z.object({ branches: z.array(z.string()) }),
      schedule: z.array(z.object({ cron: z.string() })),
      workflow_dispatch: z.unknown(),
    }),
    permissions: z.object({
      contents: z.literal("read"),
      "security-events": z.literal("write"),
    }),
    jobs: z.object({
      analyze: z.object({
        strategy: z.object({
          matrix: z.object({ language: z.array(z.string()) }),
        }),
        steps: z.array(
          z.object({
            uses: z.string(),
            with: z.record(z.string(), z.unknown()).optional(),
          }),
        ),
      }),
    }),
  })
  .parse(
    parse(await readFile(new URL("workflows/codeql.yml", github), "utf8")),
  );

const matchesPatterns = (path: string, patterns: readonly string[]): boolean =>
  patterns.some(
    (pattern) =>
      path === pattern ||
      path.startsWith(`${pattern}/`) ||
      matchesGlob(path, pattern),
  );

const excluded = (path: string): boolean =>
  matchesPatterns(path, configuration["paths-ignore"]);

it.each([
  "tests/fixtures/fakeHopper.mjs",
  "tests/conformance/ghidra/riscv-checks.mjs",
  "tests/support/analysis-efficiency/resource-run.py",
  "scripts/fixtures/http3-lab.py",
  "scripts/fixtures/managed/pe.mjs",
  "src/process/ExecFileOutput.test.ts",
  "src/process/ProcessOwnership.fixture.ts",
  "scripts/lib/http3-verifier-lifecycle.test.mjs",
  "bridge/pwndbg/test_core_context.py",
  "bridge/example_test.py",
])("excludes test-only input %s", (path) => {
  expect(excluded(path)).toBe(true);
});

it.each([
  "src/process/ExecFileOutput.ts",
  "src/filesystem/RegularFile.ts",
  "src/application/ClientConfigurationPublication.ts",
  "bridge/pwndbg/launch.py",
  "bridge/pwntools/layout_impl.py",
  "bridge/native/rea_lldb_tracer.py",
  "bridge/ghidra/ReaGhidraBridge.java",
  "install.sh",
  "scripts/rea.mjs",
  "scripts/prepack.mjs",
  "scripts/hopper-demo-x11.py",
  "scripts/ci/release-recovery.mjs",
  "scripts/verify-package-install.mjs",
  "scripts/verify-package-update.mjs",
  "scripts/verify-windows-native-artifact.mjs",
  "docs/.vitepress/config.ts",
  ".github/workflows/release.yml",
  ".github/actions/publish-mcp/action.yml",
])("retains production or release input %s", (path) => {
  expect(excluded(path)).toBe(false);
});

it("retains all packaged entrypoints and the existing local-input threat model", async () => {
  const manifest = z
    .object({ files: z.array(z.string()) })
    .parse(
      JSON.parse(
        await readFile(
          new URL("../../../package.json", import.meta.url),
          "utf8",
        ),
      ),
    );
  expect(manifest.files.filter(excluded)).toEqual([]);
  expect(configuration["threat-models"]).toEqual(["local"]);
  // A narrow allowlist would silently drop new production roots. Explicitly
  // traverse the hidden configuration directory without excluding the root.
  expect(configuration.paths).toContain(".");
  expect(configuration.paths).toContain("docs/.vitepress");
});

it("fork: scans every shipped language on main and pull requests", () => {
  expect(workflowDocument.on.push.branches).toEqual(["main"]);
  expect(workflowDocument.on.pull_request.branches).toEqual(["main"]);
  const job = workflowDocument.jobs.analyze;
  expect(job.strategy.matrix.language).toEqual([
    "javascript-typescript",
    "python",
    "java-kotlin",
    "actions",
  ]);
  const init = job.steps.find((step) =>
    step.uses.startsWith("github/codeql-action/init@"),
  );
  expect(init?.with).toMatchObject({
    languages: "${{ matrix.language }}",
    "build-mode": "none",
  });
  const analyze = job.steps.find((step) =>
    step.uses.startsWith("github/codeql-action/analyze@"),
  );
  expect(analyze?.with).toMatchObject({
    category: "/language:${{ matrix.language }}",
  });
});

const SHA_BASE = "a".repeat(40);
const SHA_HEAD = "b".repeat(40);
const selectPr = (files: readonly string[]) =>
  planCodeqlLanguages(
    { event: "pull_request", base: SHA_BASE, head: SHA_HEAD },
    { mergeBase: (base) => base, changedFiles: () => files },
  );

it("selects affected CodeQL languages on pull requests and fails closed on shared or unknown inputs", () => {
  for (const event of ["push", "schedule", "workflow_dispatch"]) {
    expect(
      planCodeqlLanguages(
        { event, base: undefined, head: SHA_HEAD },
        {
          mergeBase: () => {
            throw new Error("Non-PR events must not diff");
          },
          changedFiles: () => [],
        },
      ),
    ).toMatchObject({ run: true, languages: CODEQL_LANGUAGES });
  }
  expect(
    selectPr([
      "tests/boundary/filesystem/ciCodeqlScope.test.ts",
      "src/process/ExecFileOutput.test.ts",
      "docs/development/testing.md",
      "bridge/ghidra/ReaGhidraBridge.java",
    ]),
  ).toMatchObject({ run: false, languages: [] });
  expect(
    selectPr(["src/process/ExecFileOutput.ts", "docs/.vitepress/config.ts"]),
  ).toMatchObject({
    run: true,
    languages: ["javascript-typescript"],
  });
  expect(selectPr(["bridge/pwndbg/launch.py"])).toMatchObject({
    run: true,
    languages: ["python"],
  });
  expect(
    selectPr([
      ".github/workflows/release.yml",
      ".github/actions/publish-mcp/action.yml",
    ]),
  ).toMatchObject({
    run: true,
    languages: ["actions"],
  });
  for (const broad of [
    ".github/codeql/production.yml",
    ".github/workflows/codeql.yml",
    "install.sh",
    "scripts/unknown-entrypoint",
  ]) {
    expect(selectPr([broad]), broad).toMatchObject({
      run: true,
      languages: CODEQL_LANGUAGES,
    });
  }
  expect(
    planCodeqlLanguages(
      { event: "pull_request", base: "not-a-sha", head: SHA_HEAD },
      { mergeBase: (base) => base, changedFiles: () => [] },
    ),
  ).toMatchObject({ run: true, languages: CODEQL_LANGUAGES });
});
