"""Offline story paths and validation, without UI or third-party test dependencies."""
from itertools import product
import unittest

from play_stories import StorySession, story_titles


class StorySessionTests(unittest.TestCase):
    def test_all_paths_have_three_decisions_and_two_endings(self):
        for lang, story_id in product(("de", "en"), ("picnic", "sock", "stars")):
            endings = set()
            for path in product((0, 1), repeat=3):
                with self.subTest(lang=lang, story=story_id, path=path):
                    session = StorySession(story_id, lang)
                    for step, choice in enumerate(path):
                        self.assertEqual(session.step, step)
                        self.assertFalse(session.finished)
                        self.assertTrue(session.text)
                        self.assertEqual(len(session.choices), 2)
                        self.assertIn(session.choose(choice), {"happy", "dance", "stretch"})
                    self.assertEqual(session.step, 3)
                    self.assertTrue(session.finished)
                    self.assertEqual(session.choices, [])
                    endings.add(session.text)
            self.assertEqual(len(endings), 2)

    def test_previous_decisions_change_next_scene_and_reaction(self):
        for story_id, lang in product(("picnic", "sock", "stars"), ("de", "en")):
            with self.subTest(story=story_id, lang=lang):
                left, right = StorySession(story_id, lang), StorySession(story_id, lang)
                left.choose(0)
                right.choose(1)
                self.assertNotEqual(left.text, right.text)
                self.assertNotEqual(left.choose(0), right.choose(0))
                self.assertNotEqual(left.text, right.text)
                left, right = StorySession(story_id, lang), StorySession(story_id, lang)
                left.choose(0)
                right.choose(0)
                left.choose(0)
                right.choose(1)
                self.assertNotEqual(left.text, right.text)

    def test_invalid_choice_does_not_advance(self):
        for index in (-1, 2, None, "0", 0.5, True):
            session = StorySession("picnic")
            initial = session.text
            with self.subTest(index=index), self.assertRaises(ValueError):
                session.choose(index)
            self.assertEqual(session.step, 0)
            self.assertEqual(session.text, initial)

    def test_completed_story_cannot_replay(self):
        session = StorySession("sock")
        for _ in range(3):
            session.choose(0)
        ending = session.text
        with self.assertRaises(ValueError):
            session.choose(0)
        self.assertEqual(session.step, 3)
        self.assertEqual(session.text, ending)

    def test_titles_aliases_and_language_fallback(self):
        self.assertEqual(set(story_titles()), {"picnic", "sock", "stars"})
        self.assertNotEqual(story_titles("de"), story_titles("en"))
        self.assertEqual(story_titles("xx"), story_titles("de"))
        self.assertEqual(StorySession("story_picnic").text, StorySession("picnic").text)
        with self.assertRaises(ValueError):
            StorySession("unknown")

    def test_personalities_and_unknown_character_fallback(self):
        for lang in ("de", "en"):
            cat = StorySession("stars", lang, "cat_mochi").text
            fox = StorySession("stars", lang, "animal_fox").text
            bunny = StorySession("stars", lang, "animal_bunny").text
            self.assertEqual(len({cat, fox, bunny}), 3)
            self.assertEqual(StorySession("stars", lang, "unknown").text, cat)
            for character in (
                "cat_mochi", "cat_luna", "dog_shiba", "dog_balu", "fantasy_drago",
                "fantasy_byte", "fantasy_spooky", "fantasy_axolotl", "animal_penguin",
                "animal_bunny", "animal_fox", "animal_panda", "animal_hamster",
                "animal_raccoon", "animal_frog", "animal_arctic_fox", "animal_cocoa_bunny",
            ):
                with self.subTest(lang=lang, character=character):
                    session = StorySession("stars", lang, character)
                    for _ in range(3):
                        self.assertTrue(session.text)
                        session.choose(0)
                    self.assertTrue(session.finished)


if __name__ == "__main__":
    unittest.main()
