import { validNote } from "./validation";
test("counts PostgreSQL Unicode codepoints, not UTF-16 units", () => {
  expect(validNote("😀".repeat(200))).toBe(true);
  expect(validNote("😀".repeat(201))).toBe(false);
  expect(validNote("")).toBe(false);
  expect(validNote(null)).toBe(false);
  expect(validNote("a\u0000b")).toBe(false);
});
