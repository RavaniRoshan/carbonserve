"""
CarbonServe: trace-driven simulation of carbon-aware, SLO-constrained LLM inference routing.

Real data:
  - Azure LLM inference traces (conv + code services, May 2024, 44.1M requests):
    arrival process + per-request context/generated tokens.
  - Real hourly grid carbon intensity, 11 regions (EnsembleCI/CarbonCast datasets;
    EIA + ENTSO-E based). Window 2021-05-10..2021-05-17 (common coverage week).

Model summary (for the paper's methodology section):
  - Region fleet sized to ~2.5x its own peak home demand (per-GPU prefill 8000 tok/s).
  - Fluid queueing at 10 s steps; per-request TTFT = region queue delay at arrival +
    own ctx/prefill_rate; TPOT = base inter-token interval stretched by decode
    utilization (M/M/1-like). SLOs: p95 TTFT <= 2 s, p99 TPOT <= 150 ms.
  - GPU power idle->max linear in utilization; PUE 1.1. Idle fleet stays powered
    (conservative: no scale-to-zero; noted in paper).
  - Carbon = hourly energy per region x that grid's hourly carbon intensity.

Policies:
  local       - status quo (serve at home region)
  oracle      - carbon-greedy on TRUE CI (upper bound), capacity-guarded
  greedy      - carbon-greedy on noisy persistence POINT forecast (naive)
  casper      - CASPER-style inverse-CI weighted split over top-3 candidates
  carbonserve - OURS: uncertainty-aware (90% persistence-error band) + margin +
                utilization guard
"""
import numpy as np
import pandas as pd
import time, os, json

DATA = os.environ.get("CARBONSERVE_DATA", "/scratch/work/data")
OUT = os.environ.get("CARBONSERVE_OUT", "/scratch/work/results")
os.makedirs(OUT, exist_ok=True)

ZONES = ["CISO", "ERCO", "ISNE", "MISO", "PJM", "EPE", "DE", "ES", "NL", "PL", "SE"]
ZONE_TZ = {"CISO": -8, "ERCO": -6, "ISNE": -5, "MISO": -6, "PJM": -5, "EPE": -7,
           "DE": 1, "ES": 1, "NL": 1, "PL": 1, "SE": 1}

# ---- parameters (paper Table 1) ----
PREFILL_RATE = 8000.0     # tok/s per GPU
DECODE_RATE = 2500.0      # tok/s per GPU
BASE_TPOT_MS = 25.0      # per-request inter-token interval at low load
GPU_IDLE_W, GPU_MAX_W = 60.0, 400.0
PUE = 1.1
DT = 10.0
EPOCH = 300
CAP_HEADROOM = 2.5       # region capacity = 2.5x own peak home prefill demand
RHO_MAX = 0.80
CONF = 1.2816            # 90% band
MARGIN = 0.05
TTFT_SLO = 2.0           # s
TPOT_SLO = 150.0         # ms
SEED = 42

def load_ci():
    ci = {}
    for z in ZONES:
        df = pd.read_csv(f"{DATA}/ci/{z}_direct_emissions.csv")
        tcol = [c for c in df.columns if "UTC" in str(c)][0]
        df[tcol] = pd.to_datetime(df[tcol], utc=True, format="ISO8601")
        s = df.set_index(tcol)["carbon_intensity"].sort_index()
        s = s[~s.index.duplicated(keep="first")]
        ci[z] = s
    return ci

def pick_week(ci, start="2021-05-10", days=7):
    idx = pd.date_range(start, periods=days*24, freq="h", tz="UTC")
    return pd.DataFrame({z: ci[z].reindex(idx).ffill().bfill() for z in ZONES}, index=idx)

def persistence_forecast(ci, week_idx):
    fc = {}
    for z in ZONES:
        vals = []
        for t in week_idx:
            v = ci[z].get(t - pd.Timedelta(hours=24))
            if v is None or np.isnan(v):
                v = ci[z].get(t - pd.Timedelta(hours=48))
            vals.append(v)
        fc[z] = vals
    return pd.DataFrame(fc, index=week_idx)

def persistence_sigma(ci):
    sig = {}
    for z in ZONES:
        s = ci[z].dropna()
        err = (s - s.shift(24)).dropna()
        sig[z] = float(err.std())
    return sig

def home_shares_matrix(regions=None):
    """24 x R matrix: share of global traffic whose home is each region by UTC hour."""
    regions = regions or ZONES
    M = np.zeros((24, len(regions)))
    for j, z in enumerate(regions):
        for h in range(24):
            local = (h + ZONE_TZ[z]) % 24
            M[h, j] = 0.35 + 0.65 * np.exp(-0.5 * ((local - 13) / 4.5) ** 2)
    M = M / M.sum(axis=1, keepdims=True)
    return M

def simulate(policy, trace_name, ci_df, fc_df, sig, seed=SEED, fc_noise_scale=1.0,
             regions=ZONES, verbose=True):
    rng = np.random.default_rng(seed)
    t_arr, ctx, gen = load_trace_npz(trace_name)
    t0 = ci_df.index[0].timestamp()
    t1 = ci_df.index[-1].timestamp() + 3600
    t_arr = t_arr - t_arr[0] + t0
    keep = t_arr < t1
    t_arr, ctx, gen = t_arr[keep], ctx[keep], gen[keep]

    n_steps = int((t1 - t0) / DT)
    R = len(regions)
    step_of_req = ((t_arr - t0) / DT).astype(np.int64)
    np.clip(step_of_req, 0, n_steps - 1, out=step_of_req)
    step_bounds = np.searchsorted(step_of_req, np.arange(n_steps + 1))

    hour_of_step = (np.arange(n_steps) * DT / 3600).astype(np.int64)
    ci_hour = ci_df[regions].to_numpy()
    fc_hour = fc_df[regions].to_numpy()
    ci_step = ci_hour[hour_of_step]
    sig_arr = np.array([sig[r] for r in regions])

    # noisy persistence point forecast (same noise seed for greedy & carbonserve)
    fc_step = fc_hour[hour_of_step]
    noise = rng.standard_normal((n_steps, R))
    fc_point = fc_step + fc_noise_scale * sig_arr[None, :] * noise
    fc_low = fc_point - CONF * fc_noise_scale * sig_arr[None, :]
    fc_high = fc_point + CONF * fc_noise_scale * sig_arr[None, :]

    # home shares by UTC hour (for the active region set)
    sh24 = home_shares_matrix(regions)
    hod = hour_of_step % 24

    # region capacity: each region sized to CAP_HEADROOM x its own peak home demand
    # (peak home demand estimated from the trace over the week)
    peak_tok = np.zeros(R)
    req_count_per_step = np.bincount(step_of_req, minlength=n_steps)
    tok_per_step = np.bincount(step_of_req, weights=ctx, minlength=n_steps)
    for s in range(n_steps):
        share = sh24[hod[s]]
        peak_tok = np.maximum(peak_tok, (tok_per_step[s] / DT) * share)
    cap_pf = CAP_HEADROOM * peak_tok  # tokens/s
    gpus = np.maximum(np.ceil(cap_pf / PREFILL_RATE), 1.0)
    cap_dc = gpus * DECODE_RATE

    weights = np.eye(R)
    backlog_pf = np.zeros(R)
    carbon_g = 0.0
    energy_wh = 0.0
    ttft_bins = np.zeros(1200)     # 0..6 s, 5 ms bins
    tpot_bins = np.zeros(2000)     # 0..2000 ms, 1 ms bins
    n_req_total = 0
    routed_away = 0.0
    # --- robustness / risk metrics ---
    offloaded_req = 0.0            # requests routed away from home
    misrouted_req = 0.0            # offloaded reqs whose dest TRUE CI > home TRUE CI
    misroute_penalty_g = 0.0       # extra carbon (g) from misrouted offloads
    worst_epoch_ci_ratio = 0.0     # worst (true CI of chosen dest / true CI of home)
    dec_time = 0.0
    t_start = time.time()

    for s in range(n_steps):
        # -------- slow-timescale routing decision --------
        if s % (EPOCH // DT) == 0:
            if policy == "local":
                weights = np.eye(R)
            else:
                if policy == "oracle":
                    ci_now = ci_step[s]           # true CI, zero uncertainty
                    low_now = ci_now
                    high_now = ci_now
                else:
                    ci_now = fc_point[s]          # noisy point forecast
                    low_now = fc_low[s]
                    high_now = fc_high[s]
                W = np.zeros((R, R))
                for hi in range(R):
                    if policy in ("greedy", "oracle", "carbonserve"):
                        # rank by lower confidence bound (carbonserve/oracle)
                        # or point estimate (greedy)
                        key = low_now if policy in ("carbonserve", "oracle") else ci_now
                        if policy == "greedy":
                            # naive: send everything to min point-CI region
                            order = np.argsort(ci_now)
                            top = order[0] if order[0] != hi else order[1]
                            W[hi, top] = 1.0
                        else:
                            # uncertainty-aware weighted spreading:
                            # offload only if dest's PESSIMISTIC band beats
                            # home's OPTIMISTIC band by MARGIN (confident win);
                            # oracle (perfect info): only strictly-better regions
                            elig = [r for r in np.argsort(ci_now)
                                    if r != hi and
                                    ((high_now[r] * (1 + MARGIN) < low_now[hi]) if policy == "carbonserve"
                                     else (ci_now[r] < ci_now[hi]))]
                            elig = elig[:2]
                            if not elig:
                                W[hi, hi] = 1.0
                            else:
                                cand = [hi] + elig
                                inv = 1.0 / np.maximum(ci_now[cand], 1e-6)
                                w = inv / inv.sum()
                                W[hi, cand] = w
                    elif policy == "casper":
                        # CASPER-style: inverse-CI weights over home + top-3 point CI
                        order = [r for r in np.argsort(ci_now) if r != hi][:2]
                        cand = [hi] + order
                        inv = 1.0 / np.maximum(ci_now[cand], 1e-6)
                        W[hi, cand] = inv / inv.sum()
                weights = W

        # -------- arrivals (vectorized per step) --------
        i0, i1 = step_bounds[s], step_bounds[s + 1]
        n_r = i1 - i0
        if n_r:
            step_ctx = ctx[i0:i1]
            share = sh24[hod[s]]
            homes = rng.multinomial(n_r, share / share.sum())
            mean_ctx = step_ctx.mean()
            # utilization guard BEFORE final routing: scale offload into regions
            # whose utilization (backlog + incoming) would exceed RHO_MAX
            in_tok_dest = (homes * mean_ctx) @ weights
            cap_room = RHO_MAX * cap_pf * DT - backlog_pf
            W = weights.copy()
            for rj in np.where((W.sum(axis=0) - np.diag(W)) > 0)[0]:
                if in_tok_dest[rj] > cap_room[rj]:
                    if cap_room[rj] <= 0:
                        keep = 0.0
                    else:
                        keep = cap_room[rj] / in_tok_dest[rj]
                    for hi in np.where(W[:, rj] > 0)[0]:
                        if hi != rj:
                            moved = (1 - keep) * W[hi, rj]
                            W[hi, rj] -= moved
                            W[hi, hi] += moved
            weights_ep = W
            # route requests: exact per-request home + dest assignment
            counts = homes[:, None] * weights_ep
            home_id = np.repeat(np.arange(R), homes)
            dest_id = np.empty(n_r, dtype=np.int64)
            hstart = np.concatenate([[0], np.cumsum(homes)]).astype(int)
            for hi in range(R):
                if homes[hi] == 0:
                    continue
                seg = slice(hstart[hi], hstart[hi + 1])
                cs = np.rint(np.cumsum(counts[hi])).astype(int)
                cs[-1] = homes[hi]
                dest_id[seg] = np.searchsorted(cs, np.arange(homes[hi]), side="right")
            routed_away += float((dest_id != home_id).sum())
            n_req_total += n_r
            # risk metrics: true-CI comparison for offloaded requests
            off_mask = dest_id != home_id
            if off_mask.any():
                d_ci = ci_step[s][dest_id[off_mask]]
                h_ci = ci_step[s][home_id[off_mask]]
                bad = d_ci > h_ci
                n_off = off_mask.sum()
                offloaded_req += n_off
                misrouted_req += bad.sum()
                # token-weighted penalty: energy moved into worse-CI grids
                e_wh_req = ((step_ctx[off_mask] / PREFILL_RATE) * GPU_MAX_W
                            + (gen[i0:i1][off_mask] / DECODE_RATE) * GPU_MAX_W) / 3600.0
                misroute_penalty_g += float((e_wh_req[bad] / 1000.0 * (d_ci[bad] - h_ci[bad])).sum())

            # per-request TTFT/TPOT (vectorized)
            qdelay = backlog_pf / cap_pf
            step_ttft = qdelay[dest_id] + step_ctx / PREFILL_RATE
            load_ratio = np.clip(backlog_pf[dest_id] / (cap_pf[dest_id] * 3), 0, 0.95)
            step_tpot = BASE_TPOT_MS / (1.0 - load_ratio)
            b1 = np.minimum((step_ttft / 0.005).astype(int), 1199)
            np.clip(b1, 0, 1199, out=b1)
            ttft_bins += np.bincount(b1, minlength=1200)
            b2 = np.minimum(step_tpot.astype(int), 1999)
            np.clip(b2, 0, 1999, out=b2)
            tpot_bins += np.bincount(b2, minlength=2000)

            # load to backlogs
            load_pf = counts.sum(axis=0) * mean_ctx
            load_dc = counts.sum(axis=0) * (gen[i0:i1].mean() if n_r else 0)
            backlog_pf += load_pf

        # -------- service --------
        served_pf = np.minimum(backlog_pf, cap_pf * DT)
        backlog_pf -= served_pf

        # -------- energy & carbon --------
        util = served_pf / (cap_pf * DT)
        pwr = gpus * (GPU_IDLE_W + (GPU_MAX_W - GPU_IDLE_W) * util)
        e_wh = pwr * (DT / 3600.0) * PUE
        energy_wh += e_wh.sum()
        carbon_g += (e_wh / 1000.0 * ci_step[s]).sum()

    def pct(hist, binsz, q):
        tot = hist.sum()
        if tot == 0:
            return 0.0
        cum = np.cumsum(hist) / tot
        return int(np.searchsorted(cum, q / 100.0)) * binsz

    ttft_p95 = pct(ttft_bins, 5.0, 95)           # ms
    tpot_p99 = pct(tpot_bins, 1.0, 99)           # ms
    ttft_ok = ttft_bins[:int(TTFT_SLO * 1000 / 5)].sum()
    tpot_ok = tpot_bins[:int(TPOT_SLO)].sum()
    attain = min(ttft_ok, tpot_ok) / max(ttft_bins.sum(), 1)

    return {
        "policy": policy, "trace": trace_name, "regions": len(regions),
        "requests": int(n_req_total),
        "carbon_kg": carbon_g / 1000.0,
        "energy_kwh": energy_wh / 1000.0,
        "ttft_p95_ms": float(ttft_p95),
        "tpot_p99_ms": float(tpot_p99),
        "slo_attainment": float(attain),
        "routed_away_frac": float(routed_away / max(n_req_total, 1)),
        "misroute_rate": float(misrouted_req / max(offloaded_req, 1)),
        "misroute_penalty_kg": misroute_penalty_g / 1000.0,
        "sim_seconds": round(time.time() - t_start, 1),
    }

def load_trace_npz(name):
    d = np.load(f"{DATA}/azure_{name}.npz")
    return d["t"], d["ctx"].astype(np.float32), d["gen"].astype(np.float32)

def main():
    ci = load_ci()
    week = pick_week(ci)
    fc = persistence_forecast(ci, week.index)
    sig = persistence_sigma(ci)
    mape = float((np.abs(fc - week) / week).mean().mean())
    print(f"day-ahead persistence forecast MAPE (11 zones, sim week): {mape*100:.1f}%")
    print("zone sigma (g/kWh):", {z: round(sig[z]) for z in ZONES})

    results = []
    for trace in ["conv", "code"]:
        for policy in ["local", "oracle", "greedy", "casper", "carbonserve"]:
            r = simulate(policy, trace, week, fc, sig)
            results.append(r)
            print(f"{trace:5s} {r['policy']:12s} carbon={r['carbon_kg']:8.1f}kg "
                  f"energy={r['energy_kwh']:7.0f}kWh ttft_p95={r['ttft_p95_ms']:6.0f}ms "
                  f"tpot_p99={r['tpot_p99_ms']:6.0f}ms slo={r['slo_attainment']*100:5.1f}% "
                  f"away={r['routed_away_frac']*100:5.1f}% [{r['sim_seconds']}s]")
    pd.DataFrame(results).to_csv(f"{OUT}/e2_policy_comparison.csv", index=False)
    print("saved e2_policy_comparison.csv")

if __name__ == "__main__":
    main()
