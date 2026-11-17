"""How a form is built, step by step, and its HTML for the back of the card.

    売る (dictionary form)
     ↓ a-sound: る → ら
    売ら
     ↓ + ない
    売らない
     ↓ past: ない → なかった
    売らなかった

steps(verb, key) gives the chain; steps_html() draws it as boxes and arrows
(styled by templates/style.css, .steps). push_notes.py puts the HTML in the
Conjugation field, so rerunning push_notes.py regenerates every card.

Usage:
    python script/steps.py 売る nakatta          # print the chain
    python script/steps.py 売る                  # every form of 売る
    python script/steps.py 売る nakatta --html   # the HTML that goes on the card
    python script/steps.py --check               # every verb and form: the last
                                                 # step must equal the conjugation
"""
import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conjugate import FORM, HUMBLE, KEIGO, ROWS  # noqa: E402

SOUNDS = {"a": 0, "i": 1, "e": 2, "o": 3}
TE_GROUP = {"う": "う, つ, る → って", "つ": "う, つ, る → って", "る": "う, つ, る → って",
            "ぬ": "ぬ, ぶ, む → んで", "ぶ": "ぬ, ぶ, む → んで", "む": "ぬ, ぶ, む → んで",
            "く": "く → いて", "ぐ": "ぐ → いで", "す": "す → して"}


class Chain:
    """The steps so far: [(furigana, kana, how we got here, part to highlight)]."""

    def __init__(self, v):
        self.v, self.b = v, v.bases()
        self.kind = self.b["type"]
        self.out = [(v.word, v.reading, "dictionary form", "")]
        if v.cls == "vs-s":   # 愛する conjugates like 愛す
            self.swap("する", "す", "〜する like 愛する conjugates like a す-verb")

    @property
    def cur(self):
        return self.out[-1][:2]

    def push(self, wr, label, tail=""):
        self.out.append((wr[0], wr[1], label, tail))

    def add(self, s, label=None):
        w, r = self.cur
        self.push((w + s, r + s), label or f"+ {s}", s)

    def swap(self, old, new, label=None):
        """Replace the kana ending `old` by `new`."""
        w, r = self.cur
        assert r.endswith(old) and w.endswith(old), (w, r, old)
        self.push((w[:len(w) - len(old)] + new, r[:len(r) - len(old)] + new), label or f"{old} → {new}", new)

    def whole(self, key, label):
        """Irregular forms that are not built from a stem (する → できる)."""
        self.push(self.b[key], label)

    def stem(self, sound):
        """Dictionary form -> the a/i/e/o stem."""
        v, k = self.v, self.kind
        if k == "ichidan":
            self.swap("る", "", "drop る")
        elif k in ("suru", "kuru"):
            base = self.cur[1][:-2]
            got = self.b[sound]
            self.push(got, f"{'する' if k == 'suru' else 'くる'} → {got[1][len(base):]}")
        elif v.cls == "v5aru" and sound == "i":
            self.swap("る", "い", "special: る → い (not り)")
        else:
            end = self.cur[1][-1]
            self.swap(end, ROWS[end][SOUNDS[sound]], f"{sound}-sound: {end} → {ROWS[end][SOUNDS[sound]]}")

    def negative(self):
        """-> ...ない"""
        if self.v.cls == "v5r-i":
            self.push(("ない", "ない"), "special: ある → ない", "ない")
        else:
            self.stem("a")
            self.add("ない")

    def te(self, ta=False):
        """-> て-form (or た-form): same rule, only the last kana differs."""
        v, k = self.v, self.kind
        t = "た" if ta else "て"
        if k == "ichidan":
            self.swap("る", "", "drop る")
            self.add(t)
        elif k in ("suru", "kuru"):
            got = self.b["ta" if ta else "te"]
            self.push(got, f"{'する' if k == 'suru' else 'くる'} → {got[1][len(self.cur[1]) - 2:]}")
        elif v.cls == "v5k-s":
            self.swap("く", "っ" + t, f"行く is special: く → っ{t} (not い{t})")
        elif v.cls == "v5u-s":
            self.add(t, f"問う is special: + {t}")
        else:
            end = self.cur[1][-1]
            new = self.b["ta" if ta else "te"][1][len(self.cur[1]) - 1:]
            rule = TE_GROUP[end].replace("て", t).replace("で", "だ" if ta else "で")
            self.swap(end, new, f"{t}-form: {rule}")


def steps(v, key):
    """-> [(furigana, kana, label, highlight)], first the dictionary form."""
    c = Chain(v)
    k = c.kind
    irr = k in ("suru", "kuru")
    name = "する" if k == "suru" else "くる"

    if key in ("masu", "masen", "mashita", "mashou", "tai", "nagara"):
        c.stem("i")
        c.add({"masu": "ます", "masen": "ません", "mashita": "ました", "mashou": "ましょう",
               "tai": "たい", "nagara": "ながら"}[key])
    elif key == "masendeshita":
        c.stem("i")
        c.add("ません")
        c.add("でした", "past: + でした")
    elif key == "nai":
        c.negative()
    elif key == "nakatta":
        c.negative()
        c.swap("ない", "なかった", "past: ない → なかった (like an い-adjective)")
    elif key == "nakereba":
        c.negative()
        c.swap("ない", "なければ", "if not: ない → なければ")
        c.add("ならない", "+ ならない (it won't do)")
    elif key == "naidekudasai":
        c.stem("a")
        c.add("ないで")
        c.add("ください")
    elif key in ("te", "ta"):
        c.te(ta=key == "ta")
    elif key in ("teiru", "tekudasai"):
        c.te()
        c.add("いる" if key == "teiru" else "ください")
    elif key in ("tara", "tari"):
        c.te(ta=True)
        c.add("ら" if key == "tara" else "り")
    elif key in ("pot", "potnai"):
        if k == "godan":
            c.stem("e")
            c.add("る")
        elif k == "ichidan":
            c.stem("a")
            c.add("られる")
        else:
            c.whole("pot", f"irregular: {name} → {c.b['pot'][1][len(v.reading) - 2:]}")
        if key == "potnai":
            c.swap("る", "ない", "the potential is an ichidan verb: る → ない")
    elif key == "vol":
        if k == "godan":
            c.stem("o")
            c.add("う")
        elif k == "ichidan":
            c.stem("o")
            c.add("よう")
        else:
            c.whole("vol", f"irregular: {name} → {c.b['vol'][1][len(v.reading) - 2:]}")
    elif key == "ba":
        if k == "godan":
            c.stem("e")
            c.add("ば")
        elif k == "ichidan":
            c.stem("e")
            c.add("れば")
        else:
            c.whole("ba", f"{name} → {c.b['ba'][1][len(v.reading) - 2:]}")
    elif key == "imp":
        if k == "godan":
            c.stem("e")
            c.out[-1] = (*c.out[-1][:2], "command: " + c.out[-1][2], c.out[-1][3])
        elif k == "ichidan":
            c.stem("e")
            if v.spell == "くれる":
                c.out[-1] = (*c.out[-1][:2], "drop る (くれる is special: no ろ)", "")
            else:
                c.add("ろ")
        else:
            c.whole("imp", f"irregular: {name} → {c.b['imp'][1][len(v.reading) - 2:]}")
    elif key == "proh":
        c.add("な", "+ な (dictionary form + な)")
    elif key in ("passive", "caus", "causpass"):
        if irr:
            c.whole(key, f"irregular: {name} → {c.b[key][1][len(v.reading) - 2:]}")
        else:
            c.stem("a")
            if k == "ichidan":
                c.add({"passive": "られる", "caus": "させる", "causpass": "させられる"}[key])
            elif key == "causpass":
                if c.cur[1].endswith("さ"):   # す-verbs keep the long form
                    c.add("せられる")
                else:
                    c.add("される", "+ される (short for せられる)")
            else:
                c.add("れる" if key == "passive" else "せる")
    elif key == "zuni":
        if k == "suru":
            c.whole("zu", "する → せず")
        else:
            c.stem("a")
            c.add("ず")
        c.add("に")
    elif key in ("honor", "humble"):
        table = KEIGO if key == "honor" else HUMBLE
        what = "honorific" if key == "honor" else "humble"
        if table[v.spell]:
            c.push(table[v.spell], f"special {what} verb")
        else:
            c.stem("i")
            final = v.conj(key)
            c.push(final, f"お + stem + {'になる' if key == 'honor' else 'する'}")
    else:
        raise KeyError(key)
    return c.out


# --- HTML ------------------------------------------------------------------

FURI = re.compile(r"\s?([一-鿿々〆ヶ]+)\[([^\]]+)\]")


def ruby(text):
    return FURI.sub(r"<ruby>\1<rt>\2</rt></ruby>", text)


def word_html(w, tail):
    if tail and w.endswith(tail):
        return ruby(w[:-len(tail)]) + f"<b>{html.escape(tail)}</b>"
    return ruby(w)


def steps_html(v, key):
    chain = steps(v, key)
    parts = ['<div class="steps">']
    for n, (w, _, label, tail) in enumerate(chain):
        if n:
            parts.append(f'<div class="arrow">↓ <span>{ruby(html.escape(label, quote=False))}</span></div>')
        cls = "step last" if n == len(chain) - 1 else "step"
        parts.append(f'<div class="{cls}">{word_html(w, tail if n else "")}</div>')
    parts.append("</div>")
    return "".join(parts)


# --- CLI -------------------------------------------------------------------

def check(verbs):
    bad = 0
    for v in verbs:
        for key in v.forms():
            want = v.conj(key)
            got = steps(v, key)[-1][:2]
            if got[1] != want[1] or got[0].replace(" ", "") != want[0].replace(" ", ""):
                bad += 1
                print(f"!! {v.spell} {key}: steps give {got}, conj gives {want}")
    print(f"{sum(len(v.forms()) for v in verbs)} forms checked, {bad} mismatches")
    return bad


def main():
    from verbs import load_verbs
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("verb", nargs="?", help="dictionary form, as in data/verbs.tsv")
    ap.add_argument("forms", nargs="*", help=f"form keys: {', '.join(FORM)}")
    ap.add_argument("--html", action="store_true", help="print the card HTML")
    ap.add_argument("--check", action="store_true", help="check every verb and form")
    args = ap.parse_args()

    verbs = load_verbs()
    if args.check:
        sys.exit(1 if check(verbs) else 0)
    if not args.verb:
        ap.error("give a verb, or --check")
    found = [v for v in verbs if args.verb in (v.spell, v.reading)]
    if not found:
        ap.error(f"{args.verb} is not in data/verbs.tsv")
    for v in found:
        for key in args.forms or v.forms():
            if key not in v.forms():
                print(f"{v.spell}: no {key} card")
                continue
            print(f"== {v.spell} ({v.reading}) {key}: {FORM[key].mod}")
            if args.html:
                print(steps_html(v, key))
                continue
            for n, (w, r, label, _) in enumerate(steps(v, key)):
                if n:
                    print(f"   ↓ {label}")
                print(f"   {r}")


if __name__ == "__main__":
    main()
