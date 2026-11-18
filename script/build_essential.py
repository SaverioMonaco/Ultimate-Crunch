"""Mark the most common verbs as essential, in data/verbs.tsv.

How common a verb is comes from Tatoeba (data/raw/jpn_sentences.tsv.bz2,
see download.sh): every Japanese sentence is split into words with fugashi,
and each verb is counted under its dictionary form, as written (食べる, わかる).
- Helper uses after て/で are not counted (食べている is not a use of いる).
- A verb spelled in kanji also gets the times it was written in kana, unless
  another verb in the list has the same reading (かえる: 帰る or 変える?).
- 勉強する and the other noun + する verbs are counted as the noun followed by する.

The ESSENTIAL most common verbs get essential = 1 and their cards are tagged
UC::essential by push_notes.py (about 30% of the deck). The script writes two
columns: freq (the count) and essential. Both can be edited by hand afterwards;
rerunning this script overwrites them (and build_verbs.py drops them).

Usage:
    python script/build_essential.py
"""
import bz2
import csv
from collections import Counter
from pathlib import Path

from fugashi import Tagger

ROOT = Path(__file__).resolve().parent.parent
SENTENCES = ROOT / "data" / "raw" / "jpn_sentences.tsv.bz2"
TSV = ROOT / "data" / "verbs.tsv"

ESSENTIAL = 100
# Other spellings counted for a verb (written in kana in the deck).
ALSO = {"もらう": ["貰う"]}
# Counts that belong to another verb: kana つく is mostly 付く (気がつく),
# but the deck's つく is 点く "to be started".
NEVER = {"つく"}


def count_verbs():
    """-> (Counter of verb dictionary forms, Counter of nouns before する)."""
    tagger = Tagger()
    verbs, suru = Counter(), Counter()
    with bz2.open(SENTENCES, "rt", encoding="utf-8") as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 3:
                continue
            prev = None
            for w in tagger(cols[2]):
                ft = w.feature
                if ft.pos1 == "動詞" and not (prev and prev.feature.pos1 == "助詞" and prev.surface in ("て", "で")):
                    verbs[ft.orthBase] += 1
                    if ft.orthBase in ("する", "為る") and prev and prev.feature.pos1 == "名詞":
                        suru[prev.surface] += 1
                prev = w
    return verbs, suru


def main():
    with open(TSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    verbs, suru = count_verbs()
    readings = Counter(r["reading"] for r in rows)
    for r in rows:
        spell, reading = r["verb"], r["reading"]
        if spell.endswith("する") and len(spell) > 2:
            n = suru[spell[:-2]]
        else:
            n = verbs[spell] + sum(verbs[s] for s in ALSO.get(spell, []))
            if reading != spell and readings[reading] == 1:
                n += verbs[reading]
        r["freq"] = str(n)
    ranked = sorted((r for r in rows if r["verb"] not in NEVER), key=lambda r: -int(r["freq"]))
    top = {id(r) for r in ranked[:ESSENTIAL]}
    for r in rows:
        r["essential"] = "1" if id(r) in top else ""
    fields = [k for k in rows[0] if k not in ("freq", "essential")] + ["freq", "essential"]
    with open(TSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{ESSENTIAL} essential verbs: " + " ".join(r["verb"] for r in ranked[:ESSENTIAL]))


if __name__ == "__main__":
    main()
