"""Physics-consistency checks mirroring paper Sec. VI.V (fails loudly)."""
import csv
import glob
import statistics
import sys

CI_LO, CI_HI = 44, 478


def load(pattern):
    rows = []
    for p in glob.glob(pattern):
        rows.extend(csv.DictReader(open(p)))
    return rows


def main():
    pat = sys.argv[1] if len(sys.argv) > 1 else "results_e2_conv.csv"
    rows = load(pat)
    assert rows, "no rows; run an experiment first"
    fails = []
    for p in ("local", "carbonserve"):
        rs = [r for r in rows if r["policy"] == p]
        if not rs:
            continue
        c = statistics.mean(float(r["carbon_kg"]) for r in rs)
        e = statistics.mean(float(r["energy_kwh"]) for r in rs)
        impl = c / e * 1000 if e else 0
        ok = CI_LO <= impl <= CI_HI
        print(f"{p}: implied traffic-weighted CI {impl:.0f} g/kWh "
              f"({'OK' if ok else 'OUT OF RANGE'})")
        if not ok:
            fails.append(p)
        att = statistics.mean(float(r["viol_rate"]) for r in rs)
        print(f"{p}: mean viol_rate {att:.4f}")
    # oracle must never misroute on perfect information... except epoch-boundary
    # staleness (paper notes small residual); bound it instead of asserting 0.
    ors = [r for r in rows if r["policy"] == "oracle"]
    if ors:
        mr = statistics.mean(float(r["misroute_rate"]) for r in ors)
        print(f"oracle mean misroute_rate {mr:.4f} (must be < 0.02)")
        if mr >= 0.02:
            fails.append("oracle-misroute")
    if fails:
        print("VERIFY FAIL:", fails)
        sys.exit(1)
    print("verify PASS")


if __name__ == "__main__":
    main()
