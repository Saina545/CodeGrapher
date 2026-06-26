"""
CodeGrapher — Database Manager
Handles PostgreSQL connections, automatic table creation, and queries.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timezone

class DatabaseManager:
    def __init__(self):
        # Uses your local PostgreSQL credentials. Update the password if needed.
        self.db_url = os.environ.get(
            "DATABASE_URL", 
            "postgresql://postgres:admin123@localhost:5433/codegrapher_db"
        )
        self.init_db()

    def get_connection(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def init_db(self):
        """Automatically creates the necessary tables if they don't exist."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Create Users Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        uid VARCHAR(36) PRIMARY KEY,
                        name VARCHAR(80) NOT NULL,
                        email VARCHAR(120) UNIQUE NOT NULL,
                        pw VARCHAR(255) NOT NULL,
                        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # 2. Create Sessions Table (Using JSONB for flexible graph storage)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        sid VARCHAR(255) PRIMARY KEY,
                        uid VARCHAR(36) REFERENCES users(uid) ON DELETE CASCADE,
                        data JSONB NOT NULL,
                        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.commit()

    # ─── USER OPERATIONS ─────────────────────────────────────────────
    def get_user_by_email(self, email):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                return cur.fetchone()
    
    def create_user(self, uid, name, email, pw, created):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        "INSERT INTO users (uid, name, email, pw, created) VALUES (%s, %s, %s, %s, %s)",
                        (uid, name, email, pw, created)
                    )
                    conn.commit()
                    return True
                except psycopg2.IntegrityError:
                    return False  # Email already exists
    
    def update_user_password(self, email, pw):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET pw = %s WHERE email = %s", (pw, email))
                conn.commit()

    # ─── SESSION OPERATIONS ──────────────────────────────────────────
    def get_user_sessions(self, uid):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM sessions WHERE uid = %s ORDER BY updated DESC", (uid,))
                rows = cur.fetchall()
                return [row['data'] for row in rows]

    def get_session(self, sid):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM sessions WHERE sid = %s", (sid,))
                row = cur.fetchone()
                return row['data'] if row else None

    def upsert_session(self, sid, uid, session_data):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                now = datetime.now(timezone.utc).isoformat()
                created = session_data.get('created', now)
                
                cur.execute("""
                    INSERT INTO sessions (sid, uid, data, created, updated) 
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (sid) DO UPDATE 
                    SET data = EXCLUDED.data, updated = EXCLUDED.updated
                """, (sid, uid, json.dumps(session_data), created, now))
                conn.commit()

    def delete_session(self, sid, uid):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE sid = %s AND uid = %s", (sid, uid))
                conn.commit()