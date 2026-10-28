# Roadmap

Lugnut is built in milestones, in the order below. Each milestone lands on `main` only when it is finished and tested. Nothing is released until enough of them are done to make a useful first release, and nothing here is available until it shows up in the [release notes](release-notes.md).

## Milestones to version 1.0

| # | Milestone | What it adds | Status |
|---|-----------|--------------|--------|
| 1 | Foundation | First-run setup, login and API tokens. Automatic database backups before upgrades. Packaging, CI, the release pipeline and this site. | Done, unreleased |
| 2 | Vehicles and records | Vehicles with photos, purchase and sale details and custom fields. Records with their own fields for each type, line items with job types, estimates and attachments. Region settings for terms, units, currency and date format. All of it through the API. | Done, unreleased |
| 3 | Reminders | Reminders by date, distance or both, with repeats. Registration, insurance and inspection expiry dates create reminders on their own. Due items show in the app and can go to a Discord webhook. | Done, unreleased |
| 4 | App screens | The phone and desktop screens for vehicles, records, fuel entry, reminders, documents and settings. Installable to the home screen. | In progress |
| 5 | Insights | Fuel consumption over time, how often each kind of repair comes back, jobs that fall due close together, cost per km and total cost of ownership. | Done, unreleased |
| 6 | LubeLogger import | An [import from LubeLogger](coming-from-lubelogger.md) from a backup zip, with a preview you can correct before saving. | Done, unreleased |
| 7 | MCP server | Lets AI assistants read and write your vehicle data with an API token. | Planned |
| 8 | Version 1.0 | A Proxmox LXC script for installing and updating. A release candidate first, then 1.0. Docs for each release. | Planned |

Records use these types: work done (service, repair or upgrade), fuel, odometer, registration, insurance, inspection, tolls, parking, fines, to-do items and notes. The odometer is optional on every record. Australia is the first region, with the United States and the United Kingdom alongside it. Each region is a small data file, so adding a country needs no code.

## After 1.0

These have no order yet. They are picked up once 1.0 is out.

- AI features: a choice of provider (Anthropic, OpenAI, Google or a local model), a receipt and invoice reader that drafts records for you to check, and AI insights.
- Accounts: single sign-on (OIDC), then more than one user with shared vehicles.
- Storage: S3-compatible storage for attachments.
- Languages: interface translations and more regions.
- Integrations: a TypeScript API client on npm.

## Not planned

- Email notifications. Reminders go to Discord, and the API is open for anyone who wants another channel.
- Offline use. The app needs a connection to your server.
- Docker Hub images. Images are published to GitHub's container registry only.
