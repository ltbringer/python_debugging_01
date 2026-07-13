import asyncio
from typing import Optional

import httpx

from .fetcher import fetch, fetch_all
from .processor import Dedup
from .types import Page


class Crawler:
    def __init__(self, headers: Optional[dict] = None, seen: Optional[list] = None):
        self.headers = headers if headers is not None else {}
        self.headers.setdefault("User-Agent", "python_debugging_01/1.0")
        self.seen = seen if seen is not None else []

    async def crawl(self, urls: list[str], mode: str = "batch") -> list[Page]:
        self.seen.extend(urls)
        if mode == "stream":
            return await self._crawl_stream(urls)
        return await self._crawl_batch(urls)

    async def _crawl_batch(self, urls: list[str]) -> list[Page]:
        results: list[Page] = []
        for batch in [urls]:
            async with httpx.AsyncClient(headers=self.headers) as client:
                tasks = [fetch(client, u) for u in batch]
                batch_results = await asyncio.gather(*tasks)
            results.extend(p for p in batch_results if p is not None)
        dedup = Dedup()
        return await dedup.add_all(results)

    async def _crawl_stream(self, urls: list[str]) -> list[Page]:
        results: list[Page] = []
        async with httpx.AsyncClient(headers=self.headers) as client:
            await fetch_all(urls, results, client)
        dedup = Dedup()
        return await dedup.add_all(results)

    def stats(self) -> dict:
        return {"instance_seen": list(self.seen)}
