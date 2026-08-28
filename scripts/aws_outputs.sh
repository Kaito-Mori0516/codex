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
stack_name="WorldDataLens-${environment_name}-Frontend"
site_url="$(aws cloudformation describe-stacks \
  --stack-name "${stack_name}" \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue | [0]' \
  --output text)"

echo "World Data Lens: ${site_url}"
echo "Health check  : ${site_url}/api/health"
