Fotobox Version 0.1

Funktion:
	- lädt bei bestehender Verbindung zu 192.168.0.1 Fotos im 
	  definierten Remoteordner herunter und löscht sie auf 192.168.0.1
	- zeigt die Bilder in einem lokalen Fenster an
	- die Reihenfolge der Anzeige wird bestimmt durch das letzte
	  Anzeigedatum (default = 1.1.1900 --> neue Fotos werden
	  möglichst bald angezeigt und dann hinten angereiht)
	- Anzeigedauer je Foto: 10s
	
Bevor es losgeht...
	- FlashAir konfigurieren:
		- Basiskonfiguration abschließen
		- manuellen WLAN-aktiv-Modus aktivieren
		- WLAN-AP-Modus aktivieren (default)
		- echo "UPLOAD=1\nNOISE_CANCEL=2\n" >> <flashair>/WLAN_SD/CONFIG
		  (sonst kein Löschen der Remotefotos möglich bzw. schlechtere 
		   oder keine Verbindung in belebten Umgebungen)
	- Verbindung zu FlashAir herstellen
	- (!) immer darauf achten, dass neue Fotos nicht schreibgeschützt
	      gespeichert werden und dass sie in den Ordner 
	      <flashair>/DCIM/100CANON
	      gespeichert werden
	
	
TODO:
	- Konfiguration:
		- GUI zum Einstellen der nötigen Parameter
		- speichern ~
	- Verbindung "sichern": pairing
	- (de)aktivierbare Eventanzeige / Log
	- Überprüfen des lokalen Ordners auf Dateien und Ermöglichen
	  einer reinen Diashow-Funktion
