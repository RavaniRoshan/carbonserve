#!/bin/bash
# Data restore: public sources only. EnsembleCI grids (~33MB) + Azure traces
# (multi-GB; streamed by the harness, never fully held in memory).
set -euo pipefail
D=${1:-data}
mkdir -p "$D/ensembleci" "$D/azure"
for g in CISO ERCO ISNE MISO PJM EPE DE ES NL PL SE; do
  mkdir -p "$D/ensembleci/$g"
  for kind in direct_emissions lifecycle_emissions; do
    f="$D/ensembleci/$g/${g}_${kind}.csv"
    if [ ! -s "$f" ]; then
      # raw.githubusercontent rate-limits bursts: fail loudly, back off
      sleep 10
      curl -sfL --retry 4 --retry-delay 15 --retry-all-errors \
        "https://raw.githubusercontent.com/emmayly/EnsembleCI/main/data/$g/${g}_${kind}.csv" -o "$f"
    fi
  done
done
echo "ensembleci restored under $D/ensembleci"
echo "azure traces fetch on first run (cached under $D/azure)"
