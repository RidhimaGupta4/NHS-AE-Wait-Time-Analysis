"""
NHS A&E Wait Time Analysis — EDA & Chart Generation
====================================================
Generates 7 publication-quality charts for the portfolio.

Run:
    pip install pandas numpy matplotlib seaborn
    python 03_eda_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import warnings, os

warnings.filterwarnings("ignore")

DATA = "/home/claude/nhs-ae-analysis/data/processed"
OUT  = "/home/claude/nhs-ae-analysis/outputs"
os.makedirs(OUT, exist_ok=True)

monthly      = pd.read_csv(f"{DATA}/monthly_ae.csv")
trust_sum    = pd.read_csv(f"{DATA}/trust_summary.csv")
seasonal     = pd.read_csv(f"{DATA}/seasonal_summary.csv")
national     = pd.read_csv(f"{DATA}/national_trend.csv")

# ── Palette ───────────────────────────────────────────────────────────────────
NHS_BLUE    = "#003087"
NHS_LIGHT   = "#41B6E6"
NHS_GREEN   = "#007F3B"
NHS_WARM    = "#ED8B00"
NHS_RED     = "#DA291C"
MUTED       = "#768692"
BG          = "#F9FAFB"
TEXT        = "#1C2B39"

def style(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(BG)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color("#CBD5E1")
    ax.tick_params(colors=TEXT, labelsize=9)
    if title:  ax.set_title(title, fontsize=12, fontweight="bold", color=TEXT, pad=10)
    if xlabel: ax.set_xlabel(xlabel, fontsize=9, color=MUTED)
    if ylabel: ax.set_ylabel(ylabel, fontsize=9, color=MUTED)


# ── Chart 1: National 4-hour Performance Decline 2018–2024 ───────────────────
def chart_national_decline():
    ann = national.groupby("year").agg(
        avg_perf=("avg_perf_4hr","mean"),
        total_att=("total_attendances","sum"),
        total_br=("total_breaches","sum"),
    ).reset_index()
    ann["breach_rate"] = ann["total_br"] / ann["total_att"] * 100

    fig, ax1 = plt.subplots(figsize=(10, 5), facecolor="white")
    ax2 = ax1.twinx()

    ax1.bar(ann["year"], ann["avg_perf"], color=NHS_BLUE, alpha=0.85, width=0.5, label="4-hr performance %")
    ax2.plot(ann["year"], ann["breach_rate"], color=NHS_RED, linewidth=2.5,
             marker="o", markersize=7, label="Breach rate %")

    ax1.axhline(95, color=NHS_GREEN, linewidth=1.5, linestyle="--", alpha=0.7)
    ax1.text(2018.1, 95.8, "95% NHS Target", fontsize=9, color=NHS_GREEN, fontweight="bold")

    for _, row in ann.iterrows():
        ax1.text(row["year"], row["avg_perf"] - 2.5, f'{row["avg_perf"]:.1f}%',
                 ha="center", fontsize=9, color="white", fontweight="bold")

    style(ax1, title="NHS A&E 4-Hour Performance vs Breach Rate 2018–2024",
          xlabel="Year", ylabel="% patients seen within 4 hours")
    ax2.set_ylabel("Breach rate (%)", fontsize=9, color=MUTED)
    ax2.tick_params(colors=TEXT, labelsize=9)
    ax2.spines[["top","right"]].set_color("#CBD5E1")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.1f}%"))
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
    ax1.set_ylim(50, 100)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1+lines2, labels1+labels2, fontsize=9, framealpha=0, loc="lower left")
    plt.tight_layout()
    plt.savefig(f"{OUT}/01_national_performance_decline.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 01_national_performance_decline.png")


# ── Chart 2: Seasonal Pattern — Monthly Performance Heatmap ──────────────────
def chart_seasonal_pattern():
    pivot = monthly.groupby(["year","month"])["perf_4hr_pct"].mean().unstack()
    fig, ax = plt.subplots(figsize=(12, 5), facecolor="white")
    im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto",
                   vmin=60, vmax=90)

    ax.set_xticks(range(12))
    ax.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
                       fontsize=9, color=TEXT)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=9, color=TEXT)

    for i in range(len(pivot.index)):
        for j in range(12):
            val = pivot.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                        fontsize=8, color="white" if val < 72 else TEXT, fontweight="bold")

    plt.colorbar(im, ax=ax, label="4-hr performance (%)", shrink=0.8)
    ax.set_title("Seasonal Heatmap — 4-Hour Performance by Month & Year\n"
                 "Green = better performance · Red = worse · Winter pressure clearly visible",
                 fontsize=12, fontweight="bold", color=TEXT, pad=10)
    ax.spines[["top","right","left","bottom"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(f"{OUT}/02_seasonal_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 02_seasonal_heatmap.png")


# ── Chart 3: Trust Performance League Table 2024 ─────────────────────────────
def chart_trust_league():
    d2024 = trust_sum[trust_sum["year"]==2024].sort_values("avg_4hr_performance")
    colors = [NHS_RED if v<70 else NHS_WARM if v<80 else NHS_GREEN
              for v in d2024["avg_4hr_performance"]]

    fig, ax = plt.subplots(figsize=(10, 7), facecolor="white")
    bars = ax.barh(d2024["trust"], d2024["avg_4hr_performance"],
                   color=colors, height=0.65)

    for bar, val in zip(bars, d2024["avg_4hr_performance"]):
        ax.text(val + 0.3, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}%", va="center", fontsize=9, color=TEXT, fontweight="bold")

    ax.axvline(95, color=NHS_GREEN, linewidth=1.5, linestyle="--", alpha=0.8)
    ax.text(95.2, 0.5, "95% target", fontsize=8, color=NHS_GREEN, fontweight="bold")
    ax.axvline(70, color=NHS_RED, linewidth=1, linestyle=":", alpha=0.6)
    ax.text(70.2, 0.5, "Critical threshold", fontsize=8, color=NHS_RED)

    style(ax, title="Trust 4-Hour Performance League Table — 2024\nAll 15 major A&E trusts vs NHS 95% constitutional standard",
          xlabel="% patients seen within 4 hours")
    ax.set_xlim(50, 100)
    ax.yaxis.set_visible(True)
    ax.spines["left"].set_visible(False)
    ax.yaxis.set_tick_params(length=0)

    legend_patches = [
        mpatches.Patch(color=NHS_GREEN, label="Near target (≥80%)"),
        mpatches.Patch(color=NHS_WARM, label="Underperforming (70–80%)"),
        mpatches.Patch(color=NHS_RED, label="Critical (<70%)"),
    ]
    ax.legend(handles=legend_patches, fontsize=9, framealpha=0, loc="lower right")
    plt.tight_layout()
    plt.savefig(f"{OUT}/03_trust_league_table_2024.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 03_trust_league_table_2024.png")


# ── Chart 4: Winter vs Summer Performance Gap ─────────────────────────────────
def chart_winter_summer():
    seasonal_ord = seasonal.sort_values("month")
    months = seasonal_ord["month_name"].tolist()
    perf   = seasonal_ord["avg_perf_4hr"].tolist()
    wait   = seasonal_ord["avg_median_wait"].tolist()

    colors = [NHS_RED if m in ["Jan","Feb","Dec"] else
              NHS_WARM if m in ["Mar","Nov"] else
              NHS_LIGHT if m in ["Jul","Aug"] else
              NHS_BLUE for m in months]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), facecolor="white")

    bars = ax1.bar(months, perf, color=colors, width=0.7)
    ax1.axhline(95, color=NHS_GREEN, linewidth=1.5, linestyle="--", alpha=0.7)
    ax1.text(0, 95.8, "95% target", fontsize=8, color=NHS_GREEN, fontweight="bold")
    for bar, v in zip(bars, perf):
        ax1.text(bar.get_x()+bar.get_width()/2, v+0.4, f"{v:.1f}",
                 ha="center", fontsize=8, color=TEXT, fontweight="bold")
    style(ax1, title="Average 4-Hr Performance by Month",
          xlabel="Month", ylabel="% seen within 4 hours")
    ax1.set_ylim(60, 98)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

    ax2.plot(months, wait, color=NHS_BLUE, linewidth=2.5, marker="o", markersize=7)
    ax2.fill_between(range(12), wait, alpha=0.15, color=NHS_BLUE)
    for i, (m, w) in enumerate(zip(months, wait)):
        if m in ["Jan", "May", "Dec"]:
            ax2.annotate(f"{w:.0f} min", (i, w), textcoords="offset points",
                         xytext=(0, 10), ha="center", fontsize=8, color=TEXT)
    style(ax2, title="Average Median Wait Time by Month",
          xlabel="Month", ylabel="Median wait (minutes)")
    ax2.set_xticks(range(12))
    ax2.set_xticklabels(months, rotation=45, ha="right")
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha="right")

    legend_patches = [
        mpatches.Patch(color=NHS_RED, label="Peak winter"),
        mpatches.Patch(color=NHS_WARM, label="Winter shoulder"),
        mpatches.Patch(color=NHS_LIGHT, label="Summer peak"),
        mpatches.Patch(color=NHS_BLUE, label="Baseline"),
    ]
    ax1.legend(handles=legend_patches, fontsize=8, framealpha=0)
    plt.suptitle("Seasonal Pressure Pattern — Winter Crisis Clearly Visible",
                 fontsize=13, fontweight="bold", color=TEXT, y=1.01)
    plt.tight_layout()
    plt.savefig(f"{OUT}/04_winter_summer_gap.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 04_winter_summer_gap.png")


# ── Chart 5: COVID Impact on Attendances ─────────────────────────────────────
def chart_covid_impact():
    covid = national[national["year"].isin([2019,2020,2021])].copy()
    covid["period_label"] = covid["year"].astype(str) + "-" + covid["month"].astype(str).str.zfill(2)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), facecolor="white", sharex=False)

    for yr, col, lw in [(2019, MUTED, 1.5), (2020, NHS_RED, 2.5), (2021, NHS_BLUE, 1.8)]:
        sub = national[national["year"]==yr].sort_values("month")
        ax1.plot(sub["month"], sub["total_attendances"], color=col,
                 linewidth=lw, marker="o", markersize=4, label=str(yr))
        ax2.plot(sub["month"], sub["avg_perf_4hr"], color=col,
                 linewidth=lw, marker="o", markersize=4, label=str(yr))

    ax1.axvspan(3.5, 6.5, alpha=0.12, color=NHS_RED)
    ax1.text(4.8, ax1.get_ylim()[1]*0.95, "COVID\nlockdown", ha="center",
             fontsize=9, color=NHS_RED, fontweight="bold")
    ax2.axvspan(3.5, 6.5, alpha=0.12, color=NHS_RED)

    style(ax1, title="COVID-19 Impact — Monthly A&E Attendances (2019–2021)",
          ylabel="Total monthly attendances")
    style(ax2, title="COVID-19 Impact — 4-Hour Performance (2019–2021)",
          xlabel="Month", ylabel="% seen within 4 hours")
    ax1.set_xticks(range(1,13))
    ax2.set_xticks(range(1,13))
    ax2.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun",
                          "Jul","Aug","Sep","Oct","Nov","Dec"], fontsize=9)
    ax1.legend(fontsize=9, framealpha=0)
    ax2.legend(fontsize=9, framealpha=0)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x/1000:.0f}k"))
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
    plt.tight_layout()
    plt.savefig(f"{OUT}/05_covid_impact.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 05_covid_impact.png")


# ── Chart 6: Breach Rate Trend — Top 5 vs Bottom 5 Trusts ────────────────────
def chart_trust_divergence():
    annual = trust_sum.copy()
    best5  = annual.groupby("trust")["avg_4hr_performance"].mean().nlargest(5).index
    worst5 = annual.groupby("trust")["avg_4hr_performance"].mean().nsmallest(5).index

    fig, ax = plt.subplots(figsize=(11, 6), facecolor="white")

    for trust in best5:
        sub = annual[annual["trust"]==trust].sort_values("year")
        ax.plot(sub["year"], sub["avg_4hr_performance"], color=NHS_GREEN,
                linewidth=1.5, alpha=0.8, marker="o", markersize=4)

    for trust in worst5:
        sub = annual[annual["trust"]==trust].sort_values("year")
        ax.plot(sub["year"], sub["avg_4hr_performance"], color=NHS_RED,
                linewidth=1.5, alpha=0.8, marker="o", markersize=4)

    # National average
    nat_avg = annual.groupby("year")["avg_4hr_performance"].mean()
    ax.plot(nat_avg.index, nat_avg.values, color=NHS_BLUE,
            linewidth=3, linestyle="--", marker="D", markersize=6, label="National average", zorder=5)

    ax.axhline(95, color=NHS_GREEN, linewidth=1.2, linestyle=":", alpha=0.6)
    ax.text(2018.05, 95.6, "95% target", fontsize=8, color=NHS_GREEN)

    style(ax, title="Trust Performance Divergence 2018–2024\nBest 5 (green) vs Worst 5 (red) trusts — gap is widening",
          xlabel="Year", ylabel="Average 4-hr performance (%)")
    ax.set_xticks(range(2018,2025))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
    ax.set_ylim(50, 100)
    legend_patches = [
        mpatches.Patch(color=NHS_GREEN, label="Best 5 trusts"),
        mpatches.Patch(color=NHS_RED, label="Worst 5 trusts"),
        plt.Line2D([0],[0], color=NHS_BLUE, linewidth=2.5, linestyle="--", marker="D",
                   markersize=5, label="National average"),
    ]
    ax.legend(handles=legend_patches, fontsize=9, framealpha=0)
    plt.tight_layout()
    plt.savefig(f"{OUT}/06_trust_divergence.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 06_trust_divergence.png")


# ── Chart 7: Ambulance Handover Delay vs Breach Rate ─────────────────────────
def chart_handover_correlation():
    sample = monthly.sample(600, random_state=42)

    fig, ax = plt.subplots(figsize=(9, 6), facecolor="white")
    sc = ax.scatter(sample["ambulance_handover_delay_pct"], sample["breach_rate_pct"],
                    c=sample["median_wait_mins"], cmap="YlOrRd",
                    alpha=0.65, s=35, edgecolors="none")

    z = np.polyfit(sample["ambulance_handover_delay_pct"], sample["breach_rate_pct"], 1)
    p = np.poly1d(z)
    x_line = np.linspace(sample["ambulance_handover_delay_pct"].min(),
                          sample["ambulance_handover_delay_pct"].max(), 100)
    ax.plot(x_line, p(x_line), color=NHS_BLUE, linewidth=2, linestyle="--",
            label=f"Trend  (slope={z[0]:.2f})")

    corr = sample["ambulance_handover_delay_pct"].corr(sample["breach_rate_pct"])
    ax.text(0.05, 0.92, f"r = {corr:.2f}", transform=ax.transAxes,
            fontsize=11, color=NHS_BLUE, fontweight="bold")

    plt.colorbar(sc, ax=ax, label="Median wait (minutes)", shrink=0.85)
    style(ax, title="Ambulance Handover Delays vs A&E Breach Rate\nPositive correlation — handover delays are a predictive signal",
          xlabel="Ambulance handover delay >30 min (%)",
          ylabel="4-hour breach rate (%)")
    ax.legend(fontsize=9, framealpha=0)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
    plt.tight_layout()
    plt.savefig(f"{OUT}/07_handover_breach_correlation.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 07_handover_breach_correlation.png")


if __name__ == "__main__":
    print("Generating NHS A&E analysis charts...\n")
    chart_national_decline()
    chart_seasonal_pattern()
    chart_trust_league()
    chart_winter_summer()
    chart_covid_impact()
    chart_trust_divergence()
    chart_handover_correlation()
    print(f"\nAll 7 charts saved to {OUT}/")
