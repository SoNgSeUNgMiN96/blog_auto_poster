from __future__ import annotations

import argparse
import json
import logging
import random
import time

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.main import _process_queue_posts


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    settings = get_settings()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    parser = argparse.ArgumentParser(description="Process queued blog-engine posts")
    parser.add_argument(
        "--limit",
        type=int,
        default=settings.batch_process_limit,
        help="max number of queued posts to process in this run",
    )
    parser.add_argument(
        "--skip-random-delay",
        action="store_true",
        help="run immediately without random wait",
    )
    args = parser.parse_args()

    delay_seconds = 0
    if not args.skip_random_delay:
        delay_min = max(0, settings.worker_random_delay_min_minutes)
        delay_max = max(delay_min, settings.worker_random_delay_max_minutes)
        if delay_max > 0:
            delay_minutes = random.randint(delay_min, delay_max)
            delay_seconds = delay_minutes * 60
            logging.getLogger("blog_engine.worker").info(
                "random start delay enabled | wait_minutes=%s range=[%s,%s]",
                delay_minutes,
                delay_min,
                delay_max,
            )
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    with SessionLocal() as db:
        result = _process_queue_posts(db, args.limit)
    result["delay_seconds"] = delay_seconds
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
