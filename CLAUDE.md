# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Bob Family Tree is a FastAPI backend for managing people, families, locations, and relationships. The system automatically maintains reciprocal relationship records (e.g., when you add a parent→child relationship, it creates the corresponding child→parent relationship automatically).

## Commands

### Installation

Install dependencies in a virtual environment:
```bash
pip install -e .[dev]
```

### Database Setup

Create the SQLite database schema:
```bash
sqlite3 family_tree.db < migrations/0001_create_schema.sql
```

Alternatively, SQLAlchemy can create the schema automatically at startup during development.

### Running the Server

Start the development server:
```bash
uvicorn app.main:app --reload --app-dir src
```

Access the API:
- Interactive API docs: http://127.0.0.1:8000/docs
- HTML form UI: http://127.0.0.1:8000/

### Testing

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_people_api.py
```

Run single test:
```bash
pytest tests/test_relationships_api.py::test_create_parent_child_relationship
```

## Architecture

### Layer Structure

The application follows a clean layered architecture:

- **main.py**: FastAPI route handlers and HTML UI serving
- **schemas.py**: Pydantic DTOs for request/response validation
- **models.py**: SQLAlchemy ORM models (Person, Family, Location, Relationship, PersonLocation)
- **services.py**: Domain logic for complex operations
- **database.py**: SQLAlchemy engine and session dependency injection
- **config.py**: Application settings

### Core Domain Concepts

**Families**: Named groups (e.g., "Smith Family") that people can belong to. Deleting a family cascades to all members.

**People**: Individuals with basic biographical data (names, dates, biography). Each person can optionally belong to one family and have multiple location associations.

**Locations**: Reusable place records that can be assigned to people in different roles (birthplace, residence, burial). Locations are shared entities—multiple people can reference the same location.

**Relationships**: Directed links between two people with a type (parent, child, spouse). The system enforces a unique constraint on (from_person_id, to_person_id, type) tuples.

**PersonLocation**: Join table linking people to locations with a role. Each person can have at most one location per role (enforced by `apply_person_locations`).

### Reciprocal Relationship Management

The services layer automatically maintains relationship symmetry:

- Creating `Person A → parent → Person B` automatically creates `Person B → child → Person A`
- Creating `Person A → spouse → Person B` automatically creates `Person B → spouse → Person A`
- Updating or deleting a relationship removes the old reciprocal and creates a new one if needed

This logic is centralized in `services.py`:
- `create_relationship()`: Validates and creates both forward and reciprocal relationships
- `update_relationship()`: Removes old reciprocal, updates type, creates new reciprocal
- `delete_relationship()`: Removes both the relationship and its reciprocal
- `_ensure_reciprocal()`: Creates the reciprocal if it doesn't exist
- `_remove_reciprocal()`: Deletes the reciprocal relationship

The `RECIPROCAL_RELATIONSHIPS` mapping defines the bidirectional pairs: parent↔child, spouse↔spouse.

### Location Assignment Pattern

People can have multiple location assignments with different roles (birthplace, residence, burial). The `apply_person_locations()` service function synchronizes the person's location associations with a list of assignments:

1. Validates no duplicate roles in the request
2. Removes existing location links that aren't in the new set
3. For each assignment, either creates a new location or references an existing one
4. Creates or updates PersonLocation join records

This allows the UI to send either `location_id` (reference existing) or `new_location` (create inline) for each role.

### HTML Form UI

The application serves a lightweight HTML form at the root path that demonstrates the API. The form allows creating a person with:
- Inline family creation or selection
- Inline location creation for birthplace, residence, and burial
- Sequential API calls to `/families`, `/locations`, and `/people`

This UI is useful for manual testing and as a reference implementation for client integration.

## Important Conventions

- All route handlers use dependency injection for the database session via `get_db()`
- Tests use an in-memory SQLite database created fresh for each test via the `db_session` fixture
- The Person model uses cascade delete for relationships and locations (deleting a person removes all their relationships and location links)
- Relationship uniqueness is enforced at the database level via a unique constraint
- Location roles are validated via the `LocationRole` enum
- The migration script in `migrations/0001_create_schema.sql` should be kept in sync with model changes
