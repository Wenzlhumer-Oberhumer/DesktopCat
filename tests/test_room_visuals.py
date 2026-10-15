"""Behavioral checks for the offline wallpaper's small JavaScript clock."""
import pathlib
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is required for wallpaper script checks")
class RoomVisualTests(unittest.TestCase):
    def test_local_time_phases_and_visibility_timer(self):
        script = pathlib.Path(__file__).resolve().parents[1] / "assets/lively_room/script.js"
        checks = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {roomPhase} = require(process.argv[1]);
for (const [hour, expected] of [[0,'night'],[5,'night'],[6,'dawn'],[7,'day'],[16,'day'],[17,'dusk'],[20,'dusk'],[21,'night'],[23,'night']]) {
  assert.equal(roomPhase(hour), expected);
}
const handlers = {};
const clock = {};
const timers = new Map();
let nextTimer = 0;
const fakeDocument = {
  hidden: false,
  body: {dataset: {}},
  getElementById() { return clock; },
  addEventListener(name, fn) { handlers[name] = fn; }
};
const context = {
  document: fakeDocument,
  Date: class extends Date { constructor() { super(2026, 9, 15, 18, 7); } },
  setInterval(fn, delay) { assert.equal(delay, 60000); timers.set(++nextTimer, fn); return nextTimer; },
  clearInterval(id) { timers.delete(id); }
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
handlers.DOMContentLoaded();
assert.equal(fakeDocument.body.dataset.phase, 'dusk');
assert.equal(clock.textContent, '18:07');
assert.equal(clock.dateTime, '18:07');
assert.equal(timers.size, 1);
fakeDocument.hidden = true;
handlers.visibilitychange();
assert.equal(timers.size, 0);
fakeDocument.hidden = false;
handlers.visibilitychange();
handlers.visibilitychange();
assert.equal(timers.size, 1, 'resuming must never duplicate the clock timer');
"""
        result = subprocess.run([shutil.which("node"), "-e", checks, str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

