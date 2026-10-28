# Insights

Each vehicle has an Insights page, and the vehicle's home screen shows a short version: the fuel average, the cost per distance this year and the cost per distance since you bought it. Anything Lugnut can't work out yet shows "n/a" or a short sentence saying what is missing.

## Fuel economy

Economy is worked out from full tank to full tank. When you fill up to full, Lugnut adds the fuel from every fill since the previous full one, including partial fills in between, and divides by the distance driven. The average covers all of those stretches. "Recent" is the average of the last five, and the change shows how far it is from the overall average. Whether up is good depends on your unit: lower is better for L/100km, higher is better for mpg and km/L.

A fill is skipped when:

- it has no odometer reading or no volume
- you missed a fill, so the fuel between two full tanks is unknown
- the odometer reading went backwards

The page says how many fills were skipped. Once you have five or more tanks, a stretch more than 25% away from the median is flagged as an outlier on the chart. It still counts in the average, so check it for a typo.

## Running costs

Costs are shown for this year and for all time, split by category, with a bar chart by month. Cost per distance needs at least two odometer readings in the period.

Estimates, to-do items and notes are left out of every cost figure. An estimate is a quote and not money spent, so it only counts once you save the real record.

## Cost of ownership

Total cost of ownership is the purchase price plus running costs, minus the sale price if you sold the vehicle. It needs a purchase price on the vehicle. The page also shows it per month and per distance.

## Repeat jobs

Jobs with the same job type on work records are grouped. For each one you see how many times it was done, the usual interval in distance and days, the usual cost and when it is next expected. Estimates are ignored. A job done only once has no interval yet.

## Coming up

This lists your open reminders with a projected date. Date reminders use their due date. Distance reminders are projected from how far you drove over the last year, which needs readings spanning at least 30 days. Without that, the reminder shows "No date yet".

Reminders due within 30 days of each other are grouped, with a note that doing them in one visit could save a trip.

Each reminder shows what the same job cost last time. Lugnut matches it by the reminder's title or job type. For registration, insurance and inspection expiry reminders it uses the latest record of that type instead. If nothing matches, it says so.
