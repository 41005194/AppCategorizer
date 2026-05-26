import argparse
import asyncio

from appcategorizer import Categorizer
from rich.console import Console


console = Console(stderr=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Categorize an application name using the appcategorizer library."
    )
    parser.add_argument("app_name", help="Application name to categorize")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress messages as plain lines instead of a Rich status",
    )
    return parser


async def classify_app(app_name: str, verbose: bool) -> str:
    if verbose:
        def show_progress(message: str) -> None:
            console.print(message)

        categorizer = Categorizer(on_progress=show_progress)
        return await categorizer.resolve_and_classify(app_name)

    with console.status("[bold cyan]Starting...", spinner="dots") as status:
        categorizer = Categorizer(
            on_progress=lambda message: status.update(f"[bold cyan]{message}")
        )
        return await categorizer.resolve_and_classify(app_name)


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    category = asyncio.run(classify_app(args.app_name, args.verbose))
    print(category)


if __name__ == "__main__":
    main()
