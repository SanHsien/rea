import { readFile, writeFile } from "node:fs/promises";
import { delimiter, join } from "node:path";
import { expect } from "vitest";
import { z } from "zod";
import { packageRunnerRegistrationCommand } from "../../../src/application/ClientRegistrationIdentity.js";
import { createTestTempDirectory } from "../../fixtures/temporaryDirectory.js";
import { cliTest } from "../../support/cli/cliFixture.js";

const ompConfigurationSchema = z.object({
  mcpServers: z.object({
    rea: z.object({ command: z.string(), args: z.array(z.string()) }),
  }),
});

/**
 * Stand-in package runner that records its arguments and exits 0. Setup warms
 * the runner cache by really launching the pinned package, which installs it
 * from the npm registry; a test of the registration must not wait on that.
 */
const installRecordingRunner = async (runner: "npx" | "bunx") => {
  const directory = await createTestTempDirectory("rea-fake-runner-");
  const log = join(directory, "invocations.log");
  if (process.platform === "win32")
    await writeFile(
      join(directory, `${runner}.cmd`),
      '@echo off\r\necho %*>>"%~dp0invocations.log"\r\n',
    );
  else
    await writeFile(
      join(directory, runner),
      '#!/bin/sh\necho "$*" >> "${0%/*}/invocations.log"\n',
      { mode: 0o755 },
    );
  return {
    path: `${directory}${delimiter}${process.env.PATH ?? ""}`,
    invocations: async () =>
      (
        await readFile(log, "utf8").catch((cause: NodeJS.ErrnoException) => {
          if (cause.code === "ENOENT") return "";
          throw cause;
        })
      )
        .split(/\r?\n/u)
        .filter((line) => line !== ""),
  };
};

// Package runners set these variables for the bin they launch from a temporary cache.
for (const { runner, userAgent } of [
  { runner: "npx", userAgent: "npm/10.9.0 node/v24.11.0 linux x64" },
  { runner: "bunx", userAgent: "bun/1.4.2 npm/? node/v26.3.0 linux x64" },
] as const) {
  cliTest(
    `${runner} setup registers the pinned ${runner} launcher instead of its cache`,
    async ({ cli }) => {
      const home = await createTestTempDirectory("rea-package-runner-");
      const fakeRunner = await installRecordingRunner(runner);
      const run = (arguments_: readonly string[]) =>
        cli.run({
          arguments: arguments_,
          cwd: home,
          environment: {
            HOME: home,
            USERPROFILE: home,
            PATH: fakeRunner.path,
            npm_command: "exec",
            npm_config_user_agent: userAgent,
          },
          timeoutMs: 20_000,
        });
      const setup = await run([
        "setup",
        "--client",
        "omp",
        "--no-skill",
        "--yes",
        "--json",
      ]);
      expect(setup.exitCode).toBe(0);
      expect(setup.json).toMatchObject({
        status: "ready",
        prewarm: { status: "warmed" },
      });
      // The cache warm-up launches the pinned spec with a terminating flag.
      const pinned = packageRunnerRegistrationCommand(runner, process.platform);
      expect(await fakeRunner.invocations()).toEqual([
        [...pinned.slice(pinned.indexOf(runner) + 1, -1), "--version"].join(
          " ",
        ),
      ]);
      const configuration = ompConfigurationSchema.parse(
        JSON.parse(
          await readFile(join(home, ".omp", "agent", "mcp.json"), "utf8"),
        ),
      );
      const { command, args } = configuration.mcpServers.rea;
      expect([command, ...args]).toEqual(
        packageRunnerRegistrationCommand(runner, process.platform),
      );
      const doctor = await run(["doctor", "--client", "omp", "--json"]);
      expect(doctor.json).toMatchObject({
        identity: { registrations: [{ client: "omp", state: "aligned" }] },
      });
      const repeat = await run([
        "setup",
        "--client",
        "omp",
        "--no-skill",
        "--dry-run",
        "--json",
      ]);
      expect(repeat.json).toMatchObject({ plannedActions: [] });
    },
  );
}
