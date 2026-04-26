"""
config.py
All static configuration for the Börsen-Bar application.
"""

# How often prices are recalculated (seconds)
UPDATE_INTERVAL_SEC = 180

# Smallest price increment/decrement
PRICE_STEP = 0.5

# History length for the price chart
HISTORY_LENGTH = 50

# Flask server settings
# FLASK_HOST = "192.168.0.101"            # for real setup
FLASK_HOST = "0.0.0.0"                    # for testing  
FLASK_PORT = 5000

# Drink keys for keyboard shortcuts
DRINK_KEYS = {"b": "Bier", "c": "Cocktails", "s": "Shots", "w": "Weinschorle"}

# Ordered list of all drinks (used for consistent iteration)
DRINKS = ["Bier", "Cocktails", "Shots", "Weinschorle"]

# Per-drink price bounds
MIN_PRICE = {
    "Bier": 0.5,
    "Cocktails": 1.0,
    "Shots": 0.5,
    "Weinschorle": 0.5,
}

MAX_PRICE = {
    "Bier": 8.0,
    "Cocktails": 10.0,
    "Shots": 6.0,
    "Weinschorle": 8.0,
}

START_PRICE = {
    "Bier": 2.0,
    "Cocktails": 4.0,
    "Shots": 1.0,
    "Weinschorle": 2.0,
}

# Drink colors used in the GUI and web page
DRINK_COLORS = {
    "Bier": "#ffd966",
    "Cocktails": "#a4c2f4",
    "Shots": "#b6d7a8",
    "Weinschorle": "#f4b183",
}
