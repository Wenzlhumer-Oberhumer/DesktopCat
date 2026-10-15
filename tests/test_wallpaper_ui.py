"""Wallpaper UI delegates once; background operations report real outcomes."""
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout
from character_tree_dialog import CharacterTreeDialog


class WallpaperUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_dialog(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda key, default=None: default
        with patch.object(CharacterTreeDialog, '_setup_ui'), patch.object(CharacterTreeDialog, 'refresh_all'):
            dialog = CharacterTreeDialog(cfg)
        self.addCleanup(dialog.close)
        return dialog

    def test_activate_only_emits_once(self):
        dialog = self.make_dialog()
        requests = []
        dialog.wallpaper_requested.connect(lambda: requests.append(True))
        with patch('lively_wallpaper.apply_lively_wallpaper') as apply:
            dialog._on_activate_lively()
        self.assertEqual(requests, [True])
        apply.assert_not_called()

    def test_preview_and_restore_buttons(self):
        dialog = self.make_dialog()
        dialog.games_layout = QVBoxLayout(dialog)
        dialog._build_games()
        buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
        preview = buttons['Zimmer ansehen']
        restore = buttons['Vorherigen Hintergrund wiederherstellen']
        restored = []
        dialog.wallpaper_restore_requested.connect(lambda: restored.append(True))
        with patch('character_tree_dialog.QDesktopServices.openUrl', return_value=True) as open_url:
            preview.click()
        path = Path(open_url.call_args.args[0].toLocalFile())
        self.assertEqual(path.name, 'index.html')
        self.assertTrue(path.is_file())
        restore.click()
        self.assertEqual(restored, [True])
        self.assertTrue(all(button.minimumHeight() >= 40 for button in buttons.values()))

    def test_busy_state_disables_changes_and_preserves_result_on_rebuild(self):
        dialog = self.make_dialog()
        dialog.games_layout = QVBoxLayout(dialog)
        dialog._build_games()
        dialog.set_wallpaper_busy(True, 'Hintergrund wird geprüft …')
        for button in (dialog.btn_home_mode, dialog.btn_act_lively, dialog.btn_restore_wallpaper):
            self.assertFalse(button.isEnabled())
        self.assertTrue(dialog.btn_preview_room.isEnabled())
        self.assertEqual(dialog.lbl_wallpaper_status.text(), 'Hintergrund wird geprüft …')
        self.assertTrue(dialog.lbl_wallpaper_status.wordWrap())
        dialog.set_wallpaper_busy(False, 'Lively wurde nicht gefunden.')
        dialog._build_games()
        for button in (dialog.btn_home_mode, dialog.btn_act_lively, dialog.btn_restore_wallpaper):
            self.assertTrue(button.isEnabled())
        self.assertEqual(dialog.lbl_wallpaper_status.text(), 'Lively wurde nicht gefunden.')

    def test_worker_activation_results_and_exception(self):
        from wallpaper_worker import WallpaperWorker
        cfg, store = object(), object()
        for result in [(True, 'Ready'), (False, 'Lively unavailable')]:
            worker = WallpaperWorker(cfg, activate=True, store=store)
            results = []
            worker.completed.connect(lambda ok, message: results.append((ok, message)))
            with patch('wallpaper_worker.lively_wallpaper.apply_lively_wallpaper', return_value=result) as apply:
                worker.run()
            apply.assert_called_once_with(cfg, store)
            self.assertEqual(results, [result])
        worker = WallpaperWorker(cfg, activate=True)
        failures = []
        worker.completed.connect(lambda ok, message: failures.append((ok, message)))
        with patch('wallpaper_worker.lively_wallpaper.apply_lively_wallpaper', side_effect=OSError('test failure')):
            worker.run()
        self.assertFalse(failures[0][0])
        self.assertIn('test failure', failures[0][1])

    def test_worker_restore_results(self):
        from wallpaper_worker import WallpaperWorker
        cfg = object()
        for success in (True, False):
            worker = WallpaperWorker(cfg, activate=False)
            results = []
            worker.completed.connect(lambda ok, message: results.append((ok, message)))
            with patch('wallpaper_worker.lively_wallpaper.restore_original_wallpaper', return_value=success) as restore:
                worker.run()
            restore.assert_called_once_with(cfg, force=True)
            self.assertEqual(results[0][0], success)
            self.assertTrue(results[0][1])


if __name__ == '__main__':
    unittest.main()
