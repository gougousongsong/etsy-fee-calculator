#!/usr/bin/env python3
"""Publish pages from this repo to the server that serves tools.gougousongsong.dpdns.org.

The public host serves the repo root at "/", so absolute links, canonicals and
JSON-LD URLs that still carry the old GitHub Pages prefix are rewritten on the
way out, and the first-party beacon is added to every page once.

Idempotent: publishing the same input twice produces byte-identical output.

    python3 tools/publish_tools_site.py csv-cleaner index.html sitemap.xml
"""
import filecmp
import os
import shutil
import sys

SRC = "/home/administrator/work/etsy-fee-calculator"
DST = "/home/administrator/work/etsy-site-live"
OLD_ORIGIN = "https://gougousongsong.github.io/etsy-fee-calculator"
NEW_ORIGIN = "https://tools.gougousongsong.dpdns.org"
OLD_PREFIX = "/etsy-fee-calculator/"
BEACON = '<script src="/beacon.js" defer></script>'
TEXT_EXT = {".html", ".txt", ".xml", ".js", ".json", ".md", ".csv"}


def transform(text):
    text = text.replace(OLD_ORIGIN, NEW_ORIGIN)
    text = text.replace(OLD_PREFIX, "/")
    if BEACON not in text and "</body>" in text:
        text = text.replace("</body>", BEACON + "\n</body>")
    return text


def publish(rel):
    src = os.path.join(SRC, rel)
    dst = os.path.join(DST, rel)
    if os.path.isdir(src):
        for root, _dirs, files in os.walk(src):
            for name in files:
                publish(os.path.relpath(os.path.join(root, name), SRC))
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.splitext(rel)[1].lower() in TEXT_EXT:
        out = transform(open(src, encoding="utf-8").read())
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(out)
    else:
        shutil.copy2(src, dst)
    print(("same     " if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False) else "published"), rel)


if __name__ == "__main__":
    if not sys.argv[1:]:
        sys.exit(__doc__)
    for arg in sys.argv[1:]:
        publish(arg)
