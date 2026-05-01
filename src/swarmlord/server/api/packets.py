"""Packet endpoints — V2 work, V1 returns 501."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> APIRouter:  # pragma: no cover - V2 work
    from fastapi import APIRouter, HTTPException

    router = APIRouter()

    @router.get("/")
    async def list_packets() -> dict[str, str]:
        raise HTTPException(status_code=501, detail="V2 endpoint")

    @router.get("/{slug}")
    async def get_packet(slug: str) -> dict[str, str]:
        raise HTTPException(status_code=501, detail="V2 endpoint")

    return router
