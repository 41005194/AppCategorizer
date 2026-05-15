# appcategorizer

## Description

The application is a CLI app categorizer. It takes an application name, queries multiple public metadata sources in parallel, extracts short descriptive tokens from each source, classifies each source independently, then returns the final category selected by majority vote.

## Project Structure

- `categorizer.py`: CLI entry point, progress display, final result.
- `engine/resolver.py`: orchestrates all data sources asynchronously.
- `engine/sources/`: one module per metadata source.
- `engine/sources/base.py`: shared relevance matching logic.
- `engine/embedding_classifier.py`: embedding model, category descriptions, similarity scoring.
- `engine/logger.py`: shared logging configuration.

## Data Sources

All sources return a `list[str]` of text tokens. These tokens are later embedded and compared against category descriptions in `engine/embedding_classifier.py`.

Name validation is handled through `BaseSource.is_relevant()`, which checks exact matches, normalized matches, prefix matches, and fuzzy matching with `rapidfuzz`.

### Apple Store

**Targeted platform:** macOS / iOS

**Method:** API request

**Endpoint:**

- `https://itunes.apple.com/search?term={app_name}&entity=software&limit=1`

**Notes:** Uses Apple’s iTunes Search API. The code only reads the first result and validates it against `trackName`.

**Retrieved fields:**

- `resultCount`
- `results`
- `trackName`
- `primaryGenreName`
- `genres`
- `description`

**Returned tokens:**

- `primaryGenreName`
- `genres`
- first 200 characters of `description`

### Arch Linux

**Targeted platform:** Linux

**Method:** API request, with fallback API request to AUR

**Endpoints:**

- `https://archlinux.org/packages/search/json/`
- `https://aur.archlinux.org/rpc/v5/search/{app_name}`

**Notes:** First queries official Arch repositories. If no valid result is found, it falls back to AUR. Official packages and AUR packages use different JSON field names.

**Retrieved fields:**

- Arch official: `results`, `pkgname`, `pkgdesc`, `groups`
- AUR: `results`, `Name`, `Description`, `Keywords`

**Returned tokens:**

- Arch official: `pkgdesc`, `groups`
- AUR: `Description`, `Keywords`

### Debian

**Targeted platform:** Linux

**Method:** browser-based scraping with Playwright and HTML parsing

**Site:**

- `https://packages.debian.org/stable/{app_name}`

**Notes:** Uses Playwright Chromium instead of plain `httpx`, then parses the rendered HTML with BeautifulSoup. This makes the source heavier and requires:

```bash
playwright install chromium
```

**Retrieved fields/selectors:**

- `div#pdesc`
- inside it: `p`, `ul`, `pre`
- list items: `li`

**Returned tokens:**

- cleaned paragraphs
- cleaned lists as a single text block
- cleaned preformatted blocks

### Fedora

**Targeted platform:** Linux

**Method:** website scraping with `httpx` and BeautifulSoup

**Sites:**

- `https://packages.fedoraproject.org/pkgs/{app_name}/`
- `https://packages.fedoraproject.org/search/`

**Notes:** First tries the direct package page. If needed, it searches Fedora packages and then opens the matched package detail page.

**Retrieved fields/selectors:**

- overview page: `ul li`, then `b`
- search page: `a.package-name`, `td a[href*='/pkgs/']`
- detail page: `p`

**Returned tokens:**

- first paragraph longer than 30 characters, excluding generic Fedora interface text

### Flathub

**Targeted platform:** Linux

**Method:** API request

**Endpoint:**

- `https://flathub.org/api/v2/search`

**Notes:** Uses a POST request. The response may be either a dictionary containing `hits` or a direct list.

Request body:

```json
{
  "query": "app_name",
  "filters": []
}
```

**Retrieved fields:**

- `hits`
- `app_id`
- `name`
- `summary`
- `categories`
- category `name`

**Returned tokens:**

- `name`
- `summary`
- category `name`

### GitHub

**Targeted platform:** Universal

**Method:** API request

**Endpoint:**

- `https://api.github.com/search/repositories`

**Notes:** Can use a `GITHUB_TOKEN` environment variable to increase rate limits.

Query parameters:

- `q`: `{app_name} in:name`
- `per_page`: `5`

**Retrieved fields:**

- `items`
- `name`
- `full_name`
- `description`
- `topics`

**Returned tokens:**

- semantic hint for game/emulator repositories: `"This is an open-source video game or gaming project hosted on GitHub."`
- semantic hint otherwise: `"This is an open-source software project, development tool, or application hosted on GitHub."`
- `description`
- `topics`

### GOG

**Targeted platform:** Universal (gaming)

**Method:** API-like catalog request

**Endpoint:**

- `https://catalog.gog.com/v1/catalog?limit=5&locale=en-US&query={query}`

**Notes:** The query is normalized by replacing `:` and `-` with spaces. The request forces English/US context while the language is normally based on IP address.

**Retrieved fields:**

- `products`
- `title`
- `slug`
- `productType`
- `genres`
- genre `name`

**Returned tokens:**

- one semantic sentence built from `productType` and genre `name`

### itchio

**Targeted platform:** Universal (gaming)

**Method:** website scraping with `httpx` and BeautifulSoup

**Sites:**

- `https://itch.io/search?q={query}`
- then the matched product page URL from the search result

**Notes:** Search results are parsed from HTML. The code validates result names using the title and URL slug variants, including compact slug matching.

**Retrieved fields/selectors:**

Search selectors:

- `div.game_cell`
- `div.title`
- `div.game_title`
- nested `a`
- `href`
- link text as title

Detail selectors:

- `table.game_info_panel`
- table row labels containing `genre`
- table row labels containing `tags`
- `meta[name="description"]`
- fallback: `div.formatted_description`
- fallback paragraphs: `p`

**Returned tokens:**

- semantic hint based on genres and tags:
  - if it is not a game: `"This software is distributed on itch.io. Categories and tags: ..."`
  - otherwise: `"This is a video game, indie game, or gaming entertainment software distributed on itch.io."`
- SEO description or first useful HTML description block

### Microsoft Store

**Targeted platform:** Windows

**Method:** browser-based scraping with Playwright, then HTML parsing with `httpx` and BeautifulSoup

**Sites:**

- `https://apps.microsoft.com/search?query={app_name}&hl=en-us&gl=US`
- then the matched `/detail/` product page

**Notes:** Search requires Playwright because the page generates components dynamically. After finding a product URL, the detail page is fetched with `httpx`.

**Retrieved fields/selectors:**

Search selectors and attributes:

- links matching `a[href*='/detail/']`
- link `href`
- link `inner_text()`
- link `aria-label`

Detail selectors and data:

- `script[type="application/ld+json"]`
- JSON-LD field `@type`
- JSON-LD field `description`
- fallback: `meta[name="description"]`

**Returned tokens:**

- up to 3 cleaned description blocks from `description`

### MyAbandonware

**Targeted platform:** Universal (gaming)

**Method:** browser-based scraping with Playwright and HTML parsing

**Sites:**

- `https://www.myabandonware.com/search/q/{query}/`
- then the matched `/game/` page

**Notes:** Uses Chromium because MyAbandonware requires JavaScript and may show Cloudflare checks. The code waits up to 10 seconds for Cloudflare by watching the page title.

**Retrieved fields/selectors:**

Search data:

- current page URL
- all links with `href`
- links containing `/game/`
- `span.name`
- link text
- game slug extracted from `/game/{slug}`

Detail selectors:

- `div#desc`
- `div#description`
- `div.desc`
- `div.gameDescription`
- fallback: `meta[name="description"]`
- paragraphs: `p`

**Returned tokens:**

- semantic hint: `"This is a retro video game and single-player entertainment software."`
- up to 2 cleaned description blocks

### Snapcraft

**Targeted platform:** Linux

**Method:** API request, with fallback API search

**Endpoints:**

- `https://api.snapcraft.io/v2/snaps/info/{app_name}`
- `https://api.snapcraft.io/v2/snaps/find`

**Notes:** First tries a direct snap lookup. If it fails, it searches by name.

Direct lookup parameters:

- `fields`: `title,name,summary,categories`

Search parameters:

- `q`: `{app_name}`
- `fields`: `title,name,summary,categories`

**Retrieved fields:**

Direct response:

- root `name`
- `snap`
- `snap.title`
- `snap.summary`
- `snap.categories`

Search response:

- `results`
- `snap`
- `snap.name`
- `snap.title`
- `snap.summary`
- `snap.categories`
- category `name`

**Returned tokens:**

- display title
- summary
- category `name`

### Steam

**Targeted platform:** Universal (mostly gaming)

**Method:** API request

**Endpoints:**

- `https://store.steampowered.com/api/storesearch/`
- `https://store.steampowered.com/api/appdetails/`

**Notes:** First searches Steam to get the app ID, then fetches genres and categories for that app.

Search parameters:

- `term`: `{app_name}`
- `l`: `english`
- `cc`: `US`

Detail parameters:

- `appids`: `{appid}`
- `filters`: `genres,categories`

**Retrieved fields:**

Search:

- `items`
- first item `name`
- first item `id`

Detail:

- `{appid}.data`
- `genres`
- genre `description`
- `categories`
- category `description`

**Returned tokens:**

- genre `description`
- category `description`

### Ubuntu

**Targeted platform:** Linux

**Method:** website scraping with `httpx` and BeautifulSoup

**Sites:**

- `https://packages.ubuntu.com/noble/{app_name}`
- `https://packages.ubuntu.com/search/`

**Notes:** Targets Ubuntu suite `noble`, which corresponds to Ubuntu 24.04 LTS. First tries the direct package page, then falls back to package search.

Search parameters:

- `keywords`: `{app_name}`
- `searchon`: `names`
- `suite`: `noble`
- `section`: `all`

**Retrieved fields/selectors:**

- search results: `h3 a`
- package title: `h1`
- description container: `div#pdesc`
- short description: `h2`
- long description: `p`
- section: `a[href*='/section/']`
- Debtags: `a[href*='tag=']`

**Returned tokens:**

- short description from `h2`
- first non-empty paragraph from `p`
- package section text
- Debtags containing `::`

### Wikidata

**Targeted platform:** Universal

**Method:** API request

**Endpoint:**

- `https://www.wikidata.org/w/api.php`

**Notes:** Uses the Wikidata API in two phases: search for an entity, then fetch entity data. Classification claims are QIDs, so the code resolves each QID to an English label with another API call.

Search parameters:

- `action`: `wbsearchentities`
- `search`: `{app_name}`
- `format`: `json`
- `language`: `en`
- `type`: `item`
- `limit`: `5`

Entity parameters:

- `action`: `wbgetentities`
- `ids`: `{qid}`
- `format`: `json`
- `languages`: `en`
- `props`: `descriptions|claims`

Label resolution parameters:

- `action`: `wbgetentities`
- `ids`: `{qid}`
- `format`: `json`
- `languages`: `en`
- `props`: `labels`

**Retrieved fields:**

Search:

- `search`
- `label`
- `id`

Entity:

- `entities`
- `descriptions.en.value`
- `claims`
- claim properties:
  - `P31` = instance of
  - `P136` = genre
  - `P452` = industry
- `mainsnak.datavalue.value.id`

Label:

- `labels.en.value`

**Returned tokens:**

- English entity description
- resolved labels for `P31`, `P136`, and `P452` claims

## Categories

- Internet Browsers
- Productivity Tools
- Communication & Collaboration
- Out-of-browser Entertainment
- Utilities & Maintenance
- Media Creation
- Development & Programming
- Others

## Algorithm

It uses sentence embeddings with sentence-transformers, specifically `all-MiniLM-L6-v2`. Each category is represented by a handcrafted text description in `engine/embedding_classifier.py`. The app embeds the collected source text, compares it to each category embedding with cosine similarity, and keeps the best category when its score is above the confidence threshold. Otherwise, the result is `Others`.

Algorithm flow:

1. Normalize the input name.
2. Query all sources concurrently.
3. Validate returned results with exact, prefix, normalized, and fuzzy matching.
4. Convert each source’s tokens into one text string.
5. Embed that text with a ML algorithm (`all-MiniLM-L6-v2`).
6. Compare it to category embeddings using cosine similarity.
7. Vote across source-level predictions.
8. Print out the final category.
