"""
state.py
Shared mutable state for the Börsen-Bar application.
All modules import from here; access is protected by state_lock.
"""

import threading
import time
from collections import defaultdict, deque

from config import (
    DRINKS,
    START_PRICE,
    HISTORY_LENGTH,
)

# Thread lock — always acquire before reading or writing shared state
state_lock = threading.Lock()

# Current prices (mutable)
prices: dict[str, float] = dict(START_PRICE)

# Sales registered since the last price recalculation
sales: defaultdict[str, int] = defaultdict(int, {
    "Bier": 25,
    "Cocktails": 12,
    "Shots": 8,
    "Weinschorle": 5,
})

# Cumulative sales for the whole session
total_sold: defaultdict[str, int] = defaultdict(int, {
    "Bier": 250,
    "Cocktails": 150,
    "Shots": 120,
    "Weinschorle": 80,
})

# Realistic pre-filled price history for the chart
history: dict[str, deque] = {
    "Bier": deque([
        1.5, 1.5, 2.0, 2.0, 2.0, 2.5, 2.5, 2.5, 3.0, 3.0,
        3.0, 2.5, 2.5, 2.0, 2.0, 2.5, 3.0, 3.5, 3.0, 3.0,
        2.5, 2.5, 3.0, 3.5, 3.5, 3.5, 3.0, 2.5, 2.5, 2.0,
        2.0, 2.5, 3.0, 3.0, 3.5, 3.5, 3.0, 3.0, 2.5, 2.5,
        2.0, 2.0, 2.5, 3.0, 3.0, 2.5, 2.5, 2.0, 1.5, 1.5,
    ], maxlen=HISTORY_LENGTH),
    "Cocktails": deque([
        4.5, 4.5, 4.0, 4.0, 3.5, 3.5, 3.5, 3.5, 4.0, 4.0,
        4.5, 4.5, 4.5, 5.0, 5.0, 5.5, 5.0, 4.5, 4.5, 4.0,
        4.0, 4.0, 3.5, 3.5, 3.5, 3.5, 4.0, 4.0, 4.5, 4.5,
        4.0, 3.5, 3.5, 3.0, 3.5, 3.5, 4.0, 4.5, 4.5, 4.0,
        4.0, 4.0, 3.5, 3.5, 3.0, 3.0, 3.5, 3.5, 4.0, 4.0,
    ], maxlen=HISTORY_LENGTH),
    "Shots": deque([
        1.0, 1.0, 1.5, 2.0, 1.5, 1.5, 1.0, 1.0, 1.5, 2.0,
        2.5, 2.0, 1.5, 1.0, 1.0, 1.5, 2.0, 2.5, 2.0, 1.5,
        1.0, 1.0, 1.5, 2.0, 1.5, 1.5, 2.0, 2.5, 2.0, 1.5,
        1.5, 1.0, 1.0, 1.5, 2.0, 2.5, 2.0, 1.5, 1.0, 1.0,
        1.5, 2.0, 2.0, 1.5, 1.5, 1.0, 1.0, 1.5, 2.0, 1.5,
    ], maxlen=HISTORY_LENGTH),
    "Weinschorle": deque([
        2.0, 2.0, 2.0, 2.0, 2.5, 2.5, 2.0, 2.0, 2.0, 2.5,
        2.5, 2.5, 2.0, 2.0, 2.0, 2.5, 2.5, 2.0, 2.0, 2.0,
        2.0, 2.5, 2.5, 2.0, 2.0, 2.0, 2.0, 2.5, 2.5, 2.0,
        2.0, 2.0, 2.5, 2.5, 2.0, 2.0, 2.0, 2.0, 2.5, 2.5,
        2.0, 2.0, 2.0, 2.5, 2.5, 2.0, 2.0, 2.0, 2.0, 2.0,
    ], maxlen=HISTORY_LENGTH),
}

# Timestamp of the last price recalculation
last_update_time: float = time.time()
