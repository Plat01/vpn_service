import logging


def setup_logging(log_level: str, library_log_level: str) -> None:
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    library_level = getattr(logging, library_log_level)
    logging.getLogger("uvicorn").setLevel(library_level)
    logging.getLogger("uvicorn.access").setLevel(library_level)
    logging.getLogger("uvicorn.error").setLevel(library_level)
    logging.getLogger("sqlalchemy.engine").setLevel(library_level)
