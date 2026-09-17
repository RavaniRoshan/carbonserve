"""E3: forecast-noise sweep {0.5,1,2,4}x (paper Table III / Fig. 3)."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.driver import run_trace, GRIDS


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--data", default="data")
    a.add_argument("--out", default="results_e3.csv")
    a.add_argument("--seeds", default="0,1,2")
    a.add_argument("--trace", default="conv")
    a.add_argument("--noises", default="0.5,1.0,2.0,4.0")
    a.add_argument("--days", default=None)
    a.add_argument("--max-rows", type=int, default=None)
    o = a.parse_args()
    seeds = [int(s) for s in o.seeds.split(",")]
    days = range(7) if o.days is None else [int(d) for d in o.days.split(",")]
    policies = ["carbonserve", "casper", "greedy"]
    for nz in [float(x) for x in o.noises.split(",")]:
        out = o.out.replace(".csv", f"_n{nz}.csv")
        run_trace(o.trace, o.data, GRIDS, policies, seeds, out,
                  noise=nz, days=days, max_rows=o.max_rows)


if __name__ == "__main__":
    main()
