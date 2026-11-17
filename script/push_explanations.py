"""Copy the explanations in notes/*.md into the notes' Explanation field.

Each Markdown file is turned into HTML:
- the "# title" line becomes the title of a collapsed <details> section;
- furigana uses the card syntax, 帰[かえ]る -> <ruby>;
- an image like ![...](../tex/name.svg) is uploaded to Anki's media folder as
  _name.svg (the leading "_" keeps "Check Media" from deleting it) and linked.

EXPLANATIONS says which file goes on which cards, as an Anki search. Edit the
files, never the Explanation field in Anki: rerunning overwrites it.

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
from push_notes import NOTE_TYPE, anki, ensure_model  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes"

# notes/<file>.md -> the cards that show it (an Anki search)
EXPLANATIONS = {
}
# Notes used by another script instead (not pushed here).
USED_ELSEWHERE = {"n5-verbclassification": "recognize.py (the exceptions table)"}

FURI = re.compile(r"([一-鿿々〆]+)\[([^\]]+)\]")
IMG = re.compile(r'<img alt="([^"]*)" src="([^"]+)"\s*/?>')


def render(name):
    """-> (html, {media name: local path})"""
    path = NOTES / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    title, _, text = text.partition("\n")
    title = FURI.sub(r"<ruby>\1<rt>\2</rt></ruby>", title.lstrip("# ").strip())
    html = markdown.markdown(FURI.sub(r"<ruby>\1<rt>\2</rt></ruby>", text), extensions=["tables"])
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

    rendered = {name: render(name) for name in EXPLANATIONS}
    unused = sorted(p.stem for p in NOTES.glob("*.md") if p.stem not in EXPLANATIONS and p.stem not in USED_ELSEWHERE)
    if unused:
        print(f"!! not in EXPLANATIONS (not pushed): {', '.join(unused)}")

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
