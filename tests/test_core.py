# Copyright (c) 2026, Sorbonne Université, CNRS, LIP6.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the
# GNU Lesser General Public License v3.0 (LGPL-3.0-only)
# which accompanies this distribution, and is available at
# https://www.gnu.org/licenses/lgpl-3.0.en.html

import logging
import asyncio
import sys
import unittest

from appcategorizer import Categorizer


class FakeResolver:
    def __init__(self, results):
        self.results = results
        self.seen_names = []

    async def resolve(self, raw_name: str):
        self.seen_names.append(raw_name)
        return self.results


class FakeClassifier:
    def __init__(self, categories):
        self.categories = list(categories)
        self.seen_tokens = []

    def classify(self, tokens):
        self.seen_tokens.append(tokens)
        return self.categories.pop(0)


class CategorizerTests(unittest.TestCase):
    def test_resolve_and_classify_returns_majority_non_others(self):
        resolver = FakeResolver(
            {
                "SourceA": ["browser"],
                "SourceB": ["web"],
                "SourceC": ["unknown"],
            }
        )
        classifier = FakeClassifier(
            ["Internet Browsers", "Internet Browsers", "Others"]
        )

        result = asyncio.run(Categorizer(
            resolver=resolver,
            classifier=classifier,
        ).resolve_and_classify("Firefox"))

        self.assertEqual(result, "Internet Browsers")
        self.assertEqual(resolver.seen_names, ["Firefox"])
        self.assertEqual(classifier.seen_tokens, [["browser"], ["web"], ["unknown"]])

    def test_resolve_and_classify_returns_others_for_empty_resolver_output(self):
        resolver = FakeResolver({})
        classifier = FakeClassifier([])

        result = asyncio.run(Categorizer(
            resolver=resolver,
            classifier=classifier,
        ).resolve_and_classify("MissingApp"))

        self.assertEqual(result, "Others")

    def test_resolve_and_classify_rejects_empty_app_name(self):
        resolver = FakeResolver({})
        classifier = FakeClassifier([])

        with self.assertRaisesRegex(ValueError, "app_name"):
            asyncio.run(Categorizer(
                resolver=resolver,
                classifier=classifier,
            ).resolve_and_classify("   "))

    def test_resolve_and_classify_rejects_invalid_analysis_mode(self):
        resolver = FakeResolver({})
        classifier = FakeClassifier([])

        with self.assertRaisesRegex(ValueError, "analysis_mode"):
            asyncio.run(Categorizer(
                resolver=resolver,
                classifier=classifier,
            ).resolve_and_classify("Firefox", analysis_mode="invalid"))

    def test_resolve_and_classify_rejects_empty_model_name(self):
        resolver = FakeResolver({})
        classifier = FakeClassifier([])

        with self.assertRaisesRegex(ValueError, "local_model_name"):
            asyncio.run(Categorizer(
                resolver=resolver,
                classifier=classifier,
            ).resolve_and_classify("Firefox", local_model_name=" "))

    def test_constructing_categorizer_does_not_import_local_ml_stack(self):
        # Cloud mode only needs the resolver's regex sanitize(), so building a
        # default Categorizer must not drag in the heavy local-ML scraping
        # stack. Sources are loaded lazily on the first resolve() instead.
        for module in ("playwright", "bs4", "rapidfuzz"):
            sys.modules.pop(module, None)

        Categorizer()

        for module in ("playwright", "bs4", "rapidfuzz"):
            self.assertNotIn(
                module,
                sys.modules,
                f"{module} was imported by Categorizer() but should be lazy.",
            )

    def test_package_import_does_not_configure_root_logging(self):
        root_logger = logging.getLogger()
        handler_count = len(root_logger.handlers)
        root_level = root_logger.level

        import appcategorizer  # noqa: F401

        self.assertEqual(len(root_logger.handlers), handler_count)
        self.assertEqual(root_logger.level, root_level)


if __name__ == "__main__":
    unittest.main()
