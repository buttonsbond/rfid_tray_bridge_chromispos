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
## A quick note about RFID readers
The card reader I bought which was inexpensive Trust Ceto contactless reader whilst works perfectly with apps for reading and writing on your phone. According to the AI doesn't support PS/SC commands which is why I can only read the unique ID which is fine for either loyalty or gift card on ChromisPos but my original idea was to write the prefix into the tag, this way I could use NFC cards for both loyalty and gift card use, and possibly for user login too. The AI suggested that I actually needed a reader with readily available documentation to allow both reading and writing using a windows utility/python script - readers such as ACR122U (I've just ordered an ACR122U-A9 so if I can get this to work I'll publish another script specifically for that purpose. The ACR122U are dearer than the Trust Ceto was.

## 🚀 Installation & Usage (Windows)

### ✅ Prerequisites
- Windows PC with a PC/SC-compatible NFC reader  
- Python 3.8+ installed from [python.org](https://www.python.org/downloads/)  
  ☑️ During installation, check **“Add Python to PATH”**  
- Chromis POS (or any POS app that accepts keyboard/magstripe-style input)

### 📥 1. Clone or Download

```bash
git clone https://github.com/buttonsbond/rfid_tray_bridge_chromispos.git
cd rfid_tray_bridge_chromispos
```
(Or download the ZIP and extract it.)

### 📦 2. Install Dependencies
```bash
pip install pyscard pyautogui pystray pillow
```
### ▶️ 3. Run the Bridge
Tray mode (default):
```bash
python rfid_tray_bridge.py
```
Console mode (for debugging):
```bash
python rfid_tray_bridge.py --console
```
Console mode shows raw UIDs, the decimal payload sent to the POS, and warnings if the track data exceeds 37 digits (Track-2 limit).

The script creates rfid_bridge.ini next to itself. It’s preconfigured for Chromis POS.

### 🔧 4. Configuration (rfid_bridge.ini)
```bash
# RFID POS Bridge configuration.
# prefix: digits/letters added before the UID (magstripe PAN prefix, etc.).
#   Note: Chromis documentation suggests “M1995”, but Chromis only accepts digits.
#         The default below uses “1995” so cards are recognized.
# suffix: trailing characters (default '?' for magstripe). Leave blank if not needed.
# send_semicolon: set to "yes" to prepend ';' (Track-2 start). Chromis prefers "no".
# send_enter: set to "yes" to press Enter after typing. Chromis requires this.
# typing_interval: delay between keystrokes (seconds); increase if your POS needs slower typing.
# chromis_mode: when "yes", overrides the above to match Chromis (no ';', send Enter).
[POS]
prefix = 1995
suffix = ?
send_semicolon = no
send_enter = yes
typing_interval = 0.01
chromis_mode = yes
```
Adjust these values if you’re targeting another POS.

### 🧱 5. Build a Standalone EXE (Optional)
```bash
pip install pyinstaller
pyinstaller --onefile --noconsole rfid_tray_bridge.py
```
The executable will be in dist/rfid_tray_bridge.exe. Run it from a writable folder so it can create rfid_bridge.ini.

### ⚙️ 6. Start with Windows (Optional)
Use the tray icon → Start with Windows to add/remove the app from your Startup folder. Works for both script and EXE versions.

## 📜 Changelog
* v1.2c (latest)
  * 1.1 wasn't quite working as expected with regard for waiting for reader
  * added option to log output as well as --console on the command line
  * updated ini ready for future enhancement with nfc tag reading (new reader arriving any day) so hopefully the utility will be able to work with PS/PC readers as well as the dumb one I'm using now
  * tray icons - red - not scanning/no scanner detected. yellow - scanning, waiting for first card. green - scanning, first card was read
* v1.1
  * before scanning can begin the utility will wait for the reader to become available
  * hover over the icon to see current status and version number 
* v0.2
  * Default prefix is now numeric (1995) because Chromis ignores non-digit characters in Track-2.
  * INI comments updated to document this Chromis behavior for other POS users.
  * Console mode now logs the full payload and warns if the Track data exceeds 37 digits.
  * Fixed a typo in create_icon() that caused a syntax error.
  * Minor stability improvements for script and EXE usage.
* v0.1
  * Initial release: tray icon, autostart toggle, UID→decimal conversion, Chromis-friendly formatting, PyInstaller support.
