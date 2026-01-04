import os
import json
import logging
import psycopg2
from psycopg2.extras import Json

logger = logging.getLogger("agent-db")

class AgentDB:
    def __init__(self):
        self.dsn = os.getenv("POSTGRES_URL", "postgresql://user:pass@postgres:5432/talos_memory")
        self.conn = None
        self._connect()
        self._init_schema()

    def _connect(self):
        try:
            self.conn = psycopg2.connect(self.dsn)
            self.conn.autocommit = True
            logger.info("Connected to Postgres.")
        except Exception as e:
            logger.error(f"Failed to connect to DB: {e}")
            raise

    def _init_schema(self):
        with self.conn.cursor() as cur:
            # Enable pgvector extension (idempotent)
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Sessions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    history JSONB DEFAULT '[]',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Embeddings table (simplified)
            # Embedding dimension for llama/nomic is often 768 or 1024. Let's assume 4096 (llama3) or generic
            # For this demo, we use a generic vector for schema, but might not actively use it in the basic scenario
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT REFERENCES sessions(session_id),
                    content TEXT,
                    embedding VECTOR(768)  -- Generic size, adjust per model
                );
            """)

    def save_session(self, session_id: str, history: list):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sessions (session_id, history)
                VALUES (%s, %s)
                ON CONFLICT (session_id) DO UPDATE
                SET history = %s, updated_at = CURRENT_TIMESTAMP;
            """, (session_id, Json(history), Json(history)))

    def load_session(self, session_id: str) -> list:
        with self.conn.cursor() as cur:
            cur.execute("SELECT history FROM sessions WHERE session_id = %s", (session_id,))
            row = cur.fetchone()
            if row:
                return row[0]
            return []

    def close(self):
        if self.conn:
            self.conn.close()
