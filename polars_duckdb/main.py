#!/usr/bin/env python3
"""Mathematical foundations of time series — Polars + DuckDB rewrite."""

import sys
import argparse
import yaml
import logging
import numpy as np
import polars as pl
from datetime import date, timedelta
from pathlib import Path

from core import calculate_statistical_properties, calculate_autocorrelation, plot_mathematical_properties

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_config(config_path: Path = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Math foundations — Polars + DuckDB")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--data-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = Path(args.output_dir) if args.output_dir else Path(config["output"]["figures_dir"])
    output_dir.mkdir(exist_ok=True)

    if args.data_path and args.data_path.exists():
        df = pl.read_csv(args.data_path, try_parse_dates=True)
        series = df[config["data"]["value_column"]]
    elif config["data"]["generate_synthetic"]:
        rng = np.random.default_rng(config["data"]["seed"])
        n = config["data"]["n_periods"]
        trend = np.linspace(100, 120, n)
        series = pl.Series("value", (trend + rng.normal(0, 5, n)).tolist())
    else:
        raise ValueError("No data source specified")

    props = calculate_statistical_properties(series)
    logging.info("Statistical Properties:")
    logging.info(f"  Mean       : {props['mean']:.4f}")
    logging.info(f"  Variance   : {props['variance']:.4f}")
    logging.info(f"  Std Dev    : {props['std']:.4f}")
    logging.info(f"  Skewness   : {props['skewness']:.4f}")
    logging.info(f"  Kurtosis   : {props['kurtosis']:.4f}")
    logging.info(f"  ACF lag-1  : {props['autocorr_lag1']:.4f}")

    if config["analysis"]["calculate_acf"]:
        acf = calculate_autocorrelation(series, config["analysis"]["max_lag"])
        logging.info(f"\nACF (lags 1–{config['analysis']['max_lag']}):")
        for row in acf.iter_rows(named=True):
            logging.info(f"  lag {row['lag']:2d}: {row['acf']:.4f}")

        plot_mathematical_properties(
            series, acf,
            "Mathematical Foundations of Time Series",
            output_dir / "mathematical_properties.png",
        )

    logging.info(f"\nAnalysis complete. Figures saved to {output_dir}")


if __name__ == "__main__":
    main()
