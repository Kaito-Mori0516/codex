#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
if [[ -f "${project_dir}/infrastructure/deploy.env" ]]; then
  set -a
  source "${project_dir}/infrastructure/deploy.env"
  set +a
fi

for command_name in aws node npx python3; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} が見つかりません。READMEの初回セットアップを確認してください。" >&2
    exit 1
  fi
done

aws_region="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-northeast-1}}"
identity_json="$(aws sts get-caller-identity --output json)"
account_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["Account"])' <<<"${identity_json}")"
principal_arn="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["Arn"])' <<<"${identity_json}")"

if [[ "${principal_arn}" == *":root" ]]; then
  echo "ERROR: rootユーザーの認証情報ではデプロイしません。IAM Identity Centerからログインしてください。" >&2
  exit 1
fi

echo "AWS接続確認: OK"
echo "Account: ${account_id}"
echo "Region : ${aws_region}"
echo "Role   : ${principal_arn}"
echo "次: make aws-bootstrap"
