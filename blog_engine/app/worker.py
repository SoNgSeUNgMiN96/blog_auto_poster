from __future__ import annotations

import argparse
import json

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.main import _process_queue_posts


def main() -> None:
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
    args = parser.parse_args()

    with SessionLocal() as db:
        result = _process_queue_posts(db, args.limit)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
