import { expect, test } from "vitest";
import { fieldErrors } from "./errors";

test("fieldErrors maps nested 422 locs", () => {
  // catches: nested validation errors shown nowhere
  const d = [{ loc: ["body", "details", "line_items", 1, "job_type_id"], msg: "Unknown job type" }];
  expect(fieldErrors(d)).toEqual({ "details.line_items.1.job_type_id": "Unknown job type" });
});
