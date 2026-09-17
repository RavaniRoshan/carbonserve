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
- Paper: [`paper/CarbonServe.pdf`](paper/CarbonServe.pdf) (source:
  `paper/CarbonServe-Paper.typ` + `paper/figures/`) · venue target: IEEE IC2E 2027
- Data: Azure LLM Inference Trace 2024 (CC-BY) · EnsembleCI grid carbon datasets (EIA/ENTSO-E)

## Layout

- `simulator/` — the original experiment code: fluid simulator, 67-run batch driver
  (E1–E4), analysis + figure generation, data-restore script. Paths are
  env-overridable (`CARBONSERVE_DATA`, `CARBONSERVE_OUT`, `CARBONSERVE_FIG`);
  defaults preserve the original `/scratch/work` layout.
- `paper/` — paper source, original figures, compiled PDF.
- `documents/` — results pack and research dossier.
- `repro/` — an independent stdlib-only reimplementation built from the paper spec
  (separate validation track; see `repro/` notes). Its numbers are its own —
  qualitative agreement is the claim, not bit-identity.
- `submission/` — arXiv metadata pack + IEEE Access checklist.

## Status

Two runnable tracks, both executed in CI:

1. **Original pipeline** (`simulator/` + `original-pipeline` workflow): restores public
   data, runs the 67 experiment jobs sharded across runners, aggregates tables +
   figures. Smoke mode runs 1 job; full mode runs all 67.
2. **Independent reproduction** (`repro/` + `smoke`/`full-week` workflows): stdlib-only
   reimplementation from the paper spec. Unit tests 6/6, real-data slice end-to-end,
   persistence MAPE 10.09% vs the paper's 10.1%.

## Reproduce

```bash
# original pipeline, one job (needs numpy/pandas; ~GBs of public data)
export CARBONSERVE_DATA=$PWD/data CARBONSERVE_OUT=$PWD/work
bash simulator/restore_data.sh
python3 simulator/run_one_job.py e2_conv_carbonserve_s42
# full 67-job sweep: Actions → original-pipeline → Run workflow (mode: full)
```

```bash
# independent reproduction track
bash repro/data_restore/fetch.sh data
python3 -m pytest repro/tests/ -q
python3 repro/experiments/run_e2.py --data data --out results_e2.csv
python3 repro/analysis/tables.py results_e2_conv.csv local
```

> [!NOTE]
> Evaluation is trace-driven simulation (calibrated, physics-checked), not a live
> multi-region deployment. Trace (May 2024) and CI (May 2021, same season) windows
> differ in year; this is stated openly in the paper (§VII).
