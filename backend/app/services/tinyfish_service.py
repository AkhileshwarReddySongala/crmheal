import asyncio
import re
from typing import Any

import httpx

from app.config import settings
from app.schemas.models import CRMLeadRow


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower()) or "example"


class TinyFishService:
    def mode(self) -> str:
        if settings.use_mock_tinyfish or not settings.tinyfish_api_key:
            return "mock"
        return "configured"

    async def enrich(self, row: CRMLeadRow) -> dict[str, Any]:
        if self.mode() == "mock":
            return await self._mock(row)
        return await self._real(row)

    async def _mock(self, row: CRMLeadRow) -> dict[str, Any]:
        await asyncio.sleep(0.8 if row.id == 17 else 0.35)
        company_domain = _slug(row.company)
        title = row.title or ("Student Technology Associate" if row.id == 17 else "Senior Manager")
        email = row.email if row.email and "@" in row.email and "." in row.email.split("@")[-1] else f"{_slug(row.first_name)}.{_slug(row.last_name)}@{company_domain}.com"
        confidence = 52 if row.id == 17 else 72
        return {
            "job_title": title,
            "email": email,
            "phone": row.phone,
            "company_website": f"https://www.{company_domain}.com",
            "confidence": confidence,
            "source": "tinyfish_mock",
            "stage_used": "mock",
        }

    async def _request_with_retries(self, client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_response = None
        for attempt in range(4):
            response = await client.request(method, url, **kwargs)
            last_response = response
            if response.status_code != 429:
                response.raise_for_status()
                return response
            retry_after = response.headers.get("retry-after")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
            await asyncio.sleep(delay)
        assert last_response is not None
        last_response.raise_for_status()
        return last_response

    async def _real(self, row: CRMLeadRow) -> dict[str, Any]:
        headers = {"X-API-Key": settings.tinyfish_api_key}
        timeout = httpx.Timeout(10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            search = await self._request_with_retries(
                client,
                "GET",
                "https://api.search.tinyfish.ai",
                headers=headers,
                params={"query": f"{row.first_name} {row.last_name} {row.company}", "max_results": 3},
            )
            results = search.json()
            first = (results.get("results") or results or [{}])[0]
            url = first.get("url") or f"https://www.{_slug(row.company)}.com"
            fetch = await self._request_with_retries(
                client,
                "POST",
                "https://api.fetch.tinyfish.ai",
                headers=headers,
                json={"urls": [url], "format": "markdown"},
            )
            fetch_payload = fetch.json()
            page = (fetch_payload.get("results") or [{}])[0]
            markdown = str(page.get("text") or page)
            email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", markdown)
            confidence = 25
            enriched = {
                "job_title": row.title,
                "email": row.email,
                "phone": row.phone,
                "company_website": url,
                "source": url,
                "stage_used": "fetch",
            }
            if email_match:
                enriched["email"] = email_match.group(0)
                confidence += 25
            if enriched["job_title"]:
                confidence += 25
            if enriched["phone"]:
                confidence += 25
            enriched["confidence"] = min(confidence, 100)
            return enriched


tinyfish = TinyFishService()
