# rfid_tray_bridge_chromispos
A simple tray utility in python (executable made with pyinstaller) to read RFID cards UIDs and send on to the active window with additional payload such as that expected by mag stripe cards in ChromisPos for the loyalty system.

The executable was tested on a Windows 11 system.
The ini file is not required as it will be created automatically - you can edit it to suit your own needs. The ini file just controls the prefix and suffix added to the payload and should be fairly self explanatory.

By default the card will be prefixed with ;BB2295 followed by the UID of the scanned card then a ? (question mark).

The program sits in the system tray and can be set to automatically start with windows.

The software is free but if you want to buy me a beer, here's my paypal: https://www.paypal.com/paypalme/alltechplus

:-)

