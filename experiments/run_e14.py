"""E1: fleet-size sweep + E4: headroom sweep (paper Fig. 4 / Sec. VI.IV).

Fleet subsets are nested and documented here (paper does not name its subsets;
we span the CI spread: clean SE, dirty PL, mid/large CISO first).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.driver import run_trace

SUBSETS = {
    3: ["SE", "PL", "CISO"],
    5: ["SE", "PL", "CISO", "DE", "PJM"],
    8: ["SE", "PL", "CISO", "DE", "PJM", "ES", "MISO", "ISNE"],
    11: ["CISO", "ERCO", "ISNE", "MISO", "PJM", "EPE",
          "DE", "ES", "NL", "PL", "SE"],
}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--data", default="data")
    a.add_argument("--out", default="results_e14.csv")
    a.add_argument("--seeds", default="0,1,2")
    a.add_argument("--trace", default="conv")
    a.add_argument("--mode", default="e1", choices=["e1", "e4"])
    a.add_argument("--days", default=None)
    a.add_argument("--max-rows", type=int, default=None)
    o = a.parse_args()
    seeds = [int(s) for s in o.seeds.split(",")]
    days = range(7) if o.days is None else [int(d) for d in o.days.split(",")]
    policies = ["carbonserve", "oracle"]
    if o.mode == "e1":
        for k, cands in SUBSETS.items():
            out = o.out.replace(".csv", f"_fleet{k}.csv")
            run_trace(o.trace, o.data, cands, policies, seeds, out,
                      days=days, max_rows=o.max_rows)
    else:
        for h in (1.5, 2.5, 4.0):
            out = o.out.replace(".csv", f"_head{h}.csv")
            run_trace(o.trace, o.data, SUBSETS[11], policies, seeds, out,
                      headroom=h, days=days, max_rows=o.max_rows)


if __name__ == "__main__":
    main()
