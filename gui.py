#!/usr/bin/env python3
"""QRBatch desktop shell (tkinter). Pick a CSV -> QR PNGs + A4 print sheets."""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qr_batch import run_qrbatch


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QRBatch — Bulk QR Codes & Print Sheets")
        self.geometry("680x520")
        self.src = tk.StringVar()
        tk.Label(self, text="CSV file with a link/payload column (and an optional label column):").pack(anchor="w", padx=12, pady=(12, 2))
        row = tk.Frame(self)
        row.pack(fill="x", padx=12)
        tk.Entry(row, textvariable=self.src).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Browse…", command=self.pick).pack(side="left", padx=6)
        self.btn = tk.Button(self, text="Generate Codes & Print Sheets", command=self.run, height=2)
        self.btn.pack(pady=12)
        self.log = scrolledtext.ScrolledText(self, wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.write("QRBatch turns a CSV of links into labelled QR code PNGs plus\n"
                   "A4 print sheets (300 dpi) and a manifest you can check the\n"
                   "print run against. Everything runs locally.\n")

    def write(self, s):
        self.log.insert("end", s)
        self.log.see("end")

    def pick(self):
        p = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if p:
            self.src.set(p)

    def run(self):
        src = self.src.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showerror("QRBatch", "Choose a CSV file first.")
            return
        self.btn.config(state="disabled")
        threading.Thread(target=self._work, args=(src,), daemon=True).start()

    def _work(self, src):
        try:
            outdir = os.path.join(os.path.dirname(src), "qrbatch_output")
            s = run_qrbatch(src, outdir)
            self.write(f"\nDone. Codes generated: {s['made']} · print sheets: {s['sheets']} · "
                       f"warnings: {s['warnings']}\n"
                       f"Print sheets: {s['pdf_path']}\nManifest: {s['manifest_path']}\n"
                       f"Report: {s['report_path']}\n")
        except Exception as e:
            self.write(f"\nError: {e}\n")
        finally:
            self.btn.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
