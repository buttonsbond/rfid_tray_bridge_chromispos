# rfid_tray_bridge_chromispos
A simple tray utility in python (executable made with pyinstaller) to read RFID cards UIDs and send on to the active window with additional payload such as that expected by mag stripe cards in ChromisPos for the loyalty system.

The executable was tested on a Windows 11 system.
The ini file is not required as it will be created automatically - you can edit it to suit your own needs. The ini file just controls the prefix and suffix added to the payload and should be fairly self explanatory.

The program sits in the system tray and can be set to automatically start with windows.

The software is free but if you want to buy me a beer, here's my paypal: https://www.paypal.com/paypalme/alltechplus

ChromisPos is an excellent point of sale software available on sourceforge here: https://sourceforge.net/projects/chromispos/

:-)

p.s. the code was made with the assistance of AI. I couldn't get the first scripts I tried to read data from the cards as I couldn't authenticate the data stored on the cards but could read the UID without authentication. My original idea was to program simple text on the cards. I think now I'll just program the cards with the business name and contact details so if anyone scans if they find the card, they can return it to the outlet and/or add the contact details to their phones.

As it stands as far as Chromis is concerned this could be used as either a loyalty card or gift card but not both since the gift cards uses a different prefix, if anyone can think of a way round that feel free to contribute.

# 🚀 Installation & Usage (Windows)
✅ Prerequisites
Windows PC with a PC/SC-compatible NFC reader
Python 3.8+ installed from python.org ☑️ During installation, check “Add Python to PATH”
ChromePOS or any POS app that accepts keyboard/MagStripe-style input
📥 1. Get the Repo
git clone https://github.com/buttonsbond/rfid_tray_bridge_chromispos.git
cd rfid_tray_bridge_chromispos
Or download and extract the ZIP.

📦 2. Install Dependencies
pip install pyscard pyautogui pystray pillow
▶️ 3. Run the Bridge
Tray mode (default):
python rfid_tray_bridge.py

Console mode (for debugging):
python rfid_tray_bridge.py --console
(Logs UID, payload, and Track-2 length warnings.)

The script creates rfid_bridge.ini next to itself. By default, it’s configured for Chromis POS.

🔧 4. Configuration (rfid_bridge.ini)
* prefix: pre-pends digits/letters before the UID. For Chromis, digits only (docs say “M1995” but it fails).
* suffix: trailing char (Chromis default '?'); leave blank if not needed.
* send_semicolon: include a ';' start sentinel (Chromis needs this off).
* send_enter: press Enter after typing the card number (Chromis needs this on).
* typing_interval: delay between keystrokes in seconds.
* chromis_mode: when "yes," overrides the above for Chromis (no ';', Enter on).
[POS]
prefix = 1995
suffix = ?
send_semicolon = no
send_enter = yes
typing_interval = 0.01
chromis_mode = yes
🧱 5. Optional: Build a Standalone EXE
pip install pyinstaller
pyinstaller --onefile --noconsole rfid_tray_bridge.py
You’ll find the executable under dist\rfid_tray_bridge.exe. Run it from any writable folder (e.g. your user directory) so the INI file can sit beside it.

⚙️ 6. Start with Windows (Optional)
Use the tray icon → Start with Windows to add/remove the app from your Startup folder. Works for both script and EXE versions.

📜 Changelog
v0.2 (latest)
Chromis mode improvements: default prefix now 1995 (docs mention “M1995”, but Chromis only accepts digits).
INI comments updated to explain this behavior for other POS users.
Console mode enhanced to show the full payload and warn if the track exceeds 37 digits.
Tray icon bug fix (typo in create_icon()).
General stability improvements for both script and EXE workflow.
v0.1
First release: UID reader, decimal conversion, tray controls, autostart toggle, chromis-compatible output.
