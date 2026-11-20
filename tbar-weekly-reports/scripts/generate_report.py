#!/usr/bin/env python3
"""Render the TBAR Partners weekly client report PDF from a JSON data file.

Usage: python3 generate_report.py <data.json> <output.pdf>
Needs: weasyprint, matplotlib
"""
import base64, io, json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from weasyprint import HTML

NAVY, CREAM, ORANGE, GREY = "#15202b", "#f7f5ef", "#e29a3a", "#8d98a6"


def pct(cur, prev):
    if cur is None or prev in (None, 0):
        return None
    return (cur - prev) / prev * 100


def money(v): return f"${v:,.2f}"
def num(v): return f"{v:,.0f}"


def badge(cur, prev):
    p = pct(cur, prev)
    if p is None:
        return ""
    up = p >= 0
    return (f'<div class="badge {"up" if up else "down"}">'
            f'{"▲" if up else "▼"} {abs(p):.1f}% vs prev</div>')


def wow(cur, prev):
    p = pct(cur, prev)
    if p is None:
        return ""
    cls = "g" if p >= 0 else "r"
    return f' (<span class="{cls}">{"▲" if p >= 0 else "▼"} {abs(p):.2f}% WoW</span>)'


def chart_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, transparent=True, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def style_ax(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#d8d8d8")
    ax.tick_params(colors=GREY, labelsize=7, length=0)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.grid(axis="y", color="#e3e3e3", linewidth=0.7)
    ax.set_axisbelow(True)


def trend_chart(weeks):
    fig, ax = plt.subplots(figsize=(4.0, 1.5))
    x = list(range(len(weeks)))
    labels = [w["label"] for w in weeks]
    ax.plot(x, [w["total_gmv"] for w in weeks], color=NAVY, lw=2, marker="o", ms=5, label="Total GMV (Shop)")
    ax.plot(x, [w["gmv_max_revenue"] for w in weeks], color=ORANGE, lw=2, ls="--", marker="o", ms=5,
            mfc="white", mec=ORANGE, label="GMV Max Revenue")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlim(-0.15, len(weeks) - 0.85)
    ax.set_ylim(bottom=0)
    style_ax(ax)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=7,
              labelcolor=NAVY)
    return chart_png(fig)


def bar_chart(weeks):
    fig, ax = plt.subplots(figsize=(4.0, 1.5))
    n, w = len(weeks), 0.34
    for i, wk in enumerate(weeks):
        ax.bar(i - w / 2, wk["spend"], w, color=GREY, label="GMV Max Spend" if i == 0 else None)
        ax.bar(i + w / 2, wk["revenue"], w, color=ORANGE, label="GMV Max Revenue" if i == 0 else None)
    ax.set_xticks(range(n)); ax.set_xticklabels([x["label"] for x in weeks])
    style_ax(ax)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=7,
              labelcolor=NAVY)
    return chart_png(fig)


def main(data_path, out_path):
    d = json.load(open(data_path))
    g, o = d["gmv"], d["outreach"]
    gmv, rev, spend, roi = g["total_shop_gmv"], g["gmv_max_revenue"], g["gmv_max_spend"], g["roi"]

    summary = [f'<b>Week {d["week_label"]}.</b> {d["client_name"]} generated <b>{money(gmv["current"])}</b> in Shop GMV{wow(gmv["current"], gmv.get("previous"))}.']
    if "messages_sent" in o:
        line = f'Sent outreach contacted <b>{num(o["messages_sent"]["current"])}</b> creators'
        if "sample_requests_received" in o:
            line += f', received <b>{num(o["sample_requests_received"]["current"])}</b> sample requests'
            if "sample_requests_approved" in o:
                line += f' (<b>{num(o["sample_requests_approved"]["current"])}</b> received/approved)'
        summary.append(line + ".")
    summary.append(f'GMV Max spend was <b>{money(spend["current"])}</b>, generating <b>{money(rev["current"])}</b> '
                   f'in ad-attributed revenue — ROI <b>{roi["current"]:.2f}x</b>{wow(roi["current"], roi.get("previous"))}'
                   + (f' vs. {roi["target"]:.2f}x target' if "target" in roi else "") + ".")

    cards = [("TOTAL GMV (SHOP)", money(gmv["current"]), badge(gmv["current"], gmv.get("previous"))),
             ("GMV MAX REVENUE", money(rev["current"]), badge(rev["current"], rev.get("previous"))),
             ("ROI", f'{roi["current"]:.2f}x', badge(roi["current"], roi.get("previous"))),
             ("GMV MAX SPEND", money(spend["current"]), badge(spend["current"], spend.get("previous")))]
    cards_html = "".join(f'<div class="card"><div class="lbl">{l}</div><div class="val">{v}</div>{b}</div>' for l, v, b in cards)

    ol = [("CREATORS CONTACTED", "messages_sent"), ("SAMPLE REQUESTS RECEIVED", "sample_requests_received"),
          ("SAMPLES RECEIVED/APPROVED", "sample_requests_approved"), ("VIDEOS POSTED", "videos_posted"),
          ("CREATORS W/ CONTENT PENDING", "content_pending")]
    ol_html = "".join(
        f'<div class="card"><div class="lbl">{l}</div><div class="val">{num(o[k]["current"])}</div>'
        f'{badge(o[k]["current"], o[k].get("previous"))}</div>' for l, k in ol if k in o)

    html = f"""<html><head><style>
@page {{ size: 816px 1056px; margin: 0 }}
* {{ box-sizing: border-box }}
body {{ margin:0; background:{CREAM}; font-family: Helvetica, Arial, sans-serif; color:{NAVY}; width:816px; height:1056px; }}
.banner {{ background:{NAVY}; height:70px; padding:0 45px; display:flex; justify-content:space-between; align-items:center }}
.banner .a {{ color:#fff; font-size:21px; font-weight:bold; letter-spacing:6px }}
.banner .b {{ color:{GREY}; font-size:9px; letter-spacing:2px }}
.wrap {{ padding:20px 45px 0 }}
.head {{ display:flex; justify-content:space-between }}
.head .k {{ color:{GREY}; font-size:10px; letter-spacing:2.5px }}
.head h1 {{ margin:4px 0 0; font-size:38px }}
.head .r {{ text-align:right; color:{GREY}; font-size:13px; line-height:1.5; padding-top:2px }}
.sum {{ background:{NAVY}; color:#fff; border-radius:12px; padding:14px 26px 16px; margin-top:14px; font-size:12.5px; line-height:1.65 }}
.sum .k {{ color:{GREY}; font-size:9px; letter-spacing:3px; margin-bottom:3px }}
.g {{ color:#3ecf8e }} .r {{ color:#ff6b6b }}
.sum .r {{ color:#ff6b6b }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px 24px; margin-top:14px }}
.grid3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px 18px; margin-top:14px }}
.card {{ background:#fff; border:1px solid #e6e3da; border-radius:12px; padding:11px 18px 11px; min-height:88px }}
.lbl {{ color:{GREY}; font-size:9px; letter-spacing:1.3px; font-weight:bold }}
.val {{ font-size:32px; font-weight:bold; margin:3px 0 7px }}
.grid3 .val {{ font-size:30px }}
.badge {{ display:inline-block; font-size:9.5px; font-weight:bold; border-radius:10px; padding:3px 10px }}
.up {{ background:#dff3e6; color:#1f7a45 }} .down {{ background:#fbe0e0; color:#b3261e }}
.ch {{ padding:14px 18px 8px }}
.ch h3 {{ margin:0 0 4px; font-size:14px }}
.ch img {{ width:100%; display:block }}
h2 {{ font-size:18px; margin:18px 0 0; padding-bottom:8px; border-bottom:3px solid #e3e1da }}
.foot {{ text-align:center; color:{GREY}; font-size:8.5px; letter-spacing:1px; line-height:1.7; margin-top:18px; text-transform:uppercase }}
</style></head><body>
<div class="banner"><div class="a">TBAR PARTNERS</div><div class="b">WEEKLY CLIENT PERFORMANCE REPORT</div></div>
<div class="wrap">
<div class="head"><div><div class="k">CLIENT PERFORMANCE REPORT</div><h1>{d["client_name"]}</h1></div>
<div class="r">Week {d["week_label"]}<br>Generated {d["generated_date"]}</div></div>
<div class="sum"><div class="k">EXECUTIVE SUMMARY</div>{"<br>".join(summary)}</div>
<div class="grid2">{cards_html}
<div class="card ch"><h3>GMV TREND</h3><img src="{trend_chart(d["trend_weeks"])}"></div>
<div class="card ch"><h3>GMV MAX SPEND VS REVENUE</h3><img src="{bar_chart(d["spend_vs_revenue_weeks"])}"></div></div>
<h2>OUTREACH &amp; CONTENT</h2>
<div class="grid3">{ol_html}</div>
<div class="foot">{d["data_source_note"]}</div>
</div></body></html>"""
    doc = HTML(string=html).render()
    print("pages:", len(doc.pages))
    doc.write_pdf(out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
