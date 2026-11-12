import { describe, expect, it } from "vitest";
import {
  cleanupOwnedProcessGroup,
  type ProcessOwnershipHost,
  type ProcessRunTokenObservation,
  type ProcessTableEntry,
} from "./ProcessOwnership.js";
import { ProcessOwnershipEvidenceOwner } from "./ProcessOwnershipEvidence.js";

const member: ProcessTableEntry = {
  pid: 300,
  parentPid: 1,
  processGroupId: 100,
  state: "S",
  command: "/usr/bin/owned-child",
};

/**
 * Darwin host whose member's token read keeps failing with `reason` and whose
 * process-table listing keeps the member live until `exitsAfterMs` elapses.
 * Non-Darwin hosts never wait, so the exit window is a Darwin-only rule.
 */
const hostFor = (
  reason: "sysctl_failed_22" | "malformed_procargs",
  exitsAfterMs: number | undefined,
): { host: ProcessOwnershipHost; signals: number[] } => {
  const startedAt = performance.now();
  const signals: number[] = [];
  const host: ProcessOwnershipHost = {
    platform: "darwin",
    listProcesses: () =>
      Promise.resolve(
        exitsAfterMs !== undefined &&
          performance.now() - startedAt >= exitsAfterMs
          ? []
          : [member],
      ),
    environment: () => Promise.reject(new Error(reason)),
    runTokens: (entries) =>
      Promise.resolve(
        new Map(
          entries.map(({ pid }): [number, ProcessRunTokenObservation] => [
            pid,
            { state: "unavailable", reason },
          ]),
        ),
      ),
    signalGroup: (group) => {
      signals.push(group);
    },
  };
  return { host, signals };
};

const cleanup = (host: ProcessOwnershipHost) =>
  cleanupOwnedProcessGroup(
    {
      runId: "run-token",
      leaderPid: 100,
      processGroupId: 100,
      sweepTokenOwnedProcesses: true,
      evidenceOwner: new ProcessOwnershipEvidenceOwner(),
    },
    host,
  );

describe("darwin token reads during the exit window", () => {
  // Property: a candidate whose token read fails with EINVAL (sysctl 22) is
  // still in its exit path, so it is not provably live; once it leaves the
  // process table within the grace window the cleanup is complete.
  it("treats an EINVAL token read that resolves to exit within the grace window as cleaned", async () => {
    const { host, signals } = hostFor("sysctl_failed_22", 300);
    await expect(cleanup(host)).resolves.toMatchObject({ cleaned: true });
    expect(signals).toEqual([]);
  });

  // Property: a malformed procargs buffer that resolves to exit is treated the
  // same way; the classification does not depend on the failure's spelling.
  it("treats a malformed procargs read that resolves to exit within the grace window as cleaned", async () => {
    const { host } = hostFor("malformed_procargs", 300);
    await expect(cleanup(host)).resolves.toMatchObject({ cleaned: true });
  });

  // Property: a candidate that stays live past the grace window with an
  // unreadable token is not proven absent and keeps the fail-closed result.
  it("keeps a still-live candidate with an unreadable token fail-closed after the grace window", async () => {
    const { host } = hostFor("malformed_procargs", undefined);
    await expect(cleanup(host)).resolves.toMatchObject({
      cleaned: false,
      reason: expect.stringContaining("malformed_procargs=1"),
    });
  });
});
