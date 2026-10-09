export function validNote(text: unknown): text is string {
  return typeof text === "string" && [...text].length >= 1 && [...text].length <= 200 && !text.includes("\u0000");
}
