"""Add audio to the Ultimate Crunch notes via AnkiConnect.

- Audio: the answer (the conjugated form), spoken by edge-tts. The kana
  reading is sent, not the kanji, so 来ない is never read きない.
- ExampleAudio: the Tatoeba recording of the example sentence when one exists
  under a reusable license (credited in ExampleSrc), otherwise edge-tts.

edge-tts uses Microsoft Edge's "Read aloud" voices: free, no account, but
unofficial, so it may break if Microsoft changes things. Clips are named by
a hash of their text and stored once, so rerunning only creates what's new.

Usage (Anki must be running with AnkiConnect):
    python script/add_audio.py            # dry run: count what's missing
    python script/add_audio.py --apply    # generate and store (resumable)
"""
import argparse
import asyncio
import base64
import hashlib
import html
import json
import re
import sys
from pathlib import Path

import edge_tts
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conjugate import Verb  # noqa: E402
from verbs import load_verbs  # noqa: E402

NOTE_TYPE = "Crunch Fill"
ANKI_URL = "http://127.0.0.1:8765"
VOICE = "ja-JP-KeitaNeural"
EXAMPLE_VOICE = "ja-JP-NanamiNeural"
PARALLEL = 6
EXAMPLES = Path(__file__).resolve().parent.parent / "data" / "examples.json"

FURI = re.compile(r" ?([^ \[\]]+)\[[^\]]*\]")
TAG = re.compile(r"<[^>]+>")


def anki(action, **params):
    r = requests.post(ANKI_URL, json={"action": action, "version": 6, "params": params}).json()
    if r.get("error"):
        raise RuntimeError(f"{action}: {r['error']}")
    return r["result"]


def tts_name(text, voice):
    return f"uc_{hashlib.sha1(f'{voice}|{text}'.encode()).hexdigest()[:12]}.mp3"


async def synth(text, voice):
    data = b""
    async for chunk in edge_tts.Communicate(text, voice).stream():
        if chunk["type"] == "audio":
            data += chunk["data"]
    if not data:
        raise RuntimeError(f"edge-tts returned no audio for: {text}")
    return data


def plan():
    """-> list of (note id, field, filename, source) for every clip a note should have."""
    verbs = {f"{v.spell}|{v.reading}": v for v in load_verbs()}
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8")) if EXAMPLES.exists() else {}
    ids = anki("findNotes", query=f'"note:{NOTE_TYPE}"')
    jobs, current = [], {}
    for n in anki("notesInfo", notes=ids):
        f = current[n["noteId"]] = {k: v["value"] for k, v in n["fields"].items()}
        spell, reading, form = f["Key"].split("|")
        v: Verb = verbs.get(f"{spell}|{reading}")
        if v and v.conj(form):
            kana = v.conj(form)[1]
            jobs.append((n["noteId"], "Audio", tts_name(kana, VOICE), ("tts", kana, VOICE)))
        ex = examples.get(f["Key"])
        if f["Example"] and ex:
            if ex.get("audio"):
                aid = ex["audio"]["audio_id"]
                jobs.append((n["noteId"], "ExampleAudio", f"uc_tatoeba_{aid}.mp3", ("tatoeba", aid)))
            else:
                text = html.unescape(TAG.sub("", FURI.sub(r"\1", f["Example"])))
                jobs.append((n["noteId"], "ExampleAudio", tts_name(text, EXAMPLE_VOICE), ("tts", text, EXAMPLE_VOICE)))
    return [j for j in jobs if current[j[0]][j[1]].strip() != f"[sound:{j[2]}]"]


async def fetch(source):
    if source[0] == "tatoeba":
        r = await asyncio.to_thread(requests.get, f"https://tatoeba.org/audio/download/{source[1]}", timeout=30)
        r.raise_for_status()
        return r.content
    return await synth(source[1], source[2])


async def run(jobs):
    """Store each missing clip, and set the fields that use it as soon as it's stored."""
    have = set(anki("getMediaFilesNames", pattern="uc_*"))
    by_name = {}
    for nid, field, name, src in jobs:
        by_name.setdefault(name, (src, []))[1].append((nid, field))

    def set_fields(name):
        for nid, field in by_name[name][1]:
            anki("updateNoteFields", note={"id": nid, "fields": {field: f"[sound:{name}]"}})

    ready = [n for n in by_name if n in have]
    for name in ready:          # clips stored by an earlier, interrupted run
        set_fields(name)
    todo = [n for n in by_name if n not in have]
    print(f"{len(ready)} clips already stored, {len(todo)} to generate, {len(jobs)} fields to set")
    sem, done = asyncio.Semaphore(PARALLEL), 0

    async def one(name):
        nonlocal done
        src = by_name[name][0]
        async with sem:
            for attempt in range(3):
                try:
                    data = await fetch(src)
                    break
                except Exception as e:  # network hiccups: retry, then skip
                    if attempt == 2:
                        print(f"!! {name} {src[:2]}: {e}", flush=True)
                        return
                    await asyncio.sleep(2 * (attempt + 1))
            await asyncio.to_thread(anki, "storeMediaFile", filename=name, data=base64.b64encode(data).decode())
            await asyncio.to_thread(set_fields, name)
            done += 1
            if done % 500 == 0:
                print(f"  {done}/{len(todo)}", flush=True)

    await asyncio.gather(*(one(n) for n in todo))
    print("done")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="generate and store audio")
    args = ap.parse_args()
    jobs = plan()
    if not args.apply:
        print(f"{len(jobs)} audio fields missing or outdated (dry run, use --apply)")
        return
    asyncio.run(run(jobs))


if __name__ == "__main__":
    main()
