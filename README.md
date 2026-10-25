# QRBatch — Bulk QR Codes & Print Sheets From a CSV

Online QR generators charge per code or watermark the batch. QRBatch turns
a CSV of links into labelled, print-ready QR codes on your own machine.

## What it does
- Auto-detects the payload column (url/link/text) and a label column
- One PNG per code with the label printed underneath
- A4 print sheets (300 dpi, 12 codes per page) as a single PDF
- A manifest CSV (file → label → payload) so a print run can be checked
  item by item
- Error-correction level M (~15% damage tolerance)
- Duplicates and empty rows are reported in the open — never silently merged

## Verified behaviour
On a seeded 5-row CSV (including a duplicate payload and an empty row):
4 codes generated, 2 warnings itemized, 1 A4 sheet produced, manifest
mapping every PNG to its payload and label.

## Run from source
```
python qr_batch.py items.csv output_folder
```
Requires qrcode + Pillow. The Windows package bundles everything.
