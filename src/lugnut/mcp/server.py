import datetime as dt
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from lugnut.auth.deps import bearer_token
from lugnut.records.schemas import RecordIn, RecordType
from lugnut.reminders.schemas import CompleteIn, ReminderIn
from lugnut.reminders.state import State

INSTRUCTIONS = (
    "Lugnut tracks vehicle running costs and maintenance. Money is in minor units of the "
    "install currency (cents for AUD); distances and volumes use the units from get_settings. "
    "Odometer is optional on every record. Use list_vehicles first to find a vehicle id."
)

Obj = dict[str, Any]


def _detail(r: httpx.Response) -> str:
    detail = r.json().get("detail", r.reason_phrase)
    if isinstance(detail, list):  # FastAPI 422
        return "; ".join(f"{e['loc'][-1]}: {e['msg']}" for e in detail)
    return str(detail)


def build_mcp(app: FastAPI) -> "Endpoint":
    server = MCPServer("Lugnut", instructions=INSTRUCTIONS)

    async def _api(
        ctx: Context, method: str, path: str, *, params: Obj | None = None, json: Any = None
    ) -> Any:
        # Only the caller's token goes through, so the API does all auth and scope checks.
        headers = {"Authorization": (ctx.headers or {}).get("authorization", "")}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://lugnut") as client:
            r = await client.request(method, path, params=params, json=json, headers=headers)
        if 400 <= r.status_code < 500:
            raise ToolError(_detail(r))
        r.raise_for_status()
        return r.json()

    def _body(model: Any) -> Any:
        return model.model_dump(mode="json")

    @server.tool()
    async def list_vehicles(ctx: Context, archived: bool = False) -> list[Obj]:
        """List vehicles (active ones unless archived is true)."""
        return await _api(ctx, "GET", "/api/vehicles", params={"archived": archived})

    @server.tool()
    async def get_vehicle(ctx: Context, vehicle_id: int) -> Obj:
        """Get one vehicle, including its current odometer."""
        return await _api(ctx, "GET", f"/api/vehicles/{vehicle_id}")

    @server.tool()
    async def list_records(
        ctx: Context,
        vehicle_id: int,
        type: RecordType | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Obj]:
        """List a vehicle's records, newest first, optionally by type and date range."""
        given = {"type": type, "from": date_from, "to": date_to, "limit": limit, "offset": offset}
        params = {k: str(v) for k, v in given.items() if v is not None}
        return await _api(ctx, "GET", f"/api/vehicles/{vehicle_id}/records", params=params)

    @server.tool()
    async def get_record(ctx: Context, record_id: int) -> Obj:
        """Get one record."""
        return await _api(ctx, "GET", f"/api/records/{record_id}")

    @server.tool()
    async def list_reminders(
        ctx: Context,
        vehicle_id: int | None = None,
        state: State | None = None,
        include_completed: bool = False,
    ) -> list[Obj]:
        """List reminders, optionally for one vehicle or in one state."""
        params = {"vehicle_id": vehicle_id, "state": state, "include_completed": include_completed}
        params = {k: v for k, v in params.items() if v is not None}
        return await _api(ctx, "GET", "/api/reminders", params=params)

    @server.tool()
    async def get_insights(ctx: Context, vehicle_id: int) -> Obj:
        """Get a vehicle's running costs, fuel economy and upcoming work."""
        return await _api(ctx, "GET", f"/api/vehicles/{vehicle_id}/insights")

    @server.tool()
    async def get_settings(ctx: Context) -> Obj:
        """Get install settings: currency, units and timezone."""
        return await _api(ctx, "GET", "/api/settings")

    @server.tool()
    async def list_job_types(ctx: Context) -> list[Obj]:
        """List the job types that service and repair line items can use."""
        return await _api(ctx, "GET", "/api/job-types")

    @server.tool()
    async def add_record(ctx: Context, vehicle_id: int, record: RecordIn) -> Obj:
        """Add a record (fuel, service, repair, expense and so on) to a vehicle."""
        return await _api(ctx, "POST", f"/api/vehicles/{vehicle_id}/records", json=_body(record))

    @server.tool()
    async def update_record(ctx: Context, record_id: int, record: RecordIn) -> Obj:
        """Replace a record with the given fields (send the whole record)."""
        return await _api(ctx, "PUT", f"/api/records/{record_id}", json=_body(record))

    @server.tool()
    async def add_reminder(ctx: Context, vehicle_id: int, reminder: ReminderIn) -> Obj:
        """Add a reminder to a vehicle, due by date, distance or both."""
        path = f"/api/vehicles/{vehicle_id}/reminders"
        return await _api(ctx, "POST", path, json=_body(reminder))

    @server.tool()
    async def complete_reminder(
        ctx: Context, reminder_id: int, completion: CompleteIn | None = None
    ) -> Obj:
        """Mark a reminder done (today unless a date is given); repeating ones roll forward."""
        body = _body(completion or CompleteIn())
        return await _api(ctx, "POST", f"/api/reminders/{reminder_id}/complete", json=body)

    return Endpoint(server, app)


class Endpoint:
    """The /mcp ASGI app. Answers 401 unless the request carries a known API token; scope is
    left to the API. Enter run() in the host lifespan."""

    def __init__(self, server: MCPServer, app: FastAPI) -> None:
        self.server = server
        self.app = app
        self.mcp_app: ASGIApp | None = None

    @asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        # A session manager runs only once, so each lifespan builds a fresh one.
        self.mcp_app = self.server.streamable_http_app(
            streamable_http_path="/mcp",
            json_response=True,
            stateless_http=True,
            # A browser can't attach the bearer token, so DNS rebinding is no risk: allow any host.
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        async with self.server.session_manager.run():
            yield

    def _known(self, header: str) -> bool:
        with Session(self.app.state.engine) as db:
            return bearer_token(db, header) is not None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            header = dict(scope["headers"]).get(b"authorization", b"").decode("latin-1")
            if not await run_in_threadpool(self._known, header):
                denied = JSONResponse(
                    {"detail": "Not authenticated"}, 401, headers={"WWW-Authenticate": "Bearer"}
                )
                await denied(scope, receive, send)
                return
        assert self.mcp_app is not None, "Endpoint.run() not entered"
        await self.mcp_app(scope, receive, send)
