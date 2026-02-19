"""
Odoo JSON-RPC 2.0 Client — connects to Odoo Community 19+ via External API.

All operations are draft-only at Gold tier (approval required before posting
invoices or payments). This follows the Human-in-the-Loop principle.

Reference: https://www.odoo.com/documentation/19.0/developer/reference/external_api.html
"""

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class OdooClient:
    """Thin wrapper around Odoo's JSON-RPC 2.0 External API."""

    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.password = password
        self._uid: Optional[int] = None
        self._session = httpx.AsyncClient(timeout=30)

    async def _rpc(self, endpoint: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        """Make a JSON-RPC 2.0 call to Odoo."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "service": endpoint,
                "method": method,
                "args": args,
            },
        }
        if kwargs:
            payload["params"]["kwargs"] = kwargs

        for attempt in range(3):
            try:
                resp = await self._session.post(
                    f"{self.url}/web/dataset/call_kw",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                result = resp.json()
                if "error" in result:
                    raise RuntimeError(f"Odoo RPC error: {result['error']}")
                return result.get("result")
            except httpx.TimeoutException:
                if attempt == 2:
                    raise
                import asyncio
                await asyncio.sleep(2 ** attempt)

    async def authenticate(self) -> int:
        """Authenticate and cache uid."""
        if self._uid is not None:
            return self._uid

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "db": self.db,
                "login": self.username,
                "password": self.password,
            },
        }
        resp = await self._session.post(
            f"{self.url}/web/session/authenticate",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        uid = result.get("uid")
        if not uid:
            raise RuntimeError("Odoo authentication failed — check credentials")
        self._uid = uid
        logger.info("Authenticated to Odoo as uid=%d", uid)
        return uid

    async def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str],
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Search and read records from an Odoo model."""
        await self.authenticate()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "model": model,
                "method": "search_read",
                "args": [domain],
                "kwargs": {
                    "fields": fields,
                    "limit": limit,
                    "offset": offset,
                },
            },
        }
        resp = await self._session.post(
            f"{self.url}/web/dataset/call_kw",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            raise RuntimeError(f"Odoo search_read error: {result['error']}")
        return result.get("result", [])

    async def create(self, model: str, values: dict) -> int:
        """Create a new record (returns ID). Requires human approval before posting."""
        await self.authenticate()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "model": model,
                "method": "create",
                "args": [values],
                "kwargs": {},
            },
        }
        resp = await self._session.post(
            f"{self.url}/web/dataset/call_kw",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            raise RuntimeError(f"Odoo create error: {result['error']}")
        return result.get("result")

    async def write(self, model: str, ids: list[int], values: dict) -> bool:
        """Update existing records."""
        await self.authenticate()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "model": model,
                "method": "write",
                "args": [ids, values],
                "kwargs": {},
            },
        }
        resp = await self._session.post(
            f"{self.url}/web/dataset/call_kw",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            raise RuntimeError(f"Odoo write error: {result['error']}")
        return bool(result.get("result"))

    async def close(self) -> None:
        await self._session.aclose()
