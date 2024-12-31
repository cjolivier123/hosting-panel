-- Create a new table with server stats columns
CREATE TABLE server_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    server_type VARCHAR(50) NOT NULL,
    user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    url_code VARCHAR(50) UNIQUE,
    is_online BOOLEAN DEFAULT 0,
    cpu_usage FLOAT DEFAULT 0.0,
    memory_usage FLOAT DEFAULT 0.0,
    uptime DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- Copy data from the old table to the new one
INSERT INTO server_new (id, name, server_type, user_id, created_at, url_code, is_online)
SELECT id, name, server_type, user_id, created_at, url_code, is_online FROM server;

-- Drop the old table
DROP TABLE server;

-- Rename the new table to the original name
ALTER TABLE server_new RENAME TO server;
