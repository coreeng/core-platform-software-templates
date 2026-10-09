package io.cecg.notes;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class NotesTest {
    @Test void postgresCodepointsNotUtf16Units() {
        assertTrue(Notes.valid("😀".repeat(200)));
        assertFalse(Notes.valid("😀".repeat(201)));
        assertFalse(Notes.valid(""));
        assertFalse(Notes.valid(null));
        assertFalse(Notes.valid("a\u0000b"));
        assertTrue(Notes.valid(" "));
    }
    @Test void invalidInputNeverWritesDatabase() {
        var jdbc = mock(JdbcTemplate.class);
        assertThrows(ResponseStatusException.class, () -> new Notes(jdbc).create(new Notes.Input("")));
        verifyNoInteractions(jdbc);
    }
    @Test void creationUsesBoundValuesAndUniqueId() {
        var jdbc = mock(JdbcTemplate.class);
        var note = new Notes(jdbc).create(new Notes.Input("hello"));
        assertNotNull(note.id());
        verify(jdbc).update("INSERT INTO notes(id, text) VALUES (?, ?)", note.id(), "hello");
    }
    @Test void cleanupRequiresExactIdAndText() {
        var jdbc = mock(JdbcTemplate.class);
        var id = java.util.UUID.randomUUID();
        new Notes(jdbc).delete(id, new Notes.Input("owned"));
        verify(jdbc).update("DELETE FROM notes WHERE id = ? AND text = ?", id, "owned");
    }
}
