#!/usr/bin/env bash
# Finalise HTTPS + CloudFront pour vancelian.finance une fois les certificats ACM ISSUED.
set -euo pipefail

ZONE_ID="${VANCELIAN_ZONE_ID:-Z091663116M960F99DPZB}"
CF_CERT_ARN="${VANCELIAN_CF_CERT_ARN:-arn:aws:acm:us-east-1:411714852748:certificate/46e5eb24-35ef-4a8e-a7fa-1f1c0a68ca66}"
ALB_CERT_ARN="${VANCELIAN_ALB_CERT_ARN:-arn:aws:acm:us-east-1:411714852748:certificate/dd9243fd-5bfa-4c04-90da-219546f4c650}"
ALB_ARN="${VANCELIAN_ALB_ARN:-arn:aws:elasticloadbalancing:us-east-1:411714852748:loadbalancer/app/vancelian-alb/1536aa6259b51090}"
TG_ARN="${VANCELIAN_TG_ARN:-arn:aws:elasticloadbalancing:us-east-1:411714852748:targetgroup/vancelian-web-tg/70ba52bfa4001c5e}"
ALB_DNS="${VANCELIAN_ALB_DNS:-vancelian-alb-1936234667.us-east-1.elb.amazonaws.com}"
CF_ALB_ZONE=Z35SXDOTRQ7X7K

wait_cert() {
  local arn=$1 name=$2
  for _ in $(seq 1 40); do
    local st
    st=$(aws acm describe-certificate --region us-east-1 --certificate-arn "$arn" --query 'Certificate.Status' --output text)
    echo "  $name: $st"
    [[ "$st" == "ISSUED" ]] && return 0
    sleep 30
  done
  echo "Timeout: certificat $name non émis" >&2
  return 1
}

echo "==> Attente certificats ACM"
wait_cert "$CF_CERT_ARN" "cloudfront"
wait_cert "$ALB_CERT_ARN" "alb"

echo "==> Listener HTTPS ALB (443)"
if ! aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query 'Listeners[?Port==`443`]' --output text | grep -q .; then
  aws elbv2 create-listener \
    --load-balancer-arn "$ALB_ARN" \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn="$ALB_CERT_ARN" \
    --default-actions Type=forward,TargetGroupArn="$TG_ARN"
fi

echo "==> Redirect HTTP -> HTTPS"
HTTP_LISTENER=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query 'Listeners[?Port==`80`].ListenerArn' --output text)
aws elbv2 modify-listener \
  --listener-arn "$HTTP_LISTENER" \
  --default-actions 'Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'

echo "==> CloudFront (si pas déjà créé)"
if [[ -z "${VANCELIAN_CF_DIST_ID:-}" ]]; then
  CALLER_REF="vancelian-finance-$(date +%s)"
  ORIGIN_ID="vancelian-alb-origin"
  TMP=$(mktemp)
  cat >"$TMP" <<JSON
{
  "CallerReference": "$CALLER_REF",
  "Comment": "Vancelian Finance vitrine",
  "Enabled": true,
  "Aliases": { "Quantity": 2, "Items": ["vancelian.finance", "www.vancelian.finance"] },
  "DefaultRootObject": "",
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "$ORIGIN_ID",
      "DomainName": "$ALB_DNS",
      "CustomOriginConfig": {
        "HTTPPort": 80,
        "HTTPSPort": 443,
        "OriginProtocolPolicy": "https-only",
        "OriginSslProtocols": { "Quantity": 1, "Items": ["TLSv1.2"] }
      }
    }]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "$ORIGIN_ID",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"], "CachedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"] } },
    "Compress": true,
    "ForwardedValues": { "QueryString": true, "Cookies": { "Forward": "all" } },
    "MinTTL": 0,
    "DefaultTTL": 0,
    "MaxTTL": 31536000
  },
  "ViewerCertificate": {
    "ACMCertificateArn": "$CF_CERT_ARN",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "PriceClass": "PriceClass_100"
}
JSON
  OUT=$(aws cloudfront create-distribution --distribution-config "file://$TMP")
  rm -f "$TMP"
  VANCELIAN_CF_DIST_ID=$(echo "$OUT" | jq -r '.Distribution.Id')
  VANCELIAN_CF_DOMAIN=$(echo "$OUT" | jq -r '.Distribution.DomainName')
  echo "CloudFront créé: $VANCELIAN_CF_DIST_ID ($VANCELIAN_CF_DOMAIN)"
else
  VANCELIAN_CF_DOMAIN=$(aws cloudfront get-distribution --id "$VANCELIAN_CF_DIST_ID" --query 'Distribution.DomainName' --output text)
fi

CF_ZONE=Z2FDTNDATAQYW2
cat > /tmp/vancelian-dns-cf.json <<EOF
{
  "Comment": "vancelian.finance -> CloudFront",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "vancelian.finance",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$CF_ZONE",
          "DNSName": "$VANCELIAN_CF_DOMAIN",
          "EvaluateTargetHealth": false
        }
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "www.vancelian.finance",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$CF_ZONE",
          "DNSName": "$VANCELIAN_CF_DOMAIN",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
EOF
aws route53 change-resource-record-sets --hosted-zone-id "$ZONE_ID" --change-batch file:///tmp/vancelian-dns-cf.json
echo "==> Terminé. Tester: https://www.vancelian.finance"
