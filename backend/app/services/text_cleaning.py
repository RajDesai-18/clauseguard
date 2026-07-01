"""Repair mojibake in extracted document text.

Text pulled from some PDFs arrives double-decoded: UTF-8 bytes interpreted as
Windows-1252, so a curly apostrophe (UTF-8 ``E2 80 99``) surfaces as ``â€™``.
ftfy reverses the vast majority of these automatically.

A few smart-quote sequences can't be fully recovered by ftfy alone, because the
original mis-decode passed a byte Windows-1252 doesn't define (e.g. ``0x9D`` for
a closing double quote), losing information. Those are patched by an explicit
pre-map that runs BEFORE ftfy, while the distinguishing bytes still exist.

Clean text is returned unchanged, so this is safe to run over every parsed
document and over already-stored rows.
"""

from __future__ import annotations

import ftfy

# Smart-quote / dash sequences ftfy can't reliably reverse on its own because
# the original bad decode dropped or mangled a byte. Applied BEFORE ftfy so the
# distinguishing bytes are still present. Keys are the observed broken forms.
_PRE_MAP = {
    "\u00e2\u20ac\u009d": "\u201d",  # â€ + U+009D         -> ” right double quote
    "\u00e2\u20ac\udc9d": "\u201d",  # â€ + lone surrogate -> ” right double quote
    "\u00e2\u20ac\u0153": "\u201c",  # â€œ                 -> “ left double quote
    "\u00e2\u20ac\u2122": "\u2019",  # â€™                 -> ’ right single quote
    "\u00e2\u20ac\u201c": "\u2013",  # en dash
    "\u00e2\u20ac\u201d": "\u2014",  # em dash
}


def fix_mojibake(text: str) -> str:
    """Repair mojibake in a text value.

    Applies a targeted pre-map for smart-quote sequences ftfy can't fully
    recover, then runs ftfy for everything else. Clean input is returned
    unchanged; empty input is passed through untouched.

    Args:
        text: The possibly-corrupted text.

    Returns:
        The repaired text, or the original value if there is nothing to fix.
    """
    if not text:
        return text
    for broken, correct in _PRE_MAP.items():
        if broken in text:
            text = text.replace(broken, correct)
    return ftfy.fix_text(text)
