from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import get_settings
from app.services.engine import OTTGenEngine


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def run_scheduler() -> None:
    settings = get_settings()
    engine = OTTGenEngine(settings)
    scheduler = BlockingScheduler(timezone=settings.timezone)

    scheduler.add_job(
        engine.parse_sources,
        "cron",
        hour=settings.effective_parse_hour,
        minute=settings.effective_parse_minute,
    )
    for hour in settings.publish_hours_list:
        scheduler.add_job(engine.generate_daily_batch, "cron", hour=hour, minute=settings.effective_publish_minute)

    logging.getLogger("ott_gen.scheduler").info(
        "scheduler started | timezone=%s publish_hours=%s publish_minute=%s parse_hour=%s parse_minute=%s daily_limit=%s submit_per_run=%s",
        settings.timezone,
        settings.publish_hours_list,
        settings.effective_publish_minute,
        settings.effective_parse_hour,
        settings.effective_parse_minute,
        settings.daily_generate_limit,
        settings.effective_submit_per_run_limit,
    )
    scheduler.start()


if __name__ == "__main__":
    run_scheduler()
