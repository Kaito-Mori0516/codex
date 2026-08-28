#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
if [[ -f "${project_dir}/infrastructure/deploy.env" ]]; then
  set -a
  source "${project_dir}/infrastructure/deploy.env"
  set +a
fi

environment_name="${1:-dev}"
stack_name="WorldDataLens-${environment_name}-Backend"
function_name="$(aws cloudformation describe-stacks \
  --stack-name "${stack_name}" \
  --query 'Stacks[0].Outputs[?OutputKey==`AcquisitionFunctionName`].OutputValue | [0]' \
  --output text)"

if [[ -z "${function_name}" || "${function_name}" == "None" ]]; then
  echo "ERROR: ${stack_name} の取得Lambdaが見つかりません。" >&2
  exit 1
fi

result_file="$(mktemp)"
trap 'rm -f "${result_file}"' EXIT
aws lambda invoke \
  --function-name "${function_name}" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  "${result_file}" >/dev/null

python3 -m json.tool "${result_file}"
echo "初回データ取得: 完了"
echo "URL確認: ./scripts/aws_outputs.sh ${environment_name}"
