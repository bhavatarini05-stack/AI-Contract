"""Daily scan that turns upcoming obligation dates into in-app alerts."""

from __future__ import annotations

import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Alert, Obligation
from app.pipeline.obligations import alert_for, alert_message

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def scan_alerts(today: date | None = None) -> int:
    today = today or date.today()
    created = 0
    db = SessionLocal()
    try:
        obls = db.scalars(
            select(Obligation).where(Obligation.status == "open", Obligation.due_date.is_not(None))
        )
        for o in obls:
            already = {a.threshold_days for a in o.alerts}
            t = alert_for(o.due_date, today, already)
            if t is None:
                continue
            db.add(
                Alert(
                    obligation_id=o.id,
                    contract_id=o.contract_id,
                    threshold_days=t,
                    fire_date=today,
                    message=alert_message(o.kind, o.description, o.due_date, today),
                )
            )
            created += 1
        db.commit()
    finally:
        db.close()
    if created:
        log.info("Created %s alert(s)", created)
    return created


def start() -> None:
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        scan_alerts, "cron", hour=8, minute=0, id="alert_scan", replace_existing=True
    )
    _scheduler.start()
    scan_alerts()  # also run once at startup


def stop() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
