import csv
import os
import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple

import requests


DISCORD_AVATAR_DECORATION_BASE = "https://cdn.discordapp.com/avatar-decoration-presets"
USER_AGENT = "Mozilla/5.0 DiscordDecorationGenerator/1.0"


def validate_asset_id(asset_id: str) -> bool:
    """Ensure the value matches the expected Discord asset ID format."""
    if not asset_id or not asset_id.strip():
        return False
    cleaned = asset_id.strip()
    # Discord asset IDs are numeric, usually 17-20 digits in practice.
    return bool(re.fullmatch(r"\d{10,30}", cleaned))


def build_decoration_url(asset_id: str, size: int = 256, animated: bool = False) -> str:
    """Build a Discord CDN decoration URL in the valid format."""
    cleaned = str(asset_id).strip()
    if not validate_asset_id(cleaned):
        raise ValueError(f"Invalid Discord asset ID: {asset_id!r}")

    extension = "gif" if animated else "png"
    return f"{DISCORD_AVATAR_DECORATION_BASE}/{cleaned}.{extension}?size={size}"


def generate_asset_ids(seed: str, count: int) -> List[str]:
    """Generate numeric IDs from a seed. The values are validly structured Discord IDs."""
    if count <= 0:
        raise ValueError("The number of decorations must be greater than zero.")

    base = str(seed).strip()
    if not base:
        base = "100000000000000000"
    if not base.isdigit():
        raise ValueError("The seed must contain digits only.")

    items: List[str] = []
    for idx in range(count):
        next_id = str(int(base) + idx)
        if len(next_id) < 10:
            next_id = next_id.rjust(10, "0")
        items.append(next_id)
    return items


def validate_url(url: str, timeout: int = 10) -> Tuple[bool, str]:
    """Check if the URL responds successfully. Returns (ok, details)."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout, headers={"User-Agent": USER_AGENT})
        status = response.status_code
        if 200 <= status < 400:
            return True, f"HTTP {status}"
        return False, f"HTTP {status}"
    except requests.RequestException as exc:
        return False, str(exc)


def generate_rows(seed: str, count: int, size: int, animated: bool) -> List[dict]:
    ids = generate_asset_ids(seed, count)
    rows = []
    for idx, asset_id in enumerate(ids, start=1):
        url = build_decoration_url(asset_id, size=size, animated=animated)
        ok, detail = validate_url(url)
        rows.append({
            "index": idx,
            "asset_id": asset_id,
            "url": url,
            "valid": ok,
            "status": detail,
        })
    return rows


def save_results(rows: List[dict], file_path: str) -> str:
    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".csv":
        with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=["index", "asset_id", "url", "valid", "status"])
            writer.writeheader()
            writer.writerows(rows)
    else:
        with open(file_path, "w", encoding="utf-8") as text_file:
            for row in rows:
                text_file.write(f"{row['index']} | {row['asset_id']} | {row['url']} | valid={row['valid']} | {row['status']}\n")
    return file_path


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Discord Avatar Decoration Generator")
        self.geometry("760x640")
        self.minsize(700, 560)

        self.configure(padx=16, pady=16)

        self.count_var = tk.StringVar(value="10")
        self.seed_var = tk.StringVar(value="100000000000000000")
        self.size_var = tk.StringVar(value="256")
        self.animated_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        title = ttk.Label(self, text="Discord Avatar Decoration Generator", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", pady=(0, 12))

        frame = ttk.Frame(self, padding=(12, 12))
        frame.pack(fill="both", expand=True)

        grid = ttk.Frame(frame)
        grid.pack(fill="x", pady=(0, 12))

        ttk.Label(grid, text="Number of decorations:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(grid, textvariable=self.count_var, width=20).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(grid, text="Asset seed / starting ID:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(grid, textvariable=self.seed_var, width=30).grid(row=1, column=1, sticky="w", pady=6)

        ttk.Label(grid, text="Image size:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
        size_combo = ttk.Combobox(grid, textvariable=self.size_var, values=["128", "256", "512", "1024"], state="readonly", width=10)
        size_combo.grid(row=2, column=1, sticky="w", pady=6)

        animated = ttk.Checkbutton(grid, text="Animated gif version", variable=self.animated_var)
        animated.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 10))

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(0, 12))
        ttk.Button(button_row, text="Generate Decorations", command=self.generate).pack(side="left", padx=(0, 10))
        ttk.Button(button_row, text="Save Results", command=self.save_results).pack(side="left")

        self.output = tk.Text(frame, height=22, wrap="word", font=("Consolas", 10))
        self.output.pack(fill="both", expand=True)

        self.output.insert(tk.END, "Ready. Fill in the values and press Generate Decorations.\n")

    def generate(self) -> None:
        try:
            count = int(self.count_var.get())
            seed = self.seed_var.get().strip()
            if not seed:
                raise ValueError("Asset seed cannot be empty.")
            size = int(self.size_var.get())
            animated = self.animated_var.get()
            if count <= 0:
                raise ValueError("Number of decorations must be greater than zero.")
            rows = generate_rows(seed, count, size, animated)
            self.output.delete(1.0, tk.END)
            for row in rows:
                prefix = "OK" if row["valid"] else "FAIL"
                self.output.insert(tk.END, f"[{prefix}] {row['asset_id']} -> {row['url']} ({row['status']})\n")
            self.output.see(tk.END)
        except Exception as exc:  # pragma: no cover - GUI error handling
            messagebox.showerror("Input error", str(exc))

    def save_results(self) -> None:
        try:
            count = int(self.count_var.get())
            seed = self.seed_var.get().strip()
            size = int(self.size_var.get())
            animated = self.animated_var.get()
            if count <= 0:
                raise ValueError("Number of decorations must be greater than zero.")

            rows = generate_rows(seed, count, size, animated)
            save_path = os.path.join(os.getcwd(), "discord_decoration_links.txt")
            save_results_path = save_results(rows, save_path)
            messagebox.showinfo("Saved", f"Results were saved to:\n{save_results_path}")
        except Exception as exc:  # pragma: no cover - GUI error handling
            messagebox.showerror("Save error", str(exc))


if __name__ == "__main__":
    app = App()
    app.mainloop()
    sys.exit(0)
