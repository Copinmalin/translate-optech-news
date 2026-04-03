#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

import optech_fr_linkresolver3 as prev


def sanitize_internal_path_segments(text: str) -> str:
    replacements = {
        "/en/le bulletin/": "/en/newsletters/",
        "/en/les bulletins/": "/en/newsletters/",
        "/fr/le bulletin/": "/fr/newsletters/",
        "/fr/les bulletins/": "/fr/newsletters/",
        "/en/newsletter/": "/en/newsletters/",
        "/fr/newsletter/": "/fr/newsletters/",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


_original_postprocess_output = prev.postprocess_output


def postprocess_output(path_str: str) -> None:
    path = Path(path_str)
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")
    front_matter, body = prev.split_front_matter(text)
    body = sanitize_internal_path_segments(body)
    path.write_text(front_matter + body, encoding="utf-8")

    _original_postprocess_output(path_str)

    text = path.read_text(encoding="utf-8")
    front_matter, body = prev.split_front_matter(text)
    body = sanitize_internal_path_segments(body)
    path.write_text(front_matter + body, encoding="utf-8")


prev.postprocess_output = postprocess_output

if __name__ == "__main__":
    prev.base.process_one = prev.process_one
    prev.base.main()
