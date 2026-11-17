"""Build every card from data/ and sync it into Anki (deck "Ultimate Crunch").

What a card is made of:
- data/verbs.tsv        the verbs (edit by hand), see build_verbs.py
- script/conjugate.py   the forms, their indications and English
- data/examples.json    the Tatoeba example sentences, see build_examples.py
- notes/*.md            the Explanation, see push_explanations.py
- templates/            the card layout (front.html, back.html, style.css)

Each note has a Key field ("食べる|たべる|nai"). Rerunning updates the notes
whose content changed and adds the new ones; a note whose Key no longer
exists (verb or form removed) is listed, not deleted. Audio is added
afterwards by add_audio.py.

Which forms each verb gets: N5 and N4 verbs get every form. N3 verbs get
N3_FORMS_PER_VERB forms each, picked so that every form is drilled about as
often, preferring the forms that have an example sentence for that verb.

Usage (Anki must be running with AnkiConnect):
    python script/push_notes.py            # dry run: show counts and a few cards
    python script/push_notes.py --apply    # create/update the note type, deck and notes
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conjugate import FORM, FORMS  # noqa: E402
from furigana import annotate  # noqa: E402
from verbs import load_verbs  # noqa: E402

NOTE_TYPE = "Crunch Fill"
DECK = "Ultimate Crunch"
ANKI_URL = "http://127.0.0.1:8765"
N3_FORMS_PER_VERB = 6

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
EXAMPLES = ROOT / "data" / "examples.json"

FIELDS = ["Sentence", "SentenceMod", "Translation", "Audio", "JLPT", "Instruction", "Topic",
          "Example", "ExampleTranslation", "ExampleAudio", "ExampleSrc", "VerbType", "Explanation", "Key"]
# Fields this script owns; Audio and ExampleAudio belong to add_audio.py,
# Explanation to push_explanations.py.
OWNED = [f for f in FIELDS if f not in ("Audio", "ExampleAudio", "Explanation")]

INSTRUCTION = '<span style="color: rgb(102, 102, 102);">Conjugation Exercise</span>'
TOPIC = {"v1": "一段動詞", "vk": "不規則動詞 (来る)", "vs-i": "不規則動詞 (する)",
         "v5k-s": "五段動詞 (行く)", "v5r-i": "五段動詞 (ある)", "v5u-s": "五段動詞 (問う)",
         "v5aru": "五段動詞 (いらっしゃる)", "vs-s": "五段動詞 (〜する like 〜す)"}


def verb_type(cls):
    """JMdict class -> Ichidan / Godan / Irregular. 〜する verbs like 愛する
    conjugate like 〜す (愛さない), so they count as godan, as in TOPIC."""
    if cls.startswith("v1"):
        return "Ichidan"
    if cls.startswith("v5") or cls == "vs-s":
        return "Godan"
    return "Irregular"


# Readings unidic picks that are correct but stiff for a learner's deck.
READING_FIXES = {"私[わたくし]": "私[わたし]", "明日[あす]": "明日[あした]"}


def anki(action, **params):
    r = requests.post(ANKI_URL, json={"action": action, "version": 6, "params": params}).json()
    if r.get("error"):
        raise RuntimeError(f"{action}: {r['error']}")
    return r["result"]


def pick_forms(verbs, examples):
    """-> {verb index: [form keys]}: all forms for N5/N4 verbs, a balanced sample for N3."""
    chosen, used = {}, Counter()
    for i, v in enumerate(verbs):
        forms = v.forms()
        if v.level >= 4:
            chosen[i] = forms
            continue
        has_ex = {k for k in forms if f"{v.spell}|{v.reading}|{k}" in examples}
        # Least drilled first; among equals, prefer forms with an example.
        ranked = sorted(forms, key=lambda k: (used[k], k not in has_ex, FORMS.index(FORM[k])))
        chosen[i] = sorted(ranked[:N3_FORMS_PER_VERB], key=lambda k: FORMS.index(FORM[k]))
        used.update(chosen[i])
    return chosen


def example_fields(ex):
    if not ex or ex.get("skip"):
        return {"Example": "", "ExampleTranslation": "", "ExampleSrc": ""}
    ja = ex["ja"].replace(ex["match"], f"<b>{ex['match']}</b>", 1)
    src = (f'<a href="https://tatoeba.org/sentences/show/{ex["id"]}">Tatoeba #{ex["id"]}</a>'
           f' (CC BY 2.0 FR)')
    if ex.get("audio"):
        a = ex["audio"]
        src += f', audio by {a["user"]} ({a["license"]})'
    ja = annotate(ja)
    for old, new in READING_FIXES.items():
        ja = ja.replace(old, new)
    return {"Example": ja, "ExampleTranslation": ex["en"], "ExampleSrc": src}


def build():
    verbs = load_verbs()
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8")) if EXAMPLES.exists() else {}
    chosen = pick_forms(verbs, examples)
    notes = []
    for i, v in enumerate(verbs):
        for key in chosen[i]:
            f = FORM[key]
            word, _ = v.conj(key)
            k = f"{v.spell}|{v.reading}|{key}"
            level = min(v.level, f.level)
            fields = {
                "Sentence": f"{v.word}→&nbsp;#{word}#",
                "SentenceMod": f.mod,
                "Translation": v.english(key),
                "JLPT": str(level),
                "Instruction": INSTRUCTION,
                "Topic": TOPIC.get(v.cls, "五段動詞" if v.cls.startswith("v5") else v.cls),
                "VerbType": verb_type(v.cls),
                "Key": k,
                **example_fields(examples.get(k)),
            }
            tags = [f"UC::N{level}", f"UC::form::{key}", f"UC::verb::N{v.level}",
                    f"UC::type::{verb_type(v.cls).lower()}"]
            notes.append({"fields": fields, "tags": tags, "order": (-level, FORMS.index(f), i)})
    # New cards come in this order: N5 first, then form by form (all ます
    # cards, then ません...), verbs in list order.
    notes.sort(key=lambda n: n["order"])
    return notes


def ensure_model():
    read = lambda name: (TEMPLATES / name).read_text(encoding="utf-8")
    if NOTE_TYPE not in anki("modelNames"):
        anki("createModel", modelName=NOTE_TYPE, inOrderFields=FIELDS, css=read("style.css"),
             cardTemplates=[{"Name": "Card 1", "Front": read("front.html"), "Back": read("back.html")}])
        print(f'created note type "{NOTE_TYPE}"')
        return
    have = anki("modelFieldNames", modelName=NOTE_TYPE)
    for f in FIELDS:
        if f not in have:
            anki("modelFieldAdd", modelName=NOTE_TYPE, fieldName=f, index=len(have))
            have.append(f)
    card = next(iter(anki("modelTemplates", modelName=NOTE_TYPE)))
    anki("updateModelTemplates", model={"name": NOTE_TYPE, "templates": {
        card: {"Front": read("front.html"), "Back": read("back.html")}}})
    anki("updateModelStyling", model={"name": NOTE_TYPE, "css": read("style.css")})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write to Anki")
    args = ap.parse_args()

    notes = build()
    by_level = Counter(n["fields"]["JLPT"] for n in notes)
    with_ex = sum(1 for n in notes if n["fields"]["Example"])
    print(f"{len(notes)} cards: " + ", ".join(f"N{k} {by_level[k]}" for k in sorted(by_level, reverse=True))
          + f"; {with_ex} with an example sentence")

    if not args.apply:
        for n in notes[:3] + notes[-3:]:
            print(json.dumps({k: n["fields"][k] for k in ("Sentence", "SentenceMod", "Translation", "Example")},
                             ensure_ascii=False))
        print("dry run, use --apply")
        return

    ensure_model()
    anki("createDeck", deck=DECK)
    existing = {}
    ids = anki("findNotes", query=f'"note:{NOTE_TYPE}"')
    for info in anki("notesInfo", notes=ids) if ids else []:
        existing[info["fields"]["Key"]["value"]] = info

    to_add, updated, retag = [], 0, {}
    for n in notes:
        old = existing.pop(n["fields"]["Key"], None)
        if old is None:
            to_add.append({"deckName": DECK, "modelName": NOTE_TYPE, "fields": n["fields"], "tags": n["tags"],
                           "options": {"allowDuplicate": True}})
            continue
        changed = {f: n["fields"][f] for f in OWNED if old["fields"][f]["value"] != n["fields"][f]}
        if changed:
            anki("updateNoteFields", note={"id": old["noteId"], "fields": changed})
            updated += 1
        missing_tags = " ".join(t for t in n["tags"] if t not in old["tags"])
        if missing_tags:
            retag.setdefault(missing_tags, []).append(old["noteId"])
    for tags, ids in retag.items():  # one call per tag set, not per note
        anki("addTags", notes=ids, tags=tags)
    retagged = sum(map(len, retag.values()))
    for i in range(0, len(to_add), 500):
        anki("addNotes", notes=to_add[i:i + 500])
        print(f"  added {min(i + 500, len(to_add))}/{len(to_add)}")
    print(f"{len(to_add)} notes added, {updated} updated, {retagged} retagged")
    if existing:
        print(f"!! {len(existing)} notes in Anki whose Key is no longer generated (not deleted):")
        for k in list(existing)[:20]:
            print("   ", k)


if __name__ == "__main__":
    main()
