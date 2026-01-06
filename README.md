# rfid_tray_bridge_chromispos
A simple tray utility in python (executable made with pyinstaller) to read RFID cards UIDs and send on to the active window with additional payload such as that expected by mag stripe cards in ChromisPos for the loyalty system.

The executable was tested on a Windows 11 system.
The ini file is not required as it will be created automatically - you can edit it to suit your own needs. The ini file just controls the prefix and suffix added to the payload and should be fairly self explanatory.

By default the card will be prefixed with ;BB2295 followed by the UID of the scanned card then a ? (question mark).

The program sits in the system tray and can be set to automatically start with windows.

The software is free but if you want to buy me a beer, here's my paypal: https://www.paypal.com/paypalme/alltechplus

ChromisPos is an excellent point of sale software available on sourceforge here: https://sourceforge.net/projects/chromispos/

:-)

p.s. the code was made with the assistance of AI. I couldn't get the first scripts I tried to read data from the cards as I couldn't authenticate the data stored on the cards but could read the UID without authentication. My original idea was to program simple text on the cards. I think now I'll just program the cards with the business name and contact details so if anyone scans if they find the card, they can return it to the outlet and/or add the contact details to their phones.

As it stands as far as Chromis is concerned this could be used as either a loyalty card or gift card but not both since the gift cards uses a different prefix, if anyone can think of a way round that feel free to contribute.

🛠️ Installation & Build Guide (Windows)
✅ Prerequisites
Windows PC with USB NFC reader (PC/SC-compatible)
Python 3.8+ installed from python.org
✔️ During installation, select “Add Python to PATH”

📥 1. Download the Source
From the repository:
https://github.com/buttonsbond/rfid_tray_bridge_chromispos

Click Code → Download ZIP and extract it, or
Clone it:
git clone https://github.com/buttonsbond/rfid_tray_bridge_chromispos.git
cd rfid_tray_bridge_chromispos
📦 2. Install Dependencies
In the project folder, open Command Prompt (Shift+Right Click → “Open PowerShell window here”) and run:

pip install pyscard pyautogui pystray pillow
▶️ 3. Run the Script (No EXE needed)
To launch the tool with the tray icon:

python rfid_tray_bridge.py
A tray icon labeled “RFID POS Bridge” will appear.
A config file rfid_bridge.ini will be created next to the script.
The tool runs in the background and sends POS card data when an NFC card is scanned.
💡 Use pythonw rfid_tray_bridge.py if you prefer no console window.

🎛️ 4. Configure Card Output
Edit the generated rfid_bridge.ini file (in the same folder):

[POS]
prefix = BB2295
suffix = ?
send_semicolon = yes
send_enter = no
typing_interval = 0.01
Final output format: ;{prefix}{UID}{suffix}
Example: ;BB2295045178721E6180?

🧱 5. Optional: Build Your Own EXE
If you want a standalone executable:

Install PyInstaller:

pip install pyinstaller
Build it:

pyinstaller --onefile --noconsole rfid_tray_bridge.py
The EXE will be in the dist folder. Move it anywhere (e.g., your user folder). It will still use a local rfid_bridge.ini file right next to the EXE.

⚙️ 6. Run at Windows Startup
Right-click the tray icon → select “Start with Windows” (This adds/removes a shortcut in your Startup folder automatically.)
Alternatively, you can create your own shortcut in shell:startup pointing to:

pythonw.exe C:\Path\To\rfid_tray_bridge.py
or the compiled EXE.

🔧 Need to Modify Behavior?
You can remap prefixes based on UIDs, add logging, or extend the script—all Python source is in the repo.
The tray icon also lets you reload the INI, start/stop reading, or quit the app.
