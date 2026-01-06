import configparser
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
from smartcard.Exceptions import NoCardException

APP_NAME = "RFID POS Bridge"
pyautogui.FAILSAFE = False  # prevent accidental aborts when mouse hits the corner


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


CONFIG_PATH = app_dir() / "rfid_bridge.ini"
DEFAULT_CONFIG = """\
# RFID POS Bridge configuration.
# prefix: digits/letters added before the UID (e.g., merchant ID or magstripe PAN prefix).
#    Note: Chromis documentation suggests “M1995”, but Chromis only accepts digits;
#          the default below uses “1995” so the card is recognized.
# suffix: trailing characters (default '?' for magstripe sentinel). Leave blank if not needed.
# send_semicolon: set to "yes" to prepend ';' (magstripe Track-2 start). Chromis prefers "no".
# send_enter: set to "yes" to press Enter after the code. Chromis requires this.
# typing_interval: delay between keystrokes (seconds). Increase if your POS needs slower typing.
# chromis_mode: when "yes", overrides the above to match Chromis expectations (no ';', send Enter).
[POS]
prefix = 1995
suffix = ?
send_semicolon = no
send_enter = yes
typing_interval = 0.01
chromis_mode = yes
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
    result = {
        "prefix": section.get("prefix", ""),
        "suffix": section.get("suffix", ""),
        "send_semicolon": section.getboolean("send_semicolon", False),
        "send_enter": section.getboolean("send_enter", True),
        "typing_interval": section.getfloat("typing_interval", 0.01),
        "chromis_mode": section.getboolean("chromis_mode", True),
    }

    if result["chromis_mode"]:
        result["send_semicolon"] = False
        result["send_enter"] = True

    return result


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
    return f'"{python_exe}" "{script}"'


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
    def __init__(self, message_queue):
        super().__init__(daemon=True)
        self.message_queue = message_queue
        self.running = threading.Event()
        self.running.set()
        self.cfg_lock = threading.Lock()
        self.config = load_config()
        self.last_uid = None
        self.reader = None

    def reload_config(self):
        with self.cfg_lock:
            self.config = load_config()

    def stop(self):
        self.running.clear()

    def wait_for_card(self):
        while self.running.is_set():
            conn = self.reader.createConnection()
            try:
                conn.connect()
                return conn
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
        rdrs = readers()
        if not rdrs:
            self.message_queue.put(("error", "No smartcard readers detected."))
            return
        self.reader = rdrs[0]
        self.message_queue.put(("info", f"Using reader: {self.reader}"))

        while self.running.is_set():
            try:
                conn = self.wait_for_card()
                if not conn:
                    break

                uid_hex = self.read_uid(conn)
                self.message_queue.put(("info", f"Card UID (hex): {uid_hex}"))

                if uid_hex != self.last_uid:
                    decimal_uid = str(int(uid_hex, 16))
                    with self.cfg_lock:
                        cfg = self.config.copy()

                    pieces = []
                    if cfg["send_semicolon"]:
                        pieces.append(";")
                    pieces.append(cfg["prefix"])
                    pieces.append(decimal_uid)
                    pieces.append(cfg["suffix"])
                    payload = "".join(pieces)

                    track_digits = len(cfg["prefix"]) + len(decimal_uid)
                    self.message_queue.put(("info", f"Sending: {payload}"))

                    if track_digits > 37:
                        self.message_queue.put((
                            "warning",
                            f"Track data has {track_digits} digits (max 37). POS may reject it."
                        ))
                    else:
                        pyautogui.write(payload, interval=cfg["typing_interval"])
                        if cfg["send_enter"]:
                            pyautogui.press("enter")

                    self.last_uid = uid_hex
                else:
                    self.message_queue.put(("info", "Duplicate UID – skipped."))

            except Exception as exc:
                self.message_queue.put(("error", str(exc)))
            finally:
                try:
                    conn.disconnect()
                except Exception:
                    pass
                time.sleep(0.6)
                self.last_uid = None


def run_console():
    print("[INFO] Running in console mode. Press Ctrl+C to exit.")
    message_queue = Queue()
    worker = RFIDWorker(message_queue)
    worker.start()

    try:
        while True:
            try:
                level, msg = message_queue.get(timeout=0.5)
                print(f"[{level.upper()}] {msg}")
            except Empty:
                continue
    except KeyboardInterrupt:
        print("\n[INFO] Stopping…")
    finally:
        worker.stop()
        worker.join(timeout=2)
        print("[INFO] Exited.")


def create_icon(size=64, color="blue"):
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, size - 8, size - 8), fill=color)
    draw.text((size // 4, size // 3), "RF", fill="white")
    return img


def run_tray():
    message_queue = Queue()
    worker = None

    def start_scanning(icon, item=None):
        nonlocal worker
        if worker and worker.is_alive():
            message_queue.put(("info", "RFID scanning already running."))
            return
        worker = RFIDWorker(message_queue)
        worker.start()
        message_queue.put(("info", "RFID scanning started."))

    def stop_scanning(icon, item=None):
        nonlocal worker
        if worker and worker.is_alive():
            worker.stop()
            worker.join(timeout=2)
            message_queue.put(("info", "RFID scanning stopped."))
        else:
            message_queue.put(("info", "RFID scanning already stopped."))

    def reload_config(icon, item=None):
        nonlocal worker
        if worker and worker.is_alive():
            worker.reload_config()
        else:
            load_config()
        message_queue.put(("info", "Configuration reloaded."))

    def toggle_autostart(icon, item):
        if autostart_installed():
            if remove_autostart():
                message_queue.put(("info", "Autostart removed."))
        else:
            if install_autostart():
                message_queue.put(("info", "Autostart installed."))

    def quit_app(icon, item):
        stop_scanning(icon)
        icon.stop()

    icon = pystray.Icon(
        APP_NAME,
        create_icon(),
        menu=pystray.Menu(
            pystray.MenuItem("Start scanning", start_scanning, default=True),
            pystray.MenuItem("Stop scanning", stop_scanning),
            pystray.MenuItem("Reload config", reload_config),
            pystray.MenuItem(
                "Start with Windows",
                toggle_autostart,
                checked=lambda item: autostart_installed()
            ),
            pystray.MenuItem("Exit", quit_app)
        )
    )

    start_scanning(icon)

    def monitor_messages():
        while icon.visible:
            try:
                level, msg = message_queue.get(timeout=0.5)
                print(f"[{level.upper()}] {msg}")
            except Empty:
                continue

    threading.Thread(target=monitor_messages, daemon=True).start()
    icon.run()


def main():
    if "--console" in sys.argv:
        run_console()
    else:
        run_tray()


if __name__ == "__main__":
    main()