CREATE TABLE IF NOT EXISTS "log" (
	"id"	INTEGER UNIQUE,
	"date"	TEXT,
	"message"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE IF NOT EXISTS "log_socket" (
	"log_id"	INTEGER,
	"address"	TEXT,
	"port"	INTEGER,
	FOREIGN KEY("log_id") REFERENCES "log"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "log_topic" (
	"log_id"	INTEGER,
	"topic"	TEXT,
	FOREIGN KEY("log_id") REFERENCES "log"("id") ON DELETE CASCADE
);
