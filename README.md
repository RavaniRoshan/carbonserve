# CarbonServe: Uncertainty-Aware Carbon Routing for SLO-Constrained LLM Inference

Routing layer for geo-distributed LLM inference that treats carbon-intensity forecast
uncertainty as a first-class constraint: offload only when the remote grid's pessimistic
CI band beats the home grid's optimistic band, guarded by utilization caps that protect
latency SLOs.

**Headline:** on 44.1M Azure production requests against real hourly CI for 11 grids,
CarbonServe cuts operational carbon **29.4%** vs locality-only serving (96% of the
perfect-information oracle) while cutting routing-backfire emissions **27×** vs
CASPER-style point-forecast routing. All SLOs (p95 TTFT, p99 TPOT) hold.

- Author: Ravani Roshan (Independent Research) · ORCID
  [0009-0007-4930-977X](https://orcid.org/0009-0007-4930-977X)
- Paper: [`paper/CarbonServe.pdf`](paper/CarbonServe.pdf) (venue target: IEEE IC2E 2027)
- Data: Azure LLM Inference Trace 2024 (CC-BY) · EnsembleCI grid carbon datasets (EIA/ENTSO-E)

## Status

Working simulator is in (`sim/` + `experiments/` + `analysis/`): an **independent
reimplementation from the paper's specification**, run against the real public
data (Azure traces, EnsembleCI grids). Every number it reports comes from
actually running the code — headline comparison, noise/fleet/headroom sweeps,
and physics-consistency checks. It reproduces the paper's qualitative findings
(confidence-rule risk gap, graceful degradation); exact quantitative match with
the authors' original runs is not claimed.
Status: smoke-tested (unit tests 6/6, real-data slice end-to-end, MAPE 10.09%
vs paper's 10.1%); full-week runs execute in CI (`full-week` workflow).

## Reproduce (once artifacts land)

```bash
bash data_restore/fetch.sh data   # EnsembleCI grids; Azure traces fetch on first run
python3 -m pytest tests/ -q
python3 experiments/run_e2.py --data data --out results_e2.csv   # full week, both traces
python3 analysis/tables.py results_e2_conv.csv local
python3 analysis/verify.py results_e2_conv.csv
```

> [!NOTE]
> Evaluation is trace-driven simulation (calibrated, physics-checked), not a live
> multi-region deployment. Trace (May 2024) and CI (May 2021, same season) windows
> differ in year; this is stated openly in the paper (§VII).
