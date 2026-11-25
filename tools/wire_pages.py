#!/usr/bin/env python3
"""Wire the five new long-tail pages into the site: internal links, sitemap, llms.txt.

Idempotent: re-running never duplicates the guide block.
"""
import os
import re

SITE = "/home/administrator/work/etsy-fee-calculator"
BASE = "https://gougousongsong.github.io/etsy-fee-calculator"
TODAY = "2026-11-25"

GUIDES = [
    ("etsy-fee-on-20-dollar-sale", "Etsy fee on a $20 sale"),
    ("etsy-fee-on-50-dollar-sale", "Etsy fee on a $50 sale"),
    ("etsy-fee-on-100-dollar-sale", "Etsy fee on a $100 sale"),
    ("etsy-offsite-ads-worth-it", "Are offsite ads worth it"),
    ("etsy-digital-download-fees", "Etsy fees for digital downloads"),
]

BLOCK = (
    "<p>Fee guides: "
    + " · ".join(
        f'<a href="/etsy-fee-calculator/{s}/">{t}</a>' for s, t in GUIDES
    )
    + "</p>"
)

OLD_PAGES = [
    "index.html",
    "etsy-fees-2026/index.html",
    "amazon/index.html",
    "cleaning/index.html",
    "freelance/index.html",
]


def add_links(path):
    src = os.path.join(SITE, path)
    html = open(src).read()
    if "Fee guides:" in html:
        return "already"
    # insert inside the FIRST <footer> ... </footer> block
    m = re.search(r"(<footer>)(.*?)(</footer>)", html, re.S)
    if not m:
        return "no-footer"
    html = html[: m.start(3)] + "\n    " + BLOCK + "\n  " + html[m.start(3):]
    open(src, "w").write(html)
    return "linked"


def build_sitemap():
    urls = [(BASE + "/", "1.0"), (BASE + "/etsy-fees-2026/", "0.9")]
    for s, _ in GUIDES:
        urls.append((f"{BASE}/{s}/", "0.9"))
    for s, prio in (("cleaning", "0.8"), ("freelance", "0.8"), ("amazon", "0.8")):
        urls.append((f"{BASE}/{s}/", prio))
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, p in urls:
        parts.append("  <url>")
        parts.append(f"    <loc>{u}</loc>")
        parts.append(f"    <lastmod>{TODAY}</lastmod>")
        parts.append("    <changefreq>monthly</changefreq>")
        parts.append(f"    <priority>{p}</priority>")
        parts.append("  </url>")
    parts.append("</urlset>")
    open(os.path.join(SITE, "sitemap.xml"), "w").write("\n".join(parts) + "\n")
    return len(urls)


def update_llms():
    path = os.path.join(SITE, "llms.txt")
    txt = open(path).read()
    if "## Fee guides" in txt:
        return "already"
    guides = "\n".join(f"- [{t}]({BASE}/{s}/)" for s, t in GUIDES)
    section = (
        "\n## Fee guides (Etsy, 2026)\n\n"
        "Long-form answers to the specific questions sellers search for. Every figure is\n"
        "computed from the same fee model as the calculators, so the prose cannot drift\n"
        "from the arithmetic.\n\n"
        + guides
        + "\n"
    )
    marker = "\n## Facts worth citing"
    assert marker in txt
    txt = txt.replace(marker, section + marker, 1)
    txt = txt.replace("> Five browser-only calculators", "> Five browser-only calculators and five long-form fee guides")
    open(path, "w").write(txt)
    return "updated"


if __name__ == "__main__":
    for p in OLD_PAGES:
        print(f"{p}: {add_links(p)}")
    print("sitemap urls:", build_sitemap())
    print("llms.txt:", update_llms())
