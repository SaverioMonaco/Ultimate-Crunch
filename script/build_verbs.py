"""Build data/verbs.tsv: the JLPT N5-N3 verbs, with their conjugation class.

Sources (download them first with script/download.sh):
- JLPT word lists (jamsinclair/open-anki-jlpt-decks, based on tanos.co.uk)
  give the level, the spelling, the reading and an English gloss.
- JMdict (scriptin/jmdict-simplified) gives the verb class: v1 (る-verb),
  v5k/v5s/... (う-verb with its ending), vk (来る), vs-i (する), and whether
  the verb is transitive (vt) or intransitive (vi).

The TSV is meant to be edited by hand afterwards (fix a gloss, drop a verb,
change the level): push_notes.py reads it, not the raw sources. Rerunning
this script overwrites it, so only rerun it to start over.

Usage:
    python script/build_verbs.py
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "verbs.tsv"

VERB_POS = re.compile(r"^(v1|v1-s|v5.*|vk|vs-i|vs-s|vz)$")
# Entries in the JLPT lists that are verbs on paper but not worth drilling.
SKIP = {"ございます", "欲しい"}
# Written in kanji even though JMdict says "usually kana", so they don't look
# identical to another verb with a different conjugation (いる "to be", v1).
KEEP_KANJI = {"要る"}
SPECIAL = {"v5k-s", "v5r-i", "v5aru", "v5u-s", "vs-i", "vs-s", "vk", "vz"}
IRU_ERU = re.compile(r"[いきしちにひみりぎじびぴえけせてねへめれげぜでべぺ]る$")


def jmdict_index():
    jm = json.loads(next(RAW.glob("jmdict-eng-common-*.json")).read_text(encoding="utf-8"))
    idx = defaultdict(list)
    for w in jm["words"]:
        pos = [p for s in w["sense"] for p in s["partOfSpeech"]]
        cls = [p for p in dict.fromkeys(pos) if VERB_POS.match(p)]
        has_vs = "vs" in pos
        trans = ("vt" in pos, "vi" in pos)
        if not cls and not has_vs:
            continue
        kanji = [k["text"] for k in w["kanji"]]
        uk = all("uk" in s["misc"] for s in w["sense"][:1])
        common = [k["text"] for k in w["kanji"] if k["common"]]
        for r in w["kana"]:
            # How the verb is normally written: kana if JMdict says "usually
            # kana" (ある, する), else its first common kanji spelling (終わる).
            spell = r["text"] if uk or not kanji else (common or kanji)[0]
            entry = {"cls": cls, "vs": has_vs, "trans": trans, "spell": spell}
            for k in kanji:
                idx[(k, r["text"])].append(entry)
            idx[(r["text"], r["text"])].append(entry)  # kana spelling of any entry
    return idx


def classify(expr, reading, idx):
    """-> (spelling, reading, class, transitivity) or None if it is not a verb."""
    hits = idx.get((expr, reading))
    if hits:
        cls = [c for h in hits for c in h["cls"]]
        if cls:
            special = [c for c in cls if c in SPECIAL]
            if special:
                c = special[0]  # 行く (v5k-s), ある (v5r-i), いらっしゃる (v5aru)...
            elif "v1" in cls and IRU_ERU.search(reading):
                c = "v1"  # 駆ける: v1 and v5r, the common reading is v1
            else:
                c = next((c for c in cls if c.startswith("v5")), cls[0])
            t = tuple(any(h["trans"][i] for h in hits) for i in (0, 1))
            spell = expr if expr in KEEP_KANJI else hits[0]["spell"]
            return spell, reading, c, t
    # "勉強する", "コピーする": a する-noun + する.
    if expr.endswith("する") and len(expr) > 2:
        noun, nread = expr[:-2], reading[:-2]
        h = idx.get((noun, nread)) or idx.get((nread, nread))
        if h and any(x["vs"] for x in h):
            t = h[0]["trans"]
            return expr, reading, "vs-i", t
        return expr, reading, "vs-i", (False, False)
    return None


def main():
    idx = jmdict_index()
    rows, seen = [], set()
    for level in (5, 4, 3):
        with open(RAW / f"n{level}.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                expr = row["expression"].strip()
                reading = row["reading"].split(";")[0].strip()
                if expr.startswith(("～", "~")) or expr in SKIP:
                    continue
                if not re.sub(r"^\(\w+\)\s*", "", row["meaning"].strip()).startswith("to "):
                    continue  # nouns that JMdict also marks as する-able, adjectives...
                got = classify(expr, reading, idx)
                if not got or got[:2] in seen:
                    continue  # 在る and 有る are both ある
                seen.add(got[:2])
                expr, reading, cls, (vt, vi) = got
                trans = "vt" if vt and not vi else "vi" if vi and not vt else "vt,vi" if vt else ""
                rows.append([f"N{level}", expr, reading, cls, trans, gloss(row["meaning"])])

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["level", "verb", "reading", "class", "trans", "english"])
        w.writerows(rows)
    by = defaultdict(int)
    for r in rows:
        by[r[0]] += 1
    print(f"{len(rows)} verbs -> {OUT.relative_to(ROOT)}  ({dict(by)})")


def gloss(meaning):
    """'to meet, to see' -> 'to meet'; keeps one short sense, drops '(v.t.)' style notes."""
    meaning = re.sub(r"^\((humble|honorific|polite)\)\s*", "", meaning.strip())
    first = re.split(r"[;,]\s*(?=to )", meaning)[0]
    first = re.sub(r"\s*\((v\.?t\.?|v\.?i\.?|vt|vi)\)", "", first).strip().rstrip(",;")
    return first


if __name__ == "__main__":
    main()
