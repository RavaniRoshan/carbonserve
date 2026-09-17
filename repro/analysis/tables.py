"""Aggregate per-seed run CSVs into paper-style headline tables (stdout)."""
import csv
import glob
import statistics
import sys


def load(pattern):
    rows = []
    for p in glob.glob(pattern):
        rows.extend(csv.DictReader(open(p)))
    return rows


def agg(rows, policy):
    rs = [r for r in rows if r["policy"] == policy]
    out = {}
    for m in ("carbon_kg", "p95_ttft_ms", "viol_rate", "offload_frac",
              "misroute_rate", "misroute_penalty_kg", "energy_kwh"):
        v = [float(r[m]) for r in rs]
        out[m] = (statistics.mean(v),
                  statistics.stdev(v) if len(v) > 1 else 0.0)
    return out


def main():
    pat = sys.argv[1] if len(sys.argv) > 1 else "results_e2_conv.csv"
    base = sys.argv[2] if len(sys.argv) > 2 else "local"
    rows = load(pat)
    b = agg(rows, base)["carbon_kg"][0]
    print(f"{'policy':22s} {'carbon_kg':>12s} {'save%':>7s} "
          f"{'p95ttft':>8s} {'misroute':>8s} {'pen_kg':>8s}")
    for p in ("local", "greedy", "casper", "carbonserve", "oracle"):
        try:
            a = agg(rows, p)
        except (ValueError, statistics.StatisticsError, IndexError):
            continue
        c = a["carbon_kg"][0]
        print(f"{p:22s} {c:12.1f} {100*(1-c/b):7.1f} "
              f"{a['p95_ttft_ms'][0]:8.0f} {100*a['misroute_rate'][0]:8.1f} "
              f"{a['misroute_penalty_kg'][0]:8.2f}")


if __name__ == "__main__":
    main()
