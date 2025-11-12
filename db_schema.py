import sqlite3

# db_schema.py
# Creates an SQLite3 database with the requested schema.


SQL_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS "user" (
    userID     INTEGER PRIMARY KEY,
    username   TEXT NOT NULL,
    email      TEXT UNIQUE,
    password   TEXT,
    aubID      INTEGER,
    isDriver   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Car (
    carId    TEXT PRIMARY KEY,
    cartype  TEXT,
    carPlate TEXT,
    capacity INTEGER,
    ownerID  INTEGER NOT NULL,
    FOREIGN KEY(ownerID) REFERENCES "user"(userID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS schedule (
    scheduleID TEXT PRIMARY KEY,
    userID     INTEGER NOT NULL,
    FOREIGN KEY(userID) REFERENCES "user"(userID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Ride (
    rideID     TEXT PRIMARY KEY,
    ownerID    INTEGER NOT NULL,
    carId      TEXT,
    source     TEXT,
    destination TEXT,
    startTime  DATE,
    endTime    DATE,
    scheduleID TEXT,
    FOREIGN KEY(ownerID) REFERENCES "user"(userID) ON DELETE CASCADE,
    FOREIGN KEY(carId) REFERENCES Car(carId) ON DELETE SET NULL,
    FOREIGN KEY(scheduleID) REFERENCES schedule(scheduleID) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Rider (
    userID INTEGER NOT NULL,
    rideID TEXT NOT NULL,
    PRIMARY KEY(userID, rideID),
    FOREIGN KEY(userID) REFERENCES "user"(userID) ON DELETE CASCADE,
    FOREIGN KEY(rideID) REFERENCES Ride(rideID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Request (
    requestID   TEXT PRIMARY KEY,
    riderID     INTEGER NOT NULL,
    rideID      TEXT NOT NULL,
    status      TEXT,
    requestTime DATE,
    FOREIGN KEY(riderID) REFERENCES "user"(userID) ON DELETE CASCADE,
    FOREIGN KEY(rideID) REFERENCES Ride(rideID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS IpInfos (
    userID     INTEGER,
    userCurrentIP TEXT NOT NULL,
    FOREIGN KEY(userID) REFERENCES "user"(userID) ON DELETE CASCADE
);
"""

def create_schema(db_path: str = "aubus.db") -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SQL_SCHEMA)
        conn.commit()
    finally:
        conn.close()

create_schema()

