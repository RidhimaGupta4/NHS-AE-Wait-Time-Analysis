"""
NHS A&E Wait Time Analysis — Data Generation Script
=====================================================
Generates realistic NHS England A&E synthetic data aligned to published
NHS England statistics (2018–2024).

Real data source (use in production):
  https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/

NHS England publishes monthly A&E data as CSV/Excel. This script models:
  - Monthly attendances by Trust and A&E type
  - 4-hour wait breach rates
  - Admission rates
  - Ambulance handover delays
  - Seasonal patterns (winter pressures, summer peaks)

Run:
    pip install pandas numpy
    python 01_generate_data.py
"""

import pandas as pd
import numpy as np
import json, os

np.random.seed(42)

# ── Constants ─────────────────────────────────────────────────────────────────

TRUSTS = [
    "Barts Health NHS Trust",
    "University Hospitals Birmingham",
    "Leeds Teaching Hospitals",
    "Manchester University NHS FT",
    "King's College Hospital",
    "Sheffield Teaching Hospitals",
    "Nottingham University Hospitals",
    "Bristol Royal Infirmary",
    "Newcastle Upon Tyne Hospitals",
    "Liverpool University Hospitals",
    "Oxford University Hospitals",
    "Cambridge University Hospitals",
    "Royal Free London",
    "St George's University Hospitals",
    "Salford Royal NHS FT",
]

REGIONS = {
    "Barts Health NHS Trust": "London",
    "University Hospitals Birmingham": "Midlands",
    "Leeds Teaching Hospitals": "Yorkshire & Humber",
    "Manchester University NHS FT": "North West",
    "King's College Hospital": "London",
    "Sheffield Teaching Hospitals": "Yorkshire & Humber",
    "Nottingham University Hospitals": "Midlands",
    "Bristol Royal Infirmary": "South West",
    "Newcastle Upon Tyne Hospitals": "North East",
    "Liverpool University Hospitals": "North West",
    "Oxford University Hospitals": "South East",
    "Cambridge University Hospitals": "East of England",
    "Royal Free London": "London",
    "St George's University Hospitals": "London",
    "Salford Royal NHS FT": "North West",
}

YEARS = list(range(2018, 2025))
MONTHS = list(range(1, 13))

# Base monthly attendances per trust (Type 1 major A&E)
BASE_ATTENDANCES = {
    "Barts Health NHS Trust": 18500,
    "University Hospitals Birmingham": 16000,
    "Leeds Teaching Hospitals": 14500,
    "Manchester University NHS FT": 17000,
    "King's College Hospital": 15000,
    "Sheffield Teaching Hospitals": 12000,
    "Nottingham University Hospitals": 11500,
    "Bristol Royal Infirmary": 10500,
    "Newcastle Upon Tyne Hospitals": 11000,
    "Liverpool University Hospitals": 13000,
    "Oxford University Hospitals": 10000,
    "Cambridge University Hospitals": 9500,
    "Royal Free London": 12500,
    "St George's University Hospitals": 11000,
    "Salford Royal NHS FT": 9000,
}

# NHS 4-hour target: 95% of patients seen within 4 hours
# Real performance has declined from ~94% (2018) to ~68% (2023)
NATIONAL_PERFORMANCE = {
    2018: 88.0,
    2019: 86.0,
    2020: 84.5,  # COVID disruption
    2021: 76.0,  # Post-COVID backlog
    2022: 72.0,
    2023: 68.0,
    2024: 70.5,  # Slight recovery
}

# Seasonal multipliers for attendance (winter pressure + summer)
SEASONAL_ATTENDANCE = {
    1: 1.15,  # Jan — winter pressure
    2: 1.10,
    3: 1.05,
    4: 0.97,
    5: 0.95,
    6: 0.98,
    7: 1.05,  # Summer — injuries, heat
    8: 1.08,
    9: 0.97,
    10: 1.00,
    11: 1.08,  # Winter ramp-up
    12: 1.12,  # Christmas/New Year
}

# Seasonal impact on breach rate (winter = worse performance)
SEASONAL_BREACH_IMPACT = {
    1: +6.0, 2: +4.5, 3: +2.0, 4: -1.0,
    5: -2.5, 6: -2.0, 7: -0.5, 8: +0.5,
    9: -1.5, 10: +0.5, 11: +3.0, 12: +5.0,
}


def build_monthly_ae():
    rows = []
    for trust in TRUSTS:
        base_att = BASE_ATTENDANCES[trust]
        # Trust-specific performance offset (some trusts consistently better/worse)
        trust_offset = np.random.uniform(-4.0, 4.0)

        for year in YEARS:
            nat_perf = NATIONAL_PERFORMANCE[year]
            for month in MONTHS:
                # Attendances
                seasonal_att = SEASONAL_ATTENDANCE[month]
                year_growth = 1 + (year - 2018) * 0.018  # ~1.8% annual growth
                if year == 2020 and month in [4, 5, 6]:
                    year_growth *= 0.55  # COVID lockdown drop
                elif year == 2020 and month in [7, 8, 9]:
                    year_growth *= 0.80
                noise_att = np.random.uniform(0.96, 1.04)
                attendances = int(base_att * seasonal_att * year_growth * noise_att)

                # 4-hour performance (% seen within 4 hours)
                seasonal_breach = SEASONAL_BREACH_IMPACT[month]
                noise_perf = np.random.uniform(-2.0, 2.0)
                perf_4hr = nat_perf + trust_offset - seasonal_breach + noise_perf
                perf_4hr = max(45.0, min(99.0, perf_4hr))

                # Breach count
                breach_rate = (100 - perf_4hr) / 100
                breaches = int(attendances * breach_rate)

                # Admissions (~25-30% of attendances)
                admission_rate = np.random.uniform(0.24, 0.31)
                admissions = int(attendances * admission_rate)

                # Median wait time (minutes) — inversely related to performance
                if perf_4hr >= 90:
                    median_wait = np.random.uniform(45, 75)
                elif perf_4hr >= 80:
                    median_wait = np.random.uniform(75, 110)
                elif perf_4hr >= 70:
                    median_wait = np.random.uniform(110, 155)
                else:
                    median_wait = np.random.uniform(155, 220)

                # Ambulance handover delays >30 min (post-2021 metric)
                handover_delay_pct = max(0, (100 - perf_4hr) * 0.35 + np.random.uniform(-3, 3))
                handover_delay_pct = min(handover_delay_pct, 60)

                rows.append({
                    "trust": trust,
                    "region": REGIONS[trust],
                    "year": year,
                    "month": month,
                    "month_name": pd.Timestamp(year=year, month=month, day=1).strftime("%b"),
                    "period": f"{year}-{month:02d}",
                    "attendances": attendances,
                    "admissions": admissions,
                    "breaches": breaches,
                    "perf_4hr_pct": round(perf_4hr, 1),
                    "breach_rate_pct": round(breach_rate * 100, 1),
                    "admission_rate_pct": round(admission_rate * 100, 1),
                    "median_wait_mins": round(median_wait, 0),
                    "ambulance_handover_delay_pct": round(handover_delay_pct, 1),
                })

    return pd.DataFrame(rows)


def build_trust_summary(df):
    """Annual summary per trust — for ranking and comparison."""
    summary = df.groupby(["trust", "region", "year"]).agg(
        total_attendances=("attendances", "sum"),
        total_breaches=("breaches", "sum"),
        total_admissions=("admissions", "sum"),
        avg_4hr_performance=("perf_4hr_pct", "mean"),
        avg_median_wait=("median_wait_mins", "mean"),
        avg_handover_delay=("ambulance_handover_delay_pct", "mean"),
        worst_month_performance=("perf_4hr_pct", "min"),
        best_month_performance=("perf_4hr_pct", "max"),
    ).reset_index()

    summary["annual_breach_rate_pct"] = (
        summary["total_breaches"] / summary["total_attendances"] * 100
    ).round(1)
    summary["avg_4hr_performance"] = summary["avg_4hr_performance"].round(1)
    summary["avg_median_wait"] = summary["avg_median_wait"].round(0)
    summary["avg_handover_delay"] = summary["avg_handover_delay"].round(1)
    summary["performance_gap"] = (95 - summary["avg_4hr_performance"]).round(1)

    return summary


def build_seasonal_summary(df):
    """Average metrics by month across all trusts — for seasonal pattern analysis."""
    seasonal = df.groupby(["month", "month_name"]).agg(
        avg_attendances=("attendances", "mean"),
        avg_perf_4hr=("perf_4hr_pct", "mean"),
        avg_breach_rate=("breach_rate_pct", "mean"),
        avg_median_wait=("median_wait_mins", "mean"),
    ).reset_index()
    seasonal["avg_attendances"] = seasonal["avg_attendances"].round(0)
    seasonal["avg_perf_4hr"] = seasonal["avg_perf_4hr"].round(1)
    seasonal["avg_breach_rate"] = seasonal["avg_breach_rate"].round(1)
    seasonal["avg_median_wait"] = seasonal["avg_median_wait"].round(0)
    return seasonal.sort_values("month")


def build_national_trend(df):
    """Monthly national aggregate trend."""
    nat = df.groupby(["year", "month", "month_name", "period"]).agg(
        total_attendances=("attendances", "sum"),
        total_breaches=("breaches", "sum"),
        avg_perf_4hr=("perf_4hr_pct", "mean"),
        avg_median_wait=("median_wait_mins", "mean"),
        avg_handover_delay=("ambulance_handover_delay_pct", "mean"),
    ).reset_index()
    nat["breach_rate_pct"] = (nat["total_breaches"] / nat["total_attendances"] * 100).round(1)
    nat["avg_perf_4hr"] = nat["avg_perf_4hr"].round(1)
    nat["avg_median_wait"] = nat["avg_median_wait"].round(0)
    return nat.sort_values(["year", "month"])


def build_breach_predictor_features(df):
    """
    Feature table for breach rate prediction model.
    Features: month, year, trust size, prior month performance,
              rolling 3-month attendance trend.
    """
    df_sorted = df.sort_values(["trust", "year", "month"]).copy()
    df_sorted["prev_month_perf"] = df_sorted.groupby("trust")["perf_4hr_pct"].shift(1)
    df_sorted["prev_month_breach"] = df_sorted.groupby("trust")["breach_rate_pct"].shift(1)
    df_sorted["rolling_3m_att"] = (
        df_sorted.groupby("trust")["attendances"]
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
        .round(0)
    )
    df_sorted["att_growth_pct"] = (
        df_sorted.groupby("trust")["attendances"].pct_change() * 100
    ).round(2)
    df_sorted["is_winter"] = df_sorted["month"].isin([11, 12, 1, 2]).astype(int)
    df_sorted["is_covid_period"] = (
        (df_sorted["year"] == 2020) & (df_sorted["month"].isin([3, 4, 5, 6]))
    ).astype(int)
    return df_sorted.dropna(subset=["prev_month_perf"])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    out = "/home/claude/nhs-ae-analysis/data/processed"
    os.makedirs(out, exist_ok=True)

    print("Generating monthly A&E data...")
    df = build_monthly_ae()
    df.to_csv(f"{out}/monthly_ae.csv", index=False)
    print(f"  monthly_ae.csv — {len(df)} rows")

    print("Building trust annual summary...")
    trust_summary = build_trust_summary(df)
    trust_summary.to_csv(f"{out}/trust_summary.csv", index=False)
    print(f"  trust_summary.csv — {len(trust_summary)} rows")

    print("Building seasonal summary...")
    seasonal = build_seasonal_summary(df)
    seasonal.to_csv(f"{out}/seasonal_summary.csv", index=False)
    print(f"  seasonal_summary.csv — {len(seasonal)} rows")

    print("Building national trend...")
    national = build_national_trend(df)
    national.to_csv(f"{out}/national_trend.csv", index=False)
    print(f"  national_trend.csv — {len(national)} rows")

    print("Building predictor features...")
    features = build_breach_predictor_features(df)
    features.to_csv(f"{out}/breach_predictor_features.csv", index=False)
    print(f"  breach_predictor_features.csv — {len(features)} rows")

    # JSON for dashboard
    dashboard_data = {
        "monthly": df.to_dict(orient="records"),
        "trust_summary": trust_summary.to_dict(orient="records"),
        "seasonal": seasonal.to_dict(orient="records"),
        "national": national.to_dict(orient="records"),
    }
    with open(f"{out}/dashboard_data.json", "w") as f:
        json.dump(dashboard_data, f, separators=(",", ":"))
    print(f"  dashboard_data.json written")

    print("\n── 2024 Trust Performance Ranking ──")
    rank = trust_summary[trust_summary["year"] == 2024].sort_values("avg_4hr_performance", ascending=False)
    print(rank[["trust", "avg_4hr_performance", "annual_breach_rate_pct", "avg_median_wait"]].to_string(index=False))

    print("\n── Seasonal Breach Pattern ──")
    print(seasonal[["month_name", "avg_perf_4hr", "avg_breach_rate", "avg_median_wait"]].to_string(index=False))


# ── NHS API Stub (production use) ─────────────────────────────────────────────

def fetch_nhs_ae_data(date_from="2018-04", date_to="2024-12"):
    """
    Stub for fetching real NHS England A&E data.

    NHS publishes monthly A&E CSV at:
    https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/

    Direct CSV URL pattern:
    https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/01/Monthly-AE-Type-1-Tables-Jan24.csv

    Steps:
    1. Download monthly CSV files from the URL above
    2. Concatenate into a single dataframe
    3. Standardise column names to match this project's schema
    4. Replace the synthetic data in 01_generate_data.py with this function
    """
    import urllib.request
    base_url = "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/"
    # Implementation: loop through months, download each CSV, concat
    print(f"Fetching NHS A&E data from {date_from} to {date_to}...")
    print("Note: Replace this stub with real download logic for production use.")
    return pd.DataFrame()


if __name__ == "__main__":
    main()
