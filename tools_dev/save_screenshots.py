"""Erzeugt Screenshots der Katzen-Zustaende fuer Phase 3."""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Use default QPA (windows) if available, so Windows fonts render properly
if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
)
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
    save_ui_screenshots(out_dir)


def save_ui_screenshots(out_dir: Path):
    """Rendert die 6 neuen UI-Fenster mit Beispieldaten in einer temporaeren DB."""
    import tempfile
    from chat_history import ChatHistoryDialog
    from config import Config
    from fun_dialogs import FlashcardsDialog, FocusStatsDialog, FriendshipDialog
    from memory_store import MemoryStore
    from my_data_dialog import MyDataDialog
    from pet_sprites import get_character_info
    from sticky_notes import StickyNoteWindow

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        store = MemoryStore(db_path)
        store.add_message("user", "Hallo Kylie, wie läuft das Projekt?")
        store.add_message("assistant", "Super! Wir sind in Phase 8 der Entwicklung. 🐾✨")
        store.add_fact("Mag Katzen und Python")
        store.add_fact("Geburtstag am 14. März", due_date="03-14", kind="birthday")
        store.set_friendship_points(160)
        store.record_focus("2026-10-13", 50)
        store.record_focus("2026-10-12", 25)
        store.add_card("Allgemein", "Katze", "Cat")
        store.add_card("Allgemein", "Hund", "Dog")

        cfg = Config()
        char_info = get_character_info("cat_mochi")

        # 1. Chats
        dlg_chats = ChatHistoryDialog(cfg, store=store)
        dlg_chats.show()
        pix = dlg_chats.grab()
        pix.save(str(out_dir / "ui_chats.png"))
        dlg_chats.close()
        print(f"UI-Screenshot gespeichert: {out_dir / 'ui_chats.png'}")

        # 2. Daten
        dlg_data = MyDataDialog(cfg, store=store)
        dlg_data.show()
        pix = dlg_data.grab()
        pix.save(str(out_dir / "ui_data.png"))
        dlg_data.close()
        print(f"UI-Screenshot gespeichert: {out_dir / 'ui_data.png'}")

        # 3. Freundschaft
        dlg_friend = FriendshipDialog(store, cfg, char_info)
        dlg_friend.show()
        pix = dlg_friend.grab()
        pix.save(str(out_dir / "ui_friendship.png"))
        dlg_friend.close()
        print(f"UI-Screenshot gespeichert: {out_dir / 'ui_friendship.png'}")

        # 4. Fokus
        dlg_focus = FocusStatsDialog(store, char_info)
        dlg_focus.show()
        pix = dlg_focus.grab()
        pix.save(str(out_dir / "ui_focus.png"))
        dlg_focus.close()
        print(f"UI-Screenshot gespeichert: {out_dir / 'ui_focus.png'}")

        # 5. Lernkarten
        dlg_cards = FlashcardsDialog(store)
        dlg_cards.show()
        pix = dlg_cards.grab()
        pix.save(str(out_dir / "ui_flashcards.png"))
        dlg_cards.close()
        print(f"UI-Screenshot gespeichert: {out_dir / 'ui_flashcards.png'}")

        # 6. Haftnotiz
        note_win = StickyNoteWindow(1, "Meeting um 14 Uhr vorbereiten! 📌\nDesktop Cat v2.2.0 testen.", "yellow", 100, 100, store)
        note_win.show()
        pix = note_win.grab()
        pix.save(str(out_dir / "ui_note.png"))
        note_win.close()
        print(f"UI-Screenshot gespeichert: {out_dir / 'ui_note.png'}")

        # 7. IT-Guide (Overlay, Kylie mit Hackerbrille auf Wolke, Sprechblase)
        save_ui_guide_screenshot(out_dir)

        # 8. Onboarding (4 Phasen: Begrüßung, Spitzname, Galerie, Fertig)
        save_onboarding_screenshots(out_dir)
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


def save_ui_guide_screenshot(out_dir: Path):
    """Rendert den IT-Guide mit Fake-Desktop, Overlay-Ring, Kylie auf Wolke und Sprechblase."""
    from guide_overlay import GuideOverlay
    from pet_sprites import Pose, draw_character

    w, h = 840, 520
    canvas = QPixmap(w, h)
    canvas.fill(QColor("#1A1B1E"))

    p = QPainter(canvas)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing | QPainter.RenderHint.SmoothPixmapTransform)

    # 1. Fake Desktop / Hintergrund-App-Fenster
    win_rect = QRectF(40, 40, 420, 420)
    # Fenster-Schatten
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 90))
    p.drawRoundedRect(win_rect.adjusted(-2, 2, 8, 12), 12, 12)
    # Fenster-Körper
    p.setBrush(QColor("#26282C"))
    p.setPen(QPen(QColor("#3E4148"), 1.2))
    p.drawRoundedRect(win_rect, 10, 10)

    # Titelleiste
    p.setBrush(QColor("#33353B"))
    title_path = QPainterPath()
    title_path.addRoundedRect(QRectF(40, 40, 420, 36), 10, 10)
    p.drawPath(title_path)
    p.fillRect(QRectF(40, 66, 420, 10), QColor("#33353B"))
    p.setPen(QPen(QColor("#3E4148"), 1.0))
    p.drawLine(40, 76, 460, 76)

    # Fenstertitel
    p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    p.setPen(QColor("#F2F3F5"))
    p.drawText(QRectF(54, 40, 300, 36), Qt.AlignmentFlag.AlignVCenter, "⚙️ Windows-Einstellungen")

    # Scheinbare Menüpunkte
    items = [
        ("🔔", "Benachrichtigungen & Aktionen"),
        ("🌐", "Netzwerk & Internet"),
        ("⚙️", "Einstellungen"),
        ("🎨", "Personalisierung & Farben"),
        ("🔒", "Datenschutz & Sicherheit"),
    ]

    for idx, (icon, text) in enumerate(items):
        item_y = 100 + idx * 56
        item_r = QRectF(70, item_y, 360, 44)

        if idx == 2:  # Das Ziel
            p.setBrush(QColor("#36383E"))
            p.setPen(QPen(QColor("#55575F"), 1.2))
            p.drawRoundedRect(item_r, 8, 8)
            p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            p.setPen(QColor("#FFFFFF"))
            p.drawText(QRectF(item_r).adjusted(16, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, f"{icon}  {text}")
        else:
            p.setBrush(QColor("#2D2F35"))
            p.setPen(QPen(QColor("#383A42"), 1.0))
            p.drawRoundedRect(item_r, 8, 8)
            p.setFont(QFont("Segoe UI", 10))
            p.setPen(QColor("#8D919B"))
            p.drawText(QRectF(item_r).adjusted(16, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, f"{icon}  {text}")

    p.end()

    # 2. Guide-Overlay zeichnen
    overlay = GuideOverlay()
    overlay.set_screen_geometry(QRect(0, 0, w, h))
    pet_pos = QPoint(530, 240)
    overlay.set_target(QRect(70, 212, 360, 44), pet_pos=pet_pos, action="left", target_name="Einstellungen")
    p_overlay = QPainter(canvas)
    p_overlay.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    overlay.render(p_overlay)

    # 3. Kylie auf Wolke mit Hackerbrille zeichnen
    p_overlay.save()
    p_overlay.translate(pet_pos.x() - 10, pet_pos.y() - 10)
    p_overlay.scale(1.2, 1.2)
    pose = Pose(accessories=("cloud", "hacker_glasses"), t=0.5)
    draw_character(p_overlay, pose, "cat_mochi")
    p_overlay.restore()

    # 4. Sprechblase über Kylie mit [Weiter ▶] [Nochmal 🔁] [Fertig ✖]
    bubble_w, bubble_h = 345, 110
    bx, by = 460, 60
    bubble_rect = QRectF(bx, by, bubble_w, bubble_h)

    # Schatten
    p_overlay.setPen(Qt.PenStyle.NoPen)
    p_overlay.setBrush(QColor(0, 0, 0, 110))
    p_overlay.drawRoundedRect(bubble_rect.adjusted(-2, 3, 4, 8), 16, 16)

    # Blase Körper
    bubble_grad = QLinearGradient(bx, by, bx, by + bubble_h)
    bubble_grad.setColorAt(0.0, QColor("#35373D"))
    bubble_grad.setColorAt(1.0, QColor("#26282C"))
    p_overlay.setBrush(QBrush(bubble_grad))
    p_overlay.setPen(QPen(QColor("#45474F"), 1.2))
    p_overlay.drawRoundedRect(bubble_rect, 14, 14)

    # Pfeil nach unten Richtung Kopf
    pfeil_path = QPainterPath()
    pfeil_path.moveTo(bx + 130, by + bubble_h)
    pfeil_path.lineTo(bx + 145, by + bubble_h + 14)
    pfeil_path.lineTo(bx + 160, by + bubble_h)
    pfeil_path.closeSubpath()
    p_overlay.fillPath(pfeil_path, QBrush(QColor("#26282C")))
    p_overlay.setPen(QPen(QColor("#45474F"), 1.2))
    p_overlay.drawPolyline([QPointF(bx + 130, by + bubble_h), QPointF(bx + 145, by + bubble_h + 14), QPointF(bx + 160, by + bubble_h)])

    # Sprechblasen-Inhalt
    p_overlay.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    p_overlay.setPen(QColor("#FF8FB1"))
    p_overlay.drawText(QRectF(bx + 16, by + 12, bubble_w - 32, 20), Qt.AlignmentFlag.AlignLeft, "💡 Schritt 1/3: Klicke auf „Einstellungen“")

    p_overlay.setFont(QFont("Segoe UI", 9))
    p_overlay.setPen(QColor("#F2F3F5"))
    p_overlay.drawText(QRectF(bx + 16, by + 34, bubble_w - 32, 20), Qt.AlignmentFlag.AlignLeft, "Ich zeige dir, wo du die Option findest! 🐾")

    # 3 Aktionsbuttons
    # 1. Weiter ▶
    p_overlay.setPen(Qt.PenStyle.NoPen)
    p_overlay.setBrush(QColor("#FF8FB1"))
    p_overlay.drawRoundedRect(QRectF(bx + 16, by + 66, 96, 28), 6, 6)
    p_overlay.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    p_overlay.setPen(QColor("#26282C"))
    p_overlay.drawText(QRectF(bx + 16, by + 66, 96, 28), Qt.AlignmentFlag.AlignCenter, "Weiter ▶")

    # 2. Nochmal 🔁
    p_overlay.setBrush(QColor("#3A3C43"))
    p_overlay.drawRoundedRect(QRectF(bx + 120, by + 66, 104, 28), 6, 6)
    p_overlay.setFont(QFont("Segoe UI", 9))
    p_overlay.setPen(QColor("#F2F3F5"))
    p_overlay.drawText(QRectF(bx + 120, by + 66, 104, 28), Qt.AlignmentFlag.AlignCenter, "Nochmal 🔁")

    # 3. Fertig ✖
    p_overlay.setBrush(QColor("#4A3338"))
    p_overlay.drawRoundedRect(QRectF(bx + 232, by + 66, 96, 28), 6, 6)
    p_overlay.setFont(QFont("Segoe UI", 9))
    p_overlay.setPen(QColor("#FF8FB1"))
    p_overlay.drawText(QRectF(bx + 232, by + 66, 96, 28), Qt.AlignmentFlag.AlignCenter, "Fertig ✖")

    p_overlay.end()

    canvas.save(str(out_dir / "ui_guide.png"))
    print(f"UI-Screenshot gespeichert: {out_dir / 'ui_guide.png'}")


def save_onboarding_screenshots(out_dir: Path) -> None:
    """Erzeugt die vier Onboarding-Screenshots (Begrueßung, Spitzname, Galerie, Fertig)."""
    from onboarding import OnboardingDialog
    from config import Config

    cfg = Config()

    def _show_and_grab(dlg):
        if hasattr(dlg, "_anim"):
            dlg._anim.stop()
        if hasattr(dlg, "_opacity_effect"):
            dlg._opacity_effect.setOpacity(1.0)
        dlg.show()
        for _ in range(10):
            dlg.avatar._tick()
        QApplication.processEvents()
        dlg._scroll_to_bottom()
        sb = dlg.chat_scroll.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
        QApplication.processEvents()
        return dlg.card.grab()

    # 1. Begrüßung (ui_onboarding_1.png)
    dlg1 = OnboardingDialog(cfg)
    pix1 = _show_and_grab(dlg1)
    pix1.save(str(out_dir / "ui_onboarding_1.png"))
    dlg1.close()
    print(f"UI-Screenshot gespeichert: {out_dir / 'ui_onboarding_1.png'}")

    # 2. Spitzname mit Chips (ui_onboarding_2.png)
    dlg2 = OnboardingDialog(cfg)
    dlg2._clear_chat()
    dlg2.flow.step = 4
    dlg2.flow.answers["language"] = "de"
    dlg2.flow.answers["name"] = "Florian"
    dlg2._add_pet_bubble("Hiii! 👋 Ich bin Kylie, deine neue Desktop-Katze. Ich würde dich gern kennenlernen – ist das okay?")
    dlg2._add_user_bubble("Klar! 😺")
    dlg2._add_pet_bubble("Welche Sprache magst du?")
    dlg2._add_user_bubble("Deutsch 🇩🇪")
    dlg2._add_pet_bubble("Wie heißt du?")
    dlg2._add_user_bubble("Florian")
    dlg2._render_current_step()
    pix2 = _show_and_grab(dlg2)
    pix2.save(str(out_dir / "ui_onboarding_2.png"))
    dlg2.close()
    print(f"UI-Screenshot gespeichert: {out_dir / 'ui_onboarding_2.png'}")

    # Chips mit langen Texten (Tonfall, PC-Nutzung) - hier waren Texte abgeschnitten
    for step, fname in ((8, "ui_onboarding_tone.png"), (6, "ui_onboarding_uses.png")):
        dlg = OnboardingDialog(cfg)
        dlg._clear_chat()
        dlg.flow.step = step
        dlg.flow.answers.update({"language": "de", "name": "Florian", "user_name": "Florian"})
        dlg._add_user_bubble("coden; gaming; gym")
        dlg._render_current_step()
        _show_and_grab(dlg).save(str(out_dir / fname))
        dlg.close()
        print(f"UI-Screenshot gespeichert: {out_dir / fname}")

    # 3. Figur-Galerie (ui_onboarding_3.png)
    dlg3 = OnboardingDialog(cfg)
    dlg3._clear_chat()
    dlg3.flow.step = 12
    dlg3.flow.answers["name"] = "Florian"
    dlg3.flow.answers["user_name"] = "Flo"
    dlg3._add_pet_bubble("Und wie soll ich dich nennen?")
    dlg3._add_user_bubble("Flo")
    dlg3._add_pet_bubble("In welcher Stadt bist du ungefähr? ☀️")
    dlg3._add_user_bubble("Berlin")
    dlg3._render_current_step()
    pix3 = _show_and_grab(dlg3)
    pix3.save(str(out_dir / "ui_onboarding_3.png"))
    dlg3.close()
    print(f"UI-Screenshot gespeichert: {out_dir / 'ui_onboarding_3.png'}")

    # 4. Fertig mit Konfetti (ui_onboarding_4.png)
    dlg4 = OnboardingDialog(cfg)
    dlg4._clear_chat()
    dlg4.flow.step = 15
    dlg4.flow.answers["name"] = "Florian"
    dlg4.flow.answers["user_name"] = "Flo"
    dlg4._add_pet_bubble("Soll ich mit Windows starten?")
    dlg4._add_user_bubble("Ja, immer dabei! 🚀")
    dlg4._render_current_step()
    dlg4.avatar.pop_confetti()
    for _ in range(15):
        dlg4.avatar._tick()
    pix4 = _show_and_grab(dlg4)
    pix4.save(str(out_dir / "ui_onboarding_4.png"))
    dlg4.close()
    print(f"UI-Screenshot gespeichert: {out_dir / 'ui_onboarding_4.png'}")


if __name__ == "__main__":
    main()
