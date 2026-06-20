# Auftrag: Print Assistant Projekt aufsetzen

Baue ein vollständiges Projekt, mit dem ich PDFs, Office-Dateien und Fotos per natürlichsprachlicher Anweisung im Chat bearbeiten und direkt drucken kann. Lege die komplette Ordnerstruktur, alle Skripte und Konfigurationsdateien an. Frage nach, wo dir konkrete Werte fehlen (z. B. exakte Druckernamen) – rate nicht.

## Kontext

- Windows-Umgebung, läuft auf zwei Geräten (Desktop-PC und Surface Pro 7), beide Windows.
- Hauptdateitypen: PDF, Office (docx/xlsx/pptx), Fotos.
- Adobe Creative Cloud Abo ist vorhanden, über einen bereits verbundenen MCP-Connector ("Adobe for creativity") nutzbar.
- Drucken soll **direkt** passieren, ohne Bestätigungs-Rückfrage, sobald die Anweisung eindeutig ist. Bei Mehrdeutigkeit kurz nachfragen statt zu raten.
- Sprache: Deutsch oder Englisch. Andere Sprachen automatisch übersetzen.
- Code-Konvention: niemals Platzhalter wie "// Rest wie vorher" – immer vollständige Skripte/Funktionen.

## 1. Ordnerstruktur anlegen

```
print-assistant/
├── CLAUDE.md
├── requirements.txt
├── .mcp.json
├── .gitignore
├── config/
│   └── printers.yaml
└── scripts/
    ├── print.py
    ├── pdf_tools.py
    └── office_tools.py
```

## 2. CLAUDE.md

Lege eine `CLAUDE.md` an, die folgendes festhält (als Projektgedächtnis für künftige Sessions):
- Grundprinzip: Datei reinziehen, Anweisung in eigenen Worten, direktes Drucken ohne Rückfrage bei Eindeutigkeit.
- Tool-Routing-Tabelle: PDF-Strukturänderungen → `pdf_tools.py` (pypdf/pikepdf); Office-Inhalte → `office_tools.py` (python-docx/openpyxl/python-pptx); Office→PDF-Konvertierung → LibreOffice headless; Foto-Optik (Belichtung, Crop, Hintergrund) → Adobe-Connector; Drucken → `print.py` (SumatraPDF).
- Hinweis: reine PDF-Textbearbeitung ist mit den verfügbaren Tools nicht möglich – das dem Nutzer in dem Fall klar sagen statt es zu versuchen.
- Geräteerkennung über `socket.gethostname()`, gemappt auf Drucker in `config/printers.yaml`.

## 3. `config/printers.yaml`

Struktur:
```yaml
default:
  printer_name: "<Name des Standarddruckers>"
hosts:
  <HOSTNAME-PC>:
    printer_name: "<Druckername PC>"
  <HOSTNAME-SURFACE>:
    printer_name: "<Druckername Surface>"
```
Trage Platzhalter ein und weise mich darauf hin, dass ich die echten Druckernamen (per `wmic printer get name` oder Windows-Einstellungen) eintragen muss.

## 4. `scripts/print.py`

Ein vollständiges Skript, das:
- Dateityp anhand der Endung erkennt (PDF, docx/xlsx/pptx, Bildformate).
- Office-Dateien zuerst über LibreOffice headless (`soffice --headless --convert-to pdf`) zu PDF konvertiert.
- Aus einem strukturierten Parameter-Dict (Papierformat, Ausrichtung, Duplex, Farbe/SW, Skalierung, Seitenbereich, Kopienzahl) die passenden SumatraPDF-CLI-Flags baut (`-print-to`, `-print-settings`).
- Für reine Bilddateien Pillow nutzt, um sie aufs Zielformat zu skalieren, und über `win32print` druckt.
- Den Zieldrucker per Hostname aus `config/printers.yaml` auflöst, sofern kein Drucker explizit übergeben wird.
- Eine `main()`-Funktion mit CLI-Argumenten (argparse) hat, damit es auch direkt testbar ist, nicht nur über Claude Code aufrufbar.
- Klare Fehlermeldungen wirft, wenn SumatraPDF nicht gefunden wird oder ein Druckername nicht existiert.

## 5. `scripts/pdf_tools.py`

Vollständige Funktionen mit `pypdf` (und `pikepdf` wo pypdf nicht reicht) für: Merge, Split, Rotation, Wasserzeichen, Verschlüsselung/Entschlüsselung, Seiten extrahieren. Jede Funktion einzeln aufrufbar, mit Docstrings, die beschreiben welche natürlichsprachlichen Anfragen dazu passen (hilft Claude Code beim Routing).

## 6. `scripts/office_tools.py`

Vollständige Funktionen mit `python-docx`, `openpyxl`, `python-pptx` für grundlegende Bearbeitungen (Text ersetzen, Formatierung, einfache Inhaltsänderungen). Ebenfalls mit Docstrings für die Routing-Erkennung.

## 7. `requirements.txt`

Alle benötigten Pakete: `pypdf`, `pikepdf`, `python-docx`, `openpyxl`, `python-pptx`, `pywin32`, `Pillow`, `pyyaml`.

## 8. `.mcp.json`

Adobe-MCP-Connector projektweit registrieren, damit er beim Klonen auf dem zweiten Gerät automatisch verfügbar ist:
```
claude mcp add --transport http adobe https://adobe-creativity.adobe.io/mcp --scope project
```
Führe das aus bzw. lege die resultierende `.mcp.json` an. Weise mich darauf hin, dass ich mich nach dem Klonen auf jedem Gerät einmal per `/mcp` authentifizieren muss.

## 9. `.gitignore`

Mindestens: `__pycache__/`, `*.pyc`, `.venv/`, `*.log`, generierte PDF/Bild-Outputs falls ein Output-Ordner entsteht.

## 10. Nach dem Bauen

- Kurze README-Sektion (kann Teil der CLAUDE.md sein) mit den einmaligen Setup-Schritten pro Gerät: `pip install -r requirements.txt`, SumatraPDF installieren, LibreOffice installieren, `/mcp` authentifizieren.
- Liste mir am Ende auf, was du gebaut hast, was noch fehlt (z. B. echte Druckernamen, GitHub-Remote einrichten) und was ich als Nächstes testen sollte.
