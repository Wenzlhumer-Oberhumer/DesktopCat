# Phase 10 – Coole Einrichtung beim ersten Start („Kennenlernen mit Kylie“)

Beim ersten Öffnen lernt Kylie den User in einem kurzen, verspielten **Kennenlern-Gespräch** kennen. Die Antworten werden als **Profil** gespeichert und bei jeder Gemini-Anfrage kurz mitgeschickt, damit Kylie den User persönlich anspricht und passend antwortet. Alles bleibt jederzeit änder- und löschbar.

## 10.1 Wann
- Neue Installation: direkt nach dem Start, bevor Kylie auf die Taskleiste hüpft.
- Update von v2.1/v2.2 ohne Profil: einmal beim nächsten Start, **vorausgefüllt** mit `pet.user_name` und gewählter Figur („Ich kenn dich ja schon ein bisschen, Florian 😺 – darf ich noch ein paar Sachen fragen?“, mit Button „Später“).
- Jederzeit wiederholbar: Rechtsklick/Tray → „✨ Kennenlernen wiederholen“, und Button in „Meine Daten“.
- Config-Flag `onboarding_done` (Default `False`). „Später“ → beim nächsten Start nochmal fragen, maximal 3× (`onboarding_skips`), dann nur noch per Menü.

## 10.2 Wie es aussieht (freundlich & cool)
Neues Fenster `onboarding.py` (`OnboardingDialog`), rahmenlos, abgerundet (16 px), dunkler Stil aus `settings_dialog.STYLE`, ca. 760×520, mittig, mit sanftem Einblenden:
- **Links (~40 %)**: die gewählte Figur **groß und animiert** (gleiche Zeichnung wie am Desktop über `draw_character` + `compute_pose`, eigener QTimer ~30 fps): winkt am Anfang, schaut zum Eingabefeld, freut sich bei jeder Antwort (Herzchen/Hüpfer), setzt bei der Key-Frage die Hackerbrille auf, Konfetti am Ende.
- **Rechts (~60 %)**: Chat-Verlauf wie in „Meine Chats“ (Figur-Bubbles links, User-Bubbles rechts in Rosa), Kylies Nachrichten erscheinen mit kurzem **„tippt…“-Effekt** (3 hüpfende Punkte, 400–900 ms).
- Unten: Eingabefeld + Senden, darüber **Schnellantwort-Chips** (runde Buttons) je nach Frage. Jede Frage hat „Überspringen“ (außer Name).
- Oben rechts eine dezente **Fortschritts-Pfotenleiste** (🐾🐾🐾◦◦◦).
- Esc / „Später“ schließt jederzeit; bereits gegebene Antworten bleiben gespeichert.

## 10.3 Die Fragen (Reihenfolge)
| # | Kylie fragt (Beispiel, in Figur-Stimme) | Antwortart | Gespeichert als |
|---|---|---|---|
| 1 | „Hiii! 👋 Ich bin Kylie, deine neue Desktop-Katze. Ich würde dich gern kennenlernen – ist das okay?“ | Chips: „Klar! 😺“ / „Später“ | – |
| 2 | „Welche Sprache magst du?“ | Chips: Deutsch / English | `language` |
| 3 | „Wie heißt du?“ | Text (Pflicht) | `profile.name` |
| 4 | „Und wie soll ich dich nennen? Spitzname, Boss, Chef…?“ | Text + Chips: Vorname / „Boss“ / Spitzname aus Name (z. B. „Flo“) | `pet.user_name` (bestehender Key!) |
| 5 | „Wie soll ich über dich sprechen?“ | Chips: er / sie / they / „egal, nimm einfach meinen Namen“ | `profile.pronouns` (optional) |
| 6 | „Wofür nutzt du deinen PC am meisten?“ | Mehrfach-Chips: Schule/Studium · Arbeit · Coding · Gaming · Kreativ · Surfen | `profile.uses` |
| 7 | „Was machst du gern? Hobbys, Lieblingsdinge…“ | Text (optional) | `profile.interests` |
| 8 | „Wie soll ich so drauf sein?“ | Chips: 🥰 lieb & verspielt · 😎 frech & witzig · 🧘 ruhig & kurz · 🤓 schlau & erklärend | `profile.tone` |
| 9 | „Wie oft darf ich mich melden?“ | Chips: Oft · Ab und zu · Nur wenn du mich rufst | `pet.chatter` + Intervalle (bestehende Keys) |
| 10 | „In welcher Stadt bist du ungefähr? Dann kann ich dir morgens das Wetter sagen ☀️“ | Text (optional, Hinweis: nur Stadt) | `profile.city` (für Briefing/Wetter-Outfit statt IP-Ortung) |
| 11 | „Damit ich richtig schlau werde, brauche ich einen Gratis-Schlüssel von Google 🔑“ | Bestehender Key-Ablauf eingebettet: „Gratis-Key holen“ + Feld + „Prüfen“ (wiederverwenden: `gemini.validate_key`, `gemini.save_key`, Anleitung aus `settings_dialog`). Wird übersprungen, wenn schon ein Key da ist. | Credential Manager (bestehend) |
| 12 | „Willst du mich so lassen oder lieber eine andere Figur?“ | Kleine Galerie der 9 Figuren (Mini-Renderings), Klick wechselt live links | `pet.character` |
| 13 | Kurze Datenschutz-Karte: was gespeichert wird + 3 bestehende Schalter (`privacy.*`) | Schalter | `privacy.*` |
| 14 | „Soll ich mit Windows starten?“ | Chips Ja/Nein | `autostart` |
| 15 | „Fertig! 🎉 Schön, dich kennenzulernen, {user_name}! Ich hüpf jetzt auf deine Taskleiste – doppelklick mich, wenn du was brauchst.“ | Konfetti, Fenster blendet aus, Figur „springt“ (vorhandenes `drop_in`) | `onboarding_done = True` |

## 10.4 Gemini macht es lebendig (ohne Key läuft alles trotzdem)
- **Ohne Key** (bis Frage 11): feste, freundliche Texte pro Frage aus `i18n` (DE/EN) in Figur-Stimme.
- **Mit Key** (ab Frage 11, oder sofort wenn schon ein Key existiert): Kylie **reagiert individuell** auf jede Antwort, bevor die nächste Frage kommt. Beispiel: Hobby „Gitarre“ → „Gitarre?! 🎸 Spielst du mir mal was vor? Ich schnurr dann mit!“. Dafür ein kurzer `gemini.ask` (im QThread-Worker, Timeout 15 s), Prompt: Figur-Persona + bisheriges Profil + letzte Antwort → „Antworte mit 1 kurzen, herzlichen Reaktion (max. 1 Satz, max. 1 Emoji). Stelle KEINE neue Frage.“ Bei Fehler/Timeout: feste Reaktion („Cool! 😺“), nie hängen bleiben.
- Freitext-Antworten (Name, Hobbys, Stadt) werden **lokal** bereinigt (trimmen, max. 60/200/40 Zeichen, keine Zeilenumbrüche). Optional mit Key: Hobbys zu einer kurzen Liste zusammenfassen.

## 10.5 Speichern
- `config.DEFAULTS` neu: `"profile": {"name": "", "pronouns": "", "uses": [], "interests": "", "tone": "", "city": ""}`, `"onboarding_done": False`, `"onboarding_skips": 0`. Bestehende Keys weiterverwenden (`pet.user_name`, `pet.character`, `pet.chatter`, `language`, `privacy.*`, `autostart`).
- Hobbys/Interessen zusätzlich als Fakten in `MemoryStore` (`kind="profile"`), damit sie in „Meine Daten“ erscheinen.

## 10.6 Profil in jedem Gemini-Prompt (kurz!)
Neue reine Funktion `profile_prompt(cfg) -> str` (in `agent_brain.py`), max. ~400 Zeichen, nur gesetzte Felder, Beispiel:
```
ÜBER DEN NUTZER: Heißt Florian, möchte "Flo" genannt werden (Pronomen: er). Nutzt den PC für Schule, Coding, Gaming.
Mag: Gitarre, Katzen, Python. Wohnt in der Nähe von Linz. Gewünschter Ton: frech & witzig.
Berücksichtige das natürlich und unaufdringlich – zähle es nicht auf.
```
- Einbau in `system_prompt(...)` bzw. `_chat_cli` (eine Stelle), außerdem in Neugier-Fragen (`curious.py`), Guten-Morgen-Briefing, Vision-Kommentare und die Onboarding-Reaktionen.
- **Ton** beeinflusst den Prompt („Sei frech und witzig“ / „Antworte ruhig und sehr kurz“ / „Erkläre gern etwas genauer“).
- Nur senden, wenn `privacy.remember` an ist; sonst nur `user_name`.
- `profile.city` ersetzt bei Wetter ohne Ortsangabe die automatische Ortung (`get_weather(location=city)`).

## 10.7 Ändern & Löschen
- „Meine Daten“ bekommt oben einen Abschnitt **„Dein Profil“**: alle Felder sichtbar und direkt bearbeitbar (Textfelder/Chips), Button „✨ Kennenlernen wiederholen“, Button „Profil löschen“ (setzt `profile` zurück, mit Bestätigung).
- „Alles vergessen“ (`wipe_my_data`) löscht auch das Profil (Config-Felder zurücksetzen) und setzt `onboarding_done = False`.
- Sprachbefehle: „wie heiße ich?“, „nenn mich ab jetzt Chef“ (→ `pet.user_name` ändern, kurze Bestätigung), „was weißt du über mich?“ zeigt auch das Profil.

## 10.8 i18n
Alle Onboarding-Texte, Chips und Hinweise in `i18n.py` (DE + EN); die Sprachwahl in Frage 2 schaltet sofort um (restliche Fragen kommen in der gewählten Sprache).

## Tests (`tests/test_onboarding.py`)
- `profile_prompt`: leeres Profil → nur Name/kein Block; volles Profil < 450 Zeichen; `privacy.remember=False` → kein Profil-Block; Ton-Zeile korrekt.
- Bereinigung der Freitexte (Länge, Zeilenumbrüche, leere Eingabe).
- Ablauf-Logik als reine Zustandsmaschine (`OnboardingFlow`, ohne Qt testbar): Reihenfolge, Überspringen, Key-Frage wird übersprungen wenn `has_key()`, Vorausfüllen bei Update, „Später“-Zähler max. 3.
- „nenn mich ab jetzt Chef“ → `pet.user_name == "Chef"` (Temp-Config).
- `wipe_my_data` setzt Profil + `onboarding_done` zurück (Temp-Config/Temp-DB).
- Gemini-Reaktion: Timeout/Fehler → fester Fallback-Text (gemockt).
- Screenshots: `ref/plan/screenshots/ui_onboarding_1.png` (Begrüßung), `_2.png` (Spitzname mit Chips), `_3.png` (Figur-Galerie), `_4.png` (Fertig mit Konfetti) – ansehen und schön machen.

## Abnahme (in `08_ABNAHME.md` ergänzen)
- [ ] Frische Config (Temp-`APPDATA` oder Config umbenennen) → Kennenlernen startet, alle 15 Schritte durchspielbar, Ergebnis in Config + „Meine Daten“
- [ ] Mit Key: individuelle Reaktionen; ohne Key: feste Texte, nichts hängt
- [ ] Danach fragt man Kylie „wie heiße ich?“ → richtige Antwort; Gemini-Antworten nutzen Spitzname und Ton
- [ ] Update-Fall: bestehender `user_name` ist vorausgefüllt, „Später“ funktioniert
- [ ] „Kennenlernen wiederholen“ und „Profil löschen“ funktionieren
