Fotobox Version 0.5

Funktion:
	- lädt bei bestehender Verbindung zu flashair Fotos vom
	  definierten Remoteordner herunter und löscht sie auf flashair
	- zeigt die Bilder in einem lokalen Fenster an
	- die Reihenfolge der Anzeige wird bestimmt durch das letzte
	  Anzeigedatum (default = 1.1.1900 --> neue Fotos werden
	  möglichst bald angezeigt und dann hinten angereiht)
	- anpassbare Anzeigedauer
	- anpassbare Verzögerung, bevor Fotos heruntergeladen werden
	- Fotos können in den FotoboxBilder-Ordner kopiert werden, um in
	  die Diashow eingebunden zu werden; es ist auf diese Weise eine
	  reine Diashow möglich
	- F11 aktiviert/ deaktiviert den Vollbildmodus
	- Esc deaktiviert den Vollbildmodus
	
Vorbereitungen:
	- FlashAir konfigurieren (einmalig bis zum nächsten Reset der 
	  Karte):
		- Basiskonfiguration abschließen
		- manuellen WLAN-aktiv-Modus aktivieren (sonst beträgt die 
		  Zeit bis zur automatischen Abschaltung maximal 30 Minuten)
		(- WLAN-AP-Modus aktivieren (default))
		- echo "UPLOAD=1\nNOISE_CANCEL=2\n" >> <flashair>/WLAN_SD/CONFIG
		  (sonst kein Löschen der Remotefotos möglich bzw. schlechtere 
		   oder keine Verbindung in belebten Umgebungen)
	- Verbindung zu FlashAir herstellen
	- WLAN aktivieren: Schreibschutz des konfigurierten Bildes
	  deaktivieren (evtl. aktivieren und wieder deaktivieren)
	- (!) immer darauf achten, dass neue Fotos nicht schreibgeschützt
	      gespeichert werden und dass sie in den Ordner gespeichert 
	      werden, der im Setup definiert wurde
	- erster Start: Terminal öffnen, in den FlashAir-Fotobox-Ordner
	  wechseln und die Main.py ausführen. Es wird dann ein Starter
	  "FlashAir-Fotobox" erstellt, der auf den Schreibtisch oder an
	  einen anderen Ort kopiert werden kann. Ein Doppelklick auf
	  den Starter führt dann zukünftig das Programm aus.
	
	
TODO:
	- Verbindung "sichern": pairing ?
	- sich für eine Sprache entscheiden :-)
	- Diashow-Modus ohne Pingen der FlashAir bzw. Testen der USB-Verbindung
	- Debugging der USB-Verbindung:
	    - erkennen von Fotos, die vorher per Wifi heruntergeladen wurden und durch den Flashairbug nicht
	      gelöscht werden konnten


Version History:
    0.5
        - USB-Verbindung zur Kamera möglich (Beta)
    0.4
        - Logging
        - Icon
        - es wird versucht, die Threads sauber zu beenden (max 5s)
        - Exceptionhandling
        - Fotos, die auf der FlashAir nach Löschen wieder auftauchen, können
          wiedererkannt werden
        - diverse kleine Umstrukturierungen
    0.2.1
        - Starter wird erstellt
        - sauberen Shutdown der Threads vorbereitet
	0.2
		- Konfigurationsmöglichkeiten hinzugefügt:
		    - Kameraordner
		    - Downloadordner
		    - Anzeigedauer
		    - Downloadverzögerung
