# Coming from LubeLogger

Lugnut can import a LubeLogger backup. You see a preview you can correct before anything is saved.

## Get the backup

In LubeLogger, open Settings, then Backup, and download the zip. In Lugnut, open Settings and choose Import from LubeLogger, then pick that file. The import reads the backup only; it doesn't connect to your LubeLogger server.

## The preview

The preview shows what will be added and lets you change the parts that LubeLogger doesn't record:

- **Date order and timezone.** LubeLogger stores some dates as text and its times in UTC. Lugnut guesses the date order and the timezone from your data. If a guess is wrong, change it and the preview updates.
- **Vehicles.** Each vehicle in the backup is matched to one you already have by plate or VIN, and the preview lets you change that or add it as new.
- **Tax records.** Each one is sorted into registration or insurance, using its tag first and then its description. Change the type on any that were guessed wrong.
- **Estimates.** LubeLogger has no estimate flag. Records whose notes or description mention an estimate are marked as estimates in Lugnut, and listed so you can see them.
- **Warnings and skipped records,** with counts.

Press Import when it looks right.

## What is imported

- Vehicles, with plate, purchase and sale details, custom fields and photo. VIN, engine number and colour go into their own fields.
- Service, collision and upgrade records, as work records with the category service, repair or upgrade. Parts used become line items.
- Fuel records, odometer readings, inspections, notes (including pinned ones) and to-do items.
- Tax records, as registration or insurance. A recurring tax gets an expiry date, and the reminder for it follows from that.
- Reminders. Repeating reminders keep their month and distance intervals. Urgency thresholds are not carried over.
- Files attached to records and notes.

A record with an odometer of 0 is imported with no reading.

## What is skipped

Supply records, equipment records, and plan and inspection templates are not imported. The preview lists how many were skipped. Supplies that were used on a record still come across as line items on that record.

## Running it again

Running the import again, with the same backup or a newer one, adds only records that are new. It never changes or deletes anything already in Lugnut, including records you have edited since.
