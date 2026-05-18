"""Mathematical foundations of time series using Polars and DuckDB.

All descriptive statistics (mean, var, std, skewness, kurtosis, autocorrelation)
are computed via DuckDB aggregate functions — no pandas Series methods needed.
"""

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import polars as pl


def calculate_statistical_properties(series: pl.Series) -> dict:
    """Descriptive stats via DuckDB — replaces pandas .mean()/.var()/.skew() etc."""
    pl.DataFrame({"idx": range(len(series)), "value": series})
    props = (
        duckdb.sql("""
        WITH lagged AS (
            SELECT value, LAG(value, 1) OVER (ORDER BY idx) AS value_lag1
            FROM df
        )
        SELECT
            AVG(d.value)                                AS mean,
            VAR_SAMP(d.value)                           AS variance,
            STDDEV_SAMP(d.value)                        AS std,
            SKEWNESS(d.value)                           AS skewness,
            KURTOSIS(d.value)                           AS kurtosis,
            (SELECT CORR(value, value_lag1)
             FROM lagged
             WHERE value_lag1 IS NOT NULL)              AS autocorr_lag1
        FROM df d
    """)
        .pl()
        .row(0, named=True)
    )
    return props


def calculate_autocorrelation(series: pl.Series, max_lag: int = 10) -> pl.DataFrame:
    """ACF for lags 1..max_lag via DuckDB CORR + LAG window functions."""
    pl.DataFrame({"idx": range(len(series)), "value": series})
    lag_cols = ",\n            ".join(
        f"LAG(value, {lag}) OVER (ORDER BY idx) AS lag_{lag}"
        for lag in range(1, max_lag + 1)
    )
    corr_cols = ",\n        ".join(
        f"CORR(value, lag_{lag}) AS acf_{lag}" for lag in range(1, max_lag + 1)
    )
    row = (
        duckdb.sql(f"""
        WITH lagged AS (
            SELECT value, {lag_cols}
            FROM df
        )
        SELECT {corr_cols}
        FROM lagged
    """)
        .pl()
        .row(0, named=True)
    )
    return pl.DataFrame(
        {
            "lag": list(range(1, max_lag + 1)),
            "acf": [row[f"acf_{lag}"] for lag in range(1, max_lag + 1)],
        }
    )


def plot_mathematical_properties(
    series: pl.Series,
    acf: pl.DataFrame,
    title: str,
    output_path: Path,
):
    if not plot:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=False)
    ax1.plot(series.to_list(), color="#4A90A4", linewidth=1.2)
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Value")
    ax1.set_title(title)
    ax2.bar(
        acf["lag"].to_list(),
        acf["acf"].to_list(),
        color="#D4A574",
        alpha=0.7,
        edgecolor="none",
        width=0.6,
    )
    ax2.axhline(0, color="black", linewidth=0.5, alpha=0.3)
    ax2.set_xlabel("Lag")
    ax2.set_ylabel("ACF")
    ax2.set_title("Autocorrelation Function")
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches="tight", facecolor="white")
    plt.close()
