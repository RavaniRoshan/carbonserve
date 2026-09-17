"""Grid carbon data: EnsembleCI direct-emission series + persistence forecaster.

Independent reimplementation for CarbonServe reproduction. Data source:
https://github.com/emmayly/EnsembleCI (EIA/ENTSO-E derived, CC-BY-compatible
public research data). We use the *_direct_emissions.csv series (average grid CI,
direct emission factors), exactly as the paper's accounting does.
"""
import csv
import os
import statistics

GRIDS = ["CISO", "ERCO", "ISNE", "MISO", "PJM", "EPE",
         "DE", "ES", "NL", "PL", "SE"]
# UTC offsets in May (DST): US PDT -7, MDT -6, CDT -5, EDT -4; EU CEST +2.
TZ = {"CISO": -7, "ERCO": -5, "ISNE": -4, "MISO": -5, "PJM": -4, "EPE": -6,
      "DE": 2, "ES": 2, "NL": 2, "PL": 2, "SE": 2}

DATA_DIR = os.environ.get("CARBONSERVE_DATA",
                           os.path.join(os.path.dirname(__file__), "..", "data"))


def load_series(grid, data_dir=DATA_DIR):
    """Hourly (epoch_s, ci) sorted list from <GRID>_direct_emissions.csv."""
    path = os.path.join(data_dir, "ensembleci", grid, f"{grid}_direct_emissions.csv")
    import datetime
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            ts = r["UTC time"].strip()
            dt = datetime.datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=datetime.timezone.utc)
            out.append((int(dt.timestamp()), float(r["carbon_intensity"])))
    out.sort()
    return out


def slice_week(series, start_epoch, hours=168):
    """Hourly CI for [start, start+hours). Returns list of (epoch, ci)."""
    by_h = {e: c for e, c in series}
    return [(start_epoch + 3600 * h, by_h[start_epoch + 3600 * h])
            for h in range(hours)]


def persistence_errors(series, end_epoch, years=2):
    """Day-ahead persistence errors over `years` before end_epoch (in g/kWh)."""
    by_h = {e: c for e, c in series}
    errs = []
    t = end_epoch - years * 365 * 86400
    while t < end_epoch - 86400:
        if t in by_h and t + 86400 in by_h:
            errs.append(by_h[t + 86400] - by_h[t])
        t += 3600
    return errs


def sigma_from_errors(errs):
    return statistics.pstdev(errs) if len(errs) > 1 else 0.0


def mape(forecast, truth):
    n = len(truth)
    return sum(abs(f - t) / t for f, t in zip(forecast, truth) if t) / n * 100
