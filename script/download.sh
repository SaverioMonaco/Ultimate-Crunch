#!/bin/sh
# Download the sources into data/raw/ (about 200 MB, not committed).
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)/data/raw"
mkdir -p "$DIR" && cd "$DIR"

for l in n5 n4 n3; do
  curl -sL -o $l.csv https://raw.githubusercontent.com/jamsinclair/open-anki-jlpt-decks/main/src/$l.csv
done

url=$(curl -s https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest \
  | grep -o 'https://[^"]*jmdict-eng-common-[^"]*json.zip' | head -1)
curl -sL -o jmdict.zip "$url" && unzip -o -q jmdict.zip && rm jmdict.zip

T=https://downloads.tatoeba.org/exports
curl -sL -o jpn_sentences.tsv.bz2 $T/per_language/jpn/jpn_sentences.tsv.bz2
curl -sL -o eng_sentences.tsv.bz2 $T/per_language/eng/eng_sentences.tsv.bz2
curl -sL -o links.tar.bz2 $T/links.tar.bz2
curl -sL $T/sentences_with_audio.tar.bz2 | tar -xj
echo "done: $(pwd)"
