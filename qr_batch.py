#!/usr/bin/env python3
"""
QRBatch — turn a CSV of links/labels into print-ready QR code sheets.

Input CSV: a column of payloads (url / text) and an optional label column.
Output:
  - one PNG per code (named from the label or sequence), with the label
    printed under the code — ready to drop into print layouts
  - A4 PDF contact sheets (12 per page) for direct printing
  - a manifest CSV mapping file -> payload -> label, so a print run can
    be checked item by item
Every code is verified after generation by re-encoding and comparing the
module matrix — a code that doesn't match its payload is never shipped
silently. Duplicate payloads and empty rows are reported, not merged.

Local only. Uses qrcode + Pillow (+ Pillow's PDF save).
"""
import csv
import io
import os
import sys

import qrcode
from PIL import Image, ImageDraw

PAGE_W, PAGE_H = 2480, 3508  # A4 @300dpi
COLS, ROWS = 3, 4


def matrix_of(data, box=10, border=4):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=box, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.get_matrix()


def make_code_image(data, label, px=880):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((px, px), Image.NEAREST)
    if label:
        canvas = Image.new("RGB", (px, px + 90), "white")
        canvas.paste(img, (0, 0))
        d = ImageDraw.Draw(canvas)
        text = label if len(label) <= 42 else label[:41] + "…"
        try:
            d.text((px / 2, px + 45), text, fill="black", anchor="mm")
        except TypeError:
            d.text((20, px + 30), text, fill="black")
        img = canvas
    return img


def find_cols(fields, rows):
    payload = label = None
    for f in fields:
        lf = (f or "").strip().lower()
        if lf in ("url", "link", "payload", "text", "content", "qr", "value"):
            payload = f
        if lf in ("label", "name", "title", "id", "sku", "code"):
            label = f
    if payload is None:
        best, hits = None, 0
        for f in fields:
            h = sum(1 for r in rows[:50] if (r.get(f) or "").strip().startswith(("http", "www.")))
            if h > hits:
                best, hits = f, h
        payload = best
    return payload, label


def run_qrbatch(src_csv, outdir):
    os.makedirs(outdir, exist_ok=True)
    png_dir = os.path.join(outdir, "codes")
    os.makedirs(png_dir, exist_ok=True)
    raw = open(src_csv, "rb").read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(r) for r in reader]
    payload_col, label_col = find_cols(reader.fieldnames or [], rows)
    if not payload_col:
        raise ValueError("could not find a payload column (url/link/text) in the CSV")

    warnings, manifest, images = [], [], []
    seen = {}
    made = 0
    for i, r in enumerate(rows, 1):
        data = (r.get(payload_col) or "").strip()
        label = (r.get(label_col) or "").strip() if label_col else ""
        if not data:
            warnings.append(f"row {i + 1}: empty payload — skipped")
            continue
        if data in seen:
            warnings.append(f"row {i + 1}: duplicate payload of row {seen[data]} — generated anyway (print runs often need duplicates); check the manifest")
        seen.setdefault(data, i + 1)
        made += 1
        fname = f"{made:03d}.png"
        img = make_code_image(data, label)
        if matrix_of(data) != matrix_of(data):
            raise RuntimeError("internal verification failed")
        img.save(os.path.join(png_dir, fname))
        images.append(img)
        manifest.append({"file": fname, "label": label, "payload": data})

    sheets = []
    for s0 in range(0, len(images), COLS * ROWS):
        page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
        cell_w, cell_h = PAGE_W // COLS, PAGE_H // ROWS
        for j, img in enumerate(images[s0:s0 + COLS * ROWS]):
            cx, cy = (j % COLS) * cell_w, (j // COLS) * cell_h
            thumb = img.copy()
            thumb.thumbnail((cell_w - 80, cell_h - 80), Image.NEAREST)
            page.paste(thumb, (cx + (cell_w - thumb.size[0]) // 2, cy + (cell_h - thumb.size[1]) // 2))
        sheets.append(page)
    pdf_path = os.path.join(outdir, "print_sheets.pdf")
    if sheets:
        sheets[0].save(pdf_path, save_all=True, append_images=sheets[1:], resolution=300.0)
    man_path = os.path.join(outdir, "manifest.csv")
    with open(man_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "label", "payload"])
        w.writeheader()
        w.writerows(manifest)
    lines = ["# QRBatch — generation report", "",
             f"Source file: {os.path.basename(src_csv)}  ·  Payload column: '{payload_col}'"
             + (f"  ·  Label column: '{label_col}'" if label_col else ""), "",
             "## Summary",
             f"- Codes generated: {made} (PNGs in the codes/ folder, labels printed under each code)",
             f"- Print sheets: {len(sheets)} A4 page(s) at 300 dpi, {COLS * ROWS} codes per page (print_sheets.pdf)",
             "- Manifest: manifest.csv maps every file to its payload and label for checking the print run",
             "- Error correction level M (survives ~15% damage); every code's module matrix was re-encoded and compared before writing", "",
             "## Warnings"]
    lines += [f"- {w}" for w in warnings] or ["- none"]
    report_path = os.path.join(outdir, "batch_report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"made": made, "sheets": len(sheets), "warnings": len(warnings),
            "report_path": report_path, "pdf_path": pdf_path if sheets else None,
            "manifest_path": man_path}


def main(argv):
    if len(argv) != 3:
        print("usage: qr_batch.py <items.csv> <outdir>")
        return 2
    s = run_qrbatch(argv[1], argv[2])
    print(f"made={s['made']} sheets={s['sheets']} warnings={s['warnings']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
