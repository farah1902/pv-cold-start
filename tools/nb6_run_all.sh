#!/usr/bin/env bash
# NB6 test forecasts, every local row in the author's order (D79: local CPU, 22 Nov 2026). Resumable: a finished part
# is never recomputed, so after any stop the same command continues where it left off. Each row logs to
# results/nb6_forecasts/logs/<row>.log; the chain stops at the first failing row.
#
#   bash tools/nb6_run_all.sh [PVSF_JOBS]        # default 6 workers for the PVSetFormer rows (memory: about 1.5 GB each)
#
# The LightGBM-based rows (LGB's 5 seeds with their calibration sets, the sensor and satellite sources) use 8 workers.
# NB5a's forecasters and the foundation-model inputs are made before (--row nb5a, --fm-inputs); rows A6a and A6b run on
# Colab (NB6_colab); then python tools/nb6_forecast.py --manifest.
set -euo pipefail
cd "$(dirname "$0")/.."
PVSF_JOBS="${1:-6}"
LOGS=results/nb6_forecasts/logs
mkdir -p "$LOGS"
run() {
  local row="$1" jobs="$2"
  echo "$(date '+%Y-%m-%d %H:%M:%S') start $row (jobs $jobs)" | tee -a "$LOGS/chain.log"
  python tools/nb6_forecast.py --row "$row" --jobs "$jobs" >> "$LOGS/$row.log" 2>&1
  echo "$(date '+%Y-%m-%d %H:%M:%S') done $row" | tee -a "$LOGS/chain.log"
}
run LGB 8
run sources 8
for row in main A4c A2 A6e A6d; do
  run "$row" "$PVSF_JOBS"
done
echo "$(date '+%Y-%m-%d %H:%M:%S') all local rows done" | tee -a "$LOGS/chain.log"
