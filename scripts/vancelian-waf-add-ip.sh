#!/usr/bin/env bash
# Ajoute une ou plusieurs IPv4 à la allowlist WAF (app + console).
# Usage: ./scripts/vancelian-waf-add-ip.sh 176.204.158.33
#        ./scripts/vancelian-waf-add-ip.sh 1.2.3.4/32 5.6.7.8/32
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
IPSET_NAME="vancelian-team-allowlist"
SCOPE="REGIONAL"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <ipv4[/32]> [ipv4[/32] ...]" >&2
  exit 1
fi

NEW=()
for ip in "$@"; do
  if [[ "$ip" != */* ]]; then
    ip="${ip}/32"
  fi
  NEW+=("$ip")
done

IPSET_ID=$(aws wafv2 list-ip-sets --scope "$SCOPE" --region "$AWS_REGION" \
  --query "IPSets[?Name=='$IPSET_NAME'].Id | [0]" --output text)
if [[ -z "$IPSET_ID" || "$IPSET_ID" == "None" ]]; then
  echo "IP set $IPSET_NAME introuvable. Lancer d'abord vancelian-finance-private-launch.sh" >&2
  exit 1
fi

LOCK=$(aws wafv2 get-ip-set --name "$IPSET_NAME" --scope "$SCOPE" --id "$IPSET_ID" --region "$AWS_REGION" --query 'LockToken' --output text)
mapfile -t CURRENT < <(aws wafv2 get-ip-set --name "$IPSET_NAME" --scope "$SCOPE" --id "$IPSET_ID" --region "$AWS_REGION" \
  --query 'IPSet.Addresses[]' --output text)

declare -A SEEN=()
MERGED=()
for c in "${CURRENT[@]}"; do
  SEEN["$c"]=1
  MERGED+=("$c")
done
for n in "${NEW[@]}"; do
  if [[ -z "${SEEN[$n]:-}" ]]; then
    SEEN["$n"]=1
    MERGED+=("$n")
  fi
done

echo "==> Mise à jour $IPSET_NAME (${#MERGED[@]} adresses)"
aws wafv2 update-ip-set \
  --name "$IPSET_NAME" \
  --scope "$SCOPE" \
  --id "$IPSET_ID" \
  --lock-token "$LOCK" \
  --region "$AWS_REGION" \
  --addresses "${MERGED[@]}" >/dev/null

printf '  '
printf '%s\n' "${MERGED[@]}" | sort | tr '\n' ' '
echo ""
echo "OK — app.vancelian.finance et console.vancelian.finance (IPv4 uniquement)"
