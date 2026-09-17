"""Azure trace workload: stream public CSVs, map onto the CI study week.

Trace timestamps keep their weekday + time-of-day, mapped onto the CI week
(Mon 2021-05-10 .. Mon 2021-05-17). Streaming keeps memory flat for the full
44.1M-row replay; a `max_rows` cap enables fast smoke runs on a real prefix.
"""
import csv
import datetime
import os
import urllib.request

BASE = ("https://github.com/Azure/AzurePublicDataset/releases/download/"
        "dataset-llm-2024")
FILES = {"conv": "AzureLLMInferenceTrace_conv_1week.csv",
         "code": "AzureLLMInferenceTrace_code_1week.csv"}

EPOCH0 = 1620604800  # 2021-05-10 00:00:00 UTC (Monday)


def _parse_ts(s):
    return datetime.datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


def stream_requests(trace, data_dir, max_rows=None):
    """Yield (sim_epoch_s, cin, cout) in trace order. Downloads once, caches."""
    os.makedirs(os.path.join(data_dir, "azure"), exist_ok=True)
    local = os.path.join(data_dir, "azure", FILES[trace])
    if not os.path.exists(local):
        url = BASE + "/" + FILES[trace]
        req = urllib.request.Request(url, headers={"User-Agent": "carbonserve-repro/1.0"})
        with urllib.request.urlopen(req, timeout=120) as fh, open(local, "wb") as out:
            while True:
                chunk = fh.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
    n = 0
    with open(local, newline="") as f:
        for r in csv.DictReader(f):
            try:
                dt = _parse_ts(r["TIMESTAMP"])
                cin, cout = int(float(r["ContextTokens"])), int(float(r["GeneratedTokens"]))
            except (KeyError, ValueError):
                continue
            # weekday-preserving map onto CI week (both 7-day windows)
            day_off = (dt.weekday() - 0) % 7  # Monday -> 0
            sim = EPOCH0 + day_off * 86400 + dt.hour * 3600 + dt.minute * 60 + dt.second
            yield sim, max(1, cin), max(1, cout)
            n += 1
            if max_rows and n >= max_rows:
                return


def business_weights(utc_hour, grids, weekend=False):
    """Home-region weights by hour: business-hours profile per region timezone.

    weight = 0.15 base + 1.0 inside 08:00-18:00 local on weekdays; flat base
    weights on weekends (no business modulation). Normalized by caller.
    (Paper: hour-of-day business-hours profiles per region timezone.)
    """
    from .grids import TZ
    w = {}
    for g in grids:
        if weekend:
            w[g] = 0.15
        else:
            local = (utc_hour + TZ[g]) % 24
            w[g] = 0.15 + (1.0 if 8 <= local < 18 else 0.0)
    return w
