"""Find a Tatoeba example sentence for every (verb, form) card.

A sentence matches when it contains the exact conjugated form as a whole
word chain: 食べない matches 「もう食べない。」 but not 「食べないで」 (that is
the ないで form), and the verb's dictionary reading must match (so かける
"to hang" is not confused with a noun). Among the matches, the shortest
sentence with an English translation wins, preferring ones with reusable
Tatoeba audio. The result goes to data/examples.json, which push_notes.py
reads; delete an entry there to drop a bad example (or add "skip": true).

Usage:
    python script/build_examples.py     # ~2 minutes (tags 250k sentences)
"""
import bz2
import csv
import json
import re
import sys
import tarfile
from collections import defaultdict
from pathlib import Path

from fugashi import Tagger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conjugate import Verb, KANJI  # noqa: E402
from verbs import load_verbs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "examples.json"

MIN_LEN, MAX_LEN = 5, 32           # characters
REUSABLE = {"CC0 1.0", "CC BY 4.0", "CC BY-NC 4.0", "CC BY-SA 4.0"}
# Tokens that continue a conjugation: if one follows the match, the sentence
# has a longer form (食べ|ない|で) and does not show this one.
CONT_SURF = {"て", "で", "ば", "ちゃ", "じゃ", "たら", "たり", "だり", "ず", "ながら"}

FURI = re.compile(r" ?([^ \[\]]+)\[[^\]]*\]")


def plain(furi_text):
    return FURI.sub(r"\1", furi_text).replace(" ", "")


def kata_to_hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def load_tatoeba():
    jpn = {}
    for line in bz2.open(RAW / "jpn_sentences.tsv.bz2", "rt", encoding="utf-8"):
        i, _, text = line.rstrip("\n").split("\t", 2)
        if MIN_LEN <= len(text) <= MAX_LEN:
            jpn[i] = text
    eng = {}
    for line in bz2.open(RAW / "eng_sentences.tsv.bz2", "rt", encoding="utf-8"):
        i, _, text = line.rstrip("\n").split("\t", 2)
        eng[i] = text
    trans = {}
    with tarfile.open(RAW / "links.tar.bz2", "r:bz2") as tar:
        f = tar.extractfile("links.csv")
        for raw in f:
            a, b = raw.decode().rstrip("\n").split("\t")
            if a in jpn and b in eng:
                # Keep the shortest English translation.
                if a not in trans or len(eng[b]) < len(trans[a][1]):
                    trans[a] = (b, eng[b])
    audio = {}
    for row in csv.reader(open(RAW / "sentences_with_audio.csv", encoding="utf-8"), delimiter="\t"):
        sid, aid, user, lic = row[0], row[1], row[2], row[3]
        if sid in jpn and lic in REUSABLE and sid not in audio:
            audio[sid] = {"audio_id": aid, "user": user, "license": lic}
    return jpn, trans, audio


CAN = re.compile(r"\b(can|could|able|cannot|can't|couldn't)\b", re.I)


def english_fits(v, key, en):
    """る-verbs (and 来る) have identical potential and passive forms: 見られる is
    "can see" or "is seen". Use the English translation to tell them apart."""
    if v.cls not in ("v1", "vk") or key not in ("pot", "potnai", "passive"):
        return True
    return bool(CAN.search(en)) == (key != "passive")


def main():
    verbs = load_verbs()
    # plain surface of every card -> [(verb index, form key)]
    want = defaultdict(list)
    for vi, v in enumerate(verbs):
        for key in v.forms():
            want[plain(v.conj(key)[0])].append((vi, key))
    longest = max(map(len, want))

    print("loading Tatoeba...", file=sys.stderr)
    jpn, trans, audio = load_tatoeba()
    print(f"{len(trans)} Japanese sentences with an English translation", file=sys.stderr)

    tagger = Tagger()
    best = {}
    for n, (sid, (eid, en)) in enumerate(trans.items()):
        if n % 20000 == 0:
            print(f"  {n}/{len(trans)}", file=sys.stderr)
        text = jpn[sid]
        toks = list(tagger(text))
        for i, t in enumerate(toks):
            if i and (toks[i - 1].feature.pos1 == "動詞" or toks[i - 1].surface in ("て", "で")):
                continue  # 思い|出す, 下がって|いろ: the match is part of another verb
            surf = ""
            for j in range(i, len(toks)):
                surf += toks[j].surface
                if len(surf) > longest:
                    break
                if surf not in want:
                    continue
                nxt = toks[j + 1] if j + 1 < len(toks) else None
                if nxt is not None and (nxt.surface in CONT_SURF or nxt.feature.pos1 == "助動詞"
                                        or nxt.feature.pos2 == "非自立可能" and nxt.feature.pos1 in ("動詞", "形容詞")):
                    continue
                for vi, key in want[surf]:
                    v = verbs[vi]
                    lemma_r = kata_to_hira(getattr(t.feature, "lForm", "") or "")
                    if t.feature.pos1 == "動詞" and lemma_r and lemma_r != v.reading:
                        continue  # same spelling, other verb
                    if v.cls == "vs-i" and len(v.reading) > 2 and t.feature.pos1 == "動詞":
                        continue
                    if not english_fits(v, key, en):
                        continue
                    score = (sid not in audio, len(text), len(en))
                    k = f"{v.spell}|{v.reading}|{key}"
                    if k not in best or score < best[k]["score"]:
                        best[k] = {"score": score, "id": sid, "ja": text, "en": en, "en_id": eid,
                                   "match": surf, "audio": audio.get(sid)}
    for b in best.values():
        del b["score"]
    OUT.write_text(json.dumps(dict(sorted(best.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v.forms()) for v in verbs)
    with_audio = sum(1 for b in best.values() if b["audio"])
    print(f"{len(best)}/{total} cards have an example ({with_audio} with Tatoeba audio) -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
