import json

HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
    "Host": "lugnut.example.com",  # behind a proxy: no host allowlist
}


def rpc(client, method, params=None, token=None, headers=None):
    if headers is None:
        headers = {"Authorization": f"Bearer {token}"}
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    return client.post("/mcp", json=body, headers={**HEADERS, **headers})


def make_token(client, scope):
    r = client.post("/api/tokens", json={"name": scope, "scope": scope}, headers={"X-Lugnut": "1"})
    return r.json()["token"]


def call(client, token, name, arguments, expect_error=False):
    r = rpc(client, "tools/call", {"name": name, "arguments": arguments}, token=token)
    result = r.json()["result"]
    assert result.get("isError", False) == expect_error, result
    if expect_error:
        return result["content"][0]["text"]
    out = result.get("structuredContent") or json.loads(result["content"][0]["text"])
    return out["result"] if set(out) == {"result"} else out


def test_mcp_auth_and_tools(client, logged_in, vehicle):
    # cookie only: rejected before MCP
    assert rpc(client, "tools/list", headers={}).status_code == 401
    read, write = make_token(client, "read"), make_token(client, "write")
    init = {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "t", "version": "1"},
    }
    assert rpc(client, "initialize", init, token=read).status_code == 200
    names = {t["name"] for t in rpc(client, "tools/list", token=read).json()["result"]["tools"]}
    assert {"list_vehicles", "add_record", "get_insights"} <= names and not any(
        "delete" in n for n in names
    )
    vehicles = call(client, read, "list_vehicles", {})
    assert [v["id"] for v in vehicles] == [vehicle]
    fuel = {
        "vehicle_id": vehicle,
        "record": {
            "type": "fuel",
            "date": "2026-11-01",
            "odometer": 1000,
            "cost": 8000,
            "details": {"volume": 40},
        },
    }
    denied = call(client, read, "add_record", fuel, expect_error=True)
    assert "read-only" in denied
    bad = call(
        client,
        write,
        "add_record",
        {**fuel, "record": {**fuel["record"], "details": {}}},
        expect_error=True,
    )
    assert "volume" in bad
    created = call(client, write, "add_record", fuel)
    assert client.get(f"/api/records/{created['id']}").status_code == 200
