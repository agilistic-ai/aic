"""Bound input before spending a model call."""

MAX_NOTE_BYTES = 2000


def require_note(note: str) -> str:
    if not isinstance(note, str) or not note.strip():
        raise ValueError("Provide a nonempty note.")
    if len(note.encode("utf-8")) > MAX_NOTE_BYTES:
        raise ValueError("Notes may contain at most 2,000 UTF-8 bytes.")
    return note


def read_note(path):
    with open(path, "rb") as source:
        data = source.read(MAX_NOTE_BYTES + 1)
    if len(data) > MAX_NOTE_BYTES:
        raise ValueError("Notes may contain at most 2,000 UTF-8 bytes.")
    try:
        return require_note(data.decode("utf-8"))
    except UnicodeDecodeError:
        raise ValueError("The note must be UTF-8 text.") from None
