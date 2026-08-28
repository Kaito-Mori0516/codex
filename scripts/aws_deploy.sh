#!/usr/bin/env bash
set -euo pipefail

environment_name="${1:-dev}"
if [[ "${environment_name}" != "dev" && "${environment_name}" != "prod" ]]; then
  echo "Usage: $0 dev|prod" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
if [[ -f "${project_dir}/infrastructure/deploy.env" ]]; then
  set -a
  source "${project_dir}/infrastructure/deploy.env"
  set +a
fi
"${script_dir}/aws_preflight.sh"

operator_name="${WDL_OPERATOR_NAME:-}"
contact_email="${WDL_CONTACT_EMAIL:-}"
if [[ "${environment_name}" == "prod" && ( -z "${operator_name}" || -z "${contact_email}" ) ]]; then
  echo "ERROR: prod公開前にWDL_OPERATOR_NAMEとWDL_CONTACT_EMAILを設定してください。" >&2
  exit 1
fi

context_args=(
  --context "environment=${environment_name}"
  --context "operator_name=${operator_name}"
  --context "contact_email=${contact_email}"
  --context "business_price_label=${WDL_BUSINESS_PRICE_LABEL:-個別設定}"
  --context "business_checkout_url=${WDL_BUSINESS_CHECKOUT_URL:-}"
  --context "enterprise_contact_url=${WDL_ENTERPRISE_CONTACT_URL:-}"
  --context "sponsor_text=${WDL_SPONSOR_TEXT:-}"
  --context "sponsor_url=${WDL_SPONSOR_URL:-}"
  --context "adsense_client_id=${WDL_ADSENSE_CLIENT_ID:-}"
  --context "adsense_slot_id=${WDL_ADSENSE_SLOT_ID:-}"
  --context "alarm_email=${WDL_ALARM_EMAIL:-}"
  --context "budget_email=${WDL_BUDGET_EMAIL:-}"
)

cd "${project_dir}"
make check
cd infrastructure
npx --yes aws-cdk@2.1138.0 deploy --all "${context_args[@]}" --require-approval broadening

echo "AWSデプロイ: 完了"
echo "次: ${project_dir}/scripts/aws_seed.sh ${environment_name}"
