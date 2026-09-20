"""Generate a few fictional business card images for quick testing.

    python scripts/make_sample_cards.py      ->  writes samples/card_1.png ... card_5.png
All people and companies below are made up.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent.parent / "samples"
SIZE = (1050, 600)

CARDS = [
    ("Aarav Mehta", "Senior Sales Manager", "BrightPath Technologies Pvt. Ltd.",
     "Bengaluru, Karnataka, India", "+91 98765 43210", "aarav.mehta@brightpath.example.com", "#1F4E78"),
    ("Priya Nair", "Head of Marketing", "GreenLeaf Foods",
     "Kochi, Kerala, India", "+91 91234 56789", "priya.nair@greenleaf.example.com", "#2E7D32"),
    ("Daniel Carter", "Chief Technology Officer", "NorthWind Analytics",
     "Austin, Texas, USA", "+1 (512) 555-0147", "daniel.carter@northwind.example.com", "#6A1B9A"),
    ("Sofia Rossi", "Product Designer", "Studio Lumen",
     "Milan, Italy", "+39 02 5550 1234", "sofia.rossi@studiolumen.example.com", "#C62828"),
    ("Rohan Verma", "Founder & CEO", "Verma & Sons Logistics",
     "New Delhi, India", "+91 99887 76655", "rohan@vermalogistics.example.com", "#EF6C00"),
]

FONT_CANDIDATES = [
    "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "arial.ttf", "Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
]


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = ["DejaVuSans-Bold.ttf", "arialbd.ttf"] if bold else []
    for name in names + FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def draw_card(name, title, company, location, phone, email, color) -> Image.Image:
    img = Image.new("RGB", SIZE, "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 40, SIZE[1]], fill=color)
    d.text((90, 60), company, font=load_font(38, bold=True), fill=color)
    d.text((90, 190), name, font=load_font(56, bold=True), fill="#111111")
    d.text((90, 265), title, font=load_font(34), fill="#444444")
    d.line([90, 340, SIZE[0] - 60, 340], fill="#BBBBBB", width=2)
    d.text((90, 375), phone, font=load_font(32), fill="#222222")
    d.text((90, 430), email, font=load_font(32), fill="#222222")
    d.text((90, 485), location, font=load_font(32), fill="#222222")
    return img


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for i, card in enumerate(CARDS, start=1):
        path = OUT_DIR / f"card_{i}.png"
        draw_card(*card).save(path)
        print("wrote", path)


if __name__ == "__main__":
    main()
