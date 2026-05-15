# AppCategorizer

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Python](https://img.shields.io/badge/Python-orange)](https://www.python.org/)

`AppCategorizer` is a command-line tool that tries to classify an application into a broad software category from its name.

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

Create and activate a virtual environment if needed, then install the Python dependencies:

```bash
pip install -r requirements.txt
```

Some sources rely on Playwright because their pages require JavaScript rendering. Install Chromium for those sources:

```bash
playwright install chromium
```

The embedding model is stored locally under `engine/local_model` after the first download.

## Usage

Run the categorizer with an application name:

```bash
python3 categorizer.py Chrome
```

Enable verbose logs:

```bash
python3 categorizer.py Chrome -v
```

Example output:

```text
Internet Browsers
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


## Known Limitations

- Public sources may change their HTML or API responses.
- Ubuntu can occasionally fail for the same query.
- Debian, Microsoft Store, and MyAbandonware are heavier because they rely on Playwright.
- Category quality depends heavily on the descriptions in `engine/embedding_classifier.py`.

## Project Layout

```text
categorizer.py                  CLI entry point
engine/resolver.py              Source orchestration
engine/embedding_classifier.py  Embedding-based category classifier
engine/logger.py                Shared logger configuration
engine/sources/                 Metadata source implementations
```

## :newspaper: License

Joular Code - Java is licensed under the GNU LGPL 3 license only (LGPL-3.0-only).

Copyright © 2026, Sorbonne Université, CNRS, LIP6.
All rights reserved. This program and the accompanying materials are made available under the terms of the [GNU Lesser General Public License v3.0 (LGPL-3.0-only)](https://www.gnu.org/licenses/lgpl-3.0.en.html) which accompanies this distribution.