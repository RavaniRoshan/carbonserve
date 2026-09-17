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

Paper draft is in. The full artifact drop — simulator, experiment drivers, data-restore
scripts, 67 per-run result files, analysis scripts — lands here before submission,
with a verified reproduce path and a Zenodo snapshot (DOI).

## Reproduce (once artifacts land)

```bash
python3 -m pytest tests/ -q
python3 experiments/run_e2.py   # policy comparison, conversational + coding traces
```

> [!NOTE]
> Evaluation is trace-driven simulation (calibrated, physics-checked), not a live
> multi-region deployment. Trace (May 2024) and CI (May 2021, same season) windows
> differ in year; this is stated openly in the paper (§VII).
