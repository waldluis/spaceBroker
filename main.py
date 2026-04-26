#!/usr/bin/env python3
"""
main.py
Entry point for the Börsen-Bar application.

Usage:
    python3 main.py

Requirements:
    pip install flask ttkthemes

The Flask server starts in a background thread.
The Tkinter GUI runs in the main thread (required by Tk on most platforms).
Bar staff open http://<FLASK_HOST>:<FLASK_PORT>/ on tablets/phones to register sales.
"""

import logging
import threading

from web_server import run_flask
from gui import BorseBarGUI

logging.basicConfig(
    level=logging.ERROR,
    filename="log.txt",
    filemode="w",
    format="%(asctime)s %(levelname)s %(message)s",
)


def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True, name="flask-server")
    flask_thread.start()

    gui = BorseBarGUI()
    gui.attributes("-zoomed", True)
    gui.mainloop()


if __name__ == "__main__":
    main()
