#!/usr/bin/env python3
"""Render the TBAR Partners weekly client report (single Letter page) from a JSON data file.

Usage: python3 generate_report.py report_data_<client>_<end-date>.json <output>.pdf
"""
import base64, io, json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from weasyprint import HTML

NAVY, CREAM, ORANGE, GREY = "#152230", "#f4f1ea", "#e29a3d", "#8e98a8"
FONT = ["Liberation Sans", "DejaVu Sans"]
plt.rcParams["font.family"] = FONT


def pct(cur, prev):
    if cur is None or not prev:
        return None
    return (cur - prev) / prev * 100


def money(v): return f"${v:,.2f}"
def num(v): return f"{v:,.0f}"


def badge(cur, prev):
    p = pct(cur, prev)
    if p is None:
        return ""
    up = p >= 0
    return (f'<span class="badge {"up" if up else "down"}">'
            f'{"▲" if up else "▼"} {abs(p):.1f}% vs prev</span>')


def wow_text(cur, prev):
    p = pct(cur, prev)
    if p is None:
        return ""
    return f' (<span class="{"g" if p >= 0 else "r"}">{"▲" if p >= 0 else "▼"} {abs(p):.2f}% WoW</span>)'


def card(label, cur, prev, fmt):
    return (f'<div class="card"><div class="lbl">{label}</div>'
            f'<div class="val">{fmt(cur)}</div>{badge(cur, prev)}</div>')


def fig_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="white")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def style_ax(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#d9d9d9")
    ax.tick_params(colors=GREY, labelsize=7, length=0)
    ax.grid(axis="y", color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))


def trend_chart(weeks):
    fig, ax = plt.subplots(figsize=(3.7, 1.6))
    x = list(range(len(weeks)))
    g = [w["total_gmv"] for w in weeks]
    r = [w["gmv_max_revenue"] for w in weeks]
    ax.plot(x, g, color=NAVY, lw=1.6, marker="o", ms=5, label="Total GMV (Shop)", zorder=3)
    ax.plot(x, r, color=ORANGE, lw=1.6, ls="--", marker="o", ms=5, mfc="white", mew=1.4,
            label="GMV Max Revenue", zorder=3)
    ax.set_xticks(x); ax.set_xticklabels([w["label"] for w in weeks])
    ax.set_xlim(-0.12 if len(x) > 1 else -1, len(x) - 1 + 0.12 if len(x) > 1 else 1)
    lo, hi = min(g + r), max(g + r)
    pad = (hi - lo) * 0.15 or hi * 0.1
    ax.set_ylim(max(0, lo - pad), hi + pad)
    style_ax(ax)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False,
              fontsize=7, labelcolor=NAVY, handlelength=2.2)
    fig.subplots_adjust(left=0.2, right=0.97, top=0.82, bottom=0.14)
    return fig_png(fig)


def bar_chart(weeks):
    fig, ax = plt.subplots(figsize=(3.7, 1.6))
    n = len(weeks)
    w = 0.3
    for i, wk in enumerate(weeks):
        ax.bar(i - w / 2 - 0.01, wk["spend"], w, color=GREY, label="GMV Max Spend" if i == 0 else None, zorder=3)
        ax.bar(i + w / 2 + 0.01, wk["revenue"], w, color=ORANGE, label="GMV Max Revenue" if i == 0 else None, zorder=3)
    ax.set_xticks(range(n)); ax.set_xticklabels([wk["label"] for wk in weeks])
    ax.set_xlim(-0.6, n - 1 + 0.6)
    top = max(max(wk["spend"], wk["revenue"]) for wk in weeks)
    step = 10000 if top > 30000 else 5000 if top > 12000 else 2500
    ax.set_ylim(0, (int(top / step) + 1) * step)
    ax.set_yticks(range(0, int((int(top / step) + 1) * step) + 1, step))
    style_ax(ax)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=7,
              labelcolor=NAVY, handlelength=1, handleheight=1)
    fig.subplots_adjust(left=0.2, right=0.97, top=0.82, bottom=0.14)
    return fig_png(fig)


def build(d):
    gm, out = d["gmv"], d.get("outreach", {})
    client, week = d["client_name"], d["week_label"]
    g = lambda k: gm.get(k, {})

    # ---- executive summary
    lines = []
    if "total_shop_gmv" in gm:
        s = g("total_shop_gmv")
        lines.append(f'<b>Week {week}.</b> {client} generated <b>{money(s["current"])}</b> in Shop GMV'
                     f'{wow_text(s["current"], s.get("previous"))}.')
    if "messages_sent" in out:
        t = f'Sent outreach contacted <b>{num(out["messages_sent"]["current"])}</b> creators'
        if "sample_requests_received" in out:
            t += f', received <b>{num(out["sample_requests_received"]["current"])}</b> sample requests'
            if "sample_requests_approved" in out:
                t += f' (<b>{num(out["sample_requests_approved"]["current"])}</b> received/approved)'
        lines.append(t + ".")
    if "gmv_max_spend" in gm and "gmv_max_revenue" in gm:
        r = g("roi")
        t = (f'GMV Max spend was <b>{money(g("gmv_max_spend")["current"])}</b>, generating '
             f'<b>{money(g("gmv_max_revenue")["current"])}</b> in ad-attributed revenue')
        if "current" in r:
            t += f' — ROI <b>{r["current"]:.2f}x</b>{wow_text(r["current"], r.get("previous"))}'
            if r.get("target"):
                t += f' vs. {r["target"]:.2f}x target'
        lines.append(t + ".")
    summary = "<br>".join(lines)

    # ---- headline cards (order: GMV, GMV Max revenue, ROI, GMV Max spend)
    cards = []
    for key, label, fmt in [("total_shop_gmv", "TOTAL GMV (SHOP)", money),
                            ("gmv_max_revenue", "GMV MAX REVENUE", money),
                            ("roi", "ROI", lambda v: f"{v:.2f}x"),
                            ("gmv_max_spend", "GMV MAX SPEND", money)]:
        if key in gm:
            cards.append(card(label, gm[key]["current"], gm[key].get("previous"), fmt))

    # ---- outreach cards
    oc = []
    for key, label in [("messages_sent", "CREATORS CONTACTED"),
                       ("sample_requests_received", "SAMPLE REQUESTS RECEIVED"),
                       ("sample_requests_approved", "SAMPLES RECEIVED/APPROVED"),
                       ("videos_posted", "VIDEOS POSTED"),
                       ("content_pending", "CREATORS W/ CONTENT PENDING")]:
        if key in out:
            oc.append(card(label, out[key]["current"], out[key].get("previous"), num))

    charts = ""
    if d.get("trend_weeks") and d.get("spend_vs_revenue_weeks"):
        charts = (f'<div class="charts"><div class="chart"><h3>GMV TREND</h3><img src="{trend_chart(d["trend_weeks"])}"></div>'
                  f'<div class="chart"><h3>GMV MAX SPEND VS REVENUE</h3><img src="{bar_chart(d["spend_vs_revenue_weeks"])}"></div></div>')

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: 816px 1056px; margin: 0 }}
* {{ box-sizing: border-box }}
html, body {{ margin:0; padding:0 }}
body {{ background:{CREAM}; width:816px; height:1056px; overflow:hidden;
  font-family:'Liberation Sans','Helvetica','Arial',sans-serif; color:{NAVY}; position:relative }}
.banner {{ background:{NAVY}; height:72px; padding:0 47px; display:flex; align-items:center; justify-content:space-between }}
.brand {{ color:#fff; font-size:21px; letter-spacing:6px; font-weight:700 }}
.tag {{ color:#98a3b3; font-size:9.5px; letter-spacing:2px; font-weight:700 }}
.wrap {{ padding:0 47px }}
.head {{ display:flex; justify-content:space-between; margin-top:24px }}
.eyebrow {{ font-size:10px; letter-spacing:2.4px; color:#7b8696; font-weight:700 }}
h1 {{ font-size:39px; margin:4px 0 0; font-weight:700; line-height:1.1 }}
.meta {{ text-align:right; font-size:13px; color:#6f7a8a; line-height:1.4 }}
.exec {{ background:{NAVY}; color:#fff; border-radius:18px; padding:14px 23px 14px; margin-top:14px }}
.exec .t {{ font-size:10px; letter-spacing:3px; color:#aab4c3; font-weight:700; margin-bottom:4px }}
.exec .b {{ font-size:13.2px; line-height:1.55 }}
.g {{ color:#4ade80 }} .r {{ color:#f87171 }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:15px 23px; margin-top:14px }}
.grid3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:15px 21px; margin-top:13px }}
.card {{ background:#fff; border:1px solid #dedad0; border-radius:14px; padding:10px 18px 11px }}
.lbl {{ font-size:9px; letter-spacing:1.3px; color:#7b8696; font-weight:700; white-space:nowrap }}
.val {{ font-size:33px; font-weight:700; line-height:1.12; margin:0 0 3px }}
.badge {{ display:inline-block; font-size:9.5px; font-weight:700; padding:2px 9px; border-radius:10px }}
.badge.up {{ background:#e3f4e7; color:#1c7a3a }} .badge.down {{ background:#fbe3e3; color:#b3261e }}
.charts {{ display:grid; grid-template-columns:1fr 1fr; gap:23px; margin-top:14px }}
.chart {{ background:#fff; border:1px solid #dedad0; border-radius:14px; padding:12px 18px 6px }}
.chart h3 {{ margin:0; font-size:13px; letter-spacing:1px }}
.chart img {{ width:100%; display:block; margin-top:2px }}
h2 {{ font-size:18px; letter-spacing:.5px; margin:18px 0 0; padding-bottom:5px; border-bottom:2px solid #dedad0; font-weight:700 }}
.foot {{ position:absolute; left:60px; right:60px; bottom:18px; text-align:center; font-size:8.5px;
  color:#8b94a3; letter-spacing:.7px; line-height:1.55; text-transform:uppercase }}
</style></head><body>
<div class="banner"><div class="brand">{d["agency_name"].upper()}</div><div class="tag">WEEKLY CLIENT PERFORMANCE REPORT</div></div>
<div class="wrap">
 <div class="head"><div><div class="eyebrow">CLIENT PERFORMANCE REPORT</div><h1>{client}</h1></div>
  <div class="meta">Week {week}<br>Generated {d["generated_date"]}</div></div>
 <div class="exec"><div class="t">EXECUTIVE SUMMARY</div><div class="b">{summary}</div></div>
 <div class="grid2">{"".join(cards)}</div>
 {charts}
 <h2>OUTREACH &amp; CONTENT</h2>
 <div class="grid3">{"".join(oc)}</div>
</div>
<div class="foot">{"<br>".join(x.strip().rstrip(".") + "." for x in d.get("data_source_note","").split(". ") if x.strip())}</div>
</body></html>"""


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    HTML(string=build(data)).write_pdf(sys.argv[2])
    print("wrote", sys.argv[2])
