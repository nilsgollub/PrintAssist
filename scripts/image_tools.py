"""
image_tools.py - Fotobearbeitung vor dem Druck, ohne Adobe CC.

Reines Pillow (plattformunabhängig, Windows und Linux). Nur die
Hintergrundentfernung braucht zusätzlich `rembg` (lokales KI-Modell,
wird beim ersten Aufruf einmalig heruntergeladen, ~170 MB).

Alle Funktionen lesen `input`, schreiben `output` und geben den Ausgabepfad
zurück. EXIF-Drehung wird beim Laden angewendet, ICC-Profil und DPI bleiben
erhalten.

CLI:
    python image_tools.py adjust foto.jpg out.jpg --exposure 0.5 --contrast 1.1
    python image_tools.py auto-tone foto.jpg out.jpg [--per-channel]
    python image_tools.py white-balance foto.jpg out.jpg
    python image_tools.py fit-paper foto.jpg out.jpg --paper 10x15 --mode fill
    python image_tools.py remove-bg foto.jpg out.png --background white
    python image_tools.py grayscale foto.jpg out.jpg
"""

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

# Papierformate in mm (Breite x Höhe, Hochformat)
PAPER_MM = {
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "A6": (105, 148),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
    "10x15": (102, 152),
    "13x18": (127, 178),
    "9x13": (89, 127),
}


# ---------------------------------------------------------------------------
# Laden/Speichern
# ---------------------------------------------------------------------------

def _load(path):
    img = Image.open(path)
    img.load()
    info = {k: img.info[k] for k in ("icc_profile", "dpi") if k in img.info}
    img = ImageOps.exif_transpose(img)
    return img, info


def _split_alpha(img):
    """RGB-Bild + optionaler Alphakanal, damit Anpassungen Transparenz nicht anfassen."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        return img.convert("RGB"), img.getchannel("A")
    return img.convert("RGB"), None


def _merge_alpha(rgb, alpha):
    if alpha is None:
        return rgb
    rgb = rgb.convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


def _save(img, output, info, dpi=None):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {}
    if "icc_profile" in info:
        kwargs["icc_profile"] = info["icc_profile"]
    if dpi or "dpi" in info:
        kwargs["dpi"] = dpi or info["dpi"]
    if output.suffix.lower() in (".jpg", ".jpeg"):
        if img.mode not in ("RGB", "L"):
            img = _flatten(img, (255, 255, 255))
        kwargs["quality"] = 95
        kwargs["subsampling"] = 0
    img.save(output, **kwargs)
    return str(output)


def _flatten(img, color):
    if img.mode != "RGBA":
        return img.convert("RGB")
    bg = Image.new("RGB", img.size, color)
    bg.paste(img, mask=img.getchannel("A"))
    return bg


# ---------------------------------------------------------------------------
# Anpassungen
# ---------------------------------------------------------------------------

def _exposure_lut(ev):
    """Belichtung in Blendenstufen, im linearen Licht (sRGB-Gamma ~2.2)."""
    gain = 2.0 ** ev
    return [min(255, round(((v / 255) ** 2.2 * gain) ** (1 / 2.2) * 255)) for v in range(256)]


def _temperature(rgb, temperature):
    """temperature -100 (kühler/blauer) .. +100 (wärmer/gelber)."""
    f = temperature / 100 * 0.15
    r_gain, b_gain = 1 + f, 1 - f
    r, g, b = rgb.split()
    r = r.point(lambda v: min(255, round(v * r_gain)))
    b = b.point(lambda v: min(255, round(v * b_gain)))
    return Image.merge("RGB", (r, g, b))


def adjust(input, output, exposure=0.0, brightness=1.0, contrast=1.0,
           saturation=1.0, temperature=0, sharpness=1.0):
    """
    Alles auf einmal (Reihenfolge wie in Lightroom: Belichtung → Weißabgleich →
    Helligkeit/Kontrast → Sättigung → Schärfe).

    exposure:    Blendenstufen, z.B. +0.5 heller, -1 eine Stufe dunkler
    brightness:  Faktor, 1.0 = unverändert
    contrast:    Faktor, 1.0 = unverändert
    saturation:  Faktor, 0 = schwarzweiß, 1.0 = unverändert, 1.3 = kräftiger
    temperature: -100 (kühler) .. +100 (wärmer)
    sharpness:   Faktor, 1.0 = unverändert, 1.5-2 = deutlich schärfer
    """
    img, info = _load(input)
    rgb, alpha = _split_alpha(img)
    if exposure:
        rgb = rgb.point(_exposure_lut(exposure) * 3)
    if temperature:
        rgb = _temperature(rgb, temperature)
    if brightness != 1.0:
        rgb = ImageEnhance.Brightness(rgb).enhance(brightness)
    if contrast != 1.0:
        rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    if saturation != 1.0:
        rgb = ImageEnhance.Color(rgb).enhance(saturation)
    if sharpness != 1.0:
        rgb = ImageEnhance.Sharpness(rgb).enhance(sharpness)
    return _save(_merge_alpha(rgb, alpha), output, info)


def auto_tone(input, output, cutoff=0.5, per_channel=False):
    """
    Automatische Tonkorrektur (Tonwertspreizung, `cutoff` % Ausreißer je Ende).

    per_channel=False: farbtonerhaltend über die Helligkeit (Standard, sanft)
    per_channel=True:  jeder Kanal einzeln, entfernt auch Farbstiche, kann
                       bei stark farbigen Motiven aber übersteuern
    """
    img, info = _load(input)
    rgb, alpha = _split_alpha(img)
    if per_channel:
        rgb = Image.merge("RGB", [ImageOps.autocontrast(c, cutoff=cutoff) for c in rgb.split()])
    else:
        rgb = ImageOps.autocontrast(rgb, cutoff=cutoff, preserve_tone=True)
    return _save(_merge_alpha(rgb, alpha), output, info)


def white_balance(input, output):
    """Automatischer Weißabgleich nach der Gray-World-Annahme."""
    img, info = _load(input)
    rgb, alpha = _split_alpha(img)
    stat = [sum(i * n for i, n in enumerate(c.histogram())) / max(1, sum(c.histogram()))
            for c in rgb.split()]
    gray = sum(stat) / 3
    channels = [c.point(lambda v, g=gray / max(m, 1): min(255, round(v * g)))
                for c, m in zip(rgb.split(), stat)]
    return _save(_merge_alpha(Image.merge("RGB", channels), alpha), output, info)


def grayscale(input, output):
    """Schwarzweiß (Luminanz), z.B. für Monochrom-Druck mit besserer Kontrolle als der Druckertreiber."""
    img, info = _load(input)
    rgb, alpha = _split_alpha(img)
    gray = ImageOps.grayscale(rgb)
    if alpha is not None:
        gray = gray.convert("LA")
        gray.putalpha(alpha)
    return _save(gray, output, info)


# ---------------------------------------------------------------------------
# Zuschnitt aufs Druckformat
# ---------------------------------------------------------------------------

def fit_paper(input, output, paper="A4", mode="fill", orientation="auto",
              dpi=300, margin_mm=0, background=(255, 255, 255)):
    """
    Bringt das Bild exakt auf das Seitenverhältnis eines Papierformats.

    paper:       Schlüssel aus PAPER_MM (A4, A5, A6, Letter, 10x15, 13x18, ...)
    mode:        "fill" = randlos füllen, überstehende Ränder mittig abschneiden
                 "fit"  = ganzes Bild zeigen, Rest mit `background` auffüllen
    orientation: "auto" (wie das Bild), "portrait" oder "landscape"
    dpi:         Zielauflösung; das Bild wird nie über seine native Auflösung
                 hochskaliert, nur der DPI-Wert wird dann entsprechend gesetzt
    margin_mm:   weißer Rand rundum (nur bei mode="fit" sinnvoll)
    """
    img, info = _load(input)
    w_mm, h_mm = PAPER_MM[paper]
    landscape = img.width > img.height if orientation == "auto" else orientation == "landscape"
    if landscape:
        w_mm, h_mm = h_mm, w_mm

    target_ratio = w_mm / h_mm
    if mode == "fill":
        if img.width / img.height > target_ratio:
            new_w = round(img.height * target_ratio)
            box = ((img.width - new_w) // 2, 0, (img.width - new_w) // 2 + new_w, img.height)
        else:
            new_h = round(img.width / target_ratio)
            box = (0, (img.height - new_h) // 2, img.width, (img.height - new_h) // 2 + new_h)
        out = img.crop(box)
        eff_dpi = out.width / (w_mm / 25.4)
        if eff_dpi > dpi:
            out = out.resize((round(w_mm / 25.4 * dpi), round(h_mm / 25.4 * dpi)), Image.LANCZOS)
            eff_dpi = dpi
    elif mode == "fit":
        inner_w_mm, inner_h_mm = w_mm - 2 * margin_mm, h_mm - 2 * margin_mm
        scale = min(inner_w_mm / img.width, inner_h_mm / img.height)  # mm pro Pixel
        eff_dpi = min(dpi, 25.4 / scale)
        px_per_mm = eff_dpi / 25.4
        canvas_size = (round(w_mm * px_per_mm), round(h_mm * px_per_mm))
        fit_size = (round(inner_w_mm * px_per_mm), round(inner_h_mm * px_per_mm))
        fitted = ImageOps.contain(img.convert("RGBA"), fit_size, Image.LANCZOS)
        out = Image.new("RGB", canvas_size, tuple(background))
        out.paste(fitted, ((canvas_size[0] - fitted.width) // 2, (canvas_size[1] - fitted.height) // 2),
                  mask=fitted.getchannel("A"))
    else:
        raise ValueError(f"mode muss 'fill' oder 'fit' sein, nicht {mode!r}")

    if eff_dpi < 150:
        print(f"Hinweis: nur ~{eff_dpi:.0f} dpi auf {paper}, Druck wird sichtbar unscharf.")
    return _save(out, output, info, dpi=(round(eff_dpi), round(eff_dpi)))


# ---------------------------------------------------------------------------
# Hintergrund entfernen
# ---------------------------------------------------------------------------

def remove_background(input, output, background=None, model="u2net"):
    """
    Entfernt den Hintergrund lokal per rembg.

    background: None = transparent (Ausgabe als PNG), sonst Farbe als RGB-Tupel
                oder Name ("white"), z.B. für den Druck auf weißem Papier.
    model:      rembg-Modell; "u2net" allgemein, "u2net_human_seg" für Personen,
                "isnet-general-use" oft genauer an Kanten.
    """
    try:
        from rembg import new_session, remove
    except ImportError as e:
        raise RuntimeError("rembg fehlt: pip install \"rembg[cpu]\"") from e
    import os
    import onnxruntime
    # Feste Thread-Zahl, sonst scheitert in LXC-Containern die CPU-Affinität (laute Warnungen)
    opts = onnxruntime.SessionOptions()
    opts.intra_op_num_threads = opts.inter_op_num_threads = os.cpu_count() or 1
    img, info = _load(input)
    cut = remove(img.convert("RGB"), session=new_session(model, sess_opts=opts))
    if background is not None:
        cut = _flatten(cut, background if isinstance(background, tuple) else
                       Image.new("RGB", (1, 1), background).getpixel((0, 0)))
    elif Path(output).suffix.lower() in (".jpg", ".jpeg"):
        output = str(Path(output).with_suffix(".png"))
    return _save(cut, output, info)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Fotobearbeitung vor dem Druck")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("adjust")
    for name, default in (("exposure", 0.0), ("brightness", 1.0), ("contrast", 1.0),
                          ("saturation", 1.0), ("temperature", 0.0), ("sharpness", 1.0)):
        a.add_argument(f"--{name}", type=float, default=default)

    t = sub.add_parser("auto-tone")
    t.add_argument("--cutoff", type=float, default=0.5)
    t.add_argument("--per-channel", action="store_true")
    sub.add_parser("white-balance")
    sub.add_parser("grayscale")

    f = sub.add_parser("fit-paper")
    f.add_argument("--paper", default="A4", choices=list(PAPER_MM))
    f.add_argument("--mode", default="fill", choices=["fill", "fit"])
    f.add_argument("--orientation", default="auto", choices=["auto", "portrait", "landscape"])
    f.add_argument("--dpi", type=int, default=300)
    f.add_argument("--margin-mm", type=float, default=0)

    r = sub.add_parser("remove-bg")
    r.add_argument("--background", default=None, help="z.B. white; weglassen = transparent")
    r.add_argument("--model", default="u2net")

    for sp in sub.choices.values():
        sp.add_argument("input")
        sp.add_argument("output")

    args = p.parse_args()
    if args.cmd == "adjust":
        out = adjust(args.input, args.output, args.exposure, args.brightness, args.contrast,
                     args.saturation, args.temperature, args.sharpness)
    elif args.cmd == "auto-tone":
        out = auto_tone(args.input, args.output, args.cutoff, args.per_channel)
    elif args.cmd == "white-balance":
        out = white_balance(args.input, args.output)
    elif args.cmd == "grayscale":
        out = grayscale(args.input, args.output)
    elif args.cmd == "fit-paper":
        out = fit_paper(args.input, args.output, args.paper, args.mode, args.orientation,
                        args.dpi, args.margin_mm)
    else:
        out = remove_background(args.input, args.output, args.background, args.model)
    print(out)


if __name__ == "__main__":
    main()
