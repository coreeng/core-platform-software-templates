package io.cecg.notes;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/notes")
public class Notes {
    private final JdbcTemplate jdbc;
    public Notes(JdbcTemplate jdbc) { this.jdbc = jdbc; }
    public record Input(String text) {}
    public record Note(UUID id, String text) {}
    static boolean valid(String text) {
        return text != null && !text.contains("\u0000") && text.codePointCount(0, text.length()) >= 1 && text.codePointCount(0, text.length()) <= 200;
    }
    @GetMapping
    public List<Note> list() {
        return jdbc.query("SELECT id, text FROM notes ORDER BY created_at, id", (rs, row) -> new Note(rs.getObject("id", UUID.class), rs.getString("text")));
    }
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Note create(@RequestBody Input input) {
        if (!valid(input.text())) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Note must contain 1–200 Unicode characters");
        var note = new Note(UUID.randomUUID(), input.text());
        jdbc.update("INSERT INTO notes(id, text) VALUES (?, ?)", note.id(), note.text());
        return note;
    }
    // Internal cleanup API: UUID and exact text must both match; no bulk deletion.
    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable UUID id, @RequestBody Input input) {
        jdbc.update("DELETE FROM notes WHERE id = ? AND text = ?", id, input.text());
    }
}
