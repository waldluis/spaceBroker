"""
web_server.py
Flask web server for the Börsen-Bar tablet/control interface.
Bar staff open http://<pc-ip>:5000/ on any device to register sales.
"""

import logging

from flask import Flask, render_template_string, request, jsonify

from config import FLASK_HOST, FLASK_PORT
from state import state_lock, prices, sales, total_sold, last_update_time

# Suppress Flask's request log noise
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("werkzeug").propagate = False

app = Flask(__name__)

# ---------------------------------------------------------------------------
# HTML served to tablets / staff devices
# ---------------------------------------------------------------------------

_HTML_PAGE = r"""
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
    h1 { font-size: 22px; text-align: center; margin-bottom: 16px; }
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
    .btn:active { transform: scale(0.97); }
    .bier        { background: #ffd966; }
    .cocktail    { background: #a4c2f4; }
    .shot        { background: #b6d7a8; }
    .weinschorle { background: #f4b183; }
    #status { margin-top: 16px; font-size: 14px; text-align: center; }
  </style>
</head>
<body>
  <h1>📈 Space Broker — Bediengerät</h1>

  <div class="grid">
    <button class="btn bier"        onclick="order('Bier')">🍺 Bier</button>
    <button class="btn cocktail"    onclick="order('Cocktails')">🍸 Cocktail</button>
    <button class="btn shot"        onclick="order('Shots')">🥃 Shot</button>
    <button class="btn weinschorle" onclick="order('Weinschorle')">🍷 Weinschorle</button>
  </div>

  <div id="status">Status: bereit</div>

  <script>
    async function order(drink) {
      try {
        const r = await fetch('/order', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({drink})
        });
        const j = await r.json();
        document.getElementById('status').innerText =
          'Letzte Aktion: ' + j.message + ' | ' + new Date().toLocaleTimeString();
        flash('#eaffea', 250);
      } catch (e) {
        document.getElementById('status').innerText = 'Fehler beim Senden: ' + e;
        flash('#ffd6d6', 800);
      }
    }

    function flash(color, ms) {
      document.body.style.transition = 'background 0.25s';
      document.body.style.background = color;
      setTimeout(() => { document.body.style.background = ''; }, ms);
    }
  </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template_string(_HTML_PAGE, host=request.host)


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
            "prices": dict(prices),
            "sales": dict(sales),
            "total_sold": dict(total_sold),
            "last_update": last_update_time,
        })


# ---------------------------------------------------------------------------
# Runner (called from main.py in a background thread)
# ---------------------------------------------------------------------------

def run_flask():
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True, use_reloader=False)
