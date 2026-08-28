#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
if [[ -f "${project_dir}/infrastructure/deploy.env" ]]; then
  set -a
  source "${project_dir}/infrastructure/deploy.env"
  set +a
fi
"${script_dir}/aws_preflight.sh"

aws_region="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-northeast-1}}"
account_id="$(aws sts get-caller-identity --query Account --output text)"

cd "${project_dir}/infrastructure"
npx --yes aws-cdk@2.1138.0 bootstrap "aws://${account_id}/${aws_region}"
echo "CDK Bootstrap: 完了"
echo "次: make aws-deploy-dev"
