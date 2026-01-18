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

APP_NAME = "RFID POS Bridge"
APP_VERSION = "1.6"  # keep in sync with your latest changes
pyautogui.FAILSAFE = False
LOG_ENABLED = False


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


CONFIG_PATH = app_dir() / "rfid_bridge.ini"
DEFAULT_CONFIG = """\
# RFID POS Bridge configuration.
# prefix = digits/letters added before the UID (magstripe PAN prefix, etc.).
#   Note: Chromis docs mention “M1995”, but Chromis only accepts digits.
#         The default below uses “1995” so cards are recognized.
# suffix = trailing characters after UID
# send_semicolon = yes/no (prepend semicolon). Chromis may prefer no semicolon.
# send_enter = yes/no (press Enter after typing).
# typing_interval = delay between keystrokes (seconds). Increase if POS needs slower typing.
# chromis_mode = yes/no (Chromis mode disables semicolon and enforces Enter)
# logging_enabled = yes/no
# log_file = log filename
# startup_delay = seconds to wait for reader after login
# nfc_tag_mode = yes/no (enable NFC tag mode)
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


def startup_dir():
    return Path(os.environ["APPDATA"]) / r"Microsoft\Windows\Start Menu\Programs\Startup"


def autostart_script_path():
    return startup_dir() / f"{APP_NAME}.cmd"


def launch_command():
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    python_exe = Path(sys.executable).resolve()
    pythonw = python_exe.parent / "pythonw.exe"
    script = Path(__file__).resolve()
    if pythonw.exists():
        return f'"{pythonw}" "{script}"'
    return f'"{python_executable}" "{script}"'


def install_autostart():
    cmd_path = autostart_script_path()
    cmd_path.parent.mkdir(parents=True, exist_ok=True)
    cmd_path.write_text('@echo off\nstart "" ' + launch_command() + "\n", encoding="utf-8")
    return cmd_path.exists()


def remove_autostart():
    try:
        autostart_script_path().unlink()
        return True
    except FileNotFoundError:
        return False


def autostart_installed():
    return autostart_script_path().exists()


class RFIDWorker(threading.Thread):
    def __init__(self, queue, config, initial_config=None):
        super().__init__(daemon=True)
        self.queue = queue
        self.running = threading.Event()
        self.running.set()
        self.config = initial_config or config
        self.cfg = config
        self.reader = None
        self.last_uid = None
        self.current_status = None

    def stop(self):
        self.running.clear()

    def set_status(self, status, log_text=None):
        if status != self.current_status:
            self.current_status = status
            self.queue.put(("status", status))
        if log_text:
            self.queue.put(("log", "info", log_text))

    def wait_for_reader(self):
        delay = self.config.get("startup_delay", 0.0)
        if delay > 0:
            self.set_status("waiting", f"[STATUS] waiting {delay:.1f}s before searching for reader…")
            time.sleep(delay)

        while self.running.is_set():
            rdrs = readers()
            if rdrs:
                self.set_status("scanning", "[STATUS] reader detected.")
                return rdrs[0]
            self.set_status("waiting", "[STATUS] no reader yet—retrying in 5s.")
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
        self.reader = self.wait_for_reader()
        if not self.reader:
            return

        self.queue.put(("log", "info", f"[STATUS] using reader: {self.reader}"))
        self.set_status("scanning")

        while self.running.is_set():
            try:
                conn = self.wait_for_card()
                if not conn:
                    break

                uid_hex = self.read_uid(conn)
                self.queue.put(("log", "info", f"Card UID (hex): {uid_hex}"))
                self.set_status("card")

                if uid_hex != self.last_uid:
                    decimal_uid = str(int(uid_hex, 16))
                    payload = ""
                    if self.config["send_semicolon"]:
                        payload += ";"
                    payload += self.config["prefix"] + decimal_uid + self.config["suffix"]

                    track_digits = len(self.config["prefix"]) + len(decimal_uid)
                    self.queue.put(("log", "info", f"Sending: {payload}"))

                    if track_digits > 37:
                        self.queue.put(("log", "warning", f"Track data has {track_digits} digits (max 37)."))
                    else:
                        pyautogui.write(payload, interval=self.config["typing_interval"])
                        if self.config["send_enter"]:
                            pyautogui.press("enter")

                    self.last_uid = uid_hex
                else:
                    self.queue.put(("log", "info", "Duplicate UID – skipped."))

                self.set_status("scanning")

            except Exception as exc:
                self.queue.put(("log", "error", str(exc)))
                self.set_status("waiting")
            finally:
                try:
                    conn.disconnect()
                except Exception:
                    pass
                time.sleep(0.5)
                self.last_uid = None


def run_console():
    cfg = load_config()
    configure_logging(cfg)
    print(f"[INFO] RFID POS Bridge v{APP_VERSION} (console mode)")

    queue = Queue()
    worker = RFIDWorker(queue, cfg)
    worker.start()

    try:
        # Allow Ctrl+C to exit gracefully
        while True:
            try:
                msg = queue.get(timeout=0.5)
                if isinstance(msg, tuple) and len(msg) >= 2:
                    if msg[0] == "log":
                        _, level, text = msg
                        log_message(level, text)
                    elif msg[0] == "status":
                        # msg = ("status", "color")
                        log_message("info", f"[STATUS] {msg[1]}")
                    else:
                        log_message("info", str(msg))
                else:
                    log_message("info", str(msg))
            except Empty:
                continue
            except KeyboardInterrupt:
                print("\n[INFO] Console interrupt received. Stopping...")
                break
    finally:
        worker.stop()
        worker.join()


def create_icon(color):
    img = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=color)
    draw.text((20, 20), "RF", fill="white")
    return img


def run_tray():
    cfg = load_config()
    configure_logging(cfg)

    icons = {
        "red": create_icon("red"),
        "yellow": create_icon("yellow"),
        "green": create_icon("green"),
    }

    icon = pystray.Icon(APP_NAME, icons["red"], f"{APP_NAME} v{APP_VERSION} (idle)")
    queue = Queue()
    worker = None

    states = {
        "waiting": "waiting for reader",
        "scanning": "active",
        "card": "card scanned",
    }

    def set_state(status):
        color = {"waiting":"red","scanning":"yellow","card":"green"}.get(status,"red")
        icon.icon = icons[color]
        icon.title = f"{APP_NAME} v{APP_VERSION} ({states.get(status,'idle')})"

    def start_worker(_icon=None, _item=None):
        nonlocal worker
        if worker and worker.is_alive():
            queue.put(("log", "info", "RFID scanning already running."))
            return
        new_cfg = load_config()
        worker = RFIDWorker(queue, new_cfg)
        worker.start()
        queue.put(("log", "info", "RFID scanning started."))
        set_state("waiting")

    def stop_worker(_icon=None, _item=None):
        nonlocal worker
        if worker and worker.is_alive():
            worker.stop()
            worker.join(timeout=2)
            queue.put(("log", "info", "RFID scanning stopped."))
        else:
            queue.put(("log", "info", "RFID scanning already stopped."))
        set_state("waiting")

    def reload_config(_icon=None, _item=None):
        if worker and worker.is_alive():
            worker.reload_config()
        queue.put(("log", "info", "Configuration reloaded."))

    def toggle_startup(_icon=None, _item=None):
        if autostart_installed():
            remove_autostart()
            queue.put(("log", "info", "Autostart removed."))
        else:
            install_autostart()
            queue.put(("log", "info", "Autostart installed."))

    def quit_app(_icon=None, _item=None):
        stop_worker()
        icon.stop()

    icon.menu = pystray.Menu(
        pystray.MenuItem("Start scanning", start_worker, default=True),
        pystray.MenuItem("Stop scanning", stop_worker),
        pystray.MenuItem("Reload config", reload_config),
        pystray.MenuItem(
            "Start with Windows",
            toggle_startup,
            checked=lambda item: autostart_installed()
        ),
        pystray.MenuItem("Exit", quit_app)
    )

    start_worker()

    def pump_queue():
        while icon.visible:
            try:
                msg = queue.get(timeout=0.5)
                if isinstance(msg, tuple) and len(msg) >= 1:
                    if msg[0] == "log":
                        _, level, text = msg
                        log_message(level, text)
                    elif msg[0] == "status":
                        set_state(msg[1])
                    else:
                        log_message("info", str(msg))
                else:
                    log_message("info", str(msg))
            except Empty:
                continue

    threading.Thread(target=pump_queue, daemon=True).start()
    icon.run()


def main():
    if "--console" in sys.argv:
        run_console()
    else:
        run_tray()


if __name__ == "__main__":
    main()