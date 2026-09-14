"""FastAPI interview demo. Run: python -m uvicorn main:app --reload

Storage is in memory: restarting clears it; workers do not share it.
This is an unauthenticated learning API, not a production notes service.
"""

from threading import Lock
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteWrite(BaseModel):
    """POST and PUT input. PUT replaces all writable fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=100)
    content: str | None = Field(default=None, max_length=5000)
    completed: bool = False


class NotePatch(BaseModel):
    """Omitted means unchanged. Only content can explicitly be null."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, max_length=5000)
    completed: bool | None = None

    @field_validator("title", "completed", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: Any) -> Any:
        # Defaults are not validated here: omission is allowed, explicit null is not.
        if value is None:
            raise ValueError("This field may be omitted, but cannot be null")
        return value


class NoteRead(NoteWrite):
    """Public output includes a server-generated ID."""

    id: int


class NoteStore:
    def __init__(self) -> None:
        self.notes: dict[int, NoteRead] = {}
        self.next_id = 1
        # Sync routes run in worker threads, so compound writes need a lock.
        self.lock = Lock()


store = NoteStore()


def get_store() -> NoteStore:
    """Dependency injection makes the store replaceable in tests."""
    return store


StoreDep = Annotated[NoteStore, Depends(get_store)]
NoteId = Annotated[int, Path(gt=0, description="Positive note ID")]

app = FastAPI(
    title="FastAPI Interview Notes API",
    version="1.0.0",
    description="Learn GET, POST, PUT, PATCH, DELETE and Pydantic v2 validation.",
)


def find_note(db: NoteStore, note_id: int) -> NoteRead:
    # Call while holding db.lock.
    note = db.notes.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.get("/", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "docs": "/docs"}


@app.post("/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED,
          tags=["Notes"])
def create_note(payload: NoteWrite, response: Response, db: StoreDep) -> NoteRead:
    """POST: create a new note with a server-generated ID."""
    with db.lock:
        note = NoteRead(id=db.next_id, **payload.model_dump())
        db.notes[note.id] = note
        db.next_id += 1
    response.headers["Location"] = f"/notes/{note.id}"
    return note


@app.get("/notes", response_model=list[NoteRead], tags=["Notes"])
def list_notes(
    db: StoreDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    completed: bool | None = None,
) -> list[NoteRead]:
    """GET: list notes, optionally filtered, with bounded pagination."""
    with db.lock:
        notes = sorted(db.notes.values(), key=lambda note: note.id)
        if completed is not None:
            notes = [note for note in notes if note.completed == completed]
        return notes[offset:offset + limit]


@app.get("/notes/{note_id}", response_model=NoteRead, tags=["Notes"])
def get_note(note_id: NoteId, db: StoreDep) -> NoteRead:
    """GET: fetch one resource; return 404 if it does not exist."""
    with db.lock:
        return find_note(db, note_id)


@app.put("/notes/{note_id}", response_model=NoteRead, tags=["Notes"])
def replace_note(note_id: NoteId, payload: NoteWrite, db: StoreDep) -> NoteRead:
    """PUT: replace writable data; omitted content/completed reset to defaults."""
    with db.lock:
        find_note(db, note_id)
        note = NoteRead(id=note_id, **payload.model_dump())
        db.notes[note_id] = note
        return note


@app.patch("/notes/{note_id}", response_model=NoteRead, tags=["Notes"])
def update_note(note_id: NoteId, payload: NotePatch, db: StoreDep) -> NoteRead:
    """PATCH: update only provided fields. An empty object is a no-op."""
    with db.lock:
        existing = find_note(db, note_id)
        changes = payload.model_dump(exclude_unset=True)
        # Revalidate the merged result; model_copy(update=...) does not validate it.
        note = NoteRead.model_validate({**existing.model_dump(), **changes})
        db.notes[note_id] = note
        return note


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT,
            response_class=Response, tags=["Notes"])
def delete_note(note_id: NoteId, db: StoreDep) -> Response:
    """DELETE: remove the resource; 204 has no response body."""
    with db.lock:
        find_note(db, note_id)
        del db.notes[note_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
