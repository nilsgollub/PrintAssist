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
| PDF: reinen Text ändern | **nicht automatisierbar** – Nutzer auf einen PDF-Editor verweisen |
| PDF verkleinern / optimieren | `pdf_tools.compress_pdf()` (pikepdf) |
| Poster: PDF/Bild größer als A4 über mehrere Blätter zum Zusammenkleben | `pdf_tools.tile_poster()` – danach mit `scale=noscale` + `duplex=simplex` drucken |
| Office (Word/Excel/PowerPoint): Inhalte bearbeiten | `python-docx`, `openpyxl`, `python-pptx` (`scripts/office_tools.py`) |
| Office → PDF konvertieren (vor dem Drucken) | LibreOffice headless |
| PDF drucken | SumatraPDF CLI (`scripts/print.py`) |
| Foto/Bild drucken | `scripts/print.py` (Pillow + win32print) |
| Foto vor dem Druck bearbeiten | `scripts/image_tools.py` (siehe unten) |
| Office-Datei drucken | erst → PDF (LibreOffice), dann SumatraPDF |

Faustregel: alles in Python, keine Cloud-Dienste. Fotobearbeitung über `scripts/image_tools.py` (Pillow, Hintergrund freistellen lokal per `rembg`).

## Fotobearbeitung – `scripts/image_tools.py`

| Aufgabe | Funktion / CLI |
|---|---|
| Belichtung (Blendenstufen), Helligkeit, Kontrast, Sättigung, Farbtemperatur, Schärfe – einzeln oder alles auf einmal | `adjust(input, output, exposure=0, brightness=1, contrast=1, saturation=1, temperature=0, sharpness=1)` / `adjust` |
| Automatische Tonkorrektur | `auto_tone(input, output, per_channel=False)` / `auto-tone` (`--per-channel` entfernt auch Farbstiche, kann aber übersteuern) |
| Automatischer Weißabgleich | `white_balance(input, output)` / `white-balance` |
| Schwarzweiß | `grayscale(input, output)` / `grayscale` |
| Zuschneiden / auf Druckformat bringen (A4, A5, A6, Letter, 10x15, 13x18, 9x13) | `fit_paper(input, output, paper, mode="fill"\|"fit", orientation, dpi=300, margin_mm=0)` / `fit-paper` |
| Hintergrund entfernen (Freistellen) | `remove_background(input, output, background=None\|"white", model="u2net")` / `remove-bg` (braucht `rembg`, Modell ~170 MB wird beim ersten Aufruf geladen) |

Aufruf: `python scripts/image_tools.py <befehl> <input> <output> [optionen]`. EXIF-Drehung wird angewendet, ICC-Profil bleibt erhalten. `fit_paper` warnt unter 150 dpi.

### Was nicht geht (direkt sagen, nicht versuchen)
- PDF-Text bearbeiten ✗
- Bild über natürliche Auflösung hinaus hochskalieren ✗
- Hintergrund generativ neu erstellen oder Bild KI-gestützt erweitern ✗ (nur freistellen und mit einfarbigem Hintergrund oder weißem Rand auffüllen)
- Lightroom-Presets, Vektorisieren, Bereiche generativ füllen ✗

## Druck-Workflow (SumatraPDF)

1. Eingabedatei identifizieren (Typ per Endung/MIME).
2. Falls Office-Datei: erst mit LibreOffice headless zu PDF konvertieren.
3. Aus der Nutzerbeschreibung Druckparameter ableiten: Papierformat, Ausrichtung, Duplex, Farbe/SW, Skalierung, Seitenbereich, Kopienzahl.
   - **Duplex-Default beachten**: Der Brother MFC-L8390CDW druckt standardmäßig beidseitig. Wird `duplex` nicht gesetzt, nutzt der Drucker seinen eigenen Default (Duplex). Bei Postern/Kacheln, Fotos und Etiketten – alles mit einer Seite pro Blatt – **immer explizit `duplex=simplex`** mitgeben. Poster zusätzlich mit `scale=noscale`, sonst passen die Kacheln nicht zusammen.
4. Zieldrucker aus `config/printers.yaml` anhand Hostname auflösen (falls Nutzer keinen explizit nennt).
5. SumatraPDF mit `-print-to` + `-print-settings` aufrufen.
6. Kurze Erfolgsmeldung im Chat (kein Vorschau-Zwang, da direkt gedruckt wird).

## Konventionen

- Niemals Platzhalter-Code wie "// Rest wie vorher" – immer vollständige Skripte/Funktionen.
- Sprache: Deutsch oder Englisch. Andere Sprachen automatisch übersetzen.
- Grenzen der Fotobearbeitung beachten (kein PDF-Textediting, kein Upscaling, nichts Generatives) – wenn eine Anfrage das verlangt, das dem Nutzer kurz sagen statt es stillschweigend zu versuchen.
- Geräteerkennung über `socket.gethostname()` in Python, Mapping in `config/printers.yaml`.
- **Vorschau-Workflow**: `preview_pdf()` aufrufen, PNG als `preview.png` in den Projektordner kopieren und dem Nutzer sagen, er soll es im VS Code Explorer anklicken. `Start-Process`/`Invoke-Item` funktionieren nicht (Sandbox). `SendUserFile` und `Read` zeigen keine Bilder inline im VSCode-Chat.

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
```

## Einrichtung auf neuem Gerät

```powershell
git clone https://github.com/nilsgollub/PrintAssist.git
cd PrintAssist
powershell -ExecutionPolicy Bypass -File setup.ps1
```

`setup.ps1` erkennt Drucker automatisch und schreibt `config/printers.yaml`.
Die Datei ist gitignored — jedes Gerät hat seine eigene lokale Kopie.

## Mittelfristig: Android-Anbindung via Claude Dispatch

Claude Dispatch (Claude Mobile App → "Claude arbeitet von Ihrem Computer aus") ist die
sauberste Lösung: Datei vom Handy schicken, Druckanweisung in Freitext, Claude führt
die Skripte direkt aus – kein Telegram-Bot, kein extra Setup.

**Voraussetzung:** Ein dauerhaft laufendes Gerät (Homeserver geplant).
Die Skripte (print.py, pdf_tools.py, office_tools.py, image_tools.py) sind bereits Dispatch-kompatibel –
kein Umbau nötig, sobald der Server steht.
