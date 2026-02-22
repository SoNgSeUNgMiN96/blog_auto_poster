from __future__ import annotations

import logging

from app.config import get_settings
from app.services.engine import OTTGenEngine


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def main() -> None:
    settings = get_settings()
    engine = OTTGenEngine(settings)

    parse_result = engine.parse_sources()
    generate_result = engine.generate_daily_batch()
    print({"parse": parse_result, "generate": generate_result})


if __name__ == "__main__":
    main()
