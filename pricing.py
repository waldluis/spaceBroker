"""
pricing.py
Pure business logic for recalculating drink prices based on demand.
All state access goes through the state_lock from state.py.
"""

import math
import logging

from config import MIN_PRICE, MAX_PRICE, START_PRICE, PRICE_STEP
from state import state_lock, prices, sales, history

logger = logging.getLogger(__name__)


def compute_price_updates() -> bool:
    """
    Recalculate prices based on sales since the last update.

    Returns True if prices were updated, False if there were no sales
    (in which case prices drift slowly back toward START_PRICE).
    """
    with state_lock:
        total = sum(sales.values())

        # Nothing sold — drift prices back toward start values
        if total == 0:
            for drink in prices:
                if prices[drink] > START_PRICE[drink]:
                    prices[drink] -= PRICE_STEP
                elif prices[drink] > START_PRICE[drink]:        # TEST if working
                    prices[drink] += PRICE_STEP
                history[drink].append(prices[drink])
            return False

        avg = total / len(prices)

        for drink in list(prices.keys()):
            # Relative deviation from the average sale count
            deviation = (sales[drink] - avg) / avg

            # Larger deviation → larger price step (capped at 1.0 per update)
            scale = 0.5 + abs(deviation)
            step = min(PRICE_STEP * scale, 1.0)

            if deviation > 0:
                prices[drink] = min(prices[drink] + step, MAX_PRICE[drink])
            elif deviation < 0:
                prices[drink] = max(prices[drink] - step, MIN_PRICE[drink])

            # Snap upward to the nearest 0.50 € increment
            prices[drink] = math.ceil(prices[drink] * 2) / 2.0

            # Final clamp to stay within bounds
            prices[drink] = min(max(prices[drink], MIN_PRICE[drink]), MAX_PRICE[drink])

            history[drink].append(prices[drink])

        logger.error("Prices %s | Sales %s", dict(prices), dict(sales))

        # Reset interval counters
        for drink in list(sales.keys()):
            sales[drink] = 0

    return True


def apply_market_crash() -> None:
    """Reset all prices to their minimum and clear the sales counters."""
    with state_lock:
        for drink in prices:
            prices[drink] = MIN_PRICE[drink]
            history[drink].append(prices[drink])
        for drink in list(sales.keys()):
            sales[drink] = 0
