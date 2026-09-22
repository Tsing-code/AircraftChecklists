"""One-off script to (re)generate the PWA app icons in docs/icons/.
Run from anywhere: python gen_icons.py"""
import os

from PIL import Image, ImageDraw

BG = (10, 10, 10, 255)
GREEN = (57, 255, 106, 255)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "icons")


def draw_checkmark(size, margin_frac):
    """A rounded-square icon: dark background, a green checkmark inset by
    margin_frac of the canvas on each side (so maskable crops stay safe)."""
    img = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)

    margin = int(size * margin_frac)
    # checkmark stroke, drawn as a thick polyline
    stroke = max(2, int(size * 0.09))
    p1 = (margin, size * 0.55)
    p2 = (size * 0.42, size - margin)
    p3 = (size - margin, margin)
    draw.line([p1, p2], fill=GREEN, width=stroke, joint="curve")
    draw.line([p2, p3], fill=GREEN, width=stroke, joint="curve")
    r = stroke // 2
    for pt in (p1, p2, p3):
        draw.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=GREEN)
    return img


os.makedirs(OUT_DIR, exist_ok=True)

# "any" purpose icons: content can extend closer to the edge
draw_checkmark(192, 0.18).save(f"{OUT_DIR}/icon-192.png")
draw_checkmark(512, 0.18).save(f"{OUT_DIR}/icon-512.png")

# "maskable" icons: OS crops to various shapes, so keep content within the
# safe zone (roughly the inner 80% / a centered circle) - use a bigger margin
draw_checkmark(192, 0.28).save(f"{OUT_DIR}/icon-192-maskable.png")
draw_checkmark(512, 0.28).save(f"{OUT_DIR}/icon-512-maskable.png")

print("icons written to", OUT_DIR)
