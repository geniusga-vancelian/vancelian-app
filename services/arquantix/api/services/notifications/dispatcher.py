"""NotificationDispatcher — batched, async-safe notification writer.

Groups notification inserts and flushes them in chunks (max BATCH_SIZE=500)
to avoid overwhelming the DB with individual INSERTs during mass triggers.
"""
import logging
import threading
import time
from collections import deque
from typing import Optional

from sqlalchemy.orm import Session

from services.notifications.models import Notification

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
FLUSH_INTERVAL_SEC = 0.5


class NotificationDispatcher:
    """Thread-safe queue that batches notification inserts."""

    def __init__(self, db_factory):
        self._db_factory = db_factory
        self._queue: deque[dict] = deque()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stats = {
            "enqueued": 0,
            "flushed": 0,
            "failures": 0,
        }

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._flush_loop, daemon=True, name="notif-dispatcher")
        self._thread.start()
        logger.info("NotificationDispatcher started (batch_size=%d, interval=%.1fs)", BATCH_SIZE, FLUSH_INTERVAL_SEC)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._flush_batch()

    def enqueue(
        self,
        client_id,
        type_: str,
        title: str,
        body: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> None:
        """Add a notification to the queue. Thread-safe."""
        with self._lock:
            self._queue.append({
                "client_id": client_id,
                "type": type_,
                "title": title,
                "body": body,
                "payload": payload,
            })
            self._stats["enqueued"] += 1

    def enqueue_many(self, items: list[dict]) -> None:
        """Bulk enqueue. Each dict has keys: client_id, type, title, body, payload."""
        with self._lock:
            self._queue.extend(items)
            self._stats["enqueued"] += len(items)

    def flush_sync(self) -> int:
        """Force a synchronous flush (useful for tests). Returns flushed count."""
        return self._flush_batch()

    def _flush_loop(self) -> None:
        while self._running:
            time.sleep(FLUSH_INTERVAL_SEC)
            if self._queue:
                self._flush_batch()

    def _flush_batch(self) -> int:
        """Drain up to BATCH_SIZE items and INSERT them. Returns count inserted."""
        batch: list[dict] = []
        with self._lock:
            while self._queue and len(batch) < BATCH_SIZE:
                batch.append(self._queue.popleft())

        if not batch:
            return 0

        db: Optional[Session] = None
        try:
            db = self._db_factory()
            for item in batch:
                notif = Notification(
                    client_id=item["client_id"],
                    type=item["type"],
                    title=item["title"],
                    body=item.get("body"),
                    payload=item.get("payload"),
                )
                db.add(notif)
            db.commit()
            count = len(batch)
            self._stats["flushed"] += count
            logger.debug("NotificationDispatcher flushed %d notification(s)", count)
            return count
        except Exception:
            if db is not None:
                db.rollback()
            self._stats["failures"] += 1
            logger.exception("NotificationDispatcher flush failed (%d items lost)", len(batch))
            return 0
        finally:
            if db is not None:
                db.close()


_dispatcher: Optional[NotificationDispatcher] = None


def get_dispatcher() -> Optional[NotificationDispatcher]:
    return _dispatcher


def init_dispatcher(db_factory) -> NotificationDispatcher:
    global _dispatcher
    _dispatcher = NotificationDispatcher(db_factory)
    _dispatcher.start()
    return _dispatcher
