import logging

from app.config import get_settings
from app.services.collector import AEngineCollector


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = get_settings()
    if not settings.tmdb_api_key:
        raise RuntimeError("TMDB_API_KEY is required")

    collector = AEngineCollector(settings)
    result = collector.run_once()
    print(
        {
            "tried": result.tried,
            "filtered_provider": result.filtered_provider,
            "filtered_duplicate": result.filtered_duplicate,
            "filtered_images": result.filtered_images,
            "published": result.published,
            "failed": result.failed,
        }
    )


if __name__ == "__main__":
    main()
