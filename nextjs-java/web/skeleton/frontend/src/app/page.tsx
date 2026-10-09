"use client";
import { useEffect, useState } from "react";
import { validNote } from "../lib/validation";
type Note = { id: string; text: string };
async function loadNotes(): Promise<Note[]> {
  const response = await fetch("/api/notes", { cache: "no-store" });
  if (!response.ok) throw new Error("Could not load notes");
  return response.json();
}
export default function Notes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function refresh() {
    setNotes(await loadNotes());
  }
  useEffect(() => {
    let active = true;
    loadNotes().then(notes => { if (active) setNotes(notes); })
      .catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!validNote(text)) { setError("Enter 1–200 Unicode characters"); return; }
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/notes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      if (!response.ok) throw new Error("Could not save note");
      setText(""); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); }
    finally { setBusy(false); }
  }
  return <main><h1>Notes</h1><form onSubmit={submit}>
    <label htmlFor="note">Note (1–200 Unicode characters)</label>
    <textarea id="note" value={text} onChange={e => setText(e.target.value)} />
    <button disabled={busy} type="submit">Save note</button>
  </form><button onClick={() => refresh().catch(e => setError(e.message))}>Refresh</button>
    {error && <p role="alert">{error}</p>}
    <ul>{notes.map(note => <li key={note.id}>{note.text}</li>)}</ul>
  </main>;
}
