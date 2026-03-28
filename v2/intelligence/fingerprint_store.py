import sqlite3
import json
import numpy as np
from datetime import datetime

class FingerprintStore:
    """Stores anomaly fingerprints for similarity lookup. Self-learning: tracks if past remediation worked."""

    def __init__(self, db_path="/app/data/fingerprints.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT,
                root_cause TEXT,
                confidence REAL,
                embedding TEXT,
                action_taken TEXT,
                was_successful INTEGER DEFAULT -1,
                created_at TEXT
            )
        """)
        self.conn.commit()

    def store(self, service, root_cause, confidence, embedding, action_taken):
        self.conn.execute(
            "INSERT INTO incidents (service, root_cause, confidence, embedding, action_taken, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (service, root_cause, confidence, json.dumps(embedding), action_taken, datetime.utcnow().isoformat())
        )
        self.conn.commit()

    def mark_success(self, incident_id, was_successful: bool):
        self.conn.execute("UPDATE incidents SET was_successful = ? WHERE id = ?", (1 if was_successful else 0, incident_id))
        self.conn.commit()

    def find_similar(self, embedding, threshold=0.85):
        """Find the most similar past incident by cosine similarity."""
        rows = self.conn.execute("SELECT id, service, root_cause, confidence, embedding, action_taken, was_successful FROM incidents ORDER BY id DESC LIMIT 100").fetchall()
        if not rows:
            return None

        query_vec = np.array(embedding)
        best_match = None
        best_sim = 0.0

        for row in rows:
            stored_vec = np.array(json.loads(row[4]))
            sim = float(np.dot(query_vec, stored_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(stored_vec) + 1e-8))
            if sim > best_sim and sim > threshold:
                best_sim = sim
                success_count = self.conn.execute("SELECT COUNT(*) FROM incidents WHERE root_cause=? AND was_successful=1", (row[2],)).fetchone()[0]
                total_count = self.conn.execute("SELECT COUNT(*) FROM incidents WHERE root_cause=? AND was_successful!=-1", (row[2],)).fetchone()[0]
                best_match = {
                    "incident_id": row[0],
                    "service": row[1],
                    "root_cause": row[2],
                    "similarity": sim,
                    "action_taken": row[5],
                    "success_rate": f"{success_count}/{total_count}" if total_count > 0 else "N/A"
                }
        return best_match

    def get_recent(self, limit=20):
        rows = self.conn.execute("SELECT id, service, root_cause, confidence, action_taken, was_successful, created_at FROM incidents ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r[0], "service": r[1], "root_cause": r[2], "confidence": r[3], "action": r[4], "success": r[5], "time": r[6]} for r in rows]
