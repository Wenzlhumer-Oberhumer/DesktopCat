"""Erzeugt Screenshots der Katzen-Zustaende fuer Phase 3."""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
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


def save_anchors_sheet(out_dir: Path):
    """Zeichnet alle 9 Figuren mit ihren Ankerpunkten als kleine bunte Punkte."""
    from pet_sprites import DEFAULT_ANCHORS
    n = len(CHARACTERS)
    sheet = QPixmap(160 * n, 200)
    sheet.fill(QColor("#1E1F24"))
    p = QPainter(sheet)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.TextAntialiasing)
    p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

    for i, (cid, cdata) in enumerate(CHARACTERS.items()):
        p.save()
        p.translate(i * 160, 20)
        pose = compute_pose(PoseContext(key="idle", t=0.0, age=0.0))
        draw_character(p, pose, cid)

        # Anker zeichnen
        anchors = cdata.get("anchors", DEFAULT_ANCHORS)
        hx, hy = anchors.get("head_top", (80.0, 48.0))
        ex, ey = anchors.get("eyes", (80.0, 80.0))
        edx = anchors.get("eye_dx", 19.0)
        nx, ny = anchors.get("neck", (80.0, 114.0))
        px, py = anchors.get("paw_r", (98.0, 140.0))

        # Kopf-Top (Rot)
        p.setPen(QColor("#FFFFFF"))
        p.setBrush(QColor("#FF4757"))
        p.drawEllipse(QPointF(hx, hy), 3.5, 3.5)

        # Augen (Gruen)
        p.setBrush(QColor("#2ED573"))
        p.drawEllipse(QPointF(ex - edx, ey), 3.0, 3.0)
        p.drawEllipse(QPointF(ex + edx, ey), 3.0, 3.0)

        # Hals (Blau)
        p.setBrush(QColor("#1E90FF"))
        p.drawEllipse(QPointF(nx, ny), 3.5, 3.5)

        # Pfote (Gelb/Orange)
        p.setBrush(QColor("#FFA502"))
        p.drawEllipse(QPointF(px, py), 3.5, 3.5)

        # Beschriftung
        p.setPen(QColor("#E4E7EB"))
        p.drawText(QRectF(0, -16, 160, 16), Qt.AlignmentFlag.AlignCenter, cdata.get("name", cid))
        p.restore()

    p.end()
    out_file = out_dir / "anchors.png"
    sheet.save(str(out_file))
    print(f"Anker-Sheet gespeichert: {out_file}")


def save_accessories_sheet(out_dir: Path):
    """Zeichnet alle 9 Figuren mit verschiedenen Accessoire-Sets zur visuellen Pruefung."""
    n = len(CHARACTERS)
    rows = [
        ("Hacker + Wolke", ("hacker_glasses", "cloud")),
        ("Party + Schal", ("party_hat", "scarf")),
        ("Regenschirm + Sonne", ("umbrella", "sunglasses")),
        ("Halloween + Bandana", ("pumpkin_hat", "bandana")),
        ("Weihnachten", ("santa_hat", "scarf")),
        ("Schlafmütze", ("nightcap",)),
    ]
    sheet = QPixmap(160 * n, 190 * len(rows))
    sheet.fill(QColor("#1A1B20"))
    p = QPainter(sheet)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.TextAntialiasing)
    p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

    for r_idx, (label, accs) in enumerate(rows):
        base_y = r_idx * 190
        # Zeilen-Titel
        p.setPen(QColor("#A0AEC0"))
        p.drawText(QRectF(10, base_y + 6, 200, 20), Qt.AlignmentFlag.AlignLeft, label)

        for c_idx, (cid, cdata) in enumerate(CHARACTERS.items()):
            p.save()
            p.translate(c_idx * 160, base_y + 20)
            pose = compute_pose(PoseContext(key="idle", t=0.5, age=0.5))
            pose.accessories = accs
            draw_character(p, pose, cid)
            p.restore()

    p.end()
    out_file = out_dir / "accessories.png"
    sheet.save(str(out_file))
    print(f"Accessoire-Sheet gespeichert: {out_file}")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    assert app is not None
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
    save_anchors_sheet(out_dir)
    save_accessories_sheet(out_dir)

if __name__ == "__main__":
    main()
