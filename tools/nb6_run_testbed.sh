#!/usr/bin/env bash
# NB6 hidden-unit test bed forecasts (D18, D79), after the chain of tools/nb6_run_all.sh (the author's order: the
# test bed last). Resumable like the chain. Logs to results/nb6_forecasts/logs/tb_<row>.log.
#
#   bash tools/nb6_run_testbed.sh [PVSF_JOBS] [--wait]     # --wait: start only once the chain has logged "all local rows done"
#
# Since the D80 extension the test bed's main trains on the Colab GPU and skips here (unless PVSF_CPU_ROWS=1): the
# laptop runs only its NB5a and source rows, so --wait is no longer needed.
set -euo pipefail
cd "$(dirname "$0")/.."
PVSF_JOBS="${1:-6}"
LOGS=results/nb6_forecasts/logs
mkdir -p "$LOGS"
if [ "${2:-}" = "--wait" ]; then
  until grep -q "all local rows done" "$LOGS/chain.log" 2>/dev/null; do sleep 600; done
fi
run() {
  local row="$1" jobs="$2"
  echo "$(date '+%Y-%m-%d %H:%M:%S') start tb_$row (jobs $jobs)" | tee -a "$LOGS/chain.log"
  python tools/nb6_testbed.py --row "$row" --jobs "$jobs" >> "$LOGS/tb_$row.log" 2>&1
  echo "$(date '+%Y-%m-%d %H:%M:%S') done tb_$row" | tee -a "$LOGS/chain.log"
}
run nb5a 8
run sources 8
run main "$PVSF_JOBS"
echo "$(date '+%Y-%m-%d %H:%M:%S') test bed rows done" | tee -a "$LOGS/chain.log"
