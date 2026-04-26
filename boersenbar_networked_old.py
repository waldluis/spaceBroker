#!/usr/bin/env python3
"""
boersenbar_networked.py

Combined Tkinter GUI + Flask webserver for the "Boersen-Bar".
- GUI shows prices and charts (tkinter)
- Flask serves a simple HTML control page for bar staff (tablets/laptops)
- Bar staff press buttons on the served page to register sales; those update the GUI in real-time.
- Run on the PC connected to the beamer. Other devices open http://<pc-ip>:5000/

Requirements:
    pip install flask
Tkinter is usually preinstalled with Python on Windows/macOS/Linux desktop installs.

Run:
    python3 /path/to/boersenbar_networked.py
"""

import threading
import time
import tkinter as tk
from tkinter import ttk
from collections import defaultdict, deque
import math
import random
from ttkthemes import ThemedTk
import logging


from flask import Flask, render_template_string, request, jsonify

# ---------------- Configuration ----------------
UPDATE_INTERVAL_SEC = 180   # seconds between price recalculations
PRICE_STEP = 0.5

MIN_PRICE = {
    "Bier": 0.5,
    "Cocktails": 1,
    "Shots": 0.5,
    "Weinschorle": 0.5
}
MAX_PRICE = {
    "Bier": 8.0,
    "Cocktails": 10.0,
    "Shots": 6.0,
    "Weinschorle": 8.0
}
START_PRICE = {
    "Bier": 2.0,
    "Cocktails": 4.0,
    "Shots": 1.0,
    "Weinschorle": 2.0
}
HISTORY_LENGTH = 50

# --- Hardcoded realistic price history ---
history = {
    "Bier": deque([
        1.5, 1.5, 2.0, 2.0, 2.0, 2.5, 2.5, 2.5, 3.0, 3.0,
        3.0, 2.5, 2.5, 2.0, 2.0, 2.5, 3.0, 3.5, 3.0, 3.0,
        2.5, 2.5, 3.0, 3.5, 3.5, 3.5, 3.0, 2.5, 2.5, 2.0,
        2.0, 2.5, 3.0, 3.0, 3.5, 3.5, 3.0, 3.0, 2.5, 2.5,
        2.0, 2.0, 2.5, 3.0, 3.0, 2.5, 2.5, 2.0, 1.5, 1.5
    ], maxlen=HISTORY_LENGTH),

    "Cocktails": deque([
        4.5, 4.5, 4.0, 4.0, 3.5, 3.5, 3.5, 3.5, 4.0, 4.0,
        4.5, 4.5, 4.5, 5.0, 5.0, 5.5, 5.0, 4.5, 4.5, 4.0,
        4.0, 4.0, 3.5, 3.5, 3.5, 3.5, 4.0, 4.0, 4.5, 4.5,
        4.0, 3.5, 3.5, 3.0, 3.5, 3.5, 4.0, 4.5, 4.5, 4.0,
        4.0, 4.0, 3.5, 3.5, 3.0, 3.0, 3.5, 3.5, 4.0, 4.0
    ], maxlen=HISTORY_LENGTH),

    "Shots": deque([
        1.0, 1.0, 1.5, 2.0, 1.5, 1.5, 1.0, 1.0, 1.5, 2.0,
        2.5, 2.0, 1.5, 1.0, 1.0, 1.5, 2.0, 2.5, 2.0, 1.5,
        1.0, 1.0, 1.5, 2.0, 1.5, 1.5, 2.0, 2.5, 2.0, 1.5,
        1.5, 1.0, 1.0, 1.5, 2.0, 2.5, 2.0, 1.5, 1.0, 1.0,
        1.5, 2.0, 2.0, 1.5, 1.5, 1.0, 1.0, 1.5, 2.0, 1.5
    ], maxlen=HISTORY_LENGTH),

    "Weinschorle": deque([
        2.0, 2.0, 2.0, 2.0, 2.5, 2.5, 2.0, 2.0, 2.0, 2.5,
        2.5, 2.5, 2.0, 2.0, 2.0, 2.5, 2.5, 2.0, 2.0, 2.0,
        2.0, 2.5, 2.5, 2.0, 2.0, 2.0, 2.0, 2.5, 2.5, 2.0,
        2.0, 2.0, 2.5, 2.5, 2.0, 2.0, 2.0, 2.0, 2.5, 2.5,
        2.0, 2.0, 2.0, 2.5, 2.5, 2.0, 2.0, 2.0, 2.0, 2.0
    ], maxlen=HISTORY_LENGTH)
}

total_sold = defaultdict(int, {
    "Bier": 250,
    "Cocktails": 150,
    "Shots": 120,
    "Weinschorle": 80
})

sales = defaultdict(int, {
    "Bier": 25,
    "Cocktails": 12,
    "Shots": 8,
    "Weinschorle": 5
})

# logging stuff
logging.basicConfig(level=logging.ERROR, filename="log.txt", filemode="w", format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.ERROR)

# Flask app
app = Flask(__name__)

logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("werkzeug").propagate = False

# Shared state
state_lock = threading.Lock()
prices = dict(START_PRICE)
# sales = defaultdict(int)  # counts since last update (from tablets/buttons)
# total_sold = defaultdict(int)
# history = {k: deque([v]*HISTORY_LENGTH, maxlen=HISTORY_LENGTH) for k,v in prices.items()}
last_update_time = time.time()

DRINK_KEYS = {'b':'Bier','c':'Cocktails','s':'Shots','t':'Weinschorle'}



# ---------------- Flask routes (web control page) ----------------
# HTML_PAGE = r"""
# <!doctype html>
# <html lang="de">
# <head>
#   <meta charset="utf-8" />
#   <meta name="viewport" content="width=device-width,initial-scale=1" />
#   <title>Börsen-Bar — Bedienung</title>
#   <style>
#     body { font-family: Arial, Helvetica, sans-serif; margin: 12px; background:#f7f7f7; }
#     h1 { font-size: 20px; }
#     .grid { display:grid; grid-template-columns: repeat(2, 1fr); gap:10px; max-width:640px; margin-bottom:12px; }
#     .btn { padding:18px; font-size:18px; border-radius:8px; cursor:pointer; border:none; }
#     .bier { background:#ffd966; }
#     .cocktail { background:#a4c2f4; }
#     .shot { background:#b6d7a8; }
#     .wein { background:#f4b183; }
#     .small { font-size:12px; padding:8px; }
#     #status { margin-top:8px; }
#     .topbar { display:flex; gap:10px; align-items:center; margin-bottom:10px; }
#     input[type=text]{ padding:8px; font-size:14px; }
#   </style>
# </head>
# <body>
#   <div class="topbar">
#     <h1>📈 Space Broker — Bediengerät</h1>
#   </div>

#   <div class="grid">
#     <button class="btn bier" onclick="order('Bier')">🍺 Bier</button>
#     <button class="btn cocktail" onclick="order('Cocktails')">🍸 Cocktail</button>
#     <button class="btn shot" onclick="order('Shots')">🥃 Shot</button>
#     <button class="btn wein" onclick="order('Weinschorle')">🍷 Weinschorle</button>
#   </div> 

#   <div id="status">Status: bereit</div>

# <script>
# async function order(drink){
#   try{
#     const r = await fetch('/order', {
#       method:'POST',
#       headers: {'Content-Type':'application/json'},
#       body: JSON.stringify({drink: drink})
#     });
#     const j = await r.json();
#     document.getElementById('status').innerText = 'Letzte Aktion: '+j.message + ' | ' + new Date().toLocaleTimeString();
#     // brief visual feedback
#     document.body.style.transition = 'background 0.25s';
#     document.body.style.background = '#eaffea';
#     setTimeout(()=>{ document.body.style.background=''; }, 250);
#   } catch(e){
#     document.getElementById('status').innerText = 'Fehler beim Senden: '+e;
#     document.body.style.background = '#ffd6d6';
#     setTimeout(()=>{ document.body.style.background=''; }, 800);
#   }
# }

# function resetLocal(){
#   document.getElementById('status').innerText = 'Anzeige zurückgesetzt';
# }
# </script>
# </body>
# </html>
# """

HTML_PAGE = r"""
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Börsen-Bar — Bedienung</title>
  <style>
    body {
      font-family: Arial, Helvetica, sans-serif;
      margin: 12px;
      background: #f7f7f7;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    h1 {
      font-size: 22px;
      text-align: center;
      margin-bottom: 16px;
    }
    .grid {
      display: flex;
      flex-direction: column;
      gap: 14px;
      width: 100%;
      max-width: 400px;
    }
    .btn {
      padding: 36px;
      font-size: 30px;
      border-radius: 10px;
      cursor: pointer;
      border: none;
      width: 100%;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
      transition: transform 0.1s ease;
    }
    .btn:active {
      transform: scale(0.97);
    }
    .bier { background:#ffd966; }
    .cocktail { background:#a4c2f4; }
    .shot { background:#b6d7a8; }
    .Weinschorle { background:#f4b183; }
    #status {
      margin-top: 16px;
      font-size: 14px;
      text-align: center;
    }
  </style>
</head>
<body>
  <h1>📈 Space Broker — Bediengerät</h1>

  <div class="grid">
    <button class="btn bier" onclick="order('Bier')">🍺 Bier</button>
    <button class="btn cocktail" onclick="order('Cocktails')">🍸 Cocktail</button>
    <button class="btn shot" onclick="order('Shots')">🥃 Shot</button>
    <button class="btn Weinschorle" onclick="order('Weinschorle')">🍷 Weinschorle</button>
  </div>

  <div id="status">Status: bereit</div>

<script>
async function order(drink){
  try{
    const r = await fetch('/order', {
      method:'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({drink: drink})
    });
    const j = await r.json();
    document.getElementById('status').innerText = 
      'Letzte Aktion: '+j.message+' | '+new Date().toLocaleTimeString();

    // visual feedback
    document.body.style.transition = 'background 0.25s';
    document.body.style.background = '#eaffea';
    setTimeout(()=>{ document.body.style.background=''; }, 250);
  } catch(e){
    document.getElementById('status').innerText = 'Fehler beim Senden: '+e;
    document.body.style.background = '#ffd6d6';
    setTimeout(()=>{ document.body.style.background=''; }, 800);
  }
}

function resetLocal(){
  document.getElementById('status').innerText = 'Anzeige zurückgesetzt';
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    host = request.host
    return render_template_string(HTML_PAGE, host=host)

@app.route("/order", methods=["POST"])
def order():
    data = request.get_json(force=True)
    drink = data.get("drink")
    if drink not in prices:
        return jsonify({"success": False, "message": f"Unbekanntes Getränk: {drink}"}), 400
    with state_lock:
        sales[drink] += 1
        total_sold[drink] += 1
    return jsonify({"success": True, "message": f"Bestellung registriert: {drink}"})

@app.route("/status", methods=["GET"])
def status():
    with state_lock:
        return jsonify({
            "prices": prices,
            "sales": sales,
            "total_sold": total_sold,
            "last_update": last_update_time
        })

# ---------------- GUI (Tkinter) ----------------
class BorseBarGUI(ThemedTk):
    def __init__(self):
        super().__init__(theme="plastik")
        self.title("📈 Space Broker - Live Market")
        self.geometry("1300x900")
        self.resizable(False, False)

        # Create a nice style baseline
        self.style = ttk.Style(self)
        self.configure(bg=self.style.lookup("TFrame", "background"))
        self.style.configure("TLabel", font=("Segoe UI", 11))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("Price.TLabel", font=("Segoe UI", 13))
        self.style.configure("TButton", padding=6, font=("Segoe UI", 11))
        self.style.map("TButton",
                       background=[("active", "#4B9CD3")],
                       relief=[("pressed", "sunken"), ("!pressed", "raised")])

        self.prices = prices  # reference shared dict
        self.sales = sales
        self.total_sold = total_sold
        self.history = history
        self.last_update_time = last_update_time

        # --- 🧩 Initialize baseline sales and fake h  istory ---
        # baseline_sales = 5
        # for d in self.prices.keys():
        #     # Only initialize if not already done
        #     if d not in self.history or not self.history[d]:
        #         self.history[d] = [
        #             self.prices[d] + random.uniform(-0.3, 0.3)
        #             for _ in range(HISTORY_LENGTH)
        #         ]
        #         # Give each item a small random baseline demand
        #         self.sales.setdefault(d, baseline_sales + random.uniform(-1, 1))

        self.create_widgets()
        self.after(1000, self.gui_tick)  # update UI every second

    def create_widgets(self):
        top = ttk.Frame(self, padding=(10,10))
        top.pack(side=tk.TOP, fill=tk.X)
        # lbl = ttk.Label(top, text="                                                                                                                     Space Broker — Live Market", font=("Helvetica",20,"bold"))
        # lbl.pack(side=tk.LEFT)


        main = ttk.Frame(self, padding=(10,8))
        main.pack(fill=tk.BOTH, expand=True)

        # where the labels are placed
        left = ttk.Frame(main)
        left.pack(side=tk.TOP, fill=tk.Y, padx=(0,10))

        colors = ["#ffd966","#a4c2f4","#b6d7a8","#f4b183"]
        idx = 0

        self.price_vars = {}
        self.sales_vars = {}
        for drink in ["Bier","Cocktails","Shots","Weinschorle"]:
            card = ttk.Frame(left, borderwidth=2, relief="ridge", padding=8)
            card.pack(side=tk.LEFT, fill=tk.X, padx=0)

            name = ttk.Label(card, text=drink, font=("Helvetica",48,"bold"), background=colors[idx%len(colors)])
            name.grid(row=0, column=0, sticky="w")

            pv = tk.StringVar(value=f"{self.prices[drink]:.2f} €")
            self.price_vars[drink] = pv
            ttk.Label(card, textvariable=pv, font=("Helvetica",54)).grid(row=0, column=1, sticky="e", padx=(10,0))

            sv = tk.StringVar(value=str(self.sales.get(drink,0)))
            self.sales_vars[drink] = sv
            # ttk.Label(card, text="Verkäufe :").grid(row=1, column=0, sticky="w")
            # ttk.Label(card, textvariable=sv).grid(row=1, column=1, sticky="e")
            idx = idx + 1

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(right, width=1800, height=850, background="white")          # works on 24 inch display
        # self.canvas = tk.Canvas(right, width=900, height=700, background="white")
        self.canvas.pack(padx=6, pady=6)

        bottom = ttk.Frame(self, padding=6)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.update_info = tk.StringVar(value="Letztes Update: -")
        ttk.Label(bottom, textvariable=self.update_info).pack(side=tk.LEFT)
        ttk.Button(bottom, text="MARKTCRASH (Test)", command=self.market_crash).pack(side=tk.RIGHT)

    def manual_order(self, drink):
        with state_lock:
            sales[drink] += 1
            total_sold[drink] += 1
        self.refresh_ui()

    def compute_price_updates(self):
        # # Basic offer/demand algorithm
        # with state_lock:
        #     total = sum(sales.values()) or 1
        #     avg = total / len(prices)
        #     for d in list(prices.keys()):
        #         if sales[d] > avg:
        #             prices[d] = min(prices[d] + PRICE_STEP, MAX_PRICE[d])
        #         elif sales[d] < avg:
        #             prices[d] = max(prices[d] - PRICE_STEP, MIN_PRICE[d])
        #         # append history
        #         history[d].append(prices[d])
        #     # reset sales counters
        #     for k in list(sales.keys()):
        #         sales[k] = 0

        with state_lock:
            total = sum(sales.values())

            # If absolutely nothing sold -> go slowly back to start prices
            if total == 0:
                for p in prices:
                    if prices[p] > START_PRICE[p]:
                        prices[p] = prices[p] - PRICE_STEP
                    history[p].append(prices[p])
                # reset counters and skip price updates
                return None

            avg = total / len(prices)

            for d in list(prices.keys()): # relative deviation: +1.0 means 100% above avg, -1.0 means 100% below 
                deviation = (sales[d] - avg) / avg 
                
                # scale factor: reacts more strongly to larger differences 
                # e.g., deviation 0.5 → 1.5x step, deviation 2.0 → 3x step 
                scale = 0.5 + abs(deviation) 

                # dynamic step size 
                step = PRICE_STEP * scale 
                
                # update price based on direction 
                if deviation > 0: # high demand → price up 
                    step = min(step, 1.0)
                    prices[d] = min(prices[d] + step, MAX_PRICE[d])
                elif deviation < 0: # low demand → price down 
                    step = min(step, 1.0)
                    prices[d] = max(prices[d] - step, MIN_PRICE[d]) 
                    
                # append history for plotting or analytics 
                history[d].append(prices[d]) 
                
                # 🔹 round upward to the next 0.5 increment 
                prices[d] = math.ceil(prices[d] * 2) / 2.0 
                # prices[d] = round(prices[d] * 2) / 2.0
                
                # clamp again in case rounding exceeded max 
                prices[d] = min(max(prices[d], MIN_PRICE[d]), MAX_PRICE[d]) 
                
                # reset sales counters for next time frame 

            # save prices and sales to file
            logger.error(f"Prices {prices}, Sales {sales}")

            for k in list(sales.keys()): 
                sales[k] = 0


    def refresh_ui(self):
        with state_lock:
            for d in prices:
                self.price_vars[d].set(f"{prices[d]:.2f} €")
                self.sales_vars[d].set(str(sales.get(d,0)))
        self.redraw_canvas()

    def redraw_canvas(self):
        c = self.canvas
        c.delete("all")
        w = int(c['width']); h = int(c['height'])
        margin = 40; inner_w = w-2*margin; inner_h = h-2*margin

        # axes
        c.create_line(margin, margin, margin, h-margin)
        c.create_line(margin, h-margin, w-margin, h-margin)

        all_vals = []
        for d in history:
            all_vals.extend(history[d])
        amin = 0
        # amin = min(all_vals) if all_vals else 0
        amax = max(all_vals) if all_vals else 1
        if amax == amin:
            amax = amin + 1.0
        steps = len(next(iter(history.values())))

        for i in range(steps):
            x = margin + (i/(steps-1))*inner_w
            c.create_line(x, h-margin, x, h-margin+5)
            if i%5==0:
                c.create_text(x, h-margin+15, text=str(i), anchor="n")

        for i in range(6):
            y = margin + (i/5)*inner_h
            val = amax - (i/5)*(amax-amin)
            c.create_text(margin-10, y, text=f"{val:.2f}", anchor="e")

        names = list(history.keys())
        colors = ["#ffd966","#a4c2f4","#b6d7a8","#f4b183"]
        for idx,d in enumerate(names):
            pts = []
            hist = list(history[d])
            for i,val in enumerate(hist):
                x = margin + (i/(len(hist)-1))*inner_w
                y = margin + (1 - (val-amin)/(amax-amin))*inner_h
                pts.append((x,y))
            for i in range(len(pts)-1):
                x1,y1 = pts[i]; x2,y2 = pts[i+1]
                c.create_line(x1,y1,x2,y2, width=8, fill=colors[idx%len(colors)])
            # legend
            # lx = w - margin - 180; ly = margin + 20 + idx*20
            # c.create_rectangle(lx-8, ly-8, lx+8, ly+8, outline="black", fill=colors[idx%len(colors)])
            # c.create_text(lx+20, ly, text=f"{d} ({prices[d]:.2f} €)", anchor="w")

    def market_crash(self):
        with state_lock:
            for d in prices:
                prices[d] = MIN_PRICE[d]
                history[d].append(prices[d])
            for k in list(sales.keys()):
                sales[k] = 0
        self.refresh_ui()

    def gui_tick(self):
        # Called every second to check whether it's time to update prices
        global last_update_time
        now = time.time()
        if now - last_update_time >= UPDATE_INTERVAL_SEC:
            last_update_time = now
            self.compute_price_updates()
            self.update_info.set(f"Letztes Update: {time.strftime('%H:%M:%S', time.localtime(now))}")
            self.refresh_ui()
        else:
            # still update UI sales/prices display (reflect incoming orders)
            self.refresh_ui()
        self.after(1000, self.gui_tick)

# ---------------- Thread to run Flask ----------------
def run_flask(host='192.168.0.101', port=5000):               # 0.0.0.0 for local only
    # Disable Flask reloader (since we're running in a thread)
    app.run(host=host, port=port, threaded=True, use_reloader=False)

# ---------------- Main entry ----------------
def main():
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start Tkinter GUI in main thread
    gui = BorseBarGUI()
    gui.attributes('-zoomed', True)
    gui.mainloop()

if __name__ == "__main__":
    main()
