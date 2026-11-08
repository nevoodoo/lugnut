# Connecting an AI assistant

Lugnut has an MCP server, so an AI assistant that supports the Model Context Protocol can look up your vehicles and records and, if you allow it, add new ones.

## Create a token

In Lugnut, open Settings and find API tokens. Create a token with the scope that fits what you want:

- **Read** lets the assistant answer questions about your vehicles, records, reminders and costs.
- **Write** also lets it add and edit records and reminders.

Copy the token when it appears. It is shown once. If an assistant with a read token tries a write tool, it gets the error "Token is read-only".

## The address

The server is at `/mcp` on your Lugnut address, for example `https://YOUR-HOST/mcp`. Leave off any trailing slash. Every request must carry the token as `Authorization: Bearer YOUR-TOKEN`.

## Claude Code

```sh
claude mcp add --transport http lugnut https://YOUR-HOST/mcp --header "Authorization: Bearer YOUR-TOKEN"
```

## Other clients

Most clients take a JSON config along these lines. The exact file and key names vary, so check your client's documentation.

```json
{
  "mcpServers": {
    "lugnut": {
      "type": "http",
      "url": "https://YOUR-HOST/mcp",
      "headers": { "Authorization": "Bearer YOUR-TOKEN" }
    }
  }
}
```

## Tools

| Tool | Needs | What it does |
| --- | --- | --- |
| `list_vehicles` | read | Lists vehicles, active ones unless you ask for archived. |
| `get_vehicle` | read | Gets one vehicle, including its current odometer. |
| `list_records` | read | Lists a vehicle's records, newest first, by type and date range. |
| `get_record` | read | Gets one record. |
| `list_reminders` | read | Lists reminders, for one vehicle or in one state. |
| `get_insights` | read | Gets a vehicle's running costs, fuel economy and upcoming work. |
| `get_settings` | read | Gets the currency, units and timezone. |
| `list_job_types` | read | Lists the job types that service and repair line items can use. |
| `add_record` | write | Adds a record to a vehicle. |
| `update_record` | write | Replaces a record. The assistant sends the whole record. |
| `add_reminder` | write | Adds a reminder, due by date, distance or both. |
| `complete_reminder` | write | Marks a reminder done. Repeating reminders roll forward. |

## What assistants can't do

There is no tool to delete anything, and none to change settings, tokens or login credentials. An assistant can add and edit records and reminders, nothing more.

## Money and units

Amounts are in minor units of your currency, so cents for AUD: $45.50 is 4550. Distances and volumes use the units in your settings, which the assistant can read with `get_settings`.

## Use HTTPS from outside your home network

A token is a password. On a home network over plain HTTP that may be fine, but if you reach Lugnut from elsewhere, put it behind an HTTPS reverse proxy first. See the install pages for [Docker](install/docker.md), [local](install/local.md) and [Proxmox](install/proxmox.md). Revoke a token in Settings if you stop using it.
