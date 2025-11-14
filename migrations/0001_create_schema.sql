-- Initial schema for the Bob Family Tree API.

CREATE TABLE IF NOT EXISTS families (
    id INTEGER PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    first_name VARCHAR(64) NOT NULL,
    last_name VARCHAR(64) NOT NULL,
    birth_date DATE,
    death_date DATE,
    biography TEXT,
    family_id INTEGER,
    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    city VARCHAR(128),
    state VARCHAR(128),
    country VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS person_locations (
    id INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('birthplace', 'residence', 'burial')),
    UNIQUE(person_id, role),
    FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY,
    from_person_id INTEGER NOT NULL,
    to_person_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('parent', 'child', 'spouse')),
    UNIQUE(from_person_id, to_person_id, type),
    FOREIGN KEY (from_person_id) REFERENCES people(id) ON DELETE CASCADE,
    FOREIGN KEY (to_person_id) REFERENCES people(id) ON DELETE CASCADE
);
