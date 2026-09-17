# Research Dossier: Carbon-Aware, SLO-Constrained LLM Inference Scheduling

**Working paper title (candidates):**
1. CarbonServe: Carbon- and Uncertainty-Aware Request Routing for SLO-Constrained LLM Inference Across Geo-Distributed Cloud Regions
2. GreenRoute: Real-Time Carbon-Intensity-Aware Scheduling of LLM Inference Under Latency SLOs
3. Marginal-Carbon Scheduling for Disaggregated LLM Serving: A Multi-Region, SLO-Aware Approach

**Status:** Research phase complete. Awaiting author's go-ahead for paper drafting.

---

## 1. Problem Statement and Motivation

LLM inference has become the dominant operational AI workload — studies estimate inference can exceed training costs by 25x per year for popular models, and the cumulative operational carbon footprint now far exceeds training-phase footprint. LLM inference runs on power-hungry GPUs under strict Service Level Objectives (TTFT = time-to-first-token, TPOT/ITL = time-per-output-token / inter-token latency), producing substantial energy consumption and operational carbon emissions.

At the same time, the carbon intensity (CI) of grid electricity (gCO2eq/kWh) varies by **2–3 orders of magnitude** across hours (temporal) and regions (spatial). Every recent systematic review of AI-driven cloud resource allocation flags the same gap: only ~6% of studies integrate carbon-awareness, 70% are simulation-only, and almost none provide real deployment validation.

**Core research question:** *How should LLM inference requests be routed and scheduled across geo-distributed, heterogeneous regions — in real time, using grid carbon intensity signals — such that operational carbon is minimized while latency SLOs (TTFT/TPOT) and cost budgets are provably maintained?*

---

## 2. Background: The Two Research Threads Being Combined

### 2.1 Thread A — Carbon-aware cloud computing (the "signal" side)

| System | Venue | Core idea | Limitation |
|---|---|---|---|
| Carbon Explorer (Meta) | ASPLOS'23 | Framework for 24/7 carbon-free datacenter design; greedy carbon-aware scheduling of delay-tolerant workloads; open source | Design-space tool, not a runtime scheduler |
| CarbonScaler | SIGMETRICS'24 | Carbon "scaling" for batch jobs (scale up in low-CI hours) — 33–51% savings without completion-time extension | Batch/training only, not latency-sensitive serving |
| CASPER | IGSC'23 / arXiv'24 | Carbon-aware scheduling + provisioning for geo-distributed **web services** in Kubernetes; up to 70% carbon reduction with SLO respect | Web microservices (ms-scale requests), not stateful GPU LLM serving |
| Google carbon-aware computing (Radovanovic et al.) | arXiv'21 | Production temporal shifting at Google | Batch, proprietary |
| Sukprasert et al. | e-Energy'24 | Documents **limitations** of carbon-aware temporal/spatial shifting — shifting can be counterproductive if capacity/headroom ignored | Motivating critique |
| Wiesner et al. ("Sunk Carbon Fallacy") | 2023 | Argues schedulers must optimize **marginal**, not average, carbon — naive metrics optimize the wrong target | Conceptual/accounting |
| Uncertainty-Aware Decarbonization | HotCarbon'24 | Shows point CI predictions can cause **2.7–14% emission increases** when wrong; proposes confidence-interval-aware shifting | Datacenter level, not request-level LLM serving |

### 2.2 Thread B — Energy/carbon-efficient LLM inference serving (the "workload" side)

**Cluster-level energy management (single cluster, no geo/carbon signal):**

| System | Venue | Core idea | Savings |
|---|---|---|---|
| DynamoLLM | HPCA'25 (Microsoft) | Hierarchical control of instance count, model parallelism, GPU DVFS under SLOs; released the Azure 2024 LLM traces | 52% energy, 38% carbon, 61% cost |
| throttLL'eM | arXiv'24 | Iteration-level DVFS + parallelism autoscaling with KV/batch projection ML model (R² > 0.97) | 43.8% energy vs Triton |
| GreenLLM | arXiv'25 | Phase-specific (prefill vs decode) SLO-aware DVFS with dual-loop controller | 34% energy |
| VoltanaLLM | arXiv'25 | Control-theoretic per-iteration frequency control + state-space routing for P/D-disaggregated serving; implemented in SGLang | 36.3% energy |
| DualScale | 2026 | Phase-aware placement + MPC-based prefill DVFS, slack-aware decode DVFS vs DistServe | 39–48% energy per phase |
| AFlex | 2026 | Operator-level (Attention vs FFN) disaggregation + per-operator DVFS in SGLang | 48–49% energy/token |
| PA-vLLM / PALS | 2026 | Power caps as first-class scheduling primitive (batching × parallelism × power cap) | 26.3% efficiency |
| TAPAS | ASPLOS'25 (Microsoft) | Thermal- and power-aware scheduling for LLM inference clusters; 40% extra capacity via oversubscription | — |

**The intersection — carbon-aware LLM serving (direct competitors; all 2024–25):**

| System | Venue | Approach | Key limitation (= your opening) |
|---|---|---|---|
| EcoServe | arXiv'25 (Microsoft) | Cross-stack ILP: capacity planning + runtime provisioning for LLM serving; embodied+operational carbon; 4R principles; up to 47% carbon cut | Single-cluster resource provisioning; no real-time multi-region CI routing |
| SLIT | KDD'25 | Geo-distributed LLM request scheduling co-optimizing TTFT, carbon, **water**, cost via ML+evolutionary metaheuristic; Pareto front | Pure simulation; no real serving stack, no CI uncertainty handling |
| FREESH | arXiv'25 | Joint routing+scheduling on heterogeneous geo-distributed GPUs; frequency scaling + Least-Laxity-First; 28.6% energy / 45.45% carbon reduction | Simulation on production workloads; no real carbon-API deployment |
| CEDAR | EuroSys-GreenSys'25 workshop | Queue-level multi-objective (tail latency, cost, **marginal carbon**) routing as CMDP for agentic LLM inference; 26% cost / 27% carbon cut | Trace-driven **simulation only**; authors themselves state no production LLM serving framework incorporates real-time CI into queue-level routing |
| GreenCache | arXiv'25 | Carbon-aware KV-cache management (operational vs embodied carbon of SSDs); ILP; 15–25% carbon cut | Cache sizing dimension only |
| CarbConscious | ICIS SIGGreen'25 | Carbon-aware temporal+spatial shifting of LLM inference; Pareto decision support; 35–52% carbon cut, 99.5% SLA | Synthetic/simulated grid data; IS/workshop-level rigor |
| Janus | 2026 (EAI) | KV-cache-aware prefill/decode disaggregation + multi-cloud routing with Lyapunov drift-plus-penalty; provable guarantees | Optimizes latency/cost, **not carbon**; simulation |

---

## 3. Research Gap Analysis (verified across the literature)

**GAP 1 — No real-world deployment with live carbon signals.** Every carbon-aware LLM serving paper (SLIT, FREESH, CEDAR, CarbConscious, EcoServe) is trace-driven simulation or single-cluster. CEDAR explicitly: "to our knowledge no LLM serving framework incorporates real-time carbon intensity signals into queue-level routing." A demonstration on actual multi-region vLLM/SGLang with live ElectricityMaps/WattTime data would be the first of its kind.

**GAP 2 — Carbon-intensity forecast uncertainty is ignored.** HotCarbon'24 proved point forecasts can *increase* emissions by 2.7–14% when wrong. No LLM scheduler uses confidence intervals (from CarbonCast/EnsembleCI-style forecasters) in routing decisions. An uncertainty-aware, risk-bounded router is novel.

**GAP 3 — Marginal vs. average carbon accounting is unsettled for stateful serving.** The "sunk carbon fallacy" (Wiesner et al.) has only been applied in CEDAR's simulation. LLM serving has unique state (KV cache), so marginal accounting interacts with migration/recompute decisions — unexplored.

**GAP 4 — Carbon-awareness has not met P/D disaggregation.** Prefill/decode disaggregation (DistServe, Splitwise, Mooncake) is the dominant new architecture; routing across regions now involves KV-cache transport decisions (migrate vs. recompute vs. partial ship). Janus optimizes this for latency/cost only. Adding carbon to the KV-transport decision variable is untouched.

**GAP 5 — No carbon-aware LLM serving study covers high-CI emerging grids (e.g., India).** All evaluations use US/EU grids (CISO, PJM, ERCO, DE...). The Indian grid has one of the world's highest and most volatile carbon intensities, plus DPDP Act data-localization pressures — a strongly motivated, publishable evaluation context, and accessible via ElectricityMaps data for Indian regions.

**GAP 6 — Multi-objective formulations lack provable guarantees on real stacks.** SLIT uses metaheuristics (no guarantees); CEDAR uses CMDP but simulation-only. A Lyapunov-drift or CMDP formulation with [O(1/V), O(V)] style bounds, validated on a real serving engine, closes a methodological hole reviewers at IEEE venues will recognize.

---

## 4. Recommended Paper Framing (primary)

**Title (recommended):** *CarbonServe: Uncertainty- and SLO-Aware Carbon Routing for Geo-Distributed LLM Inference*

**One-sentence contribution:** The first LLM serving system that routes requests across geo-distributed regions using **live + forecast carbon intensity with uncertainty bounds**, jointly with latency SLOs and cost, on a **real multi-region serving stack** (vLLM/SGLang), with provable SLO guarantees via Lyapunov drift-plus-penalty / CMDP control.

**Three-pronged contribution structure (classic systems-paper shape):**
1. **Measurement/motivation study:** characterize the joint carbon–latency–cost opportunity space using Azure 2024 LLM traces × historical ElectricityMaps CI data across 6–10 regions (including 1–2 Indian regions). Quantify the carbon savings headroom under various SLO slack levels (echoes CASPER's motivating analysis, but for LLM workloads).
2. **System:** CarbonServe router — (a) CI forecaster with uncertainty (reuse EnsembleCI, open source), (b) request router solving a constrained optimization per epoch: minimize expected marginal carbon subject to p95 TTFT / p99 TPOT SLOs and cost budget; (c) graceful fallback to local region when CI uncertainty intervals overlap (directly addresses the HotCarbon'24 failure mode).
3. **Evaluation:** (a) trace-driven simulation at scale (6–10 regions, Azure + BurstGPT traces), AND (b) small real deployment: 2–3 regions (e.g., one GPU cloud VM per region running vLLM with Llama-3-8B or Qwen-7B), replaying traces against live CI signals. Report carbon, energy, TTFT/TPOT p50/p95/p99, SLO attainment, cost, and routing decision overhead.

**Differentiation from closest competitors (the "delta" paragraph reviewers will look for):**
- vs. EcoServe: we do runtime multi-region routing with live CI, not single-cluster capacity planning.
- vs. SLIT: real serving engine + uncertainty-aware + provable guarantees, not metaheuristic simulation.
- vs. FREESH: we add CI forecast uncertainty handling and (optionally) KV-transport decisions; evaluation includes real deployment.
- vs. CEDAR: real deployment with live signals, uncertainty-aware routing, and marginal-carbon accounting on a stateful serving stack.
- vs. DynamoLLM family: they optimize energy within one cluster; we exploit cross-region carbon spatiotemporal diversity — complementary and composable.

**Fallback framings (if primary proves too heavy):**
- *Framing B (simulation-only but rigorous):* "Uncertainty-Aware Carbon Routing for LLM Inference" — simulation on Azure/BurstGPT traces × real historical CI data, focus on the uncertainty-aware decision rule (GAP 2) with regret analysis. Lower engineering cost, still novel.
- *Framing C (India-focused):* "Carbon-Aware LLM Serving for High-Intensity Emerging Grids" — motivation + measurement + scheduler evaluated on Indian + global regions (GAP 5). Strong novelty for regional relevance; good for IEEE India conferences/journals if targeting fast publication, but also defensible internationally.

---

## 5. System Design Sketch

**Architecture components:**
1. **Carbon Signal Service** — pulls live CI from ElectricityMaps/WattTime; forecasts 24–96h ahead using EnsembleCI (or a simpler GBM) with prediction intervals (SPCI-style conformal bands).
2. **Workload Predictor** — request-rate forecasting per (region-facing) traffic class from Azure/BurstGPT trace statistics (lightweight templates, as in DynamoLLM).
3. **Router (core):** periodic (e.g., every 5–15 min) slow-timescale region-weight computation solving:

   minimize Σ_r E[CI_r(t)] · P_r(load_r) + λ_cost · Cost_r + λ_mig · MigrationCost
   subject to: p95 TTFT ≤ T_TTFT, p99 TPOT ≤ T_TPOT, region capacity, uncertainty guard (route to region r only if lower CI bound beats incumbent's upper bound by margin δ).

4. **Fast-timescale admission/routing** — per-request queue-aware dispatch honoring the slow-timescale weights (mirrors CASPER's CAP/CAS split, adapted to LLM phases).
5. **(Stretch) KV-transport policy** — for multi-turn traffic, decide migrate/recompute/partial-ship of KV state across regions as a carbon-priced decision (unites Janus's formulation with carbon).

**Control-theoretic options:** Lyapunov drift-plus-penalty (as in Janus) for provable [O(1/V), O(V)] bounds, or CMDP + Lagrangian PPO policy (as in CEDAR) for learned policies. Recommendation: Lyapunov for the paper's guarantees + a learned policy as a compared variant.

---

## 6. Experiment Design

**Testbed options (in increasing cost):**
- **Simulator only:** custom discrete-event simulator calibrated on published vLLM/SGLang latencies and measured GPU power curves (A100/H100/L4 published numbers; DynamoLLM/TAPAS methodology). Zero hardware cost.
- **Hybrid (recommended):** simulator at scale + 2–3 real GPU VMs (e.g., cheapest GPU instances in 2–3 cloud regions) running vLLM with a 7–8B model, live CI signals, replayed traces. This alone beats every competitor's evaluation.

**Workloads (all public, CC-BY or open):**
- Azure LLM Inference Trace 2024 (Code + Conversation services, 1 week, used by DynamoLLM) — github.com/Azure/AzurePublicDataset
- Azure LLM Inference Trace 2023 (Splitwise, ISCA'24)
- BurstGPT (10.31M traces, 213 days, Azure OpenAI regional service; includes failures and burstiness) — github.com/HPMLL/BurstGPT

**Carbon data:** ElectricityMaps (live + historical API; free academic tier) or WattTime; EIA grid-monitor data for US; ENTSO-E for EU; Indian regions via ElectricityMaps (available). CarbonCast / EnsembleCI for forecast baselines (both open source).

**Baselines to compare:**
1. Performance-only routing (least-latency / round-robin) — status quo
2. Carbon-greedy routing (route to lowest point-estimate CI region) — shows the uncertainty failure mode
3. CASPER-style carbon-aware load balancing (web-service adapted)
4. SLIT (metaheuristic) — reimplement or compare on reported settings
5. CEDAR-style CMDP (if feasible)
6. Oracle (perfect CI knowledge) — upper bound on savings

**Metrics:** operational carbon (kgCO2e), energy (kWh), p50/p95/p99 TTFT and TPOT, SLO attainment %, cost ($), routing/controller overhead (ms), carbon saved per SLO-slack tradeoff curve, robustness under CI misprediction (perturbation study).

**Key experiments:**
E1: Motivation — carbon savings headroom vs. latency budget (Pareto curves per region set).
E2: End-to-end comparison vs. baselines (traces × regions × SLO settings).
E3: Uncertainty ablation — CarbonServe with/without uncertainty guard vs. carbon-greedy under realistic forecast error (inject EnsembleCI MAPE).
E4: Sensitivity — number of regions, trace burstiness, model sizes, CI volatility (including Indian grid scenarios).
E5: Overhead & scalability of the router.
E6: (If hybrid testbed) real-deployment validation with live CI.

**Statistical rigor:** repeat runs, report confidence intervals, significance tests — directly answers the "70% simulation-only, 13% statistical validation" critique in the field's systematic reviews.

---

## 7. Datasets, Tools, and Assets Inventory

| Asset | What | Where / Access |
|---|---|---|
| Azure LLM Inference Trace 2024 | 1 week, 2 services (Code, Conversation), TIMESTAMP + context/generated tokens; the DynamoLLM dataset | github.com/Azure/AzurePublicDataset (CC-BY) |
| Azure LLM Trace 2023 / LMM 2025 | Splitwise / ModServe datasets | Same repo |
| BurstGPT | 10.31M requests, 213 days, burstiness + failures + conversation patterns | github.com/HPMLL/BurstGPT |
| ElectricityMaps | Live + historical grid CI, includes Indian regions | app.electricitymaps.com (API; academic access) |
| WattTime | Marginal-emission CI signals (US) | watttime.org |
| EIA / ENTSO-E | Raw energy-mix data | Public APIs |
| CarbonCast | 96h CI forecaster (CNN-LSTM two-tier) | github.com/carbonfirst/CarbonCast |
| EnsembleCI | SOTA CI forecaster (ensemble, ~20% better MAPE than CarbonCast) | github.com/emmayly/EnsembleCI |
| vLLM / SGLang | Serving engines with P/D disaggregation support | Open source |
| Zeus | GPU energy measurement library | Open source (MLEnergy) |
| Kepler / DCGM | Node/GPU power telemetry in Kubernetes | Open source / NVIDIA |
| Carbon Explorer | Datacenter carbon accounting framework | github.com/facebookresearch/CarbonExplorer |
| CASPER / CarbonScaler code | Prior carbon-aware schedulers | github.com/carbonfirst/casper, github.com/umassos/CarbonScaler |

---

## 8. Target Venues (ranked)

**Premier (if hybrid testbed + guarantees land):**
- ACM SoCC, ACM e-Energy, ACM/IFIP Middleware, USENIX OSDI/SOSP (long shot), ACM ASPLOS (TAPAS/DynamoLLM precedent)
- IEEE flagship: **IEEE TC (Transactions on Computers), TPDS, IEEE CLOUD 2026**, IEEE ICDCS, IEEE MASCOTS

**Solid IEEE targets with strong fit:**
- **IEEE CLOUD** (primary recommendation — cloud-native scope, systems papers like this regularly appear)
- **IEEE e-Science / IC2E / CLOUDCOM** (backup tier)
- **IEEE Access** (fast, legitimate, good if timeline is tight; mid-tier impact)
- **IEEE Transactions on Sustainable Computing** (perfect topical fit for the green angle; the adaptive-DRL green cloud paper above landed there)

**Workshop route for early feedback:** ACM e-Energy student workshop, HotCarbon, EuroSys GreenSys (CEDAR precedent).

---

## 9. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| GPU budget for real testbed | Medium | Hybrid design: full evaluation in calibrated simulator; minimal 2-region live demo as proof-of-deployment; 7–8B models on cheap GPUs (T4/L4/4090) |
| Novelty squeeze vs. CEDAR/FREESH/SLIT (fast-moving area, 2025 papers) | Medium | Differentiate on: uncertainty-awareness + real deployment + guarantees + (stretch) KV-transport carbon. Framings B/C also available |
| Reviewer skepticism of simulation realism | Medium | Calibrate simulator against measured serving latencies on the real testbed; publish calibration data |
| Carbon data licensing (ElectricityMaps free tier limits) | Low | Use historical data dumps + WattTime academic access; EIA/ENTSO-E as fallback |
| Scope creep (KV-transport, water, embodied carbon) | Medium | Keep water/embodied as future work; KV-transport only as stretch goal or second paper |

---

## 10. Key Related Work to Cite (starter bibliography, ~25 core papers)

1. Stojkovic et al., "DynamoLLM," HPCA 2025. DOI: 10.1109/HPCA61900.2025.00102
2. Patel et al., "Splitwise," ISCA 2024.
3. Hanafy et al., "CarbonScaler," SIGMETRICS 2024.
4. Bashir et al., "CASPER," IGSC 2023 / arXiv:2403.14792.
5. Acun et al., "Carbon Explorer," ASPLOS 2023.
6. Radovanovic et al., "Carbon-aware computing for datacenters," 2023 (Google).
7. Sukprasert et al., "On the Limitations of Carbon-Aware Temporal and Spatial Shifting," e-Energy 2024.
8. Wiesner et al., "Sunk carbon fallacy," 2023.
9. "Uncertainty-Aware Decarbonization for Datacenters," HotCarbon 2024.
10. "EcoServe: Designing Carbon-Aware AI Inference Systems," arXiv:2502.05043, 2025.
11. Kakolyris et al. / "SLIT: Sustainable Carbon-Aware and Water-Efficient LLM Scheduling," KDD 2025 (arXiv:2505.23554).
12. "FREESH: Fair, Resource- and Energy-Efficient Scheduling for LLM Serving on Heterogeneous GPUs," arXiv:2511.00807, 2025.
13. "CEDAR: Carbon Efficient Dynamic Allocation and Routing for Agentic LLM Inference," EuroSys GreenSys 2025.
14. "GreenCache: Carbon-Aware Caching for LLM Serving," arXiv:2505.23970, 2025.
15. Gupta et al., "CarbConscious," ICIS SIGGreen 2025.
16. "VoltanaLLM," arXiv:2509.04827, 2025. / "GreenLLM," arXiv:2508.16449, 2025. / "throttLL'eM," arXiv:2408.05235, 2024.
17. Stojkovic et al., "TAPAS," ASPLOS 2025.
18. "Janus: Prefill/Decode Disaggregation with KV-Cache-Aware Multi-Cloud Routing," EAI IoT 2026.
19. Yan et al., "EnsembleCI," e-Energy 2025. / "CarbonCast," BuildSys 2022.
20. Kwon et al., "vLLM (PagedAttention)," SOSP 2023. / Zhong et al., "DistServe," OSDI 2024.
21. AzurePublicDataset + BurstGPT dataset papers (VLDB/ACM 2025).
22. "SpEC / energy-aware serving" line (optional).
23. Zhang & Chien / Wierman et al. — carbon-aware scheduling theory foundations.
24. "AI-driven resource allocation in cloud computing: systematic review," Computing (Springer), 2026 — for the motivation-gap citation (6.3% carbon-aware).
25. "Fork in the Road (AFaaS)," OSDI 2025 — adjacent context only (not core).

---

## 11. Suggested Paper Skeleton (for the drafting phase)

1. Introduction — inference carbon crisis + grid CI variability + no real carbon-aware LLM router
2. Background & Motivation — LLM serving SLOs; CI spatiotemporal diversity; measurement study of savings headroom (Azure traces × real CI data)
3. Related Work — taxonomy: carbon-aware computing / energy-efficient LLM serving / carbon-aware LLM serving (Table from Section 2 above)
4. System Design — CarbonServe architecture, formulation, control algorithm, uncertainty guard
5. Implementation — router on vLLM/SGLang; CI service; simulator calibration
6. Evaluation — E1–E6
7. Discussion — limitations, deployment considerations, marginal-carbon accounting
8. Conclusion & Future Work — KV-carbon transport, embodied carbon, water

**Estimated page budget:** 10–12 pages double-column IEEE format (IEEE CLOUD style), or 12–14 ACM format (SoCC/e-Energy style).
