"""The "#answer#" convention used in the Sentence field.

The Sentence field holds the full sentence, with the part to fill in between
two markers: 君[きみ]の#名前[なまえ]#は. The card front shows it as a blank and
the back shows it in bold (see templates/). A "#" inside an HTML tag, such as
color="#333333", is not a marker.
"""
import re

MARK = "#"
TAG = re.compile(r"(<[^>]*>)")


def strip_markers(html):
    """Remove the markers, leaving tags (and any "#" inside them) untouched."""
    return "".join(p if TAG.fullmatch(p) else p.replace(MARK, "") for p in TAG.split(html))


def has_markers(html):
    return any(MARK in p for p in TAG.split(html) if not TAG.fullmatch(p))
