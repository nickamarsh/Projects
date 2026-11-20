#!/usr/bin/env python3
"""Render the TBAR Partners weekly client performance report (1 page, letter).

Usage: python3 scripts/generate_report.py report_data.json output.pdf
Requires: weasyprint, matplotlib
"""
import base64
import io
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from weasyprint import HTML  # noqa: E402

NAVY = "#16212e"
GRAY = "#8c97a4"
ORANGE = "#e39a3d"
SLATE = "#8c97a6"
GRID = "#e6e8eb"

plt.rcParams.update({
    "font.family": ["Liberation Sans", "DejaVu Sans"],
    "svg.fonttype": "path",
})


# ---------- helpers ----------
def pct_change(m):
    """WoW % from a {'current','previous'} dict; None if not computable."""
    if not m or m.get("previous") in (None, 0) or m.get("current") is None:
        return None
    return (m["current"] - m["previous"]) / m["previous"] * 100


def money(v):
    return f"${v:,.2f}"


def intf(v):
    return f"{v:,.0f}"


def badge(m):
    p = pct_change(m)
    if p is None:
        return ""
    up = p >= 0
    cls = "up" if up else "down"
    arrow = "&#9650;" if up else "&#9660;"
    return f'<div class="badge {cls}">{arrow} {abs(p):.1f}% vs prev</div>'


def delta_span(m):
    p = pct_change(m)
    if p is None:
        return ""
    up = p >= 0
    return (f' (<span class="{"gup" if up else "gdn"}">'
            f'{"&#9650;" if up else "&#9660;"} {abs(p):.2f}% WoW</span>)')


def card(label, value, m=None):
    return (f'<div class="card"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div>{badge(m)}</div>')


def svg_img(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue().encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}">'


def style_axes(ax):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0, labelsize=7.5, colors=GRAY)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))


# ---------- charts ----------
def gmv_trend_chart(weeks):
    fig, ax = plt.subplots(figsize=(3.55, 1.65), dpi=100)
    xs = list(range(len(weeks)))
    labels = [w["label"] for w in weeks]
    g = [w.get("total_gmv") for w in weeks]
    r = [w.get("gmv_max_revenue") for w in weeks]
    ax.plot(xs, g, color=NAVY, lw=1.8, marker="o", ms=5.5, label="Total GMV (Shop)", zorder=3)
    ax.plot(xs, r, color=ORANGE, lw=1.6, ls=(0, (4, 2)), marker="o", ms=5.5,
            mfc="white", mec=ORANGE, mew=1.5, label="GMV Max Revenue", zorder=3)
    allv = [v for v in g + r if v is not None]
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.18 or hi * 0.1
    ax.set_ylim(max(0, lo - pad), hi + pad)
    ax.set_xlim(-0.12, len(weeks) - 1 + 0.12)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels)
    ax.yaxis.set_major_locator(plt.MaxNLocator(4))
    style_axes(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.28), ncol=2, frameon=False,
              fontsize=7.5, handlelength=2.2)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.82, bottom=0.17)
    return svg_img(fig)


def spend_rev_chart(weeks):
    fig, ax = plt.subplots(figsize=(3.55, 1.65), dpi=100)
    n = len(weeks)
    w = 0.30
    xs = list(range(n))
    sp = [x.get("spend") or 0 for x in weeks]
    rv = [x.get("revenue") or 0 for x in weeks]
    ax.bar([x - w / 2 - 0.01 for x in xs], sp, w, color=SLATE, label="GMV Max Spend", zorder=3)
    ax.bar([x + w / 2 + 0.01 for x in xs], rv, w, color=ORANGE, label="GMV Max Revenue", zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["label"] for x in weeks])
    ax.set_ylim(0, max(sp + rv) * 1.08)
    ax.yaxis.set_major_locator(plt.MaxNLocator(4, integer=True))
    style_axes(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.28), ncol=2, frameon=False,
              fontsize=7.5, handlelength=1.0, handleheight=0.7)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.82, bottom=0.17)
    return svg_img(fig)


# ---------- page ----------
CSS = f"""
@page {{ size: 816px 1056px; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ width: 816px; height: 1056px; background: #f3efe9; color: {NAVY};
       font-family: 'Liberation Sans', Helvetica, Arial, sans-serif; position: relative; }}
.banner {{ background: {NAVY}; height: 69px; padding: 0 45px; display: flex;
          align-items: center; justify-content: space-between; }}
.banner .brand {{ color: #fff; font-weight: 700; font-size: 21px; letter-spacing: 0.32em; }}
.banner .tag {{ color: {GRAY}; font-size: 9.5px; font-weight: 700; letter-spacing: 0.22em; }}
.wrap {{ padding: 0 45px; }}
.head {{ display: flex; justify-content: space-between; align-items: flex-start; margin-top: 24px; }}
.head .eyebrow {{ color: {GRAY}; font-size: 9.5px; font-weight: 700; letter-spacing: 0.24em;
                 text-transform: uppercase; }}
.head .client {{ font-size: 40px; font-weight: 700; line-height: 1.02; margin-top: 2px; }}
.head .dates {{ text-align: right; color: {GRAY}; font-size: 12.5px; line-height: 1.35; margin-top: 2px; }}
.summary {{ background: {NAVY}; border-radius: 14px; margin-top: 14px; padding: 12px 22px 14px; color: #fff;
           font-size: 12.5px; line-height: 1.62; }}
.summary .eyebrow {{ color: {GRAY}; font-size: 9.5px; font-weight: 700; letter-spacing: 0.3em;
                    padding-left: 3px; text-transform: uppercase; }}
.summary b {{ font-weight: 700; }}
.gup {{ color: #4fc08d; }} .gdn {{ color: #f0716b; }}
.grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 22px; margin-top: 14px; }}
.grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 14px; }}
.card {{ background: #fff; border: 1px solid #e7e4de; border-radius: 12px; padding: 11px 17px 11px; }}
.lbl {{ color: {GRAY}; font-size: 8.5px; font-weight: 700; letter-spacing: 0.17em; text-transform: uppercase; }}
.val {{ font-size: 31px; font-weight: 700; line-height: 1.05; margin-top: 1px; }}
.badge {{ display: inline-block; margin-top: 5px; font-size: 9px; font-weight: 700; padding: 3px 8px;
         border-radius: 999px; }}
.badge.up {{ background: #e3f4e8; color: #1f7a45; }}
.badge.down {{ background: #fbe4e2; color: #b3261e; }}
.chart {{ padding: 12px 17px 6px; }}
.chart h3 {{ font-size: 12.5px; font-weight: 700; letter-spacing: 0.02em; text-transform: uppercase; }}
.chart img {{ width: 100%; display: block; margin-top: 2px; }}
h2 {{ font-size: 17px; font-weight: 700; text-transform: uppercase; margin-top: 18px;
     padding-bottom: 6px; border-bottom: 2px solid #d5d9de; }}
.foot {{ margin: 22px 45px 0; text-align: center; color: {GRAY};
        font-size: 8.4px; letter-spacing: 0.04em; text-transform: uppercase; line-height: 1.55; }}
"""


def build_html(d):
    g = d.get("gmv", {})
    o = d.get("outreach", {})
    client, week = d["client_name"], d["week_label"]

    # executive summary
    lines = []
    if "total_shop_gmv" in g:
        m = g["total_shop_gmv"]
        lines.append(f'<b>Week {week}.</b> {client} generated <b>{money(m["current"])}</b> '
                     f'in Shop GMV{delta_span(m)}.')
    else:
        lines.append(f'<b>Week {week}.</b> {client}')
    if "messages_sent" in o:
        s = f'Sent outreach contacted <b>{intf(o["messages_sent"]["current"])}</b> creators'
        if "sample_requests_received" in o:
            s += f', received <b>{intf(o["sample_requests_received"]["current"])}</b> sample requests'
        if "sample_requests_approved" in o:
            s += f' (<b>{intf(o["sample_requests_approved"]["current"])}</b> received/approved)'
        lines.append(s + ".")
    if "gmv_max_spend" in g and "gmv_max_revenue" in g:
        s = (f'GMV Max spend was <b>{money(g["gmv_max_spend"]["current"])}</b>, generating '
             f'<b>{money(g["gmv_max_revenue"]["current"])}</b> in ad-attributed revenue')
        if "roi" in g:
            s += f' &mdash; ROI <b>{g["roi"]["current"]:.2f}x</b>{delta_span(g["roi"])}'
            tgt = g["roi"].get("target")
            if tgt:
                s += f' vs. {tgt:.2f}x target'
        lines.append(s + ".")
    summary = "<br>".join(lines)

    # headline cards
    cards = []
    if "total_shop_gmv" in g:
        cards.append(card("Total GMV (Shop)", money(g["total_shop_gmv"]["current"]), g["total_shop_gmv"]))
    if "gmv_max_revenue" in g:
        cards.append(card("GMV Max Revenue", money(g["gmv_max_revenue"]["current"]), g["gmv_max_revenue"]))
    if "roi" in g:
        cards.append(card("ROI", f'{g["roi"]["current"]:.2f}x', g["roi"]))
    if "gmv_max_spend" in g:
        cards.append(card("GMV Max Spend", money(g["gmv_max_spend"]["current"]), g["gmv_max_spend"]))

    # charts
    charts = ""
    if d.get("trend_weeks"):
        charts += f'<div class="card chart"><h3>GMV Trend</h3>{gmv_trend_chart(d["trend_weeks"])}</div>'
    if d.get("spend_vs_revenue_weeks"):
        charts += (f'<div class="card chart"><h3>GMV Max Spend vs Revenue</h3>'
                   f'{spend_rev_chart(d["spend_vs_revenue_weeks"])}</div>')

    # outreach cards
    out_defs = [
        ("messages_sent", "Creators Contacted"),
        ("sample_requests_received", "Sample Requests Received"),
        ("sample_requests_approved", "Samples Received/Approved"),
        ("videos_posted", "Videos Posted"),
        ("content_pending", "Creators w/ Content Pending"),
    ]
    out_cards = [card(lbl, intf(o[k]["current"]), o[k]) for k, lbl in out_defs if k in o]

    note = d.get("data_source_note", "")
    footer = ("Total GMV from Seller Center Key Metrics. GMV Max spend/revenue/ROI from TikTok GMV Max "
              "Ads dashboard.<br>Outreach &amp; content funnel from Euka."
              + (f"<br>{note}" if note else ""))

    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="banner"><div class="brand">{d.get("agency_name", "TBAR Partners").upper()}</div>
<div class="tag">WEEKLY CLIENT PERFORMANCE REPORT</div></div>
<div class="wrap">
 <div class="head"><div><div class="eyebrow">Client Performance Report</div>
  <div class="client">{client}</div></div>
  <div class="dates">Week {week}<br>Generated {d["generated_date"]}</div></div>
 <div class="summary"><div class="eyebrow">Executive Summary</div>{summary}</div>
 <div class="grid2">{"".join(cards)}</div>
 <div class="grid2">{charts}</div>
 <h2>Outreach &amp; Content</h2>
 <div class="grid3">{"".join(out_cards)}</div>
</div>
<div class="foot">{footer}</div>
</body></html>"""


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    HTML(string=build_html(data)).write_pdf(sys.argv[2])
    print("wrote", sys.argv[2])


if __name__ == "__main__":
    main()
