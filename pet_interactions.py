"""Small, entirely local conversations and activities with the desktop pet."""
from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class Choice:
    label: str
    reply: str
    action: str = 'happy'


@dataclass(frozen=True)
class Interaction:
    id: str
    question: str
    choices: tuple[Choice, ...] = ()
    reply: str = ''
    remember: bool = True


def interactions_for(language: str = 'de') -> tuple[Interaction, ...]:
    def t(de, en):
        return en if language == 'en' else de

    return (
        Interaction('drink', t('Was macht deinen Schreibtisch gemütlicher: Kaffee oder Tee?',
                               'What makes your desk cozier: coffee or tea?'), (
            Choice(t('Kaffee', 'Coffee'), t('Dann bewache ich die Kaffeepause. Du trinkst, ich kuschle!', 'I will guard the coffee break. You sip, I snuggle!')),
            Choice(t('Tee', 'Tea'), t('Ein warmer Tee und ein kleiner Begleiter. Das klingt nach uns!', 'Warm tea and a little companion. That sounds like us!')))),
        Interaction('weather', t('Ein freier Nachmittag: Regentag mit Decke oder Sonne im Grünen?',
                                 'A free afternoon: rainy blanket time or sunshine outdoors?'), (
            Choice(t('Decke & Regen', 'Blanket & rain'), t('Ich halte uns schon mal ein kuscheliges Plätzchen frei.', 'I will save us a cozy little spot.')),
            Choice(t('Ab ins Grüne', 'Go outdoors'), t('Dann sammeln wir schöne Gedanken für später!', 'Let us collect lovely thoughts for later!')))),
        Interaction('snack', t('Eine wichtige Flauschfrage: lieber süß oder herzhaft?', 'An important fluffy question: sweet or savory?'), (
            Choice(t('Süß', 'Sweet'), t('Dann bist du heute für die Kekse zuständig. Ich für die Gesellschaft!', 'You are in charge of cookies today. I will bring the company!')),
            Choice(t('Herzhaft', 'Savory'), t('Gute Wahl! Ich sitze ganz brav neben deinem Teller.', 'Good choice! I will sit very politely beside your plate.')))),
        Interaction('trip', t('Unser kleiner Traum-Ausflug: Meer oder Berge?', 'Our little dream trip: sea or mountains?'), (
            Choice(t('Meer', 'Sea'), t('Pfotenabdrücke im Sand! Ich passe auf deine Muscheln auf.', 'Pawprints in the sand! I will look after your shells.')),
            Choice(t('Berge', 'Mountains'), t('Ein Aussichtspunkt für dich und eine warme Tasche für mich!', 'A viewpoint for you and a warm pocket for me!')))),
        Interaction('evening', t('Heute Abend lieber ein gutes Buch oder ein gemütlicher Film?', 'A good book or a cozy movie tonight?'), (
            Choice(t('Ein Buch', 'A book'), t('Ich mache es mir neben dir bequem und höre beim Umblättern zu.', 'I will settle beside you and listen to the pages turning.')),
            Choice(t('Ein Film', 'A movie'), t('Abgemacht! Ich reserviere den kleinsten Platz auf dem Sofa.', 'Deal! I will reserve the smallest spot on the sofa.')))),
        Interaction('season', t('Was magst du lieber: bunte Herbstblätter oder Frühlingsblüten?', 'Which do you prefer: autumn leaves or spring blossoms?'), (
            Choice(t('Herbstblätter', 'Autumn leaves'), t('Rascheln, Kuschelsocken und warme Farben. Herrlich!', 'Rustling leaves, cozy socks and warm colors. Lovely!')),
            Choice(t('Frühlingsblüten', 'Spring blossoms'), t('Dann schicke ich dir einen winzigen Frühlingsgruß.', 'Then I am sending you a tiny spring greeting.')))),
        Interaction('music', t('Was begleitet dich lieber: leise Musik oder gemütliche Stille?', 'What keeps you company: soft music or cozy quiet?'), (
            Choice(t('Leise Musik', 'Soft music'), t('Ich wippe ganz leise mit. Nur ein kleines Pfötchen!', 'I will sway along very quietly. Just one little paw!')),
            Choice(t('Stille', 'Quiet'), t('Dann bin ich einfach still bei dir. Gesellschaft geht auch ohne Worte.', 'Then I will sit quietly with you. Company does not need words.')))),
        Interaction('adventure', t('Stell dir vor, wir gehen auf Entdeckungsreise: Zauberwald oder Sternenhimmel?', 'Imagine our next adventure: enchanted forest or starry sky?'), (
            Choice(t('Zauberwald', 'Magic forest'), t('Ich nehme einen Mini-Rucksack und ganz viel Mut mit!', 'I will bring a mini backpack and lots of courage!')),
            Choice(t('Sternenhimmel', 'Starry sky'), t('Unser Raumschiff bekommt natürlich eine Kuschelecke.', 'Our spaceship will have a snuggle corner, of course.')))),
        Interaction('pace', t('Was klingt heute besser: ein kleines Abenteuer oder ganz entspannt sein?', 'What sounds better today: a little adventure or taking it easy?'), (
            Choice(t('Abenteuer', 'Adventure'), t('Ich bin dabei! Auch kleine Schritte können aufregend sein.', 'Count me in! Even tiny steps can be exciting.')),
            Choice(t('Entspannen', 'Take it easy'), t('Heute darf es langsam gehen. Ich bleibe an deiner Seite.', 'It is okay to go slowly today. I will stay by your side.')))),
        Interaction('breakfast', t('Sonntagsfrühstück: Pfannkuchen oder frische Brötchen?', 'Sunday breakfast: pancakes or fresh rolls?'), (
            Choice(t('Pfannkuchen', 'Pancakes'), t('Ein gemütlicher Start! Ich bringe die gute Laune dazu.', 'A cozy start! I will bring the good mood.')),
            Choice(t('Brötchen', 'Fresh rolls'), t('Knusperfrühstück! Danach ruhen wir uns einen winzigen Moment aus.', 'A crunchy breakfast! Then we can rest for a tiny moment.')))),
        Interaction('home', t('Dein perfekter Wohlfühlort: Hütte im Wald oder kleines Haus am Wasser?', 'Your perfect cozy place: woodland cabin or little waterside home?'), (
            Choice(t('Waldhütte', 'Woodland cabin'), t('Draußen Blätter, drinnen Wärme. Ich wäre sofort eingezogen!', 'Leaves outside, warmth inside. I would move in right away!')),
            Choice(t('Am Wasser', 'By the water'), t('Wir schauen den Wellen zu. Ich passe auf, dass die Decke trocken bleibt.', 'We can watch the waves. I will keep the blanket dry.')))),
        Interaction('comfort', t('Was ist gemütlicher: dicke Socken oder ein großer Lieblingspulli?', 'What is cozier: thick socks or a favorite oversized sweater?'), (
            Choice(t('Kuschelsocken', 'Cozy socks'), t('Warme Füße, glückliche Pfoten. Das verstehe ich!', 'Warm feet, happy paws. I understand that!')),
            Choice(t('Lieblingspulli', 'Favorite sweater'), t('Da passt bestimmt noch ein kleines flauschiges Wesen dazu.', 'There must be room for one more little fluffy creature.')))),
        Interaction('bright_moment', t('Was war heute dein schönster kleiner Moment?', 'What was your loveliest little moment today?'),
                    reply=t('Danke fürs Erzählen. Ich freue mich, dass du diesen Moment mit mir teilst.', 'Thank you for telling me. I am glad you shared that moment with me.')),
        Interaction('looking_forward', t('Worauf freust du dich gerade? Etwas Kleines zählt auch!', 'What are you looking forward to? Tiny things count too!'),
                    reply=t('Das behalte ich für diesen Moment ganz warm bei uns. Schön, dass du mir davon erzählst.', 'I will keep that thought warm with us for a moment. Thank you for sharing.')),
        Interaction('tiny_win', t('Was hast du heute geschafft, auch wenn es nur eine Kleinigkeit war?', 'What did you manage today, even if it was something tiny?'),
                    reply=t('Das darf zählen. Ich schicke dir ein kleines anerkennendes Pfötchen!', 'That counts. I am sending you a little paw of appreciation!')),
        Interaction('cozy_idea', t('Wie würde dein perfekter gemütlicher Abend aussehen?', 'What would your perfect cozy evening look like?'),
                    reply=t('Danke, dass du mich ein bisschen in deine Welt mitnimmst. Ich leiste dir gern Gesellschaft.', 'Thank you for letting me into your world a little. I am happy to keep you company.')),
        Interaction('pet_treat', t('Ich habe extra meinen niedlichsten Blick geübt. Ein Mini-Leckerli?', 'I practiced my cutest look. A tiny treat?'), (
            Choice(t('Ein Leckerli', 'A little treat'), t('Mmmh, danke! Das war ein ganz besonderer kleiner Glücksmoment.', 'Mmm, thank you! That was a special little happy moment.'), 'treat'),
            Choice(t('Lieber kuscheln', 'Cuddles instead'), t('Eine Kuscheleinheit ist mindestens genauso schön!', 'A cuddle is just as lovely!'))), remember=False),
        Interaction('pet_dance', t('Ich hätte Lust auf einen winzigen Freudentanz. Machen wir mit?', 'I feel like doing a tiny happy dance. Shall we?'), (
            Choice(t('Tanz für mich!', 'Dance for me!'), t('Ein Pfötchen links, ein Pfötchen rechts… nur für dich!', 'One paw left, one paw right… just for you!'), 'dance'),
            Choice(t('Gemütlich bleiben', 'Stay cozy'), t('Abgemacht. Ich sitze einfach zufrieden bei dir.', 'Deal. I will just sit happily with you.'))), remember=False),
        Interaction('pet_stretch', t('Meine Pfötchen brauchen eine kleine Pause. Zusammen strecken?', 'My paws need a little break. Shall we stretch together?'), (
            Choice(t('Streeecken', 'Streeetch'), t('Ganz lang machen… und wieder locker lassen. Fein gemacht!', 'Stretch out… and relax again. Nicely done!'), 'stretch'),
            Choice(t('Nur ein Lächeln', 'Just a smile'), t('Das nehme ich auch. Hier kommt ein kleines Lächeln zurück!', 'I will take that too. Here is a little smile back!'))), remember=False),
        Interaction('pet_rest', t('Wollen wir eine Kuschelpause machen oder ein bisschen feiern?', 'Shall we have a cozy rest or a little celebration?'), (
            Choice(t('Kuschelpause', 'Cozy rest'), t('Dann rolle ich mich gemütlich ein. Du darfst auch kurz durchatmen.', 'Then I will curl up. You can take a little breather too.'), 'sleep'),
            Choice(t('Ein bisschen feiern', 'Celebrate a little'), t('Ein kleiner Konfettimoment für uns beide!', 'A tiny confetti moment for both of us!'), 'celebrate')), remember=False),
    )


def choose_interaction(recent: list[str], language: str = 'de') -> Interaction:
    items = interactions_for(language)
    available = [item for item in items if item.id not in recent[-6:]]
    return random.choice(available or items)


def reaction_for(item: Interaction, answer, character: str, name: str, language: str = 'de'):
    if item.choices:
        if type(answer) is not int or not 0 <= answer < len(item.choices):
            return None
        choice = item.choices[answer]
        reply, action = choice.reply, choice.action
    else:
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 280:
            return None
        reply, action = item.reply, 'happy'
    if 'fox' in character:
        sound = 'Yip~' if language == 'en' else 'Fiep~'
    elif 'bunny' in character:
        sound = 'Snuggle~' if language == 'en' else 'Mümmel~'
    elif character.startswith('dog_'):
        sound = 'Woof~' if language == 'en' else 'Wuff~'
    elif character.startswith('cat_'):
        sound = 'Purr~' if language == 'en' else 'Schnurr~'
    else:
        sound = '✨'
    return f'{name}: {sound} {reply}', action


def save_answer(store, cfg, item: Interaction, answer, reply: str, character: str) -> None:
    if reaction_for(item, answer, character, '', 'de') is None:
        return
    text = item.choices[answer].label if item.choices else answer.strip()
    if cfg.get('privacy.remember', True) and item.remember:
        store.add_fact(f'{item.question} → {text}')
    if cfg.get('privacy.save_chats', True):
        store.add_message('assistant', item.question, character)
        store.add_message('user', text, character)
        store.add_message('assistant', reply, character)
