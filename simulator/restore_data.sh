#!/bin/bash
# Restore all research data from public sources (idempotent).
set -e
D="${CARBONSERVE_DATA:-/scratch/work/data}"
mkdir -p "$D/ci"
mkdir -p "${CARBONSERVE_OUT:-/scratch/work/results}"
cd "$D"

# --- real hourly carbon intensity, 11 grids (EnsembleCI dataset) ---
for zone in CISO DE EPE ERCO ES ISNE MISO NL PJM PL SE; do
  [ -s ci/${zone}_direct_emissions.csv ] || curl -sL -o "ci/${zone}_direct_emissions.csv" \
    "https://raw.githubusercontent.com/emmayly/EnsembleCI/main/data/${zone}/${zone}_direct_emissions.csv"
done
echo "CI files: $(ls ci/ | wc -l)"

# --- Azure LLM inference traces (May 2024, production) ---
[ -s azure_llm_conv_1week.csv ] || curl -sL -o azure_llm_conv_1week.csv \
  "https://github.com/Azure/AzurePublicDataset/releases/download/dataset-llm-2024/AzureLLMInferenceTrace_conv_1week.csv"
[ -s azure_llm_code_1week.csv ] || curl -sL -o azure_llm_code_1week.csv \
  "https://github.com/Azure/AzurePublicDataset/releases/download/dataset-llm-2024/AzureLLMInferenceTrace_code_1week.csv"
ls -la azure_llm_*.csv

# --- convert to npz (memory-lean, timestamps are datetime64[us]!) ---
python3 << 'EOF'
import pandas as pd, numpy as np, os
for name in ['conv','code']:
    if os.path.exists(f'azure_{name}.npz'):
        print(f'azure_{name}.npz exists'); continue
    ts_list, ctx_list, gen_list = [], [], []
    for chunk in pd.read_csv(f'azure_llm_{name}_1week.csv', chunksize=4_000_000,
                             names=['ts','ctx','gen'], skiprows=1,
                             dtype={'ctx':'int32','gen':'int32'}):
        t = pd.to_datetime(chunk['ts'], format='ISO8601', cache=False)
        # datetime64[us] -> int64 microseconds -> seconds
        ts = (t.astype('int64')//10**6).to_numpy().astype(np.int64)
        assert (np.diff(ts) >= 0).all()
        ts_list.append(ts); ctx_list.append(chunk['ctx'].to_numpy()); gen_list.append(chunk['gen'].to_numpy())
        del t, ts, chunk
    t = np.concatenate(ts_list); ctx = np.concatenate(ctx_list); gen = np.concatenate(gen_list)
    del ts_list, ctx_list, gen_list
    np.savez(f'azure_{name}.npz', t=t, ctx=ctx.astype(np.int32), gen=gen.astype(np.int32))
    print(f'azure_{name}.npz: n={len(t)}, span={(t[-1]-t[0])/86400:.2f}d')
    del t, ctx, gen
EOF
echo "DATA RESTORE COMPLETE"
