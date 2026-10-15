# SPDX-License-Identifier: GPL-3.0-or-later
"""Three small, fully offline decision stories. No UI or saved state required."""

_STORIES = {
    "de": {
        "picnic": (
            "Picknick im Regen",
            "Die Picknickdecke liegt bereit, da fallen erste Regentropfen. Wohin gehen wir?",
            (("Unter den großen Baum", "Ins gemütliche Zimmer"),
             ("Obst teilen", "Dem Regen zuhören"),
             ("Ein kleines Lied singen", "Still zusammen genießen")),
            (("Unter dem Blätterdach bleibt unsere Decke trocken.",
              "Im Zimmer bauen wir ein Picknick zwischen weichen Kissen."),
             ("Das geteilte Obst schmeckt besonders gut. Ein Tropfen klopft im Takt.",
              "Wir lauschen dem Regen. Sein leises Trommeln klingt wie Musik.")),
            ("Unser Regenpicknick endet voller Lachen. Sogar die Wolken scheinen vor Freude mitzuwippen!",
             "Unser Regenpicknick endet mit einer gemütlichen Pause. Gemeinsam ist selbst Regenwetter schön."),
        ),
        "sock": (
            "Die verschwundene Socke",
            "Eine kuschelige Socke fehlt. Wo beginnt unsere kleine Suche?",
            (("Unter dem Sofa suchen", "Im Wäschekorb nachsehen"),
             ("Der Wollspur folgen", "Leise nach der Socke rufen"),
             ("Eine Sockentheater-Bühne bauen", "Die Socken gemütlich zusammenlegen")),
            (("Unter dem Sofa entdecken wir einen Wollfaden.",
              "Im Wäschekorb ragt ein Wollfaden zwischen den Handtüchern hervor."),
             ("Die Wollspur führt zum Kissen: Dahinter steckt die Socke!",
              "Auf unser leises Rufen raschelt das Kissen. Dahinter wartet die Socke!")),
            ("Beide Socken sind wieder vereint, und wir feiern unseren Fund. Was für ein lustiges Wiedersehen!",
             "Beide Socken liegen wieder zusammen. Wir gönnen uns eine warme, zufriedene Pause."),
        ),
        "stars": (
            "Ein Abend unter Sternen",
            "Die ersten Sterne funkeln. Wo machen wir es uns gemütlich?",
            (("Auf der Wiese", "Am offenen Fenster"),
             ("Ein Sternbild erfinden", "Einen stillen Wunsch denken"),
             ("Den Sternen zuwinken", "Eine kleine Ruhepause machen")),
            (("Auf der Wiese duftet das Gras; über uns glitzert der Himmel.",
              "Am Fenster liegen weiche Kissen; der Himmel ist zum Greifen nah."),
             ("Unser erfundenes Sternbild sieht aus wie ein fliegender Keks.",
              "Unser stiller Wunsch reist in Gedanken zu einem besonders hellen Stern.")),
            ("Wir schauen zu den Sternen und kichern. Der Himmel schenkt uns einen fröhlichen Abend.",
             "Wir kuscheln uns ein und bewahren die schöne Erinnerung. Der Abend endet friedlich und warm."),
        ),
    },
    "en": {
        "picnic": (
            "Picnic in the Rain",
            "The picnic blanket is ready when the first raindrops fall. Where shall we go?",
            (("Under the big tree", "Into the cozy room"),
             ("Share some fruit", "Listen to the rain"),
             ("Sing a little song", "Enjoy a quiet moment together")),
            (("Under the leafy roof, our blanket stays dry.",
              "Inside, we build a picnic among soft cushions."),
             ("The shared fruit tastes extra sweet. A raindrop taps along.",
              "We listen to the rain. Its gentle tapping sounds like music.")),
            ("Our rainy picnic ends with laughter. Even the clouds seem to sway with joy!",
             "Our rainy picnic ends with a cozy rest. Even rainy weather feels lovely together."),
        ),
        "sock": (
            "The Missing Sock",
            "One cozy sock is missing. Where shall our little search begin?",
            (("Look under the sofa", "Check the laundry basket"),
             ("Follow the woolly trail", "Call softly for the sock"),
             ("Build a tiny sock theater", "Fold the socks snugly together")),
            (("Under the sofa, we discover a strand of wool.",
              "A strand of wool peeks between the towels in the laundry basket."),
             ("The woolly trail leads to a cushion: the sock is hiding behind it!",
              "Our soft call brings a rustle from the cushion. The sock is waiting behind it!")),
            ("Both socks are together again, and we celebrate our discovery. What a funny reunion!",
             "Both socks are together again. We settle down for a warm, contented rest."),
        ),
        "stars": (
            "An Evening under the Stars",
            "The first stars are twinkling. Where shall we get comfortable?",
            (("On the meadow", "By the open window"),
             ("Invent a constellation", "Make a quiet wish"),
             ("Wave to the stars", "Take a little rest")),
            (("On the meadow, the grass smells sweet beneath the sparkling sky.",
              "Soft cushions wait by the window, and the sky feels close enough to touch."),
             ("Our invented constellation looks like a flying cookie.",
              "In our thoughts, our quiet wish travels to a particularly bright star.")),
            ("We look up at the stars and giggle. The sky gives us a cheerful evening.",
             "We snuggle up and keep this lovely memory safe. The evening ends peacefully and warmly."),
        ),
    },
}

# Local voices keep the model independent of the Qt-based character registry.
_VOICES = {
    "cat": ("Neugierig spitze ich die Ohren.", "I perk up my ears curiously."),
    "fox": ("Mit frechem Grinsen habe ich schon einen schlauen Plan!", "With a cheeky grin, I already have a clever plan!"),
    "bunny": ("Ganz sanft rücke ich ein bisschen näher.", "Very gently, I snuggle a little closer."),
    "dog": ("Voller Vorfreude wedle ich mit dem Schwanz.", "I wag my tail with excitement."),
    "drago": ("Ein winziges, warmes Drachenfunkeln begleitet uns.", "A tiny, warm dragon sparkle joins us."),
    "byte": ("Meine kleinen Leuchten blinken vor Neugier.", "My little lights blink with curiosity."),
    "spooky": ("Ich schwebe fröhlich an deiner Seite.", "I float happily beside you."),
    "axolotl": ("Mit einem fröhlichen Lächeln bin ich dabei.", "I join in with a cheerful smile."),
    "penguin": ("Fröhlich watschle ich an deine Seite.", "I waddle happily to your side."),
    "panda": ("Gemütlich machen wir uns gemeinsam auf den Weg.", "We set off together at a cozy pace."),
    "hamster": ("Meine kleinen Schnurrhaare zucken gespannt.", "My tiny whiskers twitch eagerly."),
    "raccoon": ("Mit flinken Pfötchen bin ich bereit.", "My nimble little paws are ready."),
    "frog": ("Mit einem kleinen Freudenhüpfer bin ich dabei.", "I join in with a little happy hop."),
}


def story_titles(lang: str = "de") -> dict[str, str]:
    """Return the three stable story IDs and their localized titles."""
    return {key: data[0] for key, data in _STORIES.get(lang, _STORIES["de"]).items()}


class StorySession:
    """A three-decision story; each choice advances exactly once."""

    def __init__(self, story_id: str, lang: str = "de", character: str = "cat_mochi"):
        self.story_id = story_id.removeprefix("story_")
        self.lang = lang if lang in _STORIES else "de"
        if self.story_id not in _STORIES[self.lang]:
            raise ValueError(f"Unknown story: {story_id}")
        self._story = _STORIES[self.lang][self.story_id]
        self._history: list[int] = []
        family = {
            "cat_mochi": "cat", "cat_luna": "cat", "dog_shiba": "dog", "dog_balu": "dog",
            "fantasy_drago": "drago", "fantasy_byte": "byte", "fantasy_spooky": "spooky",
            "fantasy_axolotl": "axolotl", "animal_penguin": "penguin", "animal_bunny": "bunny",
            "animal_fox": "fox", "animal_panda": "panda", "animal_hamster": "hamster",
            "animal_raccoon": "raccoon", "animal_frog": "frog", "animal_arctic_fox": "fox",
            "animal_cocoa_bunny": "bunny",
        }.get(character, "cat")
        self._voice = _VOICES[family][self.lang == "en"]

    @property
    def step(self) -> int:
        return len(self._history)

    @property
    def finished(self) -> bool:
        return self.step == 3

    @property
    def text(self) -> str:
        if self.finished:
            # Two friendly outcomes; every decision contributes to the ending.
            return self._voice + " " + self._story[4][int(sum(self._history) >= 2)]
        scenes = [self._story[1]] if not self._history else [
            self._story[3][step][choice] for step, choice in enumerate(self._history)
        ]
        return self._voice + " " + " ".join(scenes)

    @property
    def choices(self) -> list[str]:
        return [] if self.finished else list(self._story[2][self.step])

    def choose(self, index: int) -> str:
        """Advance and return an animation; invalid/completed choices do nothing."""
        if self.finished or type(index) is not int or index not in (0, 1):
            raise ValueError("Choose an available option (0 or 1) in an unfinished story")
        previous = self._history[-1] if self._history else 0
        reaction = (("happy", "stretch"), ("dance", "happy"))[previous][index]
        self._history.append(index)
        return reaction
