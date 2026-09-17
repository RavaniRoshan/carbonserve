"""Unit tests on synthetic fixtures: rule mechanics + accounting honesty.

These use tiny hand-built fixtures (not paper data) to pin the mechanism:
the confidence rule fires exactly when bands separate, the oracle bounds
savings from above, and every joule is accounted in carbon.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import policies as P
from sim.engine import Region, Run

CI = [100.0] * 168


def test_bands_overlap_stays_home():
    fc = {"h": 100.0, "r": 90.0}
    bands = {"h": (90.0, 110.0), "r": (80.0, 100.0)}  # overlap
    w = P.carbonserve_weights(fc, bands, ["h", "r"])
    assert w["h"] == {"h": 1.0}, w


def test_separated_bands_offload():
    fc = {"h": 400.0, "r": 50.0}
    bands = {"h": (390.0, 410.0), "r": (40.0, 60.0)}
    w = P.carbonserve_weights(fc, bands, ["h", "r"])
    assert w["h"].get("r", 0) > 0.5, w  # inverse-CI favors clean region


def test_oracle_zero_width():
    truth = {"h": 400.0, "r": 50.0}
    w = P.oracle_weights(truth, ["h", "r"])
    assert w["h"].get("r", 0) > 0.5, w


HOME_CDF = [(1.0, "h")]


def test_guard_reverts_when_dest_saturated():
    regs = [Region("h", CI, 1), Region("r", CI, 1)]
    regs[1].backlog = 1e9  # saturated
    run = Run(regs, 0)
    ci = {"h": 400.0, "r": 50.0}
    run.step([(128, 32)], {"h": {"r": 1.0}}, ci, HOME_CDF, P.RHO_MAX)
    assert run.offload == 0 and run.n == 1, (run.offload, run.n)


def test_carbon_accounting_balances():
    regs = [Region("h", [200.0] * 168, 2)]
    run = Run(regs, 0)
    ci = {"h": 200.0}
    for _ in range(10):
        run.step([(128, 32)] * 10, {"h": {"h": 1.0}}, ci, HOME_CDF,
                 P.RHO_MAX)
    for _ in range(360):  # one hour of steps
        run.step([], {"h": {"h": 1.0}}, ci, HOME_CDF, P.RHO_MAX)
    R = regs[0]
    R.close_hour(0)
    assert R.carbon_kg > 0
    # single region at constant CI: implied traffic-weighted CI must equal it
    e_kwh = sum(R.e_hour) / 3.6e6
    assert abs(R.carbon_kg / e_kwh * 1000 - 200.0) < 1.0
    # home counterfactual (dynamic only) equals actual minus idle fleet power
    idle_kg = 2 * 60.0 * 1.1 * 3600 / 3.6e9 * 200.0
    assert abs(run.carbon_home_kg - (R.carbon_kg - idle_kg)) / R.carbon_kg < 0.05


def test_misroute_counts_only_dirtier_dest():
    regs = [Region("h", CI, 8), Region("r", CI, 8)]
    run = Run(regs, 1)
    w = {"h": {"r": 1.0}}
    run.step([(128, 32)], w, {"h": 400.0, "r": 50.0}, HOME_CDF, P.RHO_MAX)
    assert run.offload == 1 and run.mis_n == 0 and run.mis_pen == 0.0
    run.step([(128, 32)], w, {"h": 50.0, "r": 400.0}, HOME_CDF, P.RHO_MAX)
    assert run.mis_n == 1 and run.mis_pen > 0
