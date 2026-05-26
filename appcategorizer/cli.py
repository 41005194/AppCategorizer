import argparse
import asyncio
import contextlib
import logging

from rich.console import Console

from .core import Categorizer
from .engine.logger import logger, setup_logger


console = Console(stderr=True)


@contextlib.contextmanager
def _dummy_status():
    class Dummy:
        def update(self, msg: str) -> None:
            pass

    yield Dummy()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("app_name", help="Application name to categorize")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logs")
    return parser


async def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Configure Rich logging only for the command-line interface.
    setup_logger(args.verbose)

    if not args.verbose:
        logger.setLevel(logging.WARNING)

    status_context = (
        console.status("[bold cyan]Starting...", spinner="dots")
        if not args.verbose
        else _dummy_status()
    )

    def show_progress(status_obj, msg: str) -> None:
        if args.verbose:
            logger.info(msg)
        else:
            status_obj.update(f"[bold cyan]{msg}")

    with status_context as status:
        engine = Categorizer(on_progress=lambda msg: show_progress(status, msg))
        final_category = await engine.resolve_and_classify(args.app_name)

    print(final_category)


def main_sync(argv: list[str] | None = None) -> None:
    asyncio.run(main(argv))


if __name__ == "__main__":
    main_sync()
