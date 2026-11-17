"""Copy the explanations in notes/*.md into the notes' Explanation field.

Each Markdown file is turned into HTML:
- the "# title" line becomes the title of a collapsed <details> section;
- furigana uses the card syntax, 帰[かえ]る -> <ruby>;
- an image like ![...](../tex/name.svg) is uploaded to Anki's media folder as
  _name.svg (the leading "_" keeps "Check Media" from deleting it) and linked.

Which file goes on which cards:
- a note about a form is named after the form's key in conjugate.py, with
  its level: notes/n5-masu.md goes on every ます card (tag UC::form::masu);
- any other note is listed in EXTRA, with an Anki search for its cards.
Edit the files, never the Explanation field in Anki: rerunning overwrites it.

Usage (Anki must be running with AnkiConnect):
    python script/push_explanations.py            # dry run
    python script/push_explanations.py --apply    # upload images, update notes
"""
import argparse
import base64
import re
import sys
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conjugate import FORM  # noqa: E402
from push_notes import NOTE_TYPE, anki, ensure_model  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes"

# Other notes/<file>.md -> the cards that show it (an Anki search)
EXTRA = {
}
# Notes used by another script instead (not pushed here).
USED_ELSEWHERE = {"n5-verbclassification": "recognize.py (the exceptions table)"}

FURI = re.compile(r"([一-鿿々〆ヶ]+)\[([^\]]+)\]")
# In 毎日[まいにち] 本[ほん]を the space only separates the furigana: Japanese
# has no spaces, so drop any space between two Japanese characters (a "]"
# counts as one); keep those around → or after a comma.
JA = "ぁ-ゟ゠-ヿ一-鿿々〆ヶ"
FURI_SPACE = re.compile(rf"(?<=[\]{JA}]) (?=[{JA}])")


def is_empty(path):
    """A skeleton note: only the title, headings and empty bullets, no text yet."""
    lines = path.read_text(encoding="utf-8").splitlines()[1:]
    return not any(l.strip() and not l.lstrip().startswith("#") and l.strip() != "-" for l in lines)


def explanations():
    """-> {note name: Anki search}, form notes first in FORMS order, then EXTRA.
    Empty skeletons are left out, so they don't show as blank sections."""
    out = {}
    for key, form in FORM.items():
        name = f"n{form.level}-{key}"
        path = NOTES / f"{name}.md"
        if path.exists() and not is_empty(path):
            out[name] = f'"note:{NOTE_TYPE}" tag:UC::form::{key}'
    return {**out, **EXTRA}


def furigana(text):
    return FURI.sub(r"<ruby>\1<rt>\2</rt></ruby>", FURI_SPACE.sub("", text))
IMG = re.compile(r'<img alt="([^"]*)" src="([^"]+)"\s*/?>')


def render(name):
    """-> (html, {media name: local path})"""
    path = NOTES / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    title, _, text = text.partition("\n")
    title = furigana(title.lstrip("# ").strip())
    html = markdown.markdown(furigana(text), extensions=["tables"])
    media = {}

    def link(m):
        src = (path.parent / m[2]).resolve()
        media[f"_{src.name}"] = src
        return f'<img alt="{m[1]}" src="_{src.name}">'

    html = IMG.sub(link, html)
    html = f'<details class="explanation"><summary>{title}</summary>{html}</details>'
    return html.replace("\n", ""), media


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write to Anki")
    args = ap.parse_args()

    EXPLANATIONS = explanations()
    rendered = {name: render(name) for name in EXPLANATIONS}
    empty = sorted(p.stem for p in NOTES.glob("*.md") if is_empty(p))
    if empty:
        print(f"{len(empty)} empty notes, not pushed yet: {', '.join(empty)}")
    unused = sorted(p.stem for p in NOTES.glob("*.md")
                    if p.stem not in EXPLANATIONS and p.stem not in USED_ELSEWHERE and p.stem not in empty)
    if unused:
        print(f"!! not a form and not in EXTRA (not pushed): {', '.join(unused)}")

    if args.apply:
        ensure_model()  # makes sure the Explanation field and template exist

    # A card gets every explanation whose search matches it, in EXPLANATIONS order.
    fields = {}
    for name, query in EXPLANATIONS.items():
        html, media = rendered[name]
        ids = anki("findNotes", query=query)
        print(f"{name}: {len(ids)} notes, {len(html)} chars, images: {', '.join(media) or '-'}")
        for nid in ids:
            fields[nid] = fields.get(nid, "") + html
        if args.apply:
            for fname, src in media.items():
                anki("storeMediaFile", filename=fname, data=base64.b64encode(src.read_bytes()).decode())

    if not args.apply:
        print("dry run, use --apply")
        return

    ids = anki("findNotes", query=f'"note:{NOTE_TYPE}"')
    infos = anki("notesInfo", notes=ids)
    changed = [(i["noteId"], fields.get(i["noteId"], "")) for i in infos
               if i["fields"]["Explanation"]["value"] != fields.get(i["noteId"], "")]
    actions = [{"action": "updateNoteFields", "params": {"note": {"id": nid, "fields": {"Explanation": v}}}}
               for nid, v in changed]
    for i in range(0, len(actions), 500):
        anki("multi", actions=actions[i:i + 500])
    print(f"{len(changed)} notes updated")


if __name__ == "__main__":
    main()
