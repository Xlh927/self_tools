"""
Notes Manager - CRUD operations and Git sync for command notes
"""
import json
import os
import subprocess
from datetime import datetime
from uuid import uuid4
from pathlib import Path

NOTES_DIR = Path(__file__).parent / 'notes'
NOTES_FILE = NOTES_DIR / 'commands.json'


def ensure_notes_file():
    """Ensure notes directory and file exist"""
    NOTES_DIR.mkdir(exist_ok=True)
    if not NOTES_FILE.exists():
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump({'notes': []}, f, ensure_ascii=False, indent=2)


def load_notes():
    """Load all notes from JSON file"""
    ensure_notes_file()
    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('notes', [])


def save_notes(notes):
    """Save notes to JSON file"""
    ensure_notes_file()
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump({'notes': notes}, f, ensure_ascii=False, indent=2)


def get_all_notes(category=None, search=None):
    """Get all notes with optional filtering"""
    notes = load_notes()
    
    if category:
        notes = [n for n in notes if n.get('category', '').lower() == category.lower()]
    
    if search:
        search_lower = search.lower()
        notes = [n for n in notes if 
                 search_lower in n.get('title', '').lower() or
                 search_lower in n.get('command', '').lower() or
                 search_lower in n.get('description', '').lower()]
    
    return notes


def get_note_by_id(note_id):
    """Get a single note by ID"""
    notes = load_notes()
    for note in notes:
        if note.get('id') == note_id:
            return note
    return None


def create_note(title, category, command, description='', tags=None):
    """Create a new note"""
    notes = load_notes()
    
    new_note = {
        'id': str(uuid4()),
        'title': title,
        'category': category,
        'command': command,
        'description': description,
        'tags': tags or [],
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'updated_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    notes.append(new_note)
    save_notes(notes)
    return new_note


def update_note(note_id, **kwargs):
    """Update an existing note"""
    notes = load_notes()
    
    for i, note in enumerate(notes):
        if note.get('id') == note_id:
            # Update allowed fields
            for key in ['title', 'category', 'command', 'description', 'tags']:
                if key in kwargs:
                    note[key] = kwargs[key]
            
            note['updated_at'] = datetime.utcnow().isoformat() + 'Z'
            notes[i] = note
            save_notes(notes)
            return note
    
    return None


def delete_note(note_id):
    """Delete a note by ID"""
    notes = load_notes()
    original_len = len(notes)
    
    notes = [n for n in notes if n.get('id') != note_id]
    
    if len(notes) < original_len:
        save_notes(notes)
        return True
    return False


# Git operations removed as per user request

