ONLINE-EINKAUFSLISTE MIT LOGIN

Funktionen:
- Registrierung und Login
- Jeder Benutzer sieht nur seine eigenen Listen
- Listen erstellen, bearbeiten, löschen
- Artikel abhaken: erledigte Artikel werden grün
- Anzeige-Seite fürs iPad/Handy: /display
- Datenbank: lokal SQLite, online PostgreSQL über DATABASE_URL

LOKAL STARTEN:
1. ZIP entpacken
2. Im Ordner cmd öffnen
3. Eingeben:
   python -m pip install -r requirements.txt
   python app.py
4. Browser:
   http://localhost:5000

ONLINE AUF RENDER:
1. GitHub-Konto erstellen/anmelden
2. Neues Repository erstellen, z.B. einkaufsliste-online
3. Alle Dateien aus diesem Ordner ins Repository hochladen
4. Bei Render.com anmelden
5. New + -> Blueprint
6. GitHub verbinden und dieses Repository auswählen
7. Render erkennt render.yaml
8. Deploy starten
9. Warten, bis der Status "Live" ist
10. Deine Online-Adresse öffnen, z.B.:
    https://einkaufsliste-online.onrender.com

WICHTIG:
- Für echtes dauerhaftes Speichern sollte die Datenbank nicht nur als kurzlebige Testdatenbank laufen.
- SECRET_KEY wird in render.yaml automatisch erzeugt.
- DATABASE_URL wird automatisch mit der Render-Datenbank verbunden.