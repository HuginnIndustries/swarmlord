"""FastAPI application factory.

V1 returns 501 from every endpoint. The factory is wired up so V2 can
swap in real implementations without restructuring the package or the
install path. FastAPI is imported lazily inside ``create_app()`` so the
core CLI install (without the ``server`` extra) never imports it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI


def create_app() -> FastAPI:  # pragma: no cover - V2 work
    from fastapi import FastAPI

    from swarmlord.server.api import gates, packets, runs

    app = FastAPI(title="SwarmLord", version="0.1.0")
    app.include_router(packets.build_router(), prefix="/packets", tags=["packets"])
    app.include_router(runs.build_router(), prefix="/runs", tags=["runs"])
    app.include_router(gates.build_router(), prefix="/gates", tags=["gates"])
    return app
