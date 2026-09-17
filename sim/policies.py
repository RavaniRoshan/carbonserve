"""Routing policies: epoch weights from carbon forecasts.

All guards/caps follow the paper: confidence margin delta=5%, band z=1.28,
utilization cap rho_max=0.80, top-2 + home splits with inverse-CI weights.
`fc[g]` is the point forecast for the epoch; `bands[g]` = (lo, hi).
"""
import math

Z = 1.28
DELTA = 0.05
RHO_MAX = 0.80
TOP_K = 2


def _inv_weights(members, fc):
    inv = {g: 1.0 / max(fc[g], 1e-9) for g in members}
    s = sum(inv.values())
    return {g: v / s for g, v in inv.items()}


def local_weights(home, cands):
    return {home: {home: 1.0} for home in cands}


def greedy_weights(fc, cands):
    best = min(cands, key=lambda g: fc[g])
    return {home: {best: 1.0} for home in cands}


def casper_weights(fc, cands):
    """Home + top-2 point-CI regions, inverse-CI weights."""
    top = sorted(cands, key=lambda g: fc[g])[:TOP_K]
    out = {}
    for home in cands:
        members = [home] + [g for g in top if g != home]
        out[home] = _inv_weights(members, fc)
    return out


def carbonserve_weights(fc, bands, cands):
    """Confidence rule: (FC(r)+z.sr)(1+d) < FC(h)-z.sh, top-2 + home split."""
    top = sorted(cands, key=lambda g: fc[g])[:TOP_K]
    out = {}
    for home in cands:
        lo_h = bands[home][0]
        members = [home]
        for g in top:
            if g == home:
                continue
            hi_r = bands[g][1]
            if hi_r * (1 + DELTA) < lo_h:
                members.append(g)
        out[home] = _inv_weights(members, fc)
    return out


def oracle_weights(truth, cands):
    """CarbonServe's rule with perfect knowledge (zero-width bands)."""
    bands = {g: (truth[g], truth[g]) for g in cands}
    return carbonserve_weights(truth, bands, cands)


def epoch_forecast(truth_h, sigma, noise_scale, rng, truth_now):
    """Persistence-style forecast with scaled empirical error.

    truth_h: yesterday-same-hour truth per grid; sigma[g]: empirical std;
    at scale k the error is k× the persistence error (k=1: realistic regime).
    Returns (fc, bands) with 90% bands from scaled sigma.
    """
    fc, bands = {}, {}
    for g, t_old in truth_h.items():
        t_now = truth_now[g]
        err = (t_old - t_now) * noise_scale
        f = t_now + err
        s = sigma[g] * noise_scale
        fc[g] = f
        bands[g] = (f - Z * s, f + Z * s)
    return fc, bands
