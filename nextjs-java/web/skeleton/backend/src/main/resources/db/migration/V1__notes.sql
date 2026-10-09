CREATE TABLE notes (
  id UUID PRIMARY KEY,
  text TEXT NOT NULL CHECK (char_length(text) BETWEEN 1 AND 200),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
