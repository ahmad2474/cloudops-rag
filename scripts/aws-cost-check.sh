#!/usr/bin/env bash
# Month-to-date AWS spend by service (Cost Explorer, unblended, USD) plus the demo's
# tagged share. Read-only; needs ce:GetCostAndUsage (the cloudops-rag-dev user has it).
# Usage: scripts/aws-cost-check.sh [YYYY-MM-DD start]
set -euo pipefail

start="${1:-$(date -u +%Y-%m-01)}"
end="$(date -u -v+1d +%Y-%m-%d 2>/dev/null || date -u -d tomorrow +%Y-%m-%d)"

echo "AWS cost ${start} → ${end} (unblended USD)"
aws ce get-cost-and-usage \
  --time-period "Start=${start},End=${end}" \
  --granularity MONTHLY --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[0].Groups[?to_number(Metrics.UnblendedCost.Amount) > `0.0001`].[Keys[0], Metrics.UnblendedCost.Amount]' \
  --output text | sort -t$'\t' -k2 -gr | awk -F'\t' '{ printf "  %-45s %8.4f\n", $1, $2; t += $2 } END { printf "  %-45s %8.4f\n", "TOTAL", t }'

echo
echo "Tagged Project=cloudops-rag:"
aws ce get-cost-and-usage \
  --time-period "Start=${start},End=${end}" \
  --granularity MONTHLY --metrics UnblendedCost \
  --filter '{"Tags":{"Key":"Project","Values":["cloudops-rag"]}}' \
  --query 'ResultsByTime[0].Total.UnblendedCost.Amount' --output text \
  | awk '{ printf "  %8.4f USD\n", $1 }'
