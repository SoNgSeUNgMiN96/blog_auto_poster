from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import get_settings
from app.services.collector import AEngineCollector


def run_scheduler() -> None:
    settings = get_settings()
    collector = AEngineCollector(settings)

    scheduler = BlockingScheduler(timezone=settings.timezone)
    scheduler.add_job(collector.run_once, "cron", hour=settings.cron_hour_1, minute=0)
    scheduler.add_job(collector.run_once, "cron", hour=settings.cron_hour_2, minute=0)

    print(
        f"A-engine scheduler started. timezone={settings.timezone}, "
        f"hours=[{settings.cron_hour_1}, {settings.cron_hour_2}]"
    )
    scheduler.start()


if __name__ == "__main__":
    run_scheduler()
