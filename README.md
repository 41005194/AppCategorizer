# AppCategorizer

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Python](https://img.shields.io/badge/Python-orange)](https://www.python.org/)

`AppCategorizer` is a Python library and command-line tool that tries to classify an application into a broad software category from its name.

It gathers metadata from several public sources, classifies each source independently with a local sentence-transformer model, then keeps the category selected by majority vote.

## Features

- Queries 14 metadata sources in parallel.
- Uses a local embedding model: `all-MiniLM-L6-v2`.
- Classifies each source result independently.
- Supports verbose logs with `-v`.
- Falls back to `Others` when no reliable category is found.

## Categories

The current classifier can return:

- `Internet Browsers`
- `Productivity Tools`
- `Communication & Collaboration`
- `Out-of-browser Entertainment`
- `Utilities & Maintenance`
- `Media Creation`
- `Development & Programming`
- `Others`

## Installation

Create and activate a virtual environment if needed, then install the package in editable mode:

```bash
pip install -e .
```

Some sources rely on Playwright because their pages require JavaScript rendering. Install Chromium for those sources:

```bash
playwright install chromium
```

The default embedding model is stored in the user cache directory after the first download. You can override the cache location from Python with `Categorizer(model_cache_dir=...)`.

## Usage

Run the categorizer with an application name:

```bash
appcategorizer Chrome
```

Enable verbose logs:

```bash
appcategorizer Chrome -v
```

Example output:

```text
Internet Browsers
```

## Python API

Use `Categorizer` from your own async Python code:

```python
import asyncio
from appcategorizer import Categorizer

async def main():
    engine = Categorizer()
    result = await engine.resolve_and_classify("firefox")
    print(result)

asyncio.run(main())
```

`resolve_and_classify()` returns the final category as a plain string. The CLI handles argument parsing, Rich spinners, and logging configuration separately from the library API.

## Tkinter GUI

Install the optional GUI dependency:

```bash
pip install -e ".[gui]"
```

Run the sample desktop app:

```bash
python3 run_appcategorizer_gui.py
```

Function signature:

```python
await engine.resolve_and_classify(
    app_name: str,
    analysis_mode: str = "local_ml",
    local_model_name: str = "all-MiniLM-L6-v2",
)
```

Options:

- `app_name`: application name to resolve and classify.
- `analysis_mode`: classification backend. Use `"local_ml"` for the local embedding classifier. `"cloud_llm"` is reserved for a future cloud LLM classifier and currently raises `NotImplementedError`.
- `local_model_name`: sentence-transformer model name used when `analysis_mode="local_ml"`. Defaults to `"all-MiniLM-L6-v2"`.

The default analysis mode uses a local sentence-transformer model:

```python
result = await engine.resolve_and_classify(
    "firefox",
    analysis_mode="local_ml",
    local_model_name="all-MiniLM-L6-v2",
)
```

To use another local sentence-transformer model:

```python
result = await engine.resolve_and_classify(
    "firefox",
    local_model_name="sentence-transformers/all-MiniLM-L12-v2",
)
```

## How It Works

1. The input name is normalized by the resolver.
2. Metadata sources are queried concurrently.
3. Each source returns short text tokens such as descriptions, categories, genres, or tags.
4. The classifier embeds each source result and compares it to the category descriptions.
5. The final category is selected by majority vote, ignoring `Others` when stronger votes exist.

## Sources

The resolver currently uses:

- Apple
- Arch Linux
- Debian
- Fedora
- Flathub
- GitHub
- GOG
- itch.io
- Microsoft Store
- MyAbandonware
- Snapcraft
- Steam
- Ubuntu
- Wikidata

GitHub can use a `GITHUB_TOKEN` environment variable when available to increase API rate limits.

All source metadata is fetched from public third-party services and should be treated as untrusted text. The library uses that text only as classifier input.

## Known Limitations

- Public sources may change their HTML or API responses.
- Ubuntu can occasionally fail for the same query.
- Debian, Microsoft Store, and MyAbandonware are heavier because they rely on Playwright.
- Category quality depends heavily on the descriptions in `engine/embedding_classifier.py`.

## Project Layout

```text
appcategorizer/__init__.py                     Public Python API
appcategorizer/core.py                         Library orchestration class
appcategorizer/cli.py                          Installable CLI entry point
appcategorizer/engine/resolver.py              Source orchestration
appcategorizer/engine/embedding_classifier.py  Embedding-based category classifier
appcategorizer/engine/logger.py                Shared logger configuration
appcategorizer/engine/sources/                 Metadata source implementations
```
## License

AppCategorizer is licensed under the GNU LGPL 3 license only (LGPL-3.0-only).

Copyright © 2026, Sorbonne Université, CNRS, LIP6.
All rights reserved. This program and the accompanying materials are made available under the terms of the [GNU Lesser General Public License v3.0 (LGPL-3.0-only)](https://www.gnu.org/licenses/lgpl-3.0.en.html) which accompanies this distribution.
