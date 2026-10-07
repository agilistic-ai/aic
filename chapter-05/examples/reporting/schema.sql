CREATE TABLE workshops (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    event_date TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity >= 0)
);
CREATE TABLE bookings (
    id TEXT PRIMARY KEY,
    workshop_id TEXT NOT NULL REFERENCES workshops(id),
    seats INTEGER NOT NULL CHECK (seats > 0),
    status TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
    contribution_cents INTEGER CHECK (contribution_cents >= 0)
);
INSERT INTO workshops VALUES
    ('may', 'May repair workshop', '2026-05-16', 12),
    ('november', 'November repair workshop', '2026-11-07', 20),
    ('december', 'December repair workshop', '2026-12-05', 12);
INSERT INTO bookings VALUES
    ('b1', 'november', 2, 'confirmed', 500),
    ('b2', 'november', 3, 'confirmed', NULL),
    ('b3', 'november', 4, 'cancelled', 0),
    ('b4', 'may', 12, 'confirmed', 0);
