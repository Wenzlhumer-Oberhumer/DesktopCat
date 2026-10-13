"""Hilfsskript zur Erzeugung von assets/mochi.ico in mehreren Aufloesungen."""
import io
import sys
from pathlib import Path

# Projektwurzel zu sys.path hinzufuegen
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PIL import Image
from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtWidgets import QApplication

from paths import APP_DIR
from pet_sprites import render_icon


def generate_icon(out_path: Path | None = None) -> Path:
    if out_path is None:
        out_path = APP_DIR / "assets" / "mochi.ico"

    app = QApplication.instance() or QApplication(sys.argv)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images_by_size = {}

    for s in sizes:
        pix = render_icon(s)
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.ReadWrite)
        pix.save(buf, "PNG")
        raw = bytes(buf.data())
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        images_by_size[s] = im

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base_img = images_by_size[256]
    other_imgs = [images_by_size[s] for s in sizes if s != 256]

    base_img.save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=other_imgs,
    )
    return out_path


def main():
    dest = generate_icon()
    print(f"Icon erfolgreich erstellt: {dest}")


if __name__ == "__main__":
    main()
