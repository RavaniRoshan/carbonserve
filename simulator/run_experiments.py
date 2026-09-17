"""Loop over pending jobs, each in a fresh subprocess, until time budget exhausted."""
import os
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subprocess, time, json, glob
import run_one_job

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(os.environ.get("CARBONSERVE_OUT", "/scratch/work/results"), "runs_v2")
os.makedirs(RUNS, exist_ok=True)
TIME_BUDGET = 230.0
t0 = time.time()

jobs = run_one_job.build_jobs()
pending = [j["id"] for j in jobs if not os.path.exists(f"{RUNS}/{j['id']}.json")]
print(f"{len(jobs)-len(pending)}/{len(jobs)} cached; {len(pending)} pending", flush=True)

for jid in pending:
    if time.time() - t0 > TIME_BUDGET:
        print("INCOMPLETE", flush=True)
        sys.exit(0)
    try:
        p = subprocess.run([sys.executable, os.path.join(HERE, "run_one_job.py"), jid],
                           capture_output=True, text=True, timeout=280)
        tail = (p.stdout or p.stderr).strip().splitlines()[-1:] or ["(no output)"]
        print(f"({time.time()-t0:.0f}s) {tail[0]}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT {jid}", flush=True)

print("ALL_DONE" if not [j for j in jobs if not os.path.exists(f"{RUNS}/{j['id']}.json")] else "INCOMPLETE", flush=True)
