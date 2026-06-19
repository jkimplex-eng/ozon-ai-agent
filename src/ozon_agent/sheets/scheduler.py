"""Background auto-refresh scheduler for Google Sheets sync."""
from __future__ import annotations

import logging
import signal
import threading
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ozon_agent.sheets.sync import sync_all

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_stop_event = threading.Event()


def start_watcher(
    interval_minutes: int = 30,
    spreadsheet_id: str | None = None,
    source: str | None = None,
) -> None:
    """Start background sync scheduler.

    Syncs all tabs every `interval_minutes`. Runs until interrupted.
    """
    global _scheduler

    _scheduler = BackgroundScheduler()
    trigger = IntervalTrigger(minutes=interval_minutes)
    _scheduler.add_job(
        _run_sync,
        trigger=trigger,
        kwargs={"spreadsheet_id": spreadsheet_id, "source": source},
        id="sheets_sync",
        name="Google Sheets auto-sync",
        next_run_time=datetime.now(UTC),
    )
    _scheduler.start()
    logger.info(
        "Sheets watcher started — syncing every %d minutes", interval_minutes
    )

    def _shutdown(signum: int, frame: object) -> None:
        logger.info("Shutting down sheets watcher...")
        stop_watcher()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while not _stop_event.is_set():
            _stop_event.wait(timeout=1)
    except KeyboardInterrupt:
        stop_watcher()


def stop_watcher() -> None:
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    _stop_event.set()
    logger.info("Sheets watcher stopped")


def _run_sync(spreadsheet_id: str | None = None, source: str | None = None) -> None:
    """Execute a sync cycle."""
    try:
        results = sync_all(spreadsheet_id=spreadsheet_id, source=source)
        total = sum(v for v in results.values() if v > 0)
        failed = sum(1 for v in results.values() if v < 0)
        logger.info(
            "Sync complete: %d rows across %d tabs (%d failed)",
            total, len(results), failed,
        )
    except Exception as e:
        logger.error("Sync cycle failed: %s", e)
