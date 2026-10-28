import { expect, test } from "vitest";
import { formatDate, parseMoney } from "./format";
import type { InstallSettings as S } from "./format";

test("parseMoney accepts common forms and rejects garbage", () => {
  // catches: money saved as 0 or off by 100x
  for (const t of ["1,284.50", "1284.5", "$1284.50", " 1284.50 "]) expect(parseMoney(t, "AUD")).toBe(128450);
  expect(parseMoney("1284", "AUD")).toBe(128400);
  expect(parseMoney("", "AUD")).toBeNull();
  expect(parseMoney("12.345", "AUD")).toBe("invalid");
  expect(parseMoney("abc", "AUD")).toBe("invalid");
  expect(parseMoney("1,284", "JPY")).toBe(1284);
  expect(parseMoney("12.5", "JPY")).toBe("invalid");
});

test("formatDate follows install format", () => {
  expect(formatDate("2027-01-15", { date_format: "DD/MM/YYYY" } as S)).toBe("15/01/2027");
  expect(formatDate("2027-01-15", { date_format: "MM/DD/YYYY" } as S)).toBe("01/15/2027");
});
