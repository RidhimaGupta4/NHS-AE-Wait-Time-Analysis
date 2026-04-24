-- ============================================================
-- NHS A&E Wait Time Analysis — SQL Queries
-- ============================================================
-- Compatible with: SQLite, DuckDB, PostgreSQL
--
-- Load tables (DuckDB):
--   CREATE TABLE monthly_ae    AS SELECT * FROM read_csv_auto('data/processed/monthly_ae.csv');
--   CREATE TABLE trust_summary AS SELECT * FROM read_csv_auto('data/processed/trust_summary.csv');
--   CREATE TABLE seasonal      AS SELECT * FROM read_csv_auto('data/processed/seasonal_summary.csv');
--   CREATE TABLE national      AS SELECT * FROM read_csv_auto('data/processed/national_trend.csv');
-- ============================================================


-- ── 1. TRUST PERFORMANCE LEAGUE TABLE (2024) ───────────────────────────────
-- Which trusts are meeting / missing the 95% NHS target?

SELECT
    trust,
    region,
    ROUND(avg_4hr_performance, 1)     AS perf_4hr_pct,
    ROUND(annual_breach_rate_pct, 1)  AS breach_rate_pct,
    ROUND(avg_median_wait, 0)         AS median_wait_mins,
    total_attendances,
    total_breaches,
    ROUND(performance_gap, 1)         AS gap_to_95pct_target,
    CASE
        WHEN avg_4hr_performance >= 90 THEN 'Meeting Target'
        WHEN avg_4hr_performance >= 80 THEN 'Near Target'
        WHEN avg_4hr_performance >= 70 THEN 'Underperforming'
        ELSE 'Critical'
    END AS performance_band
FROM trust_summary
WHERE year = 2024
ORDER BY avg_4hr_performance DESC;


-- ── 2. NATIONAL PERFORMANCE DECLINE 2018–2024 ─────────────────────────────
-- Year-by-year deterioration against the 95% NHS constitutional standard

SELECT
    year,
    ROUND(AVG(avg_perf_4hr), 1)               AS national_avg_4hr_pct,
    ROUND(95 - AVG(avg_perf_4hr), 1)          AS gap_to_target,
    SUM(total_attendances)                     AS total_annual_attendances,
    SUM(total_breaches)                        AS total_annual_breaches,
    ROUND(SUM(total_breaches) * 100.0
          / SUM(total_attendances), 1)         AS national_breach_rate_pct
FROM national
GROUP BY year
ORDER BY year;


-- ── 3. SEASONAL PATTERN ANALYSIS ──────────────────────────────────────────
-- Winter pressure quantified: how much worse is Jan vs May?

SELECT
    month,
    month_name,
    ROUND(avg_perf_4hr, 1)          AS avg_4hr_performance_pct,
    ROUND(avg_breach_rate, 1)       AS avg_breach_rate_pct,
    ROUND(avg_median_wait, 0)       AS avg_median_wait_mins,
    ROUND(avg_attendances, 0)       AS avg_monthly_attendances,
    CASE
        WHEN month IN (12, 1, 2)    THEN 'Peak Winter'
        WHEN month IN (11, 3)       THEN 'Winter Shoulder'
        WHEN month IN (7, 8)        THEN 'Summer Peak'
        ELSE 'Baseline'
    END AS season_band
FROM seasonal
ORDER BY month;


-- ── 4. WORST WINTER vs BEST SUMMER GAP ────────────────────────────────────
-- Quantify the seasonal swing in performance

SELECT
    'Peak Winter (Dec-Jan-Feb)' AS period,
    ROUND(AVG(avg_perf_4hr), 1) AS avg_performance,
    ROUND(AVG(avg_breach_rate), 1) AS avg_breach_rate,
    ROUND(AVG(avg_median_wait), 0) AS avg_wait_mins
FROM seasonal WHERE month IN (12, 1, 2)
UNION ALL
SELECT
    'Best Summer (Apr-May-Jun)',
    ROUND(AVG(avg_perf_4hr), 1),
    ROUND(AVG(avg_breach_rate), 1),
    ROUND(AVG(avg_median_wait), 0)
FROM seasonal WHERE month IN (4, 5, 6);


-- ── 5. TRUST-LEVEL PERFORMANCE TREND (worst 5 trusts) ─────────────────────
-- Tracks whether underperforming trusts are improving or declining

WITH ranked AS (
    SELECT trust,
           ROUND(AVG(avg_4hr_performance), 1) AS overall_avg
    FROM trust_summary
    GROUP BY trust
    ORDER BY overall_avg ASC
    LIMIT 5
)
SELECT
    ts.trust,
    ts.year,
    ROUND(ts.avg_4hr_performance, 1)   AS perf_4hr_pct,
    ROUND(ts.annual_breach_rate_pct, 1) AS breach_rate_pct,
    ROUND(ts.avg_median_wait, 0)        AS median_wait_mins,
    ts.total_attendances
FROM trust_summary ts
JOIN ranked r ON ts.trust = r.trust
ORDER BY ts.trust, ts.year;


-- ── 6. COVID IMPACT ANALYSIS ──────────────────────────────────────────────
-- How did 2020 lockdown affect A&E attendance and performance?

SELECT
    year,
    month,
    month_name,
    SUM(total_attendances)                                    AS attendances,
    ROUND(AVG(avg_perf_4hr), 1)                               AS perf_4hr_pct,
    ROUND(SUM(total_breaches) * 100.0 / SUM(total_attendances), 1) AS breach_rate_pct,
    ROUND(AVG(avg_median_wait), 0)                            AS median_wait_mins
FROM national
WHERE year IN (2019, 2020, 2021)
GROUP BY year, month, month_name
ORDER BY year, month;


-- ── 7. REGION-LEVEL PERFORMANCE COMPARISON ────────────────────────────────
-- Are London trusts performing differently from Northern trusts?

SELECT
    region,
    year,
    ROUND(AVG(avg_4hr_performance), 1)    AS regional_avg_perf,
    ROUND(AVG(annual_breach_rate_pct), 1) AS regional_breach_rate,
    ROUND(AVG(avg_median_wait), 0)        AS avg_wait_mins,
    SUM(total_attendances)                AS total_attendances,
    COUNT(DISTINCT trust)                 AS trust_count
FROM trust_summary
GROUP BY region, year
ORDER BY year, regional_avg_perf DESC;


-- ── 8. BREACH RATE PREDICTORS ─────────────────────────────────────────────
-- Correlation between prior month performance and current breach rate

SELECT
    CASE
        WHEN prev_month_perf >= 85 THEN 'Prior month good (>=85%)'
        WHEN prev_month_perf >= 75 THEN 'Prior month fair (75-84%)'
        WHEN prev_month_perf >= 65 THEN 'Prior month poor (65-74%)'
        ELSE 'Prior month critical (<65%)'
    END AS prior_performance_band,
    ROUND(AVG(breach_rate_pct), 1)    AS avg_current_breach_rate,
    ROUND(AVG(median_wait_mins), 0)   AS avg_wait_mins,
    COUNT(*)                          AS observation_count
FROM breach_predictor_features
GROUP BY prior_performance_band
ORDER BY avg_current_breach_rate DESC;


-- ── 9. AMBULANCE HANDOVER DELAY CORRELATION ───────────────────────────────
-- Does high ambulance delay predict A&E breach rate?

SELECT
    CASE
        WHEN ambulance_handover_delay_pct >= 30 THEN 'High delay (>=30%)'
        WHEN ambulance_handover_delay_pct >= 15 THEN 'Moderate delay (15-29%)'
        WHEN ambulance_handover_delay_pct >= 5  THEN 'Low delay (5-14%)'
        ELSE 'Minimal delay (<5%)'
    END AS handover_band,
    ROUND(AVG(perf_4hr_pct), 1)      AS avg_4hr_performance,
    ROUND(AVG(breach_rate_pct), 1)   AS avg_breach_rate,
    ROUND(AVG(median_wait_mins), 0)  AS avg_wait_mins,
    COUNT(*)                         AS observations
FROM monthly_ae
GROUP BY handover_band
ORDER BY avg_breach_rate DESC;


-- ── 10. MONTHLY ATTENDANCE VOLUME vs PERFORMANCE ──────────────────────────
-- Does higher volume directly cause worse performance?

SELECT
    CASE
        WHEN attendances >= 18000 THEN 'Very High (18k+)'
        WHEN attendances >= 14000 THEN 'High (14k-18k)'
        WHEN attendances >= 10000 THEN 'Medium (10k-14k)'
        ELSE 'Lower (<10k)'
    END AS volume_band,
    ROUND(AVG(perf_4hr_pct), 1)     AS avg_4hr_performance,
    ROUND(AVG(breach_rate_pct), 1)  AS avg_breach_rate,
    ROUND(AVG(median_wait_mins), 0) AS avg_wait_mins,
    COUNT(*)                        AS observations
FROM monthly_ae
GROUP BY volume_band
ORDER BY avg_breach_rate DESC;
