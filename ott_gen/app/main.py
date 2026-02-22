from __future__ import annotations

import argparse
import logging

from app.config import get_settings
from app.services.engine import OTTGenEngine


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="OTT gen one-shot runner")
    parser.add_argument(
        "--action",
        choices=["submit", "parse", "full"],
        default="submit",
        help=(
            "submit: 일일 한도만 blog_engine 큐로 제출, "
            "parse: 소스 파싱만 수행, full: 파싱 후 일일 한도 제출"
        ),
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = OTTGenEngine(settings)

    if args.action == "parse":
        parse_result = engine.parse_sources()
        print({"action": "parse", "parse": parse_result})
        return

    if args.action == "full":
        parse_result = engine.parse_sources()
        generate_result = engine.generate_daily_batch()
        print({"action": "full", "parse": parse_result, "generate": generate_result})
        return

    generate_result = engine.generate_daily_batch()
    print({"action": "submit", "generate": generate_result})


if __name__ == "__main__":
    main()
