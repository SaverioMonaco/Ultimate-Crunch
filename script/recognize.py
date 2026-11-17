"""The "How to recognize" flowchart, as HTML, with the card's verb's path lit up.

    [ 帰る ]
       ↓
    [ する or 来る? ] ── yes → [ Irregular ]
       ↓ no
    [ Ends in る? ] ──── no → [ Godan ]
       ↓ yes
    [ Sound before る? ] ─ i, e → [ Ichidan ] ── exception → [ Godan ]
       ↓ a, u, o
    [ Godan ]

Every card gets the whole chart; the boxes and arrows its verb goes through
are highlighted, the others dimmed. Under it comes the table of exceptions,
taken from notes/n5-verbclassification.md (the verb is marked if it is in it).
Styled by templates/style.css (.flow). push_notes.py puts the HTML in the
Recognition field, so rerunning push_notes.py regenerates every card.

Usage:
    python script/recognize.py 帰る           # the path, as text
    python script/recognize.py 帰る --html    # the HTML that goes on the card
"""
import argparse
import html
import re
import sys
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
NOTE = ROOT / "notes" / "n5-verbclassification.md"
FURI = re.compile(r"\s?([一-鿿々〆ヶ]+)\[([^\]]+)\]")

VOWEL = {}
for vowel, kana in {"a": "あかがさざただなはばぱまやらわぁゃ", "i": "いきぎしじちぢにひびぴみりぃ",
                    "u": "うくぐすずつづぬふぶぷむゆるぅゅ", "e": "えけげせぜてでねへべぺめれぇ",
                    "o": "おこごそぞとどのほぼぽもよろをぉょ"}.items():
    for k in kana:
        VOWEL[k] = vowel


def ruby(text):
    return FURI.sub(r"<ruby>\1<rt>\2</rt></ruby>", text)


def path(v):
    """-> (set of lit node/arrow ids, the sound before る or None).

    Nodes: start, q1 (する/来る?), q2 (ends in る?), q3 (sound before る?),
    irr, godan1 (not る), ichidan, godan2 (a/u/o), exc (exception: godan).
    Arrows are named after the two nodes they join.
    """
    r = v.reading
    if v.cls in ("vs-i", "vk"):
        return {"start", "start-q1", "q1", "q1-irr", "irr"}, None
    if v.cls == "vs-s":   # 愛する conjugates like 愛す: not ending in る
        return {"start", "start-q1", "q1", "q1-q2", "q2", "q2-godan1", "godan1"}, None
    lit = {"start", "start-q1", "q1", "q1-q2", "q2"}
    if not r.endswith("る"):
        return lit | {"q2-godan1", "godan1"}, None
    lit |= {"q2-q3", "q3"}
    sound = VOWEL.get(r[-2]) if len(r) > 1 else None
    if sound in ("i", "e"):
        lit |= {"q3-ichidan", "ichidan"}
        if v.cls.startswith("v5"):
            lit |= {"ichidan-exc", "exc"}
    else:
        lit |= {"q3-godan2", "godan2"}
    return lit, sound


def answer(v, lit):
    for node, name in (("exc", "Godan (exception)"), ("irr", "Irregular"), ("ichidan", "Ichidan"),
                       ("godan1", "Godan"), ("godan2", "Godan")):
        if node in lit:
            return name


def exceptions_table(v):
    """The table in notes/n5-verbclassification.md, the card's verb in bold."""
    text = NOTE.read_text(encoding="utf-8")
    text = re.sub(r"\A#[^\n]*\n", "", text)              # title
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)\n?", "", text)   # the SVG (for GitHub only)
    text = re.sub(rf"(?<=[|,] ){re.escape(v.word.replace(' ', ''))}(?=,| \|)", f"**{v.word.replace(' ', '')}**", text)
    # Keep the space after commas: only the card's "思[おも]い 出[だ]す" spaces are dropped.
    text = re.sub(r"([一-鿿々〆ヶ]+)\[([^\]]+)\]", r"<ruby>\1<rt>\2</rt></ruby>", text)
    return markdown.markdown(text, extensions=["tables"]).replace("\n", "")


def recognize_html(v):
    lit, sound = path(v)
    on = lambda key: " on" if key in lit else ""

    def node(key, body, kind="q"):
        return f'<div class="node {kind}{on(key)}">{body}</div>'

    def side(arrow, label, target, body, kind):
        return (f'<div class="side"><span class="link{on(arrow)}">{label} →</span>'
                f'{node(target, body, kind)}</div>')

    def down(arrow, label=""):
        return f'<div class="down{on(arrow)}">↓ {label}</div>'

    word = ruby(v.word)
    if sound:
        # 帰る: show the sound that decides, in the reading
        r = v.reading
        q3_extra = f'<small>{html.escape(r[:-2])}<b>{r[-2]}</b>る → <b>{sound}</b></small>'
    else:
        q3_extra = ""
    special = ""
    if v.cls == "vs-s":
        special = '<small>〜する verbs like 愛する conjugate like 〜す</small>'

    rows = [
        f'<div class="row">{node("start", f"{word}<small>dictionary form</small>")}</div>',
        down("start-q1"),
        f'<div class="row">{node("q1", f"Is it <b>する</b> or <b>{ruby("来[く]る")}</b>?{special}")}'
        + side("q1-irr", "yes", "irr", f'Irregular<small>{ruby("不規則[ふきそく]動詞[どうし]")}</small>', "a irr")
        + "</div>",
        down("q1-q2", "no"),
        f'<div class="row">{node("q2", "Does it end in <b>る</b>?")}'
        + side("q2-godan1", "no", "godan1", f'Godan<small>{ruby("五段[ごだん]動詞[どうし]")}</small>', "a godan")
        + "</div>",
        down("q2-q3", "yes"),
        # The exception hangs under the Ichidan box: i, e → Ichidan ↓ unless... → Godan
        f'<div class="row top">{node("q3", f"Sound before <b>る</b>?{q3_extra}")}'
        f'<div class="side top"><span class="link{on("q3-ichidan")}">i, e →</span>'
        f'<div class="branch">'
        + node("ichidan", f'Ichidan<small>{ruby("一段[いちだん]動詞[どうし]")}</small>', "a ichidan")
        + down("ichidan-exc", "unless in the table")
        + node("exc", 'Godan<small>exception</small>', "a godan")
        + "</div></div></div>",
        down("q3-godan2", "a, u, o"),
        f'<div class="row">{node("godan2", f"Godan<small>{ruby("五段[ごだん]動詞[どうし]")}</small>", "a godan")}</div>',
    ]
    result = f'<div class="verdict">{word} → <b>{answer(v, lit)}</b></div>'
    return f'<div class="flow">{"".join(rows)}</div>{result}{exceptions_table(v)}'


def main():
    from verbs import load_verbs
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("verb", help="dictionary form, as in data/verbs.tsv")
    ap.add_argument("--html", action="store_true", help="print the card HTML")
    args = ap.parse_args()
    found = [v for v in load_verbs() if args.verb in (v.spell, v.reading)]
    if not found:
        ap.error(f"{args.verb} is not in data/verbs.tsv")
    for v in found:
        if args.html:
            print(recognize_html(v))
            continue
        lit, sound = path(v)
        order = ["start", "q1", "irr", "q2", "godan1", "q3", "ichidan", "exc", "godan2"]
        print(f"{v.spell} ({v.reading}, {v.cls}): " + " → ".join(n for n in order if n in lit)
              + (f"  [sound before る: {sound}]" if sound else "") + f"  = {answer(v, lit)}")


if __name__ == "__main__":
    main()
