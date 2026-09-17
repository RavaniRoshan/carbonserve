"""Shared harness: week replay, provisioning, epoch forecasts, CSV output.

Day-chunked streaming keeps memory flat: for each CI day, one pass over the
trace keeps only that weekday's arrivals (three compact arrays), then every
(policy, seed) replays them through its own fleet. Region backlogs persist
across days per run. Per-request RNG streams stay aligned across policies
(identical draw order), so seed variance is meaningful.
"""
import csv
import math
import os
import statistics
import sys
from array import array

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import grids, workload
from sim import policies as P
from sim.engine import Region, Run, STEP, EPOCH, work_gs

CI_START = 1620604800  # 2021-05-10 00:00 UTC (Monday)
N_HOURS = 168
GRIDS = grids.GRIDS

POLICIES = {
    "local": lambda fc, bands, truth, cands: P.local_weights(cands[0], cands),
    "greedy": lambda fc, bands, truth, cands: P.greedy_weights(fc, cands),
    "casper": lambda fc, bands, truth, cands: P.casper_weights(fc, cands),
    "carbonserve": lambda fc, bands, truth, cands: P.carbonserve_weights(fc, bands, cands),
    "oracle": lambda fc, bands, truth, cands: P.oracle_weights(truth, cands),
}


def load_week(data_dir):
    series = {g: grids.load_series(g, data_dir) for g in GRIDS}
    week = {g: [c for _, c in grids.slice_week(series[g], CI_START, N_HOURS)]
            for g in GRIDS}
    sig, mapes = {}, {}
    for g in GRIDS:
        errs = grids.persistence_errors(series[g], CI_START)
        sig[g] = grids.sigma_from_errors(errs)
        fc = [c for _, c in grids.slice_week(series[g], CI_START - 86400, N_HOURS)]
        mapes[g] = grids.mape(fc, week[g])
    print(f"persistence MAPE mean: {statistics.mean(mapes.values()):.2f}%",
          flush=True)
    return series, week, sig


def day_arrivals(trace, data_dir, day, max_rows=None):
    """Three parallel arrays (sec-in-day, cin, cout) for one CI weekday."""
    sec, cin, cout = array("I"), array("I"), array("I")
    for t, c, o in workload.stream_requests(trace, data_dir, max_rows):
        if (t - CI_START) // 86400 == day:
            sec.append(t - (CI_START + day * 86400))
            cin.append(c)
            cout.append(o)
    return sec, cin, cout


def home_cdf(hour, cands, weekend=False):
    w = workload.business_weights(hour, cands, weekend)
    s = sum(w.values())
    out, acc = [], 0.0
    for g in cands:
        acc += w[g] / s
        out.append((acc, g))
    return out


def day_peak(sec, cin, cout, cands, weekend=False):
    """Peak 5-min home work (gpu-s/s) for one day (expected shares)."""
    peak = {g: 0.0 for g in cands}
    cur = {g: 0.0 for g in cands}
    epoch = -1
    for i in range(len(sec)):
        e = sec[i] // EPOCH
        if e != epoch:
            for g in cands:
                peak[g] = max(peak[g], cur[g] / EPOCH)
                cur[g] = 0.0
            epoch = e
        h = int((CI_START + sec[i]) // 3600 % 24)
        w = workload.business_weights(h, cands, weekend)
        s = sum(w.values())
        wk = work_gs(cin[i], cout[i])
        for g in cands:
            cur[g] += wk * w[g] / s
    for g in cands:
        peak[g] = max(peak[g], cur[g] / EPOCH)
    return peak


def run_trace(trace, data_dir, cands, policy_names, seeds, out_path,
              noise=1.0, headroom=2.5, days=None, max_rows=None):
    series, week, sig = load_week(data_dir)
    # O(1) hourly index into each full series (hourly since 2019-01-01 UTC)
    base = {g: series[g][0][0] for g in GRIDS}
    hourly = {g: [c for _, c in series[g]] for g in GRIDS}

    def truth_24h_ago(g, glob_h):
        return hourly[g][(CI_START + glob_h * 3600 - 86400 - base[g]) // 3600]

    days = range(7) if days is None else days
    day_cache, peak_all = {}, None
    for d in days:
        sec, cin, cout = day_arrivals(trace, data_dir, d, max_rows)
        day_cache[d] = (sec, cin, cout)
        if len(sec):
            pk = day_peak(sec, cin, cout, cands, weekend=(d >= 5))
            peak_all = pk if peak_all is None else {
                g: max(peak_all[g], pk[g]) for g in cands}
    if peak_all is None:
        raise SystemExit("no arrivals loaded; check data/trace path")
    ngpu = {g: max(1, math.ceil(headroom * peak_all[g])) for g in cands}
    print(f"provisioned GPUs: {ngpu}", flush=True)
    fleets = {}
    for p in policy_names:
        for s in seeds:
            regs = [Region(g, week[g], ngpu[g]) for g in cands]
            fleets[(p, s)] = Run(regs, 1000 + s)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["trace", "policy", "seed", "n",
                                          "carbon_kg", "energy_kwh",
                                          "p95_ttft_ms", "p99_tpot_ms",
                                          "viol_rate", "offload_frac",
                                          "misroute_rate", "misroute_penalty_kg",
                                          "max_util"])
        w.writeheader()
        for d in days:
            sec, cin, cout = day_cache[d]
            n_steps = 86400 // STEP
            order = sorted(range(len(sec)), key=lambda i: sec[i])
            idx = [[] for _ in range(n_steps)]
            for i in order:
                idx[min(sec[i] // STEP, n_steps - 1)].append(i)
            for step in range(n_steps):
                glob_h = d * 24 + (step * STEP) // 3600
                ci_now = {g: week[g][glob_h] for g in cands}
                if step % (EPOCH // STEP) == 0:
                    fc0, bands0 = P.epoch_forecast(
                        {g: truth_24h_ago(g, glob_h) for g in cands},
                        sig, noise, None, ci_now)
                    W = {p: POLICIES[p](fc0, bands0, ci_now, cands)
                         for p in policy_names}
                arr = idx[step]
                utc_h = int((CI_START + d * 86400 + step * STEP) // 3600 % 24)
                cdf = home_cdf(utc_h, cands, weekend=(d >= 5))
                reqs = [(cin[i], cout[i]) for i in arr]
                for (p, s), run in fleets.items():
                    run.step(reqs, W[p], ci_now, cdf, P.RHO_MAX)
                if (step + 1) * STEP % 3600 == 0:
                    for run in fleets.values():
                        for R in run.regions.values():
                            R.close_hour(glob_h)
            for (p, s), run in fleets.items():
                row = {"trace": trace, "policy": p, "seed": s,
                       **run.summary()}
                w.writerow({k: (round(v, 6) if isinstance(v, float) else v)
                            for k, v in row.items()})
                f.flush()
    print(f"wrote {out_path}", flush=True)
