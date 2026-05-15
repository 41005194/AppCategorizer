import asyncio
import argparse
import logging
import contextlib
from collections import Counter

from rich.console import Console
from engine.logger import setup_logger, logger

# Initialize the Rich console.
console = Console()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app_name", help="Application name to categorize")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logs")
    args = parser.parse_args()

    # Configure logging before loading heavier dependencies.
    setup_logger(args.verbose)

    if not args.verbose:
        logger.setLevel(logging.WARNING)

    # Use a no-op status object in verbose mode so debug logs stay readable.
    @contextlib.contextmanager
    def dummy_status():
        class Dummy:
            def update(self, msg): pass
        yield Dummy()

    # Use a Rich spinner in normal mode and the no-op status in verbose mode.
    status_context = console.status("[bold cyan]Starting...", spinner="dots") if not args.verbose else dummy_status()

    # Route progress updates either to the spinner or to the logger.
    def update_status(status_obj, msg):
        if not args.verbose:
            status_obj.update(f"[bold cyan]{msg}") # Update the spinner text.
        else:
            logger.info(msg) # Send the message through the standard logger.

    # Keep the spinner active for the full categorization sequence.
    with status_context as status:
        update_status(status, "Loading libraries...")
        from engine.resolver import Resolver
        from engine.embedding_classifier import EmbeddingClassifier
        
        update_status(status, "Initializing model in memory...")
        resolver = Resolver()

        if EmbeddingClassifier.need_download():
            update_status(status, "Downloading model for the first time (this may take a moment)...")
        else:
            update_status(status, "Model found locally, loading from disk...")
            
        classifier = EmbeddingClassifier()

        update_status(status, f"Searching metadata for: '{args.app_name}'...")
        
        # Resolve metadata from network sources.
        source_tokens = await resolver.resolve(args.app_name)
        
        if not source_tokens:
            final_category = "Others"
        else:
            predicted_categories = []
            update_status(status, "Classifying results...")
            
            for source_name, tokens in source_tokens.items():
                category = classifier.classify(tokens)
                predicted_categories.append(category)
                logger.debug(f"[CLASSIFIER] {source_name} -> {category}")

            real_categories = [c for c in predicted_categories if c != "Others"]

            if real_categories:
                counter = Counter(real_categories)
                final_category = counter.most_common(1)[0][0]
            else:
                final_category = "Others"
    
    # Print only the raw final category.
    print(final_category)

if __name__ == "__main__":
    asyncio.run(main())
