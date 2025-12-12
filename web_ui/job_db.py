"""
SQLite-based job manager for multi-session support.
Provides atomic operations to prevent race conditions.
"""
import os
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class JobDB:
    """Thread-safe SQLite job manager with atomic operations."""

    MAX_CONCURRENT_JOBS = int(os.getenv('MAX_CONCURRENT_JOBS', '5'))

    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path or os.getenv('JOB_DB_PATH', 'jobs.db'))
        self._local = threading.local()
        self._init_db()
        logger.info(f"JobDB initialized at {self.db_path}, max concurrent: {self.MAX_CONCURRENT_JOBS}")

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                input_mode TEXT,
                started_at TEXT,
                completed_at TEXT,
                post_id TEXT,
                error TEXT,
                text_preview TEXT
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_started ON jobs(started_at)')
        conn.commit()
        logger.info("JobDB schema initialized")

    def can_start_new_job(self) -> bool:
        """Check if under concurrency limit."""
        conn = self._get_conn()
        count = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'running'"
        ).fetchone()[0]
        return count < self.MAX_CONCURRENT_JOBS

    def get_running_count(self) -> int:
        """Get number of currently running jobs."""
        conn = self._get_conn()
        return conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'running'"
        ).fetchone()[0]

    def create_job(self, job_id: str, input_mode: str = 'sheet', text_preview: str = None) -> bool:
        """
        Atomically create job if under concurrency limit.
        Uses BEGIN IMMEDIATE for atomic check-and-insert.

        Returns:
            True if job was created, False if at capacity
        """
        conn = self._get_conn()
        try:
            # BEGIN IMMEDIATE acquires write lock immediately
            conn.execute('BEGIN IMMEDIATE')

            count = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'running'"
            ).fetchone()[0]

            if count >= self.MAX_CONCURRENT_JOBS:
                conn.rollback()
                logger.warning(f"Job {job_id} rejected: {count}/{self.MAX_CONCURRENT_JOBS} jobs running")
                return False

            conn.execute('''
                INSERT INTO jobs (id, status, input_mode, started_at, text_preview)
                VALUES (?, 'running', ?, ?, ?)
            ''', (job_id, input_mode, datetime.now().isoformat(), text_preview))

            conn.commit()
            logger.info(f"Job {job_id} created ({input_mode} mode). Running: {count + 1}/{self.MAX_CONCURRENT_JOBS}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating job {job_id}: {e}")
            raise

    def complete_job(self, job_id: str, post_id: str = None):
        """Mark job as successfully completed."""
        conn = self._get_conn()
        conn.execute('''
            UPDATE jobs
            SET status = 'complete', post_id = ?, completed_at = ?
            WHERE id = ?
        ''', (post_id, datetime.now().isoformat(), job_id))
        conn.commit()
        logger.info(f"Job {job_id} completed. Post: {post_id}")

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed with error message."""
        conn = self._get_conn()
        # Truncate error to reasonable length
        error_truncated = error[:500] if error else 'Unknown error'
        conn.execute('''
            UPDATE jobs
            SET status = 'error', error = ?, completed_at = ?
            WHERE id = ?
        ''', (error_truncated, datetime.now().isoformat(), job_id))
        conn.commit()
        logger.error(f"Job {job_id} failed: {error_truncated[:100]}...")

    def get_job(self, job_id: str) -> dict:
        """Get job by ID."""
        conn = self._get_conn()
        row = conn.execute(
            'SELECT * FROM jobs WHERE id = ?', (job_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_running_jobs(self) -> list:
        """Get all currently running jobs."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = 'running' ORDER BY started_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent_jobs(self, limit: int = 20) -> list:
        """Get recent jobs (for UI display)."""
        conn = self._get_conn()
        rows = conn.execute('''
            SELECT * FROM jobs
            ORDER BY started_at DESC
            LIMIT ?
        ''', (limit,)).fetchall()
        return [dict(r) for r in rows]

    def cleanup_stale_jobs(self) -> int:
        """
        Mark any running jobs as error (called on server startup).
        Returns number of jobs cleaned up.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'running'"
        )
        stale_count = cursor.fetchone()[0]

        if stale_count > 0:
            conn.execute('''
                UPDATE jobs
                SET status = 'error', error = 'Server restarted during generation', completed_at = ?
                WHERE status = 'running'
            ''', (datetime.now().isoformat(),))
            conn.commit()
            logger.warning(f"Cleaned up {stale_count} stale job(s)")

        return stale_count

    def delete_old_jobs(self, days: int = 7) -> int:
        """Delete jobs older than specified days. Returns count deleted."""
        conn = self._get_conn()
        cutoff = datetime.now().isoformat()[:10]  # Just date part
        cursor = conn.execute('''
            DELETE FROM jobs
            WHERE date(started_at) < date(?, '-' || ? || ' days')
        ''', (cutoff, days))
        conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info(f"Deleted {deleted} jobs older than {days} days")
        return deleted


# Global instance - initialized on import
job_db = JobDB()
