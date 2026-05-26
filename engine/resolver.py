import asyncio
import httpx
import re

from engine.logger import logger
from engine.sources.steam import SteamSource
from engine.sources.github import GithubSource
from engine.sources.flathub import FlathubSource
from engine.sources.snapcraft import SnapcraftSource
from engine.sources.debian import DebianSource
from engine.sources.ubuntu import UbuntuSource
from engine.sources.fedora import FedoraSource
from engine.sources.arch import ArchSource
from engine.sources.itch import ItchSource
from engine.sources.gog import GogSource
from engine.sources.myabandonware import MyAbandonwareSource
from engine.sources.apple import AppleSource
from engine.sources.microsoft import MicrosoftSource
from engine.sources.wikidata import WikidataSource

class Resolver:
    def __init__(self):
        self.sources = [AppleSource(),
                        FlathubSource(),
                        SnapcraftSource(),
                        SteamSource(),
                        ArchSource(),
                        DebianSource(),
                        UbuntuSource(),
                        FedoraSource(),
                        GithubSource(),
                        WikidataSource(),
                        MicrosoftSource(),
                        MyAbandonwareSource(),
                        GogSource(),
                        ItchSource()
                        ]
        
    def sanitize(self, raw_name: str) -> str:
        name = raw_name.lower()
        name = re.sub(r'\.(exe|app|sh|bin|com|dmg|pkg)$', '', name)
        name = re.sub(r'[-_]', ' ', name)
        return name.strip()

    # Wrap source calls so each request can be logged at dispatch time.
    async def _fetch_with_log(self, source, client, app_name):
        source_name = source.__class__.__name__
        logger.debug(f"[START] Starting request for {source_name}")
        try:
            return await source.fetch(client, app_name)
        except Exception as e:
            logger.error(f"[CRITICAL_ERROR] Critical error in {source_name}: {e}")
            return e

    # Logging verbosity is handled by the shared logger configuration.
    async def resolve(self, raw_name: str) -> dict[str, list[str]]:
        app_name = self.sanitize(raw_name)
        results_by_source = {}
        
        logger.info(f"Starting resolution with {len(self.sources)} parallel sources...")

        async with httpx.AsyncClient(timeout=5.0) as client:
            # Use the wrapper instead of calling source.fetch directly.
            tasks = [self._fetch_with_log(source, client, app_name) for source in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, res in enumerate(results):
                source_name = self.sources[i].__class__.__name__
                
                if isinstance(res, list):
                    if res:
                        results_by_source[source_name] = res
                        logger.debug(f"[FOUND] {source_name} found: {res}")
                    else:
                        logger.debug(f"[EMPTY] {source_name} found nothing.")
                else:
                    logger.error(f"[ERROR] {source_name} returned an exception: {res}")

        return results_by_source
