# Page generators

The long-tail fee guides are generated, not hand-written. Every dollar figure on
those pages (and in their FAQ prose) is computed by `fee_model()` in
`gen_etsy_pages.py`, so the text cannot drift from the arithmetic.

## Rules

- **Change a rate in one place.** `TX`, `PROC_PCT`, `PROC_FLAT`, `LISTING`,
  `OFFSITE_LOW`, `OFFSITE_HIGH`, `OFFSITE_CAP` at the top of `gen_etsy_pages.py`
  are the only source of truth. Never edit a number inside a generated page.
- **Never hand-edit a generated page.** Re-run the generator instead, otherwise
  the next run silently reverts the edit.
- `wire_pages.py` is idempotent: it adds the internal-link block, rebuilds
  `sitemap.xml` and updates `llms.txt`. Running it twice does not duplicate links.

## Usage

```bash
python3 tools/gen_etsy_pages.py   # rewrites the five guide directories
python3 tools/wire_pages.py       # internal links + sitemap + llms.txt
```

Then publish (`git push`), resubmit the sitemap, and ping IndexNow.

## Fee model

Etsy US, verified 2026-11-23 against Etsy's published fee policy:

| Component | Rate | Base |
|---|---|---|
| Transaction | 6.5% | item + shipping + gift wrap |
| Payment processing | 3% + $0.25 | order total incl. tax |
| Listing | $0.20 | per publish and per auto-renew |
| Offsite ads | 15% / 12% | order total, capped at $100 |

Postage is **not** a fee. The pages treat it as a real cost (`label_cost`), which is
why "deposit" and "left for materials" are different numbers.
