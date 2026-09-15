# FastAPI basic CRUD example
# Run: uvicorn main:app --reload

from fastapi import FastAPI
from pydantic import BaseModel


# Create FastAPI application
app = FastAPI()


# Pydantic model
# Ye define karta hai ki Note mein kya data hoga
class Note(BaseModel):
    title: str
    content: str
    completed: bool = False


# Temporary database
# Abhi hum database ki jagah list use kar rahe hain
notes = []


# GET request
# Saare notes return karega
@app.get("/notes")
def get_notes():
    return notes


# GET request with ID
# Ek specific note return karega
@app.get("/notes/{note_id}")
def get_note(note_id: int):
    return notes[note_id]


# POST request
# Naya note create karega
@app.post("/notes")
def create_note(note: Note):
    notes.append(note)
    return note


# PUT request
# Existing note ko replace/update karega
@app.put("/notes/{note_id}")
def update_note(note_id: int, note: Note):
    notes[note_id] = note
    return note


# DELETE request
# Note delete karega
@app.delete("/notes/{note_id}")
def delete_note(note_id: int):
    deleted_note = notes.pop(note_id)
    return deleted_note
