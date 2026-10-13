"""Erzeugt Screenshots der Katzen-Zustaende fuer Phase 3."""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPixmap, QColor
from PyQt6.QtWidgets import QApplication

from pet_sprites import CHARACTERS, PoseContext, compute_pose, draw_cat, draw_character

def render_state(state: str, t: float = 1.0) -> QPixmap:
    pix = QPixmap(160, 160)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    ctx = PoseContext(key=state, t=t, age=t)
    pose = compute_pose(ctx)
    draw_cat(p, pose)
    p.end()
    return pix

def save_character_sheet(out_dir: Path):
    """Alle Figuren (IDLE) nebeneinander auf dunklem Grund."""
    n = len(CHARACTERS)
    sheet = QPixmap(160 * n, 180)
    sheet.fill(QColor("#202025"))
    p = QPainter(sheet)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    for i, cid in enumerate(CHARACTERS):
        p.save()
        p.translate(i * 160, 10)
        draw_character(p, compute_pose(PoseContext(key="idle", t=0.5, age=0.5)), cid)
        p.restore()
    p.end()
    sheet.save(str(out_dir / "characters.png"))
    print(f"Figuren-Sheet gespeichert: {out_dir / 'characters.png'}")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    out_dir = _ROOT / "ref" / "plan" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    states = {
        "idle": 0.5,
        "walk": ("walk_right", 0.3),
        "sleep": 2.0,
        "dance": 0.4,
        "dragged": 0.2,
    }

    pixmaps = {}
    for name, spec in states.items():
        if isinstance(spec, tuple):
            k, t = spec
        else:
            k, t = name, spec
        pix = render_state(k, t)
        pix.save(str(out_dir / f"{name}.png"))
        pixmaps[name] = pix
        print(f"Gespeichert: {out_dir / f'{name}.png'}")

    # Übersicht nebeneinander (160 * 5 = 800 x 180)
    total_w = 160 * len(states)
    overview = QPixmap(total_w, 180)
    overview.fill(QColor("#202025")) # dezenter dunkler Hintergrund zur Kontrastpruefung
    p = QPainter(overview)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    for i, (name, pix) in enumerate(pixmaps.items()):
        p.drawPixmap(i * 160, 10, pix)
    p.end()
    overview.save(str(out_dir / "overview.png"))
    print(f"Uebersicht gespeichert: {out_dir / 'overview.png'}")
    save_character_sheet(out_dir)

if __name__ == "__main__":
    main()
