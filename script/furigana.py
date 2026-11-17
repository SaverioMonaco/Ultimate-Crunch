"""Furigana for example sentences: 私[わたし]は 本[ほん]を 読[よ]む (Anki syntax).

Copied from Ultimate-Grammar's add_furigana.py (only the annotating part)."""
import re

from fugashi import Tagger

from markers import MARK


tagger = Tagger()
KANJI = re.compile(r"[一-鿿々〆]")
TAG = re.compile(r"(<[^>]+>)")



def kata_to_hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def split_okurigana(surface, reading):
    """Return (prefix_kana, kanji_core, core_reading, suffix_kana)."""
    pre = ""
    while surface and reading and not KANJI.match(surface[0]) and surface[0] == reading[0]:
        pre += surface[0]
        surface, reading = surface[1:], reading[1:]
    suf = ""
    while surface and reading and not KANJI.match(surface[-1]) and surface[-1] == reading[-1]:
        suf = surface[-1] + suf
        surface, reading = surface[:-1], reading[:-1]
    return pre, surface, reading, suf


def annotate_text(text, prev_char):
    out = ""
    for tok in tagger(text):
        surf = tok.surface
        kana = getattr(tok.feature, "kana", None)
        if not KANJI.search(surf) or not kana or kana == "*":
            out += surf
            prev_char = surf[-1] if surf else prev_char
            continue
        reading = kata_to_hira(kana)
        pre, core, core_r, suf = split_okurigana(surf, reading)
        out += pre
        if pre:
            prev_char = pre[-1]
        if out and not out.endswith((" ", ">")) and prev_char not in ("", " ", ">"):
            out += " "
        elif not out and prev_char not in ("", " ", ">"):
            out += " "
        out += f"{core}[{core_r}]{suf}"
        prev_char = suf[-1] if suf else "]"
    return out


def annotate(html):
    if "[" in html and "]" in html and KANJI.search(html):
        return html  # already has furigana, leave alone
    parts = TAG.split(html)
    result, prev = "", ""
    for p in parts:
        if TAG.fullmatch(p):
            result += p
            prev = ">"
        elif p:
            # A "#" marker is a boundary, like a tag: no furigana space after it.
            for i, seg in enumerate(p.split(MARK)):
                if i:
                    result += MARK
                    prev = ">"
                if seg:
                    piece = annotate_text(seg, prev)
                    result += piece
                    prev = piece[-1] if piece else prev
    return result
