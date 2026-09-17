# arXiv submission pack — CarbonServe

Submit via "Submit a PDF" (manuscript is Typst, not LaTeX): `paper/CarbonServe.pdf`.
Do this FIRST (preprint, establishes priority; compatible with IEEE review).

## Metadata (paste-ready)

- **Title:** CarbonServe: Uncertainty-Aware Carbon Routing for SLO-Constrained
  LLM Inference Across Geo-Distributed Cloud Regions
- **Authors:** Ravani Roshan (https://orcid.org/0009-0007-4930-977X)
- **Affiliation:** Independent Research
- **Contact:** ravaniroshansingh@gmail.com
- **Categories:** cs.DC (primary — Distributed, Parallel, and Cluster Computing);
  cross-list cs.CY (Computers and Society)
- **License:** CC BY 4.0 (recommended — matches the CC-BY data it builds on;
  alternatives: CC BY-SA, or arXiv non-exclusive). Decision: author's call at submit time.
- **Abstract:** (1753 chars — fits the 1920 limit; copy from paper verbatim)

> Large language model (LLM) inference has become a dominant operational workload
> in cloud platforms, and its electricity consumption translates directly into
> operational carbon emissions that vary by up to an order of magnitude across
> cloud regions and hours. Existing carbon-aware routing proposals for LLM serving
> act on point forecasts of grid carbon intensity (CI) and are evaluated only in
> simulation; recent results in carbon-aware computing show that such point-forecast
> decisions can backfire and increase emissions when forecasts err. We present
> CarbonServe, an uncertainty- and SLO-aware request routing layer for
> geo-distributed LLM inference. CarbonServe combines a day-ahead persistence CI
> forecaster with per-grid empirical error distributions, and offloads traffic to a
> remote region only when the remote grid's pessimistic (upper) CI band beats the
> home grid's optimistic (lower) band by a margin, subject to utilization guards that
> protect latency SLOs. We evaluate CarbonServe on 44.1 million production LLM
> inference requests (Azure traces) replayed against real hourly CI data for 11 grids
> in North America and Europe. Under realistic forecast error (10.1% MAPE),
> CarbonServe reduces operational carbon by 29.4% versus locality-only serving —
> capturing 96% of the perfect-information oracle's savings — while reducing routing
> backfire (requests directed into grids dirtier than home) by 27x relative to
> CASPER-style point-forecast routing. As forecast quality degrades, point-forecast
> policies lose up to half their savings and incur order-of-magnitude emission
> penalties, whereas CarbonServe degrades gracefully and dominates on both savings
> and risk. All latency SLOs (p95 TTFT, p99 TPOT) are maintained with negligible
> router overhead.

## Account + endorsement (author actions, ~10 min + waiting)

1. Register at arxiv.org (email + username; use an institutional email if available —
   it expedites endorsement).
2. First-time cs.* submission needs **one positive endorsement**: start a submission to
   get the endorsement-request link, then ask one established author from the paper's
   own references (Stojkovic, Bashir, Irwin, Shenoy — findable via "Which authors of
   this paper are endorsers?" on their abstract pages). One is enough; do not mass-email.
3. Upload `paper/CarbonServe.pdf` via the PDF route, paste metadata above, announce.
