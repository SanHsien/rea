import { z } from "incur";

import type { CliInstance } from "./types.js";
import { visitRegisteredCommands } from "./visitRegisteredCommands.js";

type CommandInputs = Partial<Record<(typeof INPUT_GROUPS)[number], unknown>>;

const INPUT_GROUPS = ["args", "env", "options"] as const;

/**
 * Advertise parser-filled defaults as omittable CLI inputs.
 *
 * Incur derives `--schema`, the `--llms` manifests, and help synopses from
 * Zod's output view, where a defaulted field always has a value and is
 * therefore listed as required. Callers may omit such a field, so each one is
 * wrapped as optional while its default, constraints, metadata, and parsed
 * value stay unchanged.
 */
export const presentOmittableDefaults = (cli: CliInstance): void => {
  visitRegisteredCommands(cli, (command) => presentInputs(command));
};

const presentInputs = (command: CommandInputs): void => {
  for (const group of INPUT_GROUPS) {
    const schema = command[group];
    if (schema instanceof z.ZodObject)
      command[group] = withOmittableDefaults(schema);
  }
};

const withOmittableDefaults = (schema: z.ZodObject): z.ZodObject => {
  const omittable = Object.entries(schema.shape).filter(([, field]) =>
    fillsOmission(field),
  );
  if (omittable.length === 0) return schema;
  return schema.safeExtend(
    Object.fromEntries(
      omittable.map(([key, field]) => [key, optionalWithMetadata(field)]),
    ),
  );
};

/**
 * Zod accepts an omitted value (`optin`) but always produces one (`optout`).
 *
 * Zod 4.4 reports a `.default()` field's `optin` as `"optional"`; Zod 4.6
 * reports `"defaulted"`. Both mean "the parser fills an omitted value", so a
 * field that is merely optional (`optout` is `"optional"`) never matches.
 *
 * This whole module exists because Incur's `Schema.js` calls `z.toJSONSchema`
 * without `io: "input"` (observed in incur 0.6.1 and 0.7.1), so Zod's output
 * view lists every defaulted field as required in `--schema`, `--llms`, and MCP
 * output. That has been true since Zod 4.4; the only 4.6 change this module had
 * to follow is the `optin` value above.
 * Remove it once Incur passes `io: "input"` and
 * `tests/boundary/cli/cliInputSchemaRequired.test.ts` stays green without it.
 */
const fillsOmission = (field: z.ZodType): boolean =>
  (field._zod.optin === "optional" || field._zod.optin === "defaulted") &&
  field._zod.optout === undefined;

const optionalWithMetadata = (field: z.ZodType): z.ZodType => {
  const metadata = field.meta();
  return metadata === undefined
    ? field.optional()
    : field.optional().meta(metadata);
};
