"""Who owns which conversation. The messages themselves live in the LangGraph checkpointer.

Postgres when DATABASE_URL is set (the class deployment), in memory otherwise (tests, local runs).
"""

import time
import uuid
from dataclasses import asdict, dataclass


@dataclass
class Thread:
    id: str
    student: str
    persona: str
    title: str
    created_at: float
    updated_at: float

    def to_dict(self) -> dict:
        return asdict(self)


class MemoryThreads:
    def __init__(self):
        self.rows: dict[str, Thread] = {}

    def create(self, student: str, persona: str, title: str, thread_id: str | None = None) -> Thread:
        now = time.time()
        t = Thread(thread_id or str(uuid.uuid4()), student, persona, title, now, now)
        self.rows[t.id] = t
        return t

    def get(self, thread_id: str) -> Thread | None:
        return self.rows.get(thread_id)

    def touch(self, thread_id: str) -> None:
        if thread_id in self.rows:
            self.rows[thread_id].updated_at = time.time()

    def of(self, student: str) -> list[Thread]:
        return sorted((t for t in self.rows.values() if t.student == student), key=lambda t: -t.updated_at)


class PostgresThreads:
    def __init__(self, pool):
        self.pool = pool
        with pool.connection() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS acme_threads (
                    id TEXT PRIMARY KEY, student TEXT NOT NULL, persona TEXT NOT NULL, title TEXT NOT NULL,
                    created_at DOUBLE PRECISION NOT NULL, updated_at DOUBLE PRECISION NOT NULL)"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS acme_threads_student ON acme_threads (student)")

    def _rows(self, sql: str, *args) -> list[Thread]:
        with self.pool.connection() as conn:
            return [Thread(*row) for row in conn.execute(sql, args).fetchall()]

    def create(self, student: str, persona: str, title: str, thread_id: str | None = None) -> Thread:
        now = time.time()
        t = Thread(thread_id or str(uuid.uuid4()), student, persona, title, now, now)
        with self.pool.connection() as conn:
            conn.execute("INSERT INTO acme_threads VALUES (%s, %s, %s, %s, %s, %s)",
                         (t.id, t.student, t.persona, t.title, t.created_at, t.updated_at))
        return t

    def get(self, thread_id: str) -> Thread | None:
        rows = self._rows("SELECT * FROM acme_threads WHERE id = %s", thread_id)
        return rows[0] if rows else None

    def touch(self, thread_id: str) -> None:
        with self.pool.connection() as conn:
            conn.execute("UPDATE acme_threads SET updated_at = %s WHERE id = %s", (time.time(), thread_id))

    def of(self, student: str) -> list[Thread]:
        return self._rows("SELECT * FROM acme_threads WHERE student = %s ORDER BY updated_at DESC", student)
