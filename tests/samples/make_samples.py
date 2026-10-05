"""Generate synthetic Spanish sample documents (no real data)."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent
FONT = "/System/Library/Fonts/Helvetica.ttc"


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def invoice() -> Image.Image:
    img = Image.new("RGB", (1240, 1600), "white")
    d = ImageDraw.Draw(img)
    d.text((80, 80), "FACTURA DE VENTA N° 0001234", font=font(44), fill="black")
    d.text((80, 160), "Proveedor: Distribuciones Muñoz S.A.S.  NIT 900.123.456-7", font=font(30), fill="black")
    d.text((80, 210), "Cliente: Andrés Peña – Medellín, Antioquia", font=font(30), fill="black")
    d.text((80, 260), "Fecha de emisión: 05/10/2026", font=font(30), fill="black")
    rows = [
        ("Descripción", "Cant.", "Valor unitario", "Total"),
        ("Café molido 500 g", "10", "$12.500,00", "$125.000,00"),
        ("Azúcar 1 kg", "20", "$4.200,00", "$84.000,00"),
        ("Total a pagar", "", "", "$209.000,00"),
    ]
    xs, y = [80, 560, 700, 960], 380
    for r in rows:
        for x, cell in zip(xs, r):
            d.text((x + 10, y + 12), cell, font=font(28), fill="black")
        y += 60
    for i in range(len(rows) + 1):
        d.line((80, 380 + i * 60, 1160, 380 + i * 60), fill="black", width=2)
    for x in xs + [1160]:
        d.line((x, 380, x, 380 + len(rows) * 60), fill="black", width=2)
    return img


def contract() -> Image.Image:
    img = Image.new("RGB", (1240, 1600), "white")
    d = ImageDraw.Draw(img)
    d.text((80, 80), "CONTRATO DE PRESTACIÓN DE SERVICIOS", font=font(40), fill="black")
    lines = [
        "CLÁUSULA PRIMERA. Objeto: el contratista prestará servicios de",
        "consultoría administrativa a favor del contratante.",
        "CLÁUSULA SEGUNDA. Valor: $5.000.000 pagaderos en dos cuotas.",
        "CLÁUSULA TERCERA. Duración: seis (6) meses contados desde la firma.",
    ]
    for i, t in enumerate(lines):
        d.text((80, 200 + i * 60), t, font=font(30), fill="black")
    return img


def report() -> Image.Image:
    """Table-heavy Spanish business report."""
    img = Image.new("RGB", (1240, 1600), "white")
    d = ImageDraw.Draw(img)
    d.text((80, 70), "INFORME TRIMESTRAL DE VENTAS – SEGUNDO TRIMESTRE", font=font(36), fill="black")
    d.text((80, 130), "Región Andina · Cifras en pesos colombianos (COP)", font=font(28), fill="black")
    rows = [
        ("Ciudad", "Abril", "Mayo", "Junio", "Total"),
        ("Bogotá", "$1.200.000", "$1.350.000", "$1.500.000", "$4.050.000"),
        ("Medellín", "$980.000", "$1.020.000", "$1.100.000", "$3.100.000"),
        ("Cali", "$750.000", "$800.000", "$870.000", "$2.420.000"),
        ("Bucaramanga", "$420.000", "$450.000", "$510.000", "$1.380.000"),
        ("Total", "$3.350.000", "$3.620.000", "$3.980.000", "$10.950.000"),
    ]
    xs, top, h = [80, 380, 600, 820, 1040], 220, 70
    for i, r in enumerate(rows):
        for x, cell in zip(xs, r):
            d.text((x + 12, top + i * h + 18), cell, font=font(28), fill="black")
    for i in range(len(rows) + 1):
        d.line((80, top + i * h, 1200, top + i * h), fill="black", width=2)
    for x in xs + [1200]:
        d.line((x, top, x, top + len(rows) * h), fill="black", width=2)
    d.text((80, top + len(rows) * h + 50), "Nota: los totales incluyen ventas en línea.", font=font(28), fill="black")
    return img


def scanned() -> Image.Image:
    """Image-only page: slightly rotated, with sensor noise, like a phone scan."""
    import random

    random.seed(7)
    img = contract().rotate(1.5, expand=False, fillcolor="white")
    px = img.load()
    for _ in range(40000):
        x, y = random.randrange(img.width), random.randrange(img.height)
        v = random.randint(150, 255)
        px[x, y] = (v, v, v)
    return img


def rich() -> Image.Image:
    """Formula, bar chart and a table with merged cells."""
    img = Image.new("RGB", (1240, 1600), "white")
    d = ImageDraw.Draw(img)
    d.text((80, 70), "ANÁLISIS FINANCIERO – RENTABILIDAD", font=font(38), fill="black")
    d.text((80, 150), "La rentabilidad se calcula con la siguiente fórmula:", font=font(30), fill="black")
    d.text((300, 230), "ROI = (Ganancia - Inversión) / Inversión × 100", font=font(36), fill="black")
    d.text((80, 340), "Figura 1. Ventas por trimestre (millones de pesos)", font=font(28), fill="black")
    base, left = 800, 160
    d.line((left, 400, left, base), fill="black", width=3)
    d.line((left, base, 1100, base), fill="black", width=3)
    for i, (label, val) in enumerate([("T1", 120), ("T2", 200), ("T3", 280), ("T4", 340)]):
        x = left + 80 + i * 220
        d.rectangle((x, base - val, x + 120, base), fill=(60, 90, 160))
        d.text((x + 35, base + 10), label, font=font(28), fill="black")
        d.text((x + 25, base - val - 40), str(val), font=font(26), fill="black")
    top, h = 940, 70
    cells = [
        (80, top, 1160, top + h, "Resumen anual de gastos"),
        (80, top + h, 620, top + 2 * h, "Operativos"),
        (620, top + h, 1160, top + 2 * h, "Administrativos"),
        (80, top + 2 * h, 350, top + 3 * h, "Enero"),
        (350, top + 2 * h, 620, top + 3 * h, "$500.000"),
        (620, top + 2 * h, 890, top + 3 * h, "Enero"),
        (890, top + 2 * h, 1160, top + 3 * h, "$300.000"),
    ]
    for x0, y0, x1, y1, text in cells:
        d.rectangle((x0, y0, x1, y1), outline="black", width=2)
        d.text((x0 + 14, y0 + 18), text, font=font(28), fill="black")
    return img


if __name__ == "__main__":
    invoice().save(OUT / "factura.png")
    contract().save(OUT / "contrato.png")
    contract().save(OUT / "contrato.pdf")
    Image.new("RGB", (800, 600), "white").save(OUT / "en_blanco.png")
    report().save(OUT / "informe.pdf")
    scanned().save(OUT / "escaneado.pdf")
    rich().save(OUT / "formulas_graficos.png")
    print("ok")
