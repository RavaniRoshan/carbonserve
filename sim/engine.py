"""Fluid-queueing experiment engine (stdlib only).

Time is sliced into 10 s steps; within a step each region's arrivals are
spread uniformly (served_so_far interpolation), so same-step arrivals do NOT
falsely serialize behind each other. Queue delay comes from the GPU-second
backlog, TPOT stretches mildly with load, power follows 60+340u W/GPU with
PUE 1.1. Carbon accrues hourly against true CI. p95 TTFT comes from a per-run
reservoir sample. All metrics are computed from the simulated trajectory —
nothing is hardcoded.
"""
import random

STEP = 10            # s, fluid timestep
EPOCH = 300          # s, routing epoch (5 min)
PREFILL_TPS = 8000.0
DECODE_TPS = 2500.0
P_IDLE, P_MAX = 60.0, 400.0
PUE = 1.1
TPOT_BASE_MS = 25.0
SLO_TTFT_MS = 2000.0
SLO_TPOT_MS = 150.0
RESERVOIR = 200000


def work_gs(cin, cout):
    return cin / PREFILL_TPS + cout / DECODE_TPS


class Region:
    __slots__ = ("name", "ci", "ngpu", "backlog", "e_j", "e_hour",
                 "hour_ci", "carbon_kg")

    def __init__(self, name, ci_hourly, ngpu):
        self.name = name
        self.ci = ci_hourly          # list of 168 hourly CI values
        self.ngpu = ngpu
        self.backlog = 0.0           # gpu-s of queued work
        self.e_j = 0.0               # energy this hour (J)
        self.e_hour = []             # closed hour energies
        self.hour_ci = []
        self.carbon_kg = 0.0

    def start_util(self):
        return min(1.0, self.backlog / max(self.ngpu * STEP, 1e-9))

    def close_hour(self, h):
        self.e_hour.append(self.e_j)
        self.hour_ci.append(self.ci[h])
        self.carbon_kg += self.e_j * self.ci[h] / 3.6e9
        self.e_j = 0.0


class Run:
    def __init__(self, regions, seed):
        self.regions = {r.name: r for r in regions}
        self.rng = random.Random(seed)
        self.n = 0
        self.viol = 0
        self.offload = 0
        self.mis_n = 0
        self.mis_pen = 0.0
        self.carbon_home_kg = 0.0    # carbon had everything stayed home
        self.ttft = []               # reservoir sample (ms)
        self.tpot = []
        self.max_util = 0.0

    def _sample(self, buf, x):
        if len(buf) < RESERVOIR:
            buf.append(x)
        else:
            j = self.rng.randrange(self.n + 1)
            if j < RESERVOIR:
                buf[j] = x

    def _draw_home(self, cdf):
        r = self.rng.random()
        for acc, g in cdf:
            if r <= acc:
                return g
        return cdf[-1][1]

    def _draw_dest(self, home, W):
        r = self.rng.random()
        for g, p in W[home].items():
            r -= p
            if r <= 0:
                return g
        return home

    def step(self, arrivals, W, ci_now, cdf, rho_max):
        """Two-pass fluid step. arrivals: list of (cin, cout) in time order."""
        regs = self.regions
        # pass 1: route (guard reads step-start backlog PLUS intra-step
        # admitted load, per the paper: "queue backlog plus admitted load")
        pending = {g: [] for g in regs}
        admitted = {g: 0.0 for g in regs}
        for cin, cout in arrivals:
            home = self._draw_home(cdf)
            dest = self._draw_dest(home, W)
            wk = work_gs(cin, cout)
            if dest != home:
                R = regs[dest]
                if (R.backlog + admitted[dest]) / max(R.ngpu * STEP, 1e-9) >= rho_max:
                    dest = home  # saturated: excess reverts home
                else:
                    admitted[dest] += wk
            pending[dest].append((cin, cout, home))
        # pass 2: uniform-spread service + metrics
        for g, lst in pending.items():
            R = regs[g]
            n = len(lst)
            b0 = R.backlog
            cap = R.ngpu * STEP
            u0 = min(1.0, b0 / max(cap, 1e-9))
            if u0 > self.max_util:
                self.max_util = u0
            wk_so_far = 0.0
            p_w = (P_IDLE + (P_MAX - P_IDLE) * u0) * PUE
            for k, (cin, cout, home) in enumerate(lst):
                served = cap * (k / n) if n else 0.0
                wait_s = max(0.0, b0 + wk_so_far - served) / max(R.ngpu, 1)
                ttft = wait_s * 1000.0 + cin / PREFILL_TPS * 1000.0
                tpot = TPOT_BASE_MS * (1.0 + u0 * u0)
                wk = work_gs(cin, cout)
                e_j = wk * p_w
                if g != home:
                    self.offload += 1
                    dci = ci_now[g] - ci_now[home]
                    if dci > 0:
                        self.mis_n += 1
                        self.mis_pen += e_j * dci / 3.6e9
                self.carbon_home_kg += e_j * ci_now[home] / 3.6e9
                if ttft > SLO_TTFT_MS or tpot > SLO_TPOT_MS:
                    self.viol += 1
                self.n += 1
                self._sample(self.ttft, ttft)
                self._sample(self.tpot, tpot)
                wk_so_far += wk
            served_tot = min(b0 + wk_so_far, cap)
            R.backlog = b0 + wk_so_far - served_tot
            u = served_tot / max(cap, 1e-9)
            R.e_j += R.ngpu * (P_IDLE + (P_MAX - P_IDLE) * u) * PUE * STEP

    def summary(self):
        tt = sorted(self.ttft)
        tp = sorted(self.tpot)
        q = lambda a, p: a[min(len(a) - 1, int(p * len(a)))] if a else 0.0
        carbon = sum(R.carbon_kg for R in self.regions.values())
        energy_kwh = sum(sum(R.e_hour) for R in self.regions.values()) / 3.6e6
        return {
            "n": self.n,
            "carbon_kg": carbon,
            "energy_kwh": energy_kwh,
            "p95_ttft_ms": q(tt, 0.95),
            "p99_tpot_ms": q(tp, 0.99),
            "viol_rate": self.viol / max(self.n, 1),
            "offload_frac": self.offload / max(self.n, 1),
            "misroute_rate": self.mis_n / max(self.offload, 1),
            "misroute_penalty_kg": self.mis_pen,
            "max_util": self.max_util,
        }
