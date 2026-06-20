# Print Assistant

Ein Projekt, das Drucken, PDF-Bearbeitung, Office-Bearbeitung und Foto-Bearbeitung über natürlichsprachliche Anweisungen im Chat steuert. Datei reinziehen, in eigenen Worten beschreiben was passieren soll, Claude Code erledigt den Rest – inklusive direktem Druck ohne Rückfrage.

## Grundprinzip

- Der Nutzer beschreibt das gewünschte Ergebnis in eigenen Worten (kein technisches Vokabular nötig).
- Claude Code übersetzt das in konkrete Parameter und führt sie aus.
- **Drucken passiert direkt, ohne Bestätigung**, sobald die Anweisung eindeutig verstanden ist. Bei Unklarheit (z. B. unklare Seitenzahl, fehlendes Papierformat) kurz nachfragen statt zu raten.
- Mehrgeräte-Setup: PC (RTX 2070) und Surface Pro 7, beide Windows. Geräteabhängige Werte (Drucker) liegen in `config/printers.yaml`, gekeyt nach Hostname.

## Tool-Routing

| Aufgabe | Werkzeug |
|---|---|
| PDF: Merge, Split, Rotation, Wasserzeichen, Seitenbereich | `pypdf` / `pikepdf` (`scripts/pdf_tools.py`) |
| PDF: reinen Text ändern | **nicht automatisierbar** – Nutzer auf Acrobat verweisen |
| Office (Word/Excel/PowerPoint): Inhalte bearbeiten | `python-docx`, `openpyxl`, `python-pptx` (`scripts/office_tools.py`) |
| Office → PDF konvertieren (vor dem Drucken) | LibreOffice headless |
| Foto: Belichtung, Crop, Hintergrund entfernen, Presets | Adobe-Connector (Lightroom/Photoshop-Tools) |
| PDF drucken | SumatraPDF CLI (`scripts/print.py`) |
| Foto/Bild drucken | `scripts/print.py` (Pillow + win32print) |
| Office-Datei drucken | erst → PDF (LibreOffice), dann SumatraPDF |

Faustregel: Python zuerst, wenn es rein strukturelle/mechanische Änderungen sind (Seiten drehen, Format konvertieren). Adobe-Connector nur, wenn es um Bildqualität/Optik geht (Belichtung, Farbe, Freistellen) – dafür ist er klar besser als ein schnelles Skript.

## Druck-Workflow (SumatraPDF)

1. Eingabedatei identifizieren (Typ per Endung/MIME).
2. Falls Office-Datei: erst mit LibreOffice headless zu PDF konvertieren.
3. Aus der Nutzerbeschreibung Druckparameter ableiten: Papierformat, Ausrichtung, Duplex, Farbe/SW, Skalierung, Seitenbereich, Kopienzahl.
4. Zieldrucker aus `config/printers.yaml` anhand Hostname auflösen (falls Nutzer keinen explizit nennt).
5. SumatraPDF mit `-print-to` + `-print-settings` aufrufen.
6. Kurze Erfolgsmeldung im Chat (kein Vorschau-Zwang, da direkt gedruckt wird).

## Konventionen

- Niemals Platzhalter-Code wie "// Rest wie vorher" – immer vollständige Skripte/Funktionen.
- Sprache: Deutsch oder Englisch. Andere Sprachen automatisch übersetzen.
- Bei Adobe-Connector-Aufrufen: Tool-Limitierungen beachten (kein PDF-Textediting, kein Upscaling, keine generative Hintergrund-Ersetzung) – wenn eine Anfrage das verlangt, das dem Nutzer kurz sagen statt es stillschweigend zu versuchen.
- Geräteerkennung über `socket.gethostname()` in Python, Mapping in `config/printers.yaml`.

## Einmaliges Setup pro Gerät

```bash
# 1. Python-Abhängigkeiten installieren
pip install -r requirements.txt

# 2. SumatraPDF installieren (für PDF-Druck)
#    https://www.sumatrapdfreader.org/download-free-pdf-viewer

# 3. LibreOffice installieren (für Office→PDF-Konvertierung)
#    https://www.libreoffice.org/download/download/

# 4. Druckernamen eintragen (echte Namen per Befehl ermitteln):
#    wmic printer get name
#    Dann config/printers.yaml editieren – Platzhalter <HOSTNAME-...> durch
#    echten Hostnamen (socket.gethostname()) und <Druckername-...> durch
#    den exakten Windows-Druckernamen ersetzen.

# 5. Adobe MCP-Connector authentifizieren (einmalig pro Gerät):
#    In Claude Code: /mcp  → adobe-creativity → einloggen
```

## Noch offen / vom Nutzer zu erledigen

- [x] Druckernamen in `config/printers.yaml` eingetragen (Brother MFC-L8390CDW series)
- [x] SumatraPDF installiert
- [x] `pip install -r requirements.txt` auf Desktop ausgeführt
- [ ] `setup.ps1` auf Surface Pro 7 ausführen
- [ ] `/mcp` Authentifizierung auf jedem Gerät einmalig durchführen
- [ ] GitHub-Remote einrichten, damit das Repo auf beiden Geräten synchron bleibt

## Mittelfristig: Android-Anbindung via Claude Dispatch

Claude Dispatch (Claude Mobile App → "Claude arbeitet von Ihrem Computer aus") ist die
sauberste Lösung: Datei vom Handy schicken, Druckanweisung in Freitext, Claude führt
die Skripte direkt aus – kein Telegram-Bot, kein extra Setup.

**Voraussetzung:** Ein dauerhaft laufendes Gerät (Homeserver geplant).
Die Skripte (print.py, pdf_tools.py, office_tools.py) sind bereits Dispatch-kompatibel –
kein Umbau nötig, sobald der Server steht.
