"""E2: policy comparison on both traces (paper Table II)."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.driver import run_trace, GRIDS


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--data", default="data")
    a.add_argument("--out", default="results_e2.csv")
    a.add_argument("--seeds", default="0,1,2")
    a.add_argument("--traces", default="conv,code")
    a.add_argument("--days", default=None)   # e.g. "6" for smoke
    a.add_argument("--max-rows", type=int, default=None)
    o = a.parse_args()
    seeds = [int(s) for s in o.seeds.split(",")]
    days = range(7) if o.days is None else [int(d) for d in o.days.split(",")]
    policies = ["local", "greedy", "casper", "carbonserve", "oracle"]
    first = True
    for trace in o.traces.split(","):
        out = o.out if len(o.traces.split(",")) == 1 else o.out.replace(".csv", f"_{trace}.csv")
        run_trace(trace, o.data, GRIDS, policies, seeds, out,
                  days=days, max_rows=o.max_rows)
        first = False


if __name__ == "__main__":
    main()
