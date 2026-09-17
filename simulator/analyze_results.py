"""Aggregate all experiment results into tables + publication figures."""
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np, json, glob, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNS = os.path.join(os.environ.get("CARBONSERVE_OUT", "/scratch/work/results"), "runs_v2")
OUT = os.environ.get("CARBONSERVE_OUT", "/scratch/work/results")
FIG = os.environ.get("CARBONSERVE_FIG", "/workspace/outputs")
os.makedirs(FIG, exist_ok=True)

rows = []
for f in glob.glob(f"{RUNS}/*.json"):
    rows.append(json.load(open(f)))
df = pd.DataFrame(rows)
print(f"loaded {len(df)} runs")

pol_label = {"local": "Local-only", "oracle": "Oracle (perfect CI)",
             "greedy": "Carbon-greedy (point fcst)", "casper": "CASPER-style",
             "carbonserve": "CarbonServe (ours)"}

# ---------------- E2 table ----------------
e2 = df[df.exp == "E2"]
local_ref = e2[e2.policy == "local"].groupby("trace")["carbon_kg"].mean().to_dict()
tab = e2.groupby(["trace", "policy"]).agg(
    carbon_mean=("carbon_kg", "mean"), carbon_std=("carbon_kg", "std"),
    ttft=("ttft_p95_ms", "mean"), tpot=("tpot_p99_ms", "mean"),
    slo=("slo_attainment", "mean"), away=("routed_away_frac", "mean"),
    mis=("misroute_rate", "mean"), pen=("misroute_penalty_kg", "mean")).reset_index()
tab["savings_pct"] = tab.apply(
    lambda r: (1 - r.carbon_mean / local_ref[r.trace]) * 100, axis=1)
tab.to_csv(f"{OUT}/table_e2.csv", index=False)
print("\n=== TABLE E2 (mean over 3 seeds) ===")
for tr in ["conv", "code"]:
    print(f"--- trace: {tr} (local = {local_ref[tr]:.1f} kg) ---")
    for _, r in tab[tab.trace == tr].sort_values("savings_pct", ascending=False).iterrows():
        print(f"  {pol_label[r.policy]:26s} carbon={r.carbon_mean:7.1f}±{r.carbon_std or 0:5.1f} "
              f"({r.savings_pct:+5.1f}%) ttft_p95={r.ttft:5.0f}ms tpot_p99={r.tpot:4.0f}ms "
              f"slo={r.slo*100:5.1f}% away={r.away*100:4.1f}% misroute={r.mis*100:4.1f}% "
              f"penalty={r.pen:.2f}kg")

# ---------------- E3 table ----------------
e3 = df[df.exp == "E3"]
e3_local = df[(df.exp == "E2") & (df.trace == "conv") & (df.policy == "local")]["carbon_kg"].mean()
tab3 = e3.groupby(["fc_noise_scale", "policy"]).agg(
    carbon=("carbon_kg", "mean"), mis=("misroute_rate", "mean"),
    pen=("misroute_penalty_kg", "mean"), away=("routed_away_frac", "mean")).reset_index()
tab3["savings_pct"] = (1 - tab3.carbon / e3_local) * 100
tab3.to_csv(f"{OUT}/table_e3.csv", index=False)
print(f"\n=== TABLE E3 (conv, local = {e3_local:.1f} kg) ===")
for _, r in tab3.iterrows():
    print(f"  noise={r.fc_noise_scale:3.1f}x {pol_label[r.policy]:26s} savings={r.savings_pct:+5.1f}% "
          f"misroute={r.mis*100:5.1f}% penalty={r.pen:6.2f}kg away={r.away*100:4.1f}%")

# ---------------- E1 table ----------------
e1 = df[df.exp == "E1"].copy()
e1["k"] = e1["id"].str.extract(r"e1_k(\d+)_").astype(int)
e1 = e1.drop(columns=["k_regions"], errors="ignore")
tab1 = e1.pivot_table(index="k", columns="policy", values="carbon_kg")
tab1_pct = (1 - tab1.div(tab1["local"], axis=0)) * 100
tab1_pct.to_csv(f"{OUT}/table_e1.csv")
print("\n=== TABLE E1: savings % vs region count (conv) ===")
print(tab1_pct.round(1).to_string())

# ---------------- E4 table ----------------
e4 = df[df.exp == "E4"].copy()
tab4 = e4.pivot_table(index="cap_headroom", columns="policy", values="carbon_kg")
tab4_pct = (1 - tab4.div(tab4["local"], axis=0)) * 100
tab4_pct.to_csv(f"{OUT}/table_e4.csv")
print("\n=== TABLE E4: savings % vs capacity headroom (conv) ===")
print(tab4_pct.round(1).to_string())

# ================= FIGURES =================
plt.rcParams.update({"font.size": 11, "figure.dpi": 150})

# Fig 1: CI diversity motivation (needs raw data)
import carbonserve_sim as cs
ci = cs.load_ci()
week = cs.pick_week(ci)
fig, ax = plt.subplots(figsize=(10, 4.5))
for z in cs.ZONES:
    ax.plot(week.index, week[z], lw=1.1, label=z)
ax.set_ylabel("Carbon intensity (gCO$_2$/kWh)")
ax.set_xlabel("Date (May 2021, UTC)")
ax.set_title("Hourly grid carbon intensity: 11 regions (EnsembleCI/EIA/ENTSO-E data)")
ax.legend(ncol=6, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.22), frameon=False)
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(f"{FIG}/fig1_ci_diversity.png", bbox_inches="tight")
plt.close(fig)

# Fig 2: E2 bar chart (savings + risk)
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
pols = ["local", "greedy", "casper", "carbonserve", "oracle"]
lbls = [pol_label[p].replace(" (point fcst)", "") for p in pols]
for ax, trace, title in [(axes[0], "conv", "Conversation trace"),
                          (axes[1], "code", "Code trace")]:
    sav = [tab[(tab.trace == trace) & (tab.policy == p)].savings_pct.mean() for p in pols]
    mis = [tab[(tab.trace == trace) & (tab.policy == p)].mis.mean() * 100 for p in pols]
    x = np.arange(len(pols))
    b1 = ax.bar(x - 0.2, sav, 0.4, color="#2a9d8f", label="Carbon savings (%)")
    ax2 = ax.twinx()
    b2 = ax2.bar(x + 0.2, mis, 0.4, color="#e76f51", label="Misroute rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(["Local", "Greedy", "CASPER", "CarbonServe\n(ours)", "Oracle"], fontsize=9)
    ax.set_ylabel("Carbon savings vs local (%)"); ax2.set_ylabel("Misroute rate (%)")
    ax.set_title(f"{title} ({local_ref[trace]:.0f} kg CO$_2$e baseline)")
    if trace == "conv":
        ax.legend(handles=[b1, b2], labels=["Carbon savings (%)", "Misroute rate (%)"], fontsize=8, loc="upper left")
fig.suptitle("E2: Carbon savings vs routing risk (mean of 3 seeds)")
fig.tight_layout()
fig.savefig(f"{FIG}/fig2_e2_bars.png", bbox_inches="tight")
plt.close(fig)

# Fig 3: E3 uncertainty ablation (the key figure)
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
colors = {"greedy": "#e9c46a", "casper": "#e76f51", "carbonserve": "#2a9d8f", "oracle": "#6c757d"}
for pol in ["greedy", "casper", "carbonserve", "oracle"]:
    d = tab3[tab3.policy == pol].sort_values("fc_noise_scale")
    axes[0].plot(d.fc_noise_scale, d.savings_pct, "o-", color=colors[pol], label=pol_label[pol])
    axes[1].plot(d.fc_noise_scale, d.pen, "o-", color=colors[pol], label=pol_label[pol])
axes[0].set_xlabel("Forecast noise scale (x persistence σ)"); axes[0].set_ylabel("Carbon savings (%)")
axes[0].set_title("Average savings vs forecast quality")
axes[1].set_xlabel("Forecast noise scale (x persistence σ)"); axes[1].set_ylabel("Misroute penalty (kg CO$_2$e)")
axes[1].set_title("Routing backfire risk (log scale)"); axes[1].set_yscale("log")
axes[0].legend(fontsize=8)
axes[1].legend(fontsize=8)
fig.suptitle("E3: Robustness to forecast uncertainty (conv trace, 27.3M requests)")
fig.tight_layout()
fig.savefig(f"{FIG}/fig3_e3_uncertainty.png", bbox_inches="tight")
plt.close(fig)

# Fig 4: E1 region count
fig, ax = plt.subplots(figsize=(6, 4))
for pol in ["oracle", "carbonserve"]:
    d = tab1_pct[pol]
    ax.plot(d.index, d.values, "o-", color=colors[pol], label=pol_label[pol])
ax.set_xlabel("Number of regions"); ax.set_ylabel("Carbon savings (%)")
ax.set_title("E1: Savings vs fleet size (conv trace)")
ax.set_xticks([3, 5, 8, 11])
ax.legend()
fig.tight_layout()
fig.savefig(f"{FIG}/fig4_e1_regions.png", bbox_inches="tight")
plt.close(fig)

print(f"\nfigures saved to {FIG}/fig*.png")
print("tables saved to", OUT)
