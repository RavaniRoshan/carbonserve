"""Run ONE experiment job by id (fresh process, avoids memory fragmentation).
Usage: python3 run_one_job.py <job_id>"""
import os
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carbonserve_sim as cs
import numpy as np, json, os, time

def build_jobs():
    jobs = []
    for trace in ["conv", "code"]:
        for seed in [42, 7, 123]:
            for pol in ["local", "oracle", "greedy", "casper", "carbonserve"]:
                jobs.append(dict(id=f"e2_{trace}_{pol}_s{seed}", exp="E2", trace=trace,
                                 pol=pol, seed=seed, fc_noise_scale=1.0, k_regions=None))
    for scale in [0.5, 1.0, 2.0, 4.0]:
        for pol in ["greedy", "casper", "carbonserve", "oracle"]:
            jobs.append(dict(id=f"e3_conv_{pol}_n{scale}", exp="E3", trace="conv",
                             pol=pol, seed=42, fc_noise_scale=scale, k_regions=None))
    for k in [3, 5, 8, 11]:
        regs = list(np.random.default_rng(0).choice(cs.ZONES, size=k, replace=False))
        for pol in ["local", "oracle", "carbonserve"]:
            jobs.append(dict(id=f"e1_k{k}_{pol}", exp="E1", trace="conv",
                             pol=pol, seed=42, fc_noise_scale=1.0, k_regions=regs))
    for hr in [1.5, 2.5, 4.0]:
        for pol in ["local", "oracle", "carbonserve"]:
            jobs.append(dict(id=f"e4_h{hr}_{pol}", exp="E4", trace="conv",
                             pol=pol, seed=42, fc_noise_scale=1.0, k_regions=None,
                             cap_headroom=hr))
    return jobs

def main():
    job_id = sys.argv[1]
    job = next(j for j in build_jobs() if j["id"] == job_id)
    ci = cs.load_ci()
    week = cs.pick_week(ci)
    fc = cs.persistence_forecast(ci, week.index)
    sig = cs.persistence_sigma(ci)
    cs.CAP_HEADROOM = job.get("cap_headroom", 2.5)
    r = cs.simulate(job["pol"], job["trace"], week, fc, sig,
                    seed=job["seed"], fc_noise_scale=job["fc_noise_scale"],
                    regions=job["k_regions"] or cs.ZONES)
    r.update(job)
    out = f"{cs.OUT}/runs_v2/{job['id']}.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(r, open(out, "w"), indent=1, default=str)
    print(f"OK {job['id']}: carbon={r['carbon_kg']:.1f}kg "
          f"misroute={r.get('misroute_rate', 0)*100:.1f}% penalty={r.get('misroute_penalty_kg', 0):.2f}kg")

if __name__ == "__main__":
    main()
