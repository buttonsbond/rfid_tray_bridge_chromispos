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
