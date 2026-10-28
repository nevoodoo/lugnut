import { ApiError } from "../../api/client";
import { fieldErrors } from "../../lib/errors";

export const errorsOf = (e: unknown): Record<string, string> =>
  e instanceof ApiError ? { ...fieldErrors(e.detail), form: e.message } : { form: e instanceof Error ? e.message : String(e) };
