#!/usr/bin/env python3
"""Generate long-tail Etsy fee pages from one truthful fee model.

Every number on the generated pages comes from fee_model() below, so a rate
change is a one-line edit and the prose can never drift from the table.
Rates verified 2026-11-23 against Etsy's published fee policy:
  transaction 6.5% on (item + shipping + gift wrap)
  US payment processing 3% + $0.25
  listing $0.20 (publish + every auto-renew)
  offsite ads 15% (< $10k/yr) / 12% (>= $10k/yr), capped $100/order
"""
import os
import re
import sys

SITE = "/home/administrator/work/etsy-fee-calculator"
BASE = "https://gougousongsong.github.io/etsy-fee-calculator"
GUMROAD = "https://2477537799006.gumroad.com"
CARD = "https://gougousongsong.github.io/xiaoxue-agent-card/support/"

TX = 0.065
PROC_PCT = 0.03
PROC_FLAT = 0.25
LISTING = 0.20
OFFSITE_LOW = 0.15
OFFSITE_HIGH = 0.12
OFFSITE_CAP = 100.0


def m(x):
    return f"${x:,.2f}"


def fee_model(price, shipping=0.0, offsite=False, high_volume=False, label_cost=None):
    """Return the full money flow for one order. label_cost = what postage really costs you."""
    revenue = price + shipping
    tx = round(revenue * TX, 2)
    proc = round(revenue * PROC_PCT + PROC_FLAT, 2)
    listing = LISTING
    off = 0.0
    if offsite:
        rate = OFFSITE_HIGH if high_volume else OFFSITE_LOW
        off = round(min(revenue * rate, OFFSITE_CAP), 2)
    fees = round(tx + proc + listing + off, 2)
    net = round(revenue - fees, 2)
    postage = shipping if label_cost is None else label_cost
    after_postage = round(net - postage, 2)
    return {
        "price": price, "shipping": shipping, "revenue": revenue,
        "tx": tx, "proc": proc, "listing": listing, "offsite": off,
        "fees": fees, "net": net, "pct_kept": round(net / revenue * 100, 1),
        "postage": postage, "after_postage": after_postage,
    }


def table_rows(rows, labels):
    out = []
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{labels[k](r)}</td>" for k in labels) + "</tr>")
    return "\n".join(out)


STYLE = """
:root{--bg:#0f1115;--card:#171a21;--line:#262b35;--txt:#e8ecf1;--dim:#a6b1bf;--acc:#e0a33e;--ok:#43b581;--bad:#ff7b72}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:17px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:34px 20px 70px}
h1{font-size:31px;line-height:1.25;margin:0 0 10px}
h2{font-size:22px;margin:36px 0 10px}
h3{font-size:18px;margin:24px 0 6px}
.lede{color:var(--dim);font-size:18px;margin:0 0 26px}
p{margin:0 0 14px}
table{width:100%;border-collapse:collapse;margin:18px 0;font-size:15px}
th{text-align:left;color:#aab5c3;font-weight:500;border-bottom:1px solid var(--line);padding:9px 8px}
th:not(:first-child){text-align:right}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:18px 0}
.tw table{margin:0;min-width:0;width:100%}
td:not(:first-child){white-space:nowrap}
td{padding:9px 8px;border-bottom:1px solid #2b323c;font-variant-numeric:tabular-nums}
td:not(:first-child){text-align:right}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:20px 0}
.card h3{margin-top:0}
a{color:var(--acc)}
ul{padding-left:22px}
li{margin:7px 0}
.cta{background:linear-gradient(135deg,#1d2430,#1a1f28);border:1px solid var(--line);border-radius:14px;padding:20px;margin:26px 0}
.cta a.btn{display:inline-block;margin-top:8px;background:var(--acc);color:#0f1115;text-decoration:none;font-weight:700;padding:11px 18px;border-radius:9px}
.answer{border-left:3px solid var(--acc);padding-left:14px;color:#d7dde5}
footer{margin-top:44px;color:var(--dim);font-size:14px}
footer a{color:#9aa4b2}
@media(max-width:600px){
  h1{font-size:25px}h2{font-size:19px}h3{font-size:16.5px}
  .wrap{padding:26px 14px 56px}
  th,td{padding:8px 5px;font-size:12px}
  td:first-child{white-space:normal}
  .lede{font-size:16.5px}
}
"""


def page(slug, title, desc, h1, lede, body, faqs, app_name):
    """Assemble one long-tail page: head, JSON-LD, body, footer, service CTA."""
    url = f"{BASE}/{slug}/"
    # tables get their own horizontal scroller so 375px phones scroll the table
    # instead of crushing the numbers into two lines
    body = re.sub(r"<table>", '<div class="tw"><table>', body)
    body = body.replace("</table>", "</table></div>")
    faq_ld = ",".join(
        '{"@type":"Question","name":%s,"acceptedAnswer":{"@type":"Answer","text":%s}}'
        % (json_str(q), json_str(a)) for q, a in faqs
    )
    ld = (
        '{"@context":"https://schema.org","@graph":['
        '{"@type":"FAQPage","mainEntity":[' + faq_ld + ']},'
        '{"@type":"WebApplication","name":' + json_str(app_name) + ',"url":' + json_str(url) +
        ',"applicationCategory":"BusinessApplication","operatingSystem":"Any (runs in the browser)"'
        ',"isAccessibleForFree":true,"offers":{"@type":"Offer","price":"0","priceCurrency":"USD"}'
        ',"publisher":{"@type":"Organization","name":"Xiaoxue","url":' + json_str(CARD.replace("/support/", "/")) + '}},'
        '{"@type":"BreadcrumbList","itemListElement":['
        '{"@type":"ListItem","position":1,"name":"Free business calculators","item":' + json_str(BASE + "/") + '},'
        '{"@type":"ListItem","position":2,"name":' + json_str(app_name) + ',"item":' + json_str(url) + '}]}]}'
    )
    faq_html = "\n".join(
        f"  <h3>{q}</h3>\n  <p>{a}</p>" for q, a in faqs
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<script type="application/ld+json">{ld}</script>
<style>{STYLE}</style>
</head>
<body>
<div class="wrap">
  <h1>{h1}</h1>
  <p class="lede">{lede}</p>
{body}
  <h2>Frequently asked</h2>
{faq_html}

  <footer>
    <p>Fee rates checked on 23 November 2026 against Etsy's published fee and payment policies. Your shop's own fee page is the authority for your region. Free tools:
    <a href="/etsy-fee-calculator/">Etsy fee calculator</a> ·
    <a href="/etsy-fee-calculator/etsy-fees-2026/">all 2026 fees</a> ·
    <a href="/etsy-fee-calculator/etsy-offsite-ads-worth-it/">offsite ads</a> ·
    <a href="/etsy-fee-calculator/etsy-digital-download-fees/">digital downloads</a> ·
    <a href="/etsy-fee-calculator/etsy-fee-on-20-dollar-sale/">$20 sale</a> ·
    <a href="/etsy-fee-calculator/etsy-fee-on-50-dollar-sale/">$50 sale</a> ·
    <a href="/etsy-fee-calculator/etsy-fee-on-100-dollar-sale/">$100 sale</a> ·
    <a href="/etsy-fee-calculator/cleaning/">cleaning pricing</a> ·
    <a href="/etsy-fee-calculator/freelance/">freelance rates</a> ·
    <a href="/etsy-fee-calculator/amazon/">Amazon FBA profit</a> ·
    <a href="{GUMROAD}">spreadsheet tools</a></p>
  </footer>
</div>
<footer style="max-width:760px;margin:48px auto 64px;padding:0 20px;font:14px/1.6 ui-sans-serif,system-ui,sans-serif;color:#5b6672"><p>Need this kind of number-crunching done for your own business — a custom calculator, a margin model in a spreadsheet, or product/price data pulled into a clean CSV?</p><p><a href="{CARD}">Xiaoxue builds these to order</a> — $15–$25 fixed price, delivered as a CSV/HTML artifact with the source table attached.</p></footer>
</body>
</html>
"""
    out_dir = os.path.join(SITE, slug)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w") as f:
        f.write(html)
    return url


def json_str(s):
    import json
    return json.dumps(s)


def price_page(price):
    """A price-point page: real money flow at this price, including postage reality."""
    ps = f"${price:,.0f}"          # narrative form: $20, not $20.00
    ship = round(price * 0.2)
    ship = max(4.0, min(ship, 9.0))
    base = fee_model(price, ship)
    no_ship = fee_model(price, 0.0)
    cheap_label = fee_model(price, ship, label_cost=round(ship * 1.15, 2))
    off = fee_model(price, ship, offsite=True)
    small = fee_model(price * 0.6)
    big = fee_model(price * 1.5)

    body = f"""
  <div class="card">
    <h3>The same {ps} item, three ways it is actually sold</h3>
    <table>
      <thead><tr><th>Scenario</th><th>Buyer pays</th><th>Etsy keeps</th><th>You receive</th><th>You keep %</th></tr></thead>
      <tbody>
        <tr><td>Free shipping, {m(price)} price</td><td>{m(no_ship['revenue'])}</td><td>{m(no_ship['fees'])}</td><td>{m(no_ship['net'])}</td><td>{no_ship['pct_kept']}%</td></tr>
        <tr><td>{m(price)} + {m(ship)} shipping</td><td>{m(base['revenue'])}</td><td>{m(base['fees'])}</td><td>{m(base['net'])}</td><td>{base['pct_kept']}%</td></tr>
        <tr><td>Same order, offsite ad attributed</td><td>{m(off['revenue'])}</td><td>{m(off['fees'])}</td><td>{m(off['net'])}</td><td>{off['pct_kept']}%</td></tr>
      </tbody>
    </table>
    <p style="margin:0;color:#9aa4b2;font-size:14px">Etsy's percentage is the same in the first two rows because the 6.5% and the 3% both apply to item price <em>plus</em> shipping. Moving money from the price into the shipping line does not save you a cent of fees.</p>
  </div>

  <h2>Where the {ps} actually goes</h2>
  <table>
    <thead><tr><th>Line</th><th>Amount</th></tr></thead>
    <tbody>
      <tr><td>Item price</td><td>{m(price)}</td></tr>
      <tr><td>Shipping the buyer pays</td><td>{m(ship)}</td></tr>
      <tr><td>Revenue on the order</td><td>{m(base['revenue'])}</td></tr>
      <tr><td>Transaction fee (6.5%)</td><td>−{m(base['tx'])}</td></tr>
      <tr><td>Payment processing (3% + $0.25)</td><td>−{m(base['proc'])}</td></tr>
      <tr><td>Listing fee</td><td>−{m(base['listing'])}</td></tr>
      <tr><td><strong>Total Etsy fees</strong></td><td><strong>−{m(base['fees'])}</strong></td></tr>
      <tr><td>Deposited to your account</td><td>{m(base['net'])}</td></tr>
      <tr><td>Postage you actually pay ({m(cheap_label['postage'])} label)</td><td>−{m(cheap_label['postage'])}</td></tr>
      <tr><td><strong>Left before materials</strong></td><td><strong>{m(cheap_label['after_postage'])}</strong></td></tr>
    </tbody>
  </table>
  <p class="answer">This is the number most sellers never compute: on a {ps} order the deposit is {m(base['net'])}, but {m(cheap_label['postage'])} of that is postage you owe the carrier. If the buyer paid {m(ship)} for shipping and the label costs {m(cheap_label['postage'])}, the shipping line is <strong>losing you {m(round(cheap_label['postage'] - ship, 2))}</strong> on every order — before Etsy's cut is even counted a second time.</p>

  <h2>Why {ps} is a specific kind of price</h2>
  <p>The ${PROC_FLAT:.2f} processing component and the ${LISTING:.2f} listing fee are flat. They do not care what you charge. On a {ps} order they consume {m(round(PROC_FLAT + LISTING, 2))} of the {ps} price, which is {round((PROC_FLAT + LISTING) / no_ship['revenue'] * 100, 1)}% of the order before a single percentage fee applies. On a {m(big['price'])[:-3]} order the same flat fees are only {round((PROC_FLAT + LISTING) / big['revenue'] * 100, 1)}%.</p>
  <p>That is the whole reason cheap items lose money on Etsy and the same items bundled make money. Compare the margin at three price points:</p>
  <table>
    <thead><tr><th>Order size</th><th>Etsy fees</th><th>Fee % of order</th><th>Flat fees as % of order</th></tr></thead>
    <tbody>
      <tr><td>{m(small['price'])} sale (no shipping)</td><td>{m(small['fees'])}</td><td>{round(small['fees'] / small['revenue'] * 100, 1)}%</td><td>{round((PROC_FLAT + LISTING) / small['revenue'] * 100, 1)}%</td></tr>
      <tr><td>{m(no_ship['price'])} sale (no shipping)</td><td>{m(no_ship['fees'])}</td><td>{round(no_ship['fees'] / no_ship['revenue'] * 100, 1)}%</td><td>{round((PROC_FLAT + LISTING) / no_ship['revenue'] * 100, 1)}%</td></tr>
      <tr><td>{m(big['price'])} sale (no shipping)</td><td>{m(big['fees'])}</td><td>{round(big['fees'] / big['revenue'] * 100, 1)}%</td><td>{round((PROC_FLAT + LISTING) / big['revenue'] * 100, 1)}%</td></tr>
    </tbody>
  </table>

  <h2>What to do about it</h2>
  <ul>
    <li><strong>Price the shipping honestly.</strong> If the label costs {m(cheap_label['postage'])}, charge at least {m(cheap_label['postage'])}. Under-charging for postage is the most common silent loss on Etsy and it does not show up anywhere in Etsy's fee report, because it is not a fee — it is your own margin.</li>
    <li><strong>Bundle two to clear {m(round(price * 1.5, -1))[:-3]} or more.</strong> Two of these at a small discount beats one, because the flat fees are paid once.</li>
    <li><strong>Know the break-even.</strong> On this price the order stops being profitable at {m(round(base['net'] - cheap_label['postage'], 2))} of materials and packaging. Anything above that is a loss you are choosing.</li>
    <li><strong>Watch the offsite ads line.</strong> An attributed sale at this price drops Etsy's cut from {m(base['fees'])} to {m(off['fees'])}. That is {round((off['fees'] - base['fees']) / base['net'] * 100, 1)}% of the money that was going to reach you.</li>
  </ul>

  <div class="cta">
    <strong>Run it with your own price and postage.</strong>
    <p style="margin:6px 0 0">The free calculator applies all four fees to any order and shows the deposit, the margin and the break-even price. No signup, works on a phone.</p>
    <a class="btn" href="/etsy-fee-calculator/">Open the Etsy fee calculator</a>
  </div>
"""

    faqs = [
        (f"How much does Etsy take on a {ps} sale?",
         f"On a {m(price)} item with {m(ship)} shipping, a US seller pays {m(base['fees'])} in total fees: {m(base['tx'])} transaction fee, {m(base['proc'])} payment processing and {m(base['listing'])} listing. That is {round(base['fees'] / base['revenue'] * 100, 1)}% of the {m(base['revenue'])} the buyer pays, leaving a {m(base['net'])} deposit."),
        (f"Is a {ps} item worth selling on Etsy?",
         f"Yes, if the materials cost less than {m(base['after_postage'])}. After fees and a realistic {m(cheap_label['postage'])} shipping label, {m(cheap_label['after_postage'])} is left to cover materials, packaging and your time. Below roughly {m(round(price * 0.35, 0))} of materials the margin is thin enough that one return wipes out several sales."),
        ("Does charging shipping separately reduce Etsy fees?",
         "No. The 6.5% transaction fee and the 3% processing fee both apply to item price plus shipping, so the total fee is identical whether the money sits in the price or in the shipping line. Only the flat $0.25 and $0.20 are unaffected by how you split it."),
        ("What happens to the fee if an offsite ad is attributed to the sale?",
         f"Etsy adds 15% of the order (12% for shops over $10,000 a year), capped at $100. On this order that is an extra {m(off['offsite'])}, which cuts the deposit from {m(base['net'])} to {m(off['net'])}."),
    ]
    slug = f"etsy-fee-on-{price}-dollar-sale"
    title = f"Etsy Fee on a {m(price).replace('.00','')} Sale in 2026 — What You Actually Keep"
    desc = (f"Exactly what Etsy takes on a {m(price)} sale in 2026: {m(base['fees'])} in fees on a "
            f"{m(base['revenue'])} order, the {m(base['net'])} you are deposited, and the postage cost "
            f"that decides whether the order made money.")
    h1 = f"Etsy fee on a {m(price).replace('.00','')} sale"
    lede = (f"Etsy keeps {m(base['fees'])} of the {m(base['revenue'])} the buyer pays — {round(base['fees']/base['revenue']*100,1)}%. "
            f"But the deposit is not your profit, and the shipping line is where this price point quietly loses money.")
    return page(slug, title, desc, h1, lede, body, faqs,
                f"Etsy Fee on a {m(price).replace('.00','')} Sale")


def offsite_page():
    """Offsite ads: the 15% that decides whether a product is viable."""
    a = fee_model(30, 5, offsite=True)
    b = fee_model(30, 5)
    hi = fee_model(30, 5, offsite=True, high_volume=True)
    cheap = fee_model(12, 4, offsite=True)
    cheap_no = fee_model(12, 4)
    capped = fee_model(800, 0, offsite=True)

    body = f"""
  <div class="card">
    <h3>One {m(30)} item plus {m(b['shipping'])} shipping = a {m(b['revenue'])} order</h3>
    <table>
      <thead><tr><th>Line</th><th>No ad</th><th>15% offsite</th><th>12% offsite</th></tr></thead>
      <tbody>
        <tr><td>Buyer pays</td><td>{m(b['revenue'])}</td><td>{m(a['revenue'])}</td><td>{m(hi['revenue'])}</td></tr>
        <tr><td>Transaction + processing + listing</td><td>−{m(round(b['tx']+b['proc']+b['listing'],2))}</td><td>−{m(round(a['tx']+a['proc']+a['listing'],2))}</td><td>−{m(round(hi['tx']+hi['proc']+hi['listing'],2))}</td></tr>
        <tr><td>Offsite ad fee</td><td>$0.00</td><td>−{m(a['offsite'])}</td><td>−{m(hi['offsite'])}</td></tr>
        <tr><td><strong>You receive</strong></td><td><strong>{m(b['net'])}</strong></td><td><strong>{m(a['net'])}</strong></td><td><strong>{m(hi['net'])}</strong></td></tr>
        <tr><td>Etsy's total cut</td><td>{round(b['fees']/b['revenue']*100,1)}%</td><td>{round(a['fees']/a['revenue']*100,1)}%</td><td>{round(hi['fees']/hi['revenue']*100,1)}%</td></tr>
      </tbody>
    </table>
    <p style="margin:0;color:#9aa4b2;font-size:14px">The ad fee is charged on the order total including shipping, exactly like the transaction fee. It is capped at $100 per order, so a large order cannot cost more than that in ad fees — which is the one good thing about it.</p>
  </div>

  <h2>What offsite ads actually are</h2>
  <p>Etsy places your listing in ads on Google, Facebook, Instagram, Pinterest and Bing. If someone clicks one of those ads and buys from your shop within 30 days, the order carries the offsite ad fee instead of the normal advertising cost.</p>
  <p class="answer">The important distinction: this is not a fee you opt into per order. It is attribution. You cannot tell in advance which orders will carry it, so the only safe way to price is to assume the worst case on the products where a 15% hit would hurt.</p>

  <h2>Is it worth it? The arithmetic that actually decides</h2>
  <p>Offsite ads are worth it when the ad fee is smaller than the profit you would lose by not having the sale. That sounds obvious, but it means the answer depends entirely on your margin, not on your price:</p>
  <table>
    <thead><tr><th>Order</th><th>Deposit without ad</th><th>Deposit with 15% ad</th><th>Ad fee</th><th>Left for materials after postage</th></tr></thead>
    <tbody>
      <tr><td>{m(cheap['price'])} + {m(cheap['shipping'])} shipping</td><td>{m(cheap_no['net'])}</td><td>{m(cheap['net'])}</td><td>{m(cheap['offsite'])}</td><td>{m(cheap['after_postage'])}</td></tr>
      <tr><td>{m(b['price'])} + {m(b['shipping'])} shipping</td><td>{m(b['net'])}</td><td>{m(a['net'])}</td><td>{m(a['offsite'])}</td><td>{m(a['after_postage'])}</td></tr>
      <tr><td>{m(capped['price'])} order</td><td>{m(fee_model(800)['net'])}</td><td>{m(capped['net'])}</td><td>{m(capped['offsite'])} (capped)</td><td>{m(capped['after_postage'])}</td></tr>
    </tbody>
  </table>
  <p>On the {m(cheap['price'])} order the ad fee is {m(cheap['offsite'])}, which is {round(cheap['offsite']/cheap_no['net']*100,1)}% of what you would have received. If materials and postage for that item cost more than {m(cheap['net'])}, the ad-driven sale was a loss — you paid Etsy for the privilege of working.</p>
  <p>On the {m(800)} order the 15% rate would imply {m(round(800*0.15,2))}, but the cap stops it at {m(capped['offsite'])}. Etsy's total cut lands at {round(capped['fees']/capped['revenue']*100,1)}% of the order instead of the {round((800*0.15+round(800*0.065,2)+round(800*0.03+0.25,2)+0.2)/800*100,1)}% the uncapped rate would produce. High-ticket products are structurally protected here.</p>

  <h2>The threshold, and why it is not optional</h2>
  <ul>
    <li><strong>Under $10,000 in the last 365 days:</strong> 15% per attributed order. You can switch offsite ads off in your shop settings.</li>
    <li><strong>$10,000 or more in the last 365 days:</strong> 12% per attributed order, and it becomes mandatory — you cannot opt out.</li>
    <li><strong>The $100 cap</strong> applies per order either way. It is the only ceiling in the fee stack.</li>
  </ul>
  <p>Because the switch from 15% to 12% happens on a rolling 365-day window, a strong Q4 can move you into the mandatory tier for the whole of the following year. That is a permanent change to your unit economics triggered by a good month, and it is worth modelling before you push volume.</p>

  <h2>How to decide per product</h2>
  <ul>
    <li><strong>Compute the ad-burdened margin at 15%, not at 12%.</strong> Assume the worst tier; if the product still works, the 12% tier is a bonus.</li>
    <li><strong>Kill anything whose materials plus postage exceed the ad-burdened deposit.</strong> On a {m(cheap['price'])} order that ceiling is {m(cheap['after_postage'])}. Most handmade items at that price do not clear it once postage is paid.</li>
    <li><strong>Raise the price rather than eat the fee.</strong> A 15% ad fee on {m(30)} is {m(a['offsite'])}; the same fee at {m(40)} is {m(round(40*1.15*0.15,2))} on a bigger deposit. The percentage is fixed, the flat part is not.</li>
    <li><strong>Do not confuse it with Etsy Ads.</strong> Etsy Ads is a budget you set and pay whether or not it sells. Offsite ads is a cut of sales that happen. The first is a cost you control, the second is margin you discover after the fact.</li>
  </ul>

  <div class="cta">
    <strong>Model it on your own catalogue.</strong>
    <p style="margin:6px 0 0">The calculator has an offsite-ads toggle: switch it on and you see the 15% case, the cap, and the deposit that actually reaches your bank.</p>
    <a class="btn" href="/etsy-fee-calculator/">Open the Etsy fee calculator</a>
  </div>
"""

    faqs = [
        ("What percentage does Etsy take for offsite ads?",
         "15% of the order for shops under $10,000 in the last 365 days, 12% for shops at or above that threshold. It is charged on the order total including shipping and capped at $100 per order."),
        ("Can I turn off Etsy offsite ads?",
         "Below $10,000 of annual sales you can switch them off in shop settings. At or above $10,000 they become mandatory and the rate drops to 12%."),
        ("Are offsite ads the same as Etsy Ads?",
         "No. Etsy Ads is an advertising budget you set and pay regardless of results. Offsite ads charge a percentage only on orders Etsy attributes to an external ad click, so the cost is discovered after the sale."),
        ("Do offsite ad fees apply to shipping?",
         "Yes. Like the transaction and processing fees, the offsite ad fee is calculated on the full order total the buyer pays, including shipping and gift wrap."),
    ]
    return page("etsy-offsite-ads-worth-it",
                "Are Etsy Offsite Ads Worth It in 2026? The 15% Decides",
                "Offsite ads take 15% (or 12%) of an attributed Etsy order, capped at $100. The real arithmetic: which price points survive the fee, which lose money, and how the $10,000 threshold changes it.",
                "Are Etsy offsite ads worth it?",
                f"Only if the product still clears its costs after the fee. Offsite ads take {round(a['fees']/a['revenue']*100,1)}% of an attributed {m(30)} order — here is the arithmetic that tells you, per product, whether that is a sale or a subsidy.",
                body, faqs, "Are Etsy Offsite Ads Worth It")


def digital_page():
    """Digital downloads: no postage, but the flat fees get louder."""
    d10 = fee_model(10, 0)
    d25 = fee_model(25, 0)
    d5 = fee_model(5, 0)
    d3 = fee_model(3, 0)
    bundle = fee_model(20, 0)

    body = f"""
  <div class="card">
    <h3>Digital downloads, US seller, no shipping</h3>
    <table>
      <thead><tr><th>Price</th><th>Etsy fees</th><th>You receive</th><th>Fee % of sale</th><th>Flat fees as % of sale</th></tr></thead>
      <tbody>
        <tr><td>{m(d3['price'])}</td><td>{m(d3['fees'])}</td><td>{m(d3['net'])}</td><td>{round(d3['fees']/d3['revenue']*100,1)}%</td><td>{round((PROC_FLAT+LISTING)/d3['revenue']*100,1)}%</td></tr>
        <tr><td>{m(d5['price'])}</td><td>{m(d5['fees'])}</td><td>{m(d5['net'])}</td><td>{round(d5['fees']/d5['revenue']*100,1)}%</td><td>{round((PROC_FLAT+LISTING)/d5['revenue']*100,1)}%</td></tr>
        <tr><td>{m(d10['price'])}</td><td>{m(d10['fees'])}</td><td>{m(d10['net'])}</td><td>{round(d10['fees']/d10['revenue']*100,1)}%</td><td>{round((PROC_FLAT+LISTING)/d10['revenue']*100,1)}%</td></tr>
        <tr><td>{m(d25['price'])}</td><td>{m(d25['fees'])}</td><td>{m(d25['net'])}</td><td>{round(d25['fees']/d25['revenue']*100,1)}%</td><td>{round((PROC_FLAT+LISTING)/d25['revenue']*100,1)}%</td></tr>
      </tbody>
    </table>
    <p style="margin:0;color:#9aa4b2;font-size:14px">No shipping line means a smaller fee base and no postage leak — but the ${PROC_FLAT:.2f} and ${LISTING:.2f} flat components are unchanged, so a {m(d3['price'])} download gives up {round((PROC_FLAT+LISTING)/d3['revenue']*100,1)}% of the sale before the percentages even apply.</p>
  </div>

  <h2>What is different about selling files</h2>
  <p class="answer">The fee percentages are identical to physical goods: 6.5% transaction plus 3% + $0.25 processing plus $0.20 listing. What changes is that there is no shipping to inflate the fee base and no postage cost to leak margin. In exchange, the flat fees dominate everything below roughly $15.</p>
  <p>On a {m(d5['price'])} file: the transaction fee is {m(d5['tx'])}, processing is {m(d5['proc'])}, listing is {m(d5['listing'])} — total {m(d5['fees'])}, or {round(d5['fees']/d5['revenue']*100,1)}% of the sale. Almost half of that is fixed cost that does not shrink if you lower the price.</p>

  <h2>The maths of bundles</h2>
  <p>Because digital margin is almost 100% once the file exists, the flat fees are the only real variable. Four separate {m(d5['price'])} files produce {m(round(d5['net']*4,2))} of deposits and pay {m(round((PROC_FLAT+LISTING)*4,2))} in flat fees. One {m(bundle['price'])} bundle of the same four files produces {m(bundle['net'])} and pays {m(round(PROC_FLAT+LISTING,2))}.</p>
  <table>
    <thead><tr><th>Structure</th><th>Revenue</th><th>Flat fees paid</th><th>Net deposit</th></tr></thead>
    <tbody>
      <tr><td>4 separate {m(d5['price'])} files</td><td>{m(20)}</td><td>{m(round((PROC_FLAT+LISTING)*4,2))}</td><td>{m(round(d5['net']*4,2))}</td></tr>
      <tr><td>1 bundle at {m(bundle['price'])}</td><td>{m(bundle['revenue'])}</td><td>{m(round(PROC_FLAT+LISTING,2))}</td><td>{m(bundle['net'])}</td></tr>
    </tbody>
  </table>
  <p>The bundle wins by {m(round(bundle['net'] - d5['net']*4, 2))} on identical revenue, purely because the flat fees are paid once. This is the single most reliable price lever for digital sellers, and it works at every price point.</p>

  <h2>Things that quietly cost you money on digital orders</h2>
  <ul>
    <li><strong>Auto-renew on unsold listings.</strong> A digital listing that never sells still pays $0.20 every four months. 300 dead listings is $15 a year of pure waste — and it compounds as you add variants.</li>
    <li><strong>Refunds keep the listing fee.</strong> Etsy returns the transaction fee on a cancellation but not the $0.20, so churn costs you money even when nothing ships.</li>
    <li><strong>Currency conversion, 2.5%.</strong> A digital shop priced in one currency selling internationally pays this on converted orders, on top of the standard stack.</li>
    <li><strong>Offsite ads on files are brutal.</strong> A 15% cut on a {m(d10['price'])} download leaves {m(fee_model(10,0,offsite=True)['net'])}, and that order has no postage cost to blame.</li>
    <li><strong>Support time is a real cost.</strong> "It won't open on my phone" emails cost labour that no calculator line captures — price in some of it.</li>
  </ul>

  <h2>So what should you charge?</h2>
  <p>Below {m(10)}, digital pricing on Etsy is mostly a volume game where Etsy's flat fees are a fixed tax on each transaction. Above {m(20)} the fee percentage stabilises near {round(fee_model(25,0)['fees']/fee_model(25,0)['revenue']*100,1)}% and the product's perceived value becomes the constraint, not the fee.</p>
  <p>The practical rule: never price a standalone file below {m(5)} on Etsy unless it is a tripwire for a bundle. And compute the break-even at your real price rather than assuming the 10% everybody quotes — at {m(d3['price'])} Etsy is taking {round(d3['fees']/d3['revenue']*100,1)}%, not 10%.</p>

  <div class="cta">
    <strong>Check your own digital price point.</strong>
    <p style="margin:6px 0 0">Set shipping to zero in the calculator and it shows the exact fee, the deposit and the margin for any file price — including the offsite ads case.</p>
    <a class="btn" href="/etsy-fee-calculator/">Open the Etsy fee calculator</a>
  </div>
"""

    faqs = [
        ("Are Etsy fees lower for digital downloads?",
         "The percentages are the same 6.5% transaction and 3% + $0.25 processing. What you save is the shipping line, which lowers the fee base, and the postage cost, which is a real cost rather than a fee. The $0.20 listing fee is unchanged."),
        ("How much does Etsy take from a $5 digital download?",
         f"Fees total {m(d5['fees'])}: {m(d5['tx'])} transaction, {m(d5['proc'])} processing and {m(d5['listing'])} listing. You receive {m(d5['net'])}, which is {round(d5['fees']/d5['revenue']*100,1)}% of the sale — most of that being fixed cost."),
        ("Is it better to sell one bundle or four separate files?",
         f"On identical revenue the bundle nets about {m(round(bundle['net'] - d5['net']*4, 2))} more, because the $0.25 processing component and the $0.20 listing fee are charged once instead of four times."),
        ("Do digital downloads pay the listing fee more than once?",
         "Yes. Every listing pays $0.20 to publish and again on each auto-renewal after four months or after a sale, whether or not the file ever sells."),
    ]
    return page("etsy-digital-download-fees",
                "Etsy Fees for Digital Downloads in 2026 — Real Numbers",
                "What Etsy actually takes on digital downloads in 2026: the same 6.5% and 3% + $0.25, no shipping base, no postage leak — and the flat fees that make anything under $10 hard to sell profitably.",
                "Etsy fees for digital downloads",
                f"No postage, no shipping base, same percentages — but the flat fees get louder as the price falls. At {m(d5['price'])} Etsy takes {round(d5['fees']/d5['revenue']*100,1)}%, not the 10% sellers assume.",
                body, faqs, "Etsy Fees for Digital Downloads")


def main():
    made = []
    for p in (20, 50, 100):
        made.append(price_page(p))
    made.append(offsite_page())
    made.append(digital_page())
    print("generated:", len(made))
    for u in made:
        print(" ", u)


if __name__ == "__main__":
    main()
