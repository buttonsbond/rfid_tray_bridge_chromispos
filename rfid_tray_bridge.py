#!/usr/bin/env python3
import configparser
import logging
import os
import sys
import threading
import time
from pathlib import Path
from queue import Queue, Empty

import pyautogui
import pystray
from PIL import Image, ImageDraw
from smartcard.System import readers
from smartcard.Exceptions import NoCardException, CardConnectionException
from smartcard.scard import SCARD_PROTOCOL_RAW

APP_NAME = "RFID POS Bridge"
APP_VERSION = "1.6"
pyautogui.FAILSAFE = False
LOG_ENABLED = False

def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

CONFIG_PATH = app_dir() / "rfid_bridge.ini"

# Default config tailored for Chromis-like operation
DEFAULT_CONFIG = """\
[POS]
prefix = 1995
suffix = ?
send_semicolon = no
send_enter = yes
typing_interval = 0.01
chromis_mode = yes
logging_enabled = yes
log_file = rfid_bridge.log
startup_delay = 5.0
nfc_tag_mode = no
"""

def ensure_config():
    if CONFIG_PATH.exists():
        return
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(DEFAULT_CONFIG, encoding="utf-8")
    print(f"[INFO] Created default config at {CONFIG_PATH}")

def load_config():
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding="utf-8")
    section = config["POS"]
    vals = {
        "prefix": section.get("prefix", ""),
        "suffix": section.get("suffix", ""),
        "send_semicolon": section.getboolean("send_semicolon", False),
        "send_enter": section.getboolean("send_enter", True),
        "typing_interval": section.getfloat("typing_interval", 0.01),
        "chromis_mode": section.getboolean("chromis_mode", True),
        "logging_enabled": section.getboolean("logging_enabled", True),
        "log_file": section.get("log_file", "rfid_bridge.log"),
        "startup_delay": section.getfloat("startup_delay", 5.0),
        "nfc_tag_mode": section.getboolean("nfc_tag_mode", False),
    }
    if vals["chromis_mode"]:
        vals["send_semicolon"] = False
        vals["send_enter"] = True
    return vals

def configure_logging(cfg):
    global LOG_ENABLED
    if LOG_ENABLED or not cfg.get("logging_enabled", False):
        return
    log_path = app_dir() / cfg.get("log_file", "rfid_bridge.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8", mode="a")],
    )
    LOG_ENABLED = True
    logging.info("Logging enabled. Writing to %s", log_path)

def log_message(level, message):
    print(f"[{level.upper()}] {message}")
    if LOG_ENABLED:
        logging.log(getattr(logging, level.upper(), logging.INFO), message)

def create_icon(color):
    img = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=color)
    draw.text((20, 20), "RF", fill="white")
    return img

def main():
    # Console mode and Tray mode share this core; we expose both
    if "--console" in sys.argv:
        run_console()
    else:
        run_tray()

# Console mode
def run_console():
    cfg = load_config()
    configure_logging(cfg)
    print(f"[INFO] RFID POS Bridge v{APP_VERSION} (console mode)")

    queue = Queue()
    # A minimal worker for console mode: wait for reader/card, then log status
    worker = RFIDWorker(queue, cfg)
    worker.start()

    try:
        while True:
            try:
                pair = queue.get(timeout=0.5)
                # tolerate both (level, msg) and (msg,) shapes
                if isinstance(pair, tuple) and len(pair) >= 2 and pair[0] == "log":
                    _, level, text = pair
                    log_message(level, text)
                elif isinstance(pair, tuple) and pair and pair[0] == "status":
                    log_message("info", f"[STATUS] {pair[1]}")
                else:
                    log_message("info", str(pair))
            except Empty:
                continue
            except KeyboardInterrupt:
                print("\n[INFO] Console interrupt received. Stopping...")
                break
    finally:
        worker.stop()
        worker.join()

# Tray mode
def run_tray():
    cfg = load_config()
    configure_logging(cfg)

    # colors
    icon_red = create_icon("red")
    icon_yellow = create_icon("yellow")
    icon_green = create_icon("green")
    icons = {
        "red": icon_red,
        "yellow": icon_yellow,
        "green": icon_green,
    }

    icon = pystray.Icon(APP_NAME, icons["red"], f"{APP_NAME} v{APP_VERSION} (idle)")
    queue = Queue()
    worker = None

    def set_state(color, label):
        icon.icon = icons[color]
        icon.title = f"{APP_NAME} v{APP_VERSION} ({label})"

    def start_worker(_icon=None, _item=None):
        nonlocal worker
        if worker and worker.is_alive():
            queue.put(("log", "info", "RFID scanning already running."))
            return
        new_cfg = load_config()
        worker = RFIDWorker(queue, new_cfg)
        worker.start()
        queue.put(("log", "info", "RFID scanning started."))
        set_state("yellow", "active")

    def stop_worker(_icon=None, _item=None):
        nonlocal worker
        if worker and worker.is_alive():
            worker.stop()
            worker.join(timeout=2)
            queue.put(("log", "info", "RFID scanning stopped."))
        else:
            queue.put(("log", "info", "RFID scanning already stopped."))
        set_state("red", "idle")

    # no reload/config or startup
    icon.menu = pystray.Menu(
        pystray.MenuItem("Start scanning", start_worker, default=True),
        pystray.MenuItem("Stop scanning", stop_worker),
        pystray.MenuItem("Exit", lambda: (stop_worker(), icon.stop()))
    )

    start_worker()

    def pump_queue():
        while icon.visible:
            try:
                msg = queue.get(timeout=0.5)
                if isinstance(msg, tuple) and len(msg) >= 1:
                    if msg[0] == "log":
                        level, text = msg[1], msg[2]
                        log_message(level, text)
                    elif msg[0] == "status":
                        set_state(msg[1], "active" if msg[1] != "red" else "idle")
                    else:
                        log_message("info", str(msg))
                else:
                    log_message("info", str(msg))
            except Empty:
                continue

    threading.Thread(target=pump_queue, daemon=True).start()
    icon.run()

# Small RFIDWorker class for core functionality
class RFIDWorker(threading.Thread):
    def __init__(self, queue, config, initial_config=None):
        super().__init__(daemon=True)
        self.queue = queue
        self.running = threading.Event()
        self.running.set()
        self.config = config or {}
        self.reader = None
        self.last_uid = None

    def stop(self):
        self.running.clear()

    def _get_reader(self):
        delay = self.config.get("startup_delay", 0.0)
        if delay > 0:
            self.queue.put(("log", "info", f"[STATUS] waiting {delay:.1f}s before searching for reader…"))
            time.sleep(delay)
        while self.running.is_set():
            rdrs = readers()
            if rdrs:
                self.queue.put(("log", "info", f"[STATUS] reader detected: {rdrs[0]}"))
                return rdrs[0]
            self.queue.put(("log", "warning", "[STATUS] no reader yet—retrying in 5s."))
            time.sleep(5)
        return None

    def wait_for_card(self):
        while self.running.is_set():
            connection = self.reader.createConnection()
            try:
                connection.connect()
                return connection
            except NoCardException:
                time.sleep(0.2)
        return None

    def read_uid(self, connection):
        apdu = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        data, sw1, sw2 = connection.transmit(apdu)
        if sw1 == 0x90 and sw2 == 0x00:
            return "".join(f"{byte:02X}" for byte in data)
        raise RuntimeError(f"Failed to read UID: {sw1:02X} {sw2:02X}")

    def run(self):
        self.reader = self._get_reader()
        if not self.reader:
            self.queue.put(("log", "info", "[STATUS] no reader detected; stopping."))
            return
        self.queue.put(("log", "info", f"[STATUS] using reader: {self.reader}"))
        self.queue.put(("status", "yellow"))

        while self.running.is_set():
            try:
                conn = self.wait_for_card()
                if not conn:
                    break
                uid = self.read_uid(conn)
                self.queue.put(("log", "info", f"Card UID (hex): {uid}"))
                if uid != self.last_uid:
                    decimal_uid = str(int(uid, 16))
                    payload = self.config["prefix"] + decimal_uid + self.config["suffix"]
                    track_digits = len(self.config["prefix"]) + len(decimal_uid)
                    self.queue.put(("log", "info", f"Sending: {payload}"))

                    if track_digits > 37:
                        self.queue.put(("log", "warning", f"Track data has {track_digits} digits (max 37)."))
                    else:
                        pyautogui.write(";" + payload if False else payload, interval=self.config["typing_interval"])
                        if self.config["send_enter"]:
                            pyautogui.press("enter")

                    self.last_uid = uid
                else:
                    self.queue.put(("log", "info", "Duplicate UID – skipped."))

            except Exception as exc:
                self.queue.put(("log", "error", str(exc)))
            finally:
                try:
                    conn.disconnect()
                except Exception:
                    pass
                time.sleep(0.5)
                self.last_uid = None

def main():
    if "--console" in sys.argv:
        run_console()
    else:
        run_tray()

if __name__ == "__main__":
    main()