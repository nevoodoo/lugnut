# Roadmap

Lugnut is in active development. Nothing on this page is available until it appears in the [release notes](release-notes.md). A release only goes out with finished, usable features.

## Planned for version 1

- Records with their own fields for each type: work done (service, repair, upgrade), fuel, odometer, registration, insurance, inspection, tolls, parking and fines, and to-do items.
- Vehicles with photos, purchase and sale details, and custom fields.
- Reminders by date, distance or both, with repeats. Expiry dates create reminders automatically. Due items show in the app and can be sent to a Discord webhook.
- Attachments stored on disk, and pinnable notes.
- Insights from plain maths: fuel consumption, repair recurrence, jobs due close together, cost per km, total cost of ownership and running cost breakdowns.
- Region settings for terminology, units, currency and date format. Australia comes first, and each country is a small data file.
- A complete [LubeLogger import](coming-from-lubelogger.md) from a backup zip or the API.
- A phone-first interface that can be installed to the home screen.
- An API that does everything the interface does, with personal access tokens.
- An MCP server so AI assistants can read and write your vehicle data.
- In-place upgrades with automatic backups.

## Later

- AI provider support, a receipt and invoice reader that produces draft records for review, and AI insights
- Single sign-on (OIDC)
- S3-compatible attachment storage
- Interface translations
- A Proxmox LXC install script
- Multiple users and sharing
- More regions
- A TypeScript API client on npm

## Not planned

- Email notifications
- Offline use
- Docker Hub images (images are published to GitHub's registry only)
