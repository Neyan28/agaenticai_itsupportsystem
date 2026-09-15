CREATE TABLE IF NOT EXISTS it_members (
    member_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    active_tickets INT DEFAULT 0
);

INSERT INTO it_members (name) VALUES
    ('Alice'),
    ('Bob'),
    ('Charlie'),
    ('Diana');

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id SERIAL PRIMARY KEY,
    user_query TEXT NOT NULL,
    solution TEXT,
    status VARCHAR(20) DEFAULT 'open',
    assigned_to INT REFERENCES it_members(member_id),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);
