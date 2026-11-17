"""Read data/verbs.tsv (see build_verbs.py) into conjugate.Verb objects."""
import csv
from pathlib import Path

from conjugate import Verb

TSV = Path(__file__).resolve().parent.parent / "data" / "verbs.tsv"


def load_verbs():
    with open(TSV, encoding="utf-8") as f:
        return [Verb(r["verb"], r["reading"], r["class"], r["trans"], r["english"], int(r["level"][1]))
                for r in csv.DictReader(f, delimiter="\t")]
