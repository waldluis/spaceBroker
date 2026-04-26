"""
gui.py
Tkinter GUI for the Börsen-Bar beamer display.
Shows live prices and a price-history chart for all drinks.
"""

import time
import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk

from config import DRINKS, DRINK_COLORS, UPDATE_INTERVAL_SEC
from state import state_lock, prices, sales, total_sold, history, last_update_time
from pricing import compute_price_updates, apply_market_crash

import state  # for updating last_update_time in-place


class BorseBarGUI(ThemedTk):
    def __init__(self):
        super().__init__(theme="plastik")
        self.title("📈 Space Broker - Live Market")
        self.geometry("1300x900")
        self.resizable(False, False)

        self._setup_styles()

        # References to shared state (no copies — mutations are visible immediately)
        self.prices = prices
        self.sales = sales
        self.total_sold = total_sold
        self.history = history

        self._create_widgets()
        self.after(1000, self._tick)

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _setup_styles(self):
        self.style = ttk.Style(self)
        self.configure(bg=self.style.lookup("TFrame", "background"))
        self.style.configure("TLabel", font=("Segoe UI", 11))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("Price.TLabel", font=("Segoe UI", 13))
        self.style.configure("TButton", padding=6, font=("Segoe UI", 11))
        self.style.map(
            "TButton",
            background=[("active", "#4B9CD3")],
            relief=[("pressed", "sunken"), ("!pressed", "raised")],
        )

    def _create_widgets(self):
        # ---- Top bar ----
        ttk.Frame(self, padding=(10, 10)).pack(side=tk.TOP, fill=tk.X)

        main = ttk.Frame(self, padding=(10, 8))
        main.pack(fill=tk.BOTH, expand=True)

        # ---- Price cards (left column) ----
        left = ttk.Frame(main)
        left.pack(side=tk.TOP, fill=tk.Y, padx=(0, 10))

        self.price_vars = {}
        self.sales_vars = {}

        for drink in DRINKS:
            color = DRINK_COLORS[drink]
            card = ttk.Frame(left, borderwidth=2, relief="ridge", padding=8)
            card.pack(side=tk.LEFT, fill=tk.X, padx=0)

            ttk.Label(card, text=drink, font=("Helvetica", 48, "bold"),
                      background=color).grid(row=0, column=0, sticky="w")

            pv = tk.StringVar(value=f"{self.prices[drink]:.2f} €")
            self.price_vars[drink] = pv
            ttk.Label(card, textvariable=pv, font=("Helvetica", 54)).grid(
                row=0, column=1, sticky="e", padx=(10, 0)
            )

            sv = tk.StringVar(value=str(self.sales.get(drink, 0)))
            self.sales_vars[drink] = sv

        # ---- Chart canvas (right area) ----
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(right, width=1800, height=850, background="white")
        self.canvas.pack(padx=6, pady=6)

        # ---- Bottom bar ----
        bottom = ttk.Frame(self, padding=6)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)

        self.update_info = tk.StringVar(value="Letztes Update: -")
        ttk.Label(bottom, textvariable=self.update_info).pack(side=tk.LEFT)
        ttk.Button(bottom, text="MARKTCRASH (Test)",
                   command=self._on_market_crash).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def manual_order(self, drink: str):
        """Register a single sale directly from the GUI (keyboard shortcut etc.)."""
        with state_lock:
            sales[drink] += 1
            total_sold[drink] += 1
        self._refresh_ui()

    def _on_market_crash(self):
        apply_market_crash()
        self._refresh_ui()

    # ------------------------------------------------------------------
    # UI update cycle
    # ------------------------------------------------------------------

    def _tick(self):
        """Called every second. Triggers a price update when the interval elapses."""
        now = time.time()
        if now - state.last_update_time >= UPDATE_INTERVAL_SEC:
            state.last_update_time = now
            compute_price_updates()
            self.update_info.set(
                f"Letztes Update: {time.strftime('%H:%M:%S', time.localtime(now))}"
            )
        self._refresh_ui()
        self.after(1000, self._tick)

    def _refresh_ui(self):
        with state_lock:
            for drink in prices:
                self.price_vars[drink].set(f"{prices[drink]:.2f} €")
                self.sales_vars[drink].set(str(sales.get(drink, 0)))
        self._redraw_canvas()

    def _redraw_canvas(self):
        c = self.canvas
        c.delete("all")
        w = int(c["width"])
        h = int(c["height"])
        margin = 40
        inner_w = w - 2 * margin
        inner_h = h - 2 * margin

        # Axes
        c.create_line(margin, margin, margin, h - margin)
        c.create_line(margin, h - margin, w - margin, h - margin)

        # Value range across all drinks
        all_vals = [v for d in history for v in history[d]]
        amin = 0
        amax = max(all_vals) if all_vals else 1.0
        if amax == amin:
            amax = amin + 1.0

        steps = len(next(iter(history.values())))

        # X-axis tick marks
        for i in range(steps):
            x = margin + (i / (steps - 1)) * inner_w
            c.create_line(x, h - margin, x, h - margin + 5)
            if i % 5 == 0:
                c.create_text(x, h - margin + 15, text=str(i), anchor="n")

        # Y-axis labels
        for i in range(6):
            y = margin + (i / 5) * inner_h
            val = amax - (i / 5) * (amax - amin)
            c.create_text(margin - 10, y, text=f"{val:.2f}", anchor="e")

        # Price lines per drink
        colors = list(DRINK_COLORS.values())
        for idx, drink in enumerate(DRINKS):
            hist = list(history[drink])
            if len(hist) < 2:
                continue
            pts = [
                (
                    margin + (i / (len(hist) - 1)) * inner_w,
                    margin + (1 - (val - amin) / (amax - amin)) * inner_h,
                )
                for i, val in enumerate(hist)
            ]
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                c.create_line(x1, y1, x2, y2, width=8, fill=colors[idx % len(colors)])
