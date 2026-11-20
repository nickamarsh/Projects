#!/usr/bin/env python3
"""TBAR Partners weekly client performance report -> single-page PDF.

Usage: python3 generate_report.py report_data_<client>_<end>.json out.pdf
Any metric key that is missing is dropped (no fake zeros / blank cards).
WoW % is always computed here from {"current","previous"}; never pre-compute it.
"""
import base64, io, json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
from weasyprint import HTML

NAVY, ORANGE, GREY = "#16202b", "#e39a3b", "#8e99a8"
plt.rcParams["font.family"] = ["Liberation Sans", "DejaVu Sans"]


def pct(cur, prev):
    if cur is None or not prev:
        return None
    return (cur - prev) / prev * 100


def money(v):
    return f"${v:,.2f}"


def intf(v):
    return f"{v:,.0f}"


def badge(m, up_is_good=True):
    """Green/red WoW pill; grey note pill if only a note; nothing otherwise."""
    p = pct(m.get("current"), m.get("previous"))
    if p is None:
        return f'<span class="badge neutral">{m["note"]}</span>' if m.get("note") else ""
    cls, arrow = ("up", "▲") if p >= 0 else ("down", "▼")
    return f'<span class="badge {cls}">{arrow} {abs(p):.1f}% vs prev</span>'


def wow_txt(m):
    p = pct(m.get("current"), m.get("previous"))
    if p is None:
        return ""
    cls, arrow = ("pos", "▲") if p >= 0 else ("neg", "▼")
    return f' (<span class="{cls}">{arrow} {abs(p):.2f}% WoW</span>)'


def card(label, value, m):
    return (f'<div class="card"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div>{badge(m)}</div>')


def png_uri(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=220, transparent=True)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def style_ax(ax, fmt):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#e4e1d8")
    ax.grid(axis="y", color="#e4e1d8", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, labelsize=7.5, colors="#6b7684")
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.yaxis.set_major_formatter(FuncFormatter(fmt))


def trend_chart(weeks):
    fig, ax = plt.subplots(figsize=(4.3, 1.85))
    x = range(len(weeks))
    ax.plot(x, [w["total_gmv"] for w in weeks], color=NAVY, lw=2, marker="o", ms=5, label="Total GMV (Shop)")
    ax.plot(x, [w["gmv_max_revenue"] for w in weeks], color=ORANGE, lw=2, ls="--", marker="o", ms=5,
            mfc="white", mew=1.6, label="GMV Max Revenue")
    ax.set_xticks(list(x)); ax.set_xticklabels([w["label"] for w in weeks])
    ax.set_xlim(-0.15, len(weeks) - 0.85)
    style_ax(ax, lambda v, _: f"${v:,.0f}")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=7.5)
    fig.tight_layout(pad=0.3)
    return png_uri(fig)


def bar_chart(weeks):
    fig, ax = plt.subplots(figsize=(4.3, 1.85))
    n, w = len(weeks), 0.34
    ax.bar([i - w / 2 - 0.01 for i in range(n)], [k["spend"] for k in weeks], w, color=GREY, label="GMV Max Spend")
    ax.bar([i + w / 2 + 0.01 for i in range(n)], [k["revenue"] for k in weeks], w, color=ORANGE, label="GMV Max Revenue")
    ax.set_xticks(range(n)); ax.set_xticklabels([k["label"] for k in weeks])
    ax.set_ylim(bottom=0)
    style_ax(ax, lambda v, _: f"${v:,.0f}")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=7.5)
    fig.tight_layout(pad=0.3)
    return png_uri(fig)


CSS = """
@page { size: 816px 1056px; margin: 0; }
* { box-sizing: border-box; }
body { margin:0; background:#f3f0e8; font-family:'Liberation Sans','Helvetica',Arial,sans-serif; color:#16202b; width:816px; height:1056px; position:relative; }
.banner { background:#16202b; height:70px; padding:0 45px; display:flex; justify-content:space-between; align-items:center; }
.banner .brand { color:#fff; font-size:23px; font-weight:bold; letter-spacing:7px; }
.banner .tag { color:#8e99a8; font-size:10px; letter-spacing:1.6px; text-transform:uppercase; }
.wrap { padding:0 45px; }
.head { display:flex; justify-content:space-between; margin-top:22px; }
.eyebrow { color:#8e99a8; font-size:10.5px; letter-spacing:2.4px; text-transform:uppercase; }
.client { font-size:40px; font-weight:bold; margin-top:2px; }
.meta { text-align:right; color:#8e99a8; font-size:14px; line-height:1.5; margin-top:2px; }
.exec { background:#16202b; color:#fff; border-radius:14px; padding:14px 26px 14px; margin-top:14px; font-size:13px; line-height:1.55; }
.exec .eb { color:#8e99a8; font-size:9.5px; letter-spacing:3px; text-transform:uppercase; margin-bottom:5px; }
.exec b { font-weight:bold; }
.pos { color:#3ecf8e; } .neg { color:#ff7a70; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px 26px; margin-top:14px; }
.grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px 24px; margin-top:14px; }
.grid3 .lbl { letter-spacing:1.2px; font-size:9px; white-space:nowrap; }
.card { background:#fff; border:1px solid #e4e1d8; border-radius:14px; padding:12px 20px 12px; min-height:80px; }
.grid2 .card { min-height:88px; }
.lbl { color:#8e99a8; font-size:9.5px; letter-spacing:1.9px; text-transform:uppercase; }
.val { font-size:32px; font-weight:bold; margin:1px 0 5px; }
.grid3 .val { font-size:31px; }
.badge { display:inline-block; font-size:9.5px; font-weight:bold; border-radius:10px; padding:3px 9px; }
.badge.up { background:#e3f4e8; color:#1d7a3c; } .badge.down { background:#fde8e6; color:#b42318; }
.badge.neutral { background:#eeece5; color:#6b7684; }
.chart { background:#fff; border:1px solid #e4e1d8; border-radius:14px; padding:14px 20px 8px; }
.chart h3 { margin:0 0 2px; font-size:15px; }
.chart img { width:100%; display:block; }
h2 { font-size:20px; margin:20px 0 0; padding-bottom:8px; border-bottom:2px solid #e4e1d8; letter-spacing:.2px; text-transform:uppercase; }
.foot { text-align:center; color:#8e99a8; font-size:9px; letter-spacing:1px; text-transform:uppercase; line-height:1.6; margin-top:16px; }
"""


def build(d):
    g, o = d["gmv"], d.get("outreach", {})
    cur = lambda m: m["current"]
    s = [f'<b>Week {d["week_label"]}.</b> {d["client_name"]} generated <b>{money(cur(g["total_shop_gmv"]))}</b> in Shop GMV{wow_txt(g["total_shop_gmv"])}.']
    parts = []
    if "messages_sent" in o:
        parts.append(f'Sent outreach contacted <b>{intf(cur(o["messages_sent"]))}</b> creators')
    if "sample_requests_received" in o:
        t = f'received <b>{intf(cur(o["sample_requests_received"]))}</b> sample requests'
        if "sample_requests_approved" in o:
            t += f' (<b>{intf(cur(o["sample_requests_approved"]))}</b> received/approved)'
        parts.append(t)
    if parts:
        s.append(", ".join(parts) + ".")
    roi = g["roi"]
    tgt = f' vs. {roi["target"]:.2f}x target' if roi.get("target") else ""
    s.append(f'GMV Max spend was <b>{money(cur(g["gmv_max_spend"]))}</b>, generating <b>{money(cur(g["gmv_max_revenue"]))}</b> '
             f'in ad-attributed revenue — ROI <b>{cur(roi):.2f}x</b>{tgt}{wow_txt(roi)}.')

    top = [("Total GMV (Shop)", money(cur(g["total_shop_gmv"])), g["total_shop_gmv"]),
           ("GMV Max Revenue", money(cur(g["gmv_max_revenue"])), g["gmv_max_revenue"]),
           ("ROI", f'{cur(roi):.2f}x', roi),
           ("GMV Max Spend", money(cur(g["gmv_max_spend"])), g["gmv_max_spend"])]
    om = [("messages_sent", "Creators Contacted"), ("sample_requests_received", "Sample Requests Received"),
          ("sample_requests_approved", "Samples Received/Approved"), ("videos_posted", "Videos Posted"),
          ("content_pending", "Creators w/ Content Pending")]
    ocards = "".join(card(l, intf(cur(o[k])), o[k]) for k, l in om if k in o)

    tw, sw = d.get("trend_weeks", []), d.get("spend_vs_revenue_weeks", [])
    charts = ""
    if tw:
        charts += f'<div class="chart"><h3>GMV Trend</h3><img src="{trend_chart(tw)}"></div>'
    if sw:
        charts += f'<div class="chart"><h3>GMV Max Spend vs Revenue</h3><img src="{bar_chart(sw)}"></div>'

    foot = d.get("footer") or [
        "Total GMV from TikTok Shop via Euka. GMV Max spend/revenue/ROI from TikTok GMV Max ads via Euka.",
        "Outreach & content funnel from Euka.",
        d.get("gmv_finalized_note", "")]
    foot_html = "<br>".join(x for x in foot if x)

    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="banner"><div class="brand">{d["agency_name"].upper()}</div><div class="tag">Weekly Client Performance Report</div></div>
<div class="wrap">
<div class="head"><div><div class="eyebrow">Client Performance Report</div><div class="client">{d["client_name"]}</div></div>
<div class="meta">Week {d["week_label"]}<br>Generated {d["generated_date"]}</div></div>
<div class="exec"><div class="eb">Executive Summary</div>{"<br>".join(s)}</div>
<div class="grid2">{"".join(card(*t) for t in top)}</div>
<div class="grid2" style="margin-top:16px">{charts}</div>
<h2>Outreach &amp; Content</h2>
<div class="grid3">{ocards}</div>
<div class="foot">{foot_html}</div>
</div></body></html>"""


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    data.setdefault("gmv_finalized_note", "")
    HTML(string=build(data)).write_pdf(sys.argv[2])
    print("wrote", sys.argv[2])
