#!/usr/bin/env python3
"""TBAR Partners weekly client report -> single-page PDF.
Usage: generate_report.py data.json out.pdf
"""
import base64, io, json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from weasyprint import HTML

NAVY, ORANGE, GRAY, GRID = "#15202b", "#e39a3b", "#8d97a5", "#e4e1d8"

def pct(m):
    if not isinstance(m, dict) or "previous" not in m or not m["previous"]:
        return None
    return (m["current"] - m["previous"]) / m["previous"] * 100

def badge(m):
    p = pct(m)
    if p is None:
        return ""
    up = p >= 0
    return (f'<span class="badge {"up" if up else "down"}">'
            f'{"▲" if up else "▼"} {abs(p):.1f}% vs prev</span>')

def arrow(m, dec=2):
    p = pct(m)
    if p is None:
        return ""
    up = p >= 0
    return f'(<span class="{"gu" if up else "gd"}">{"▲" if up else "▼"} {abs(p):.{dec}f}% WoW</span>)'

money = lambda v: f"${v:,.2f}"
num = lambda v: f"{v:,.0f}"

def card(label, value, m):
    return f'<div class="card"><div class="lbl">{label}</div><div class="val">{value}</div>{badge(m)}</div>'

def fig_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=220, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

def style_ax(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, labelsize=6.5, colors=GRAY)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))

def nice_ticks(lo, hi, n=4):
    import math
    span = max(hi - lo, 1)
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=raw)
    start = math.floor(lo / step) * step
    ticks = []
    t = start
    while t < hi + step * 0.99:
        ticks.append(t); t += step
    return ticks

def line_chart(weeks):
    fig, ax = plt.subplots(figsize=(4.4, 1.75))
    x = range(len(weeks))
    g = [w["total_gmv"] for w in weeks]; r = [w["gmv_max_revenue"] for w in weeks]
    ax.plot(x, g, color=NAVY, lw=1.8, marker="o", ms=4.5, label="Total GMV (Shop)")
    ax.plot(x, r, color=ORANGE, lw=1.6, ls="--", marker="o", ms=4.5,
            mfc="white", mec=ORANGE, label="GMV Max Revenue")
    ticks = nice_ticks(min(g + r) * 0.9, max(g + r))
    ax.set_yticks(ticks); ax.set_ylim(ticks[0], ticks[-1])
    ax.set_xticks(list(x)); ax.set_xticklabels([w["label"] for w in weeks])
    ax.set_xlim(-0.15, len(weeks) - 0.85)
    style_ax(ax)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False,
              fontsize=6.5, handlelength=2.2, borderaxespad=0.2)
    return fig_b64(fig)

def bar_chart(weeks):
    fig, ax = plt.subplots(figsize=(4.4, 1.75))
    n = len(weeks); w = 0.34
    for i, wk in enumerate(weeks):
        ax.bar(i - w / 2, wk["spend"], w, color=GRAY, label="GMV Max Spend" if i == 0 else None)
        ax.bar(i + w / 2, wk["revenue"], w, color=ORANGE, label="GMV Max Revenue" if i == 0 else None)
    top = max(max(k["spend"], k["revenue"]) for k in weeks)
    ticks = nice_ticks(0, top)
    ax.set_yticks(ticks); ax.set_ylim(0, ticks[-1])
    ax.set_xticks(range(n)); ax.set_xticklabels([k["label"] for k in weeks])
    style_ax(ax)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False,
              fontsize=6.5, handlelength=0.9, borderaxespad=0.2)
    return fig_b64(fig)

def build(d):
    g, o = d["gmv"], d.get("outreach", {})
    agency, client, wk = d["agency_name"], d["client_name"], d["week_label"]

    # executive summary
    lines = []
    if "total_shop_gmv" in g:
        m = g["total_shop_gmv"]
        lines.append(f'<b>Week {wk}.</b> {client} generated <b>{money(m["current"])}</b> in Shop GMV {arrow(m)}.')
    parts = []
    if "messages_sent" in o:
        parts.append(f'Sent outreach contacted <b>{num(o["messages_sent"]["current"])}</b> creators')
    if "sample_requests_received" in o:
        s = f'received <b>{num(o["sample_requests_received"]["current"])}</b> sample requests'
        if "sample_requests_approved" in o:
            s += f' (<b>{num(o["sample_requests_approved"]["current"])}</b> received/approved)'
        parts.append(s)
    if parts:
        lines.append(", ".join(parts) + ".")
    if all(k in g for k in ("gmv_max_spend", "gmv_max_revenue", "roi")):
        r = g["roi"]
        t = f' vs. target {r["target"]:.2f}x' if "target" in r else ""
        lines.append(f'GMV Max spend was <b>{money(g["gmv_max_spend"]["current"])}</b>, generating '
                     f'<b>{money(g["gmv_max_revenue"]["current"])}</b> in ad-attributed revenue — '
                     f'ROI <b>{r["current"]:.2f}x</b>{t} {arrow(r)}.')
    summary = "<br>".join(lines)

    # headline cards (2x2)
    heads = []
    if "total_shop_gmv" in g: heads.append(card("Total GMV (Shop)", money(g["total_shop_gmv"]["current"]), g["total_shop_gmv"]))
    if "gmv_max_revenue" in g: heads.append(card("GMV Max Revenue", money(g["gmv_max_revenue"]["current"]), g["gmv_max_revenue"]))
    if "roi" in g: heads.append(card("ROI", f'{g["roi"]["current"]:.2f}x', g["roi"]))
    if "gmv_max_spend" in g: heads.append(card("GMV Max Spend", money(g["gmv_max_spend"]["current"]), g["gmv_max_spend"]))

    # outreach cards
    spec = [("messages_sent", "Creators Contacted"), ("sample_requests_received", "Sample Requests Received"),
            ("sample_requests_approved", "Samples Received/Approved"), ("videos_posted", "Videos Posted"),
            ("content_pending", "Content Pending")]
    outs = [card(lbl, num(o[k]["current"]), o[k]) for k, lbl in spec if k in o]

    charts = ""
    if d.get("trend_weeks") and d.get("spend_vs_revenue_weeks"):
        charts = f'''<div class="grid2">
          <div class="card chart"><h3>GMV TREND</h3><img src="data:image/png;base64,{line_chart(d["trend_weeks"])}"></div>
          <div class="card chart"><h3>GMV MAX SPEND VS REVENUE</h3><img src="data:image/png;base64,{bar_chart(d["spend_vs_revenue_weeks"])}"></div>
        </div>'''

    foot = d.get("footer_lines") or [
        "TOTAL GMV, GMV MAX SPEND/REVENUE/ROI AND OUTREACH &amp; CONTENT FUNNEL FROM CRUVA.",
        "GMV MAX ROI AS REPORTED BY THE GMV MAX DASHBOARD. DATA PULLED " + d["generated_date"] + "; 11/19 MAY BE PRELIMINARY."]
    foot_html = "<br>".join(foot)

    css = f'''
    @page {{ size: 816px 1056px; margin: 0 }}
    * {{ box-sizing: border-box; margin: 0; padding: 0 }}
    body {{ width: 816px; height: 1056px; overflow: hidden; background: #f3f0e9; font-family: "Helvetica Neue", Helvetica, Arial, "Liberation Sans", sans-serif; color: {NAVY}; }}
    .banner {{ background: {NAVY}; height: 70px; padding: 0 45px; display: flex; align-items: center; justify-content: space-between }}
    .banner .a {{ color: #fff; font-size: 21px; letter-spacing: 6px; font-weight: 600 }}
    .banner .b {{ color: #8d97a5; font-size: 9px; letter-spacing: 1.6px }}
    .wrap {{ padding: 0 45px }}
    .head {{ display: flex; justify-content: space-between; margin-top: 24px }}
    .head .k {{ font-size: 9.5px; letter-spacing: 2.2px; color: #6f7a88 }}
    .head h1 {{ font-size: 40px; font-weight: 600; line-height: 1.1; margin-top: 2px }}
    .head .r {{ text-align: right; color: #7a8491; font-size: 13px; line-height: 1.55; margin-top: 3px }}
    .sum {{ background: {NAVY}; color: #fff; border-radius: 10px; padding: 14px 24px 15px; margin-top: 12px; font-size: 12.5px; line-height: 1.6 }}
    .sum .t {{ font-size: 9.5px; letter-spacing: 3px; color: #8d97a5; margin-bottom: 3px }}
    .gu {{ color: #3ecf8e }} .gd {{ color: #ff7b72 }}
    .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px 24px; margin-top: 14px }}
    .grid3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; margin-top: 14px }}
    .card {{ background: #fff; border: 1px solid #e6e2d8; border-radius: 10px; padding: 14px 19px 14px }}
    .lbl {{ font-size: 8.5px; letter-spacing: 1.6px; color: #8a94a1; text-transform: uppercase; font-weight: 600 }}
    .val {{ font-size: 33px; font-weight: 600; margin: 3px 0 5px; letter-spacing: -0.5px }}
    .badge {{ display: inline-block; font-size: 8.5px; font-weight: 700; padding: 3px 8px; border-radius: 9px }}
    .badge.up {{ background: #e1f3e4; color: #1f7a3a }} .badge.down {{ background: #fbe0e0; color: #b3261e }}
    .chart {{ padding: 12px 14px 8px }} .chart h3 {{ font-size: 13px; margin: 0 0 2px 5px }}
    .chart img {{ width: 100%; display: block }}
    h2 {{ font-size: 18px; font-weight: 700; margin-top: 18px; padding-bottom: 7px; border-bottom: 2px solid #e1ddd2; text-transform: uppercase }}
    .foot {{ text-align: center; font-size: 8.5px; letter-spacing: .8px; color: #6f7a88; line-height: 1.75; margin-top: 16px }}
    '''
    html = f'''<html><head><meta charset="utf-8"><style>{css}</style></head><body>
    <div class="banner"><div class="a">{agency.upper()}</div><div class="b">WEEKLY CLIENT PERFORMANCE REPORT</div></div>
    <div class="wrap">
      <div class="head"><div><div class="k">CLIENT PERFORMANCE REPORT</div><h1>{client}</h1></div>
        <div class="r">Week {wk}<br>Generated {d["generated_date"]}</div></div>
      <div class="sum"><div class="t">EXECUTIVE SUMMARY</div>{summary}</div>
      <div class="grid2">{"".join(heads)}</div>
      {charts}
      <h2>Outreach &amp; Content</h2>
      <div class="grid3">{"".join(outs)}</div>
      <div class="foot">{foot_html}</div>
    </div></body></html>'''
    return html

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    HTML(string=build(data)).write_pdf(sys.argv[2])
    print("wrote", sys.argv[2])
