SHELL := /bin/bash
PYTHON ?= python3
VENV_PY := .venv/bin/python
CDK_VERSION ?= 2.1138.0

.PHONY: setup test test-infra check synth aws-check aws-bootstrap aws-launch-dev aws-deploy-dev aws-seed-dev aws-url

setup:
	$(PYTHON) -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r requirements-dev.txt -r infrastructure/requirements-dev.txt

test:
	$(VENV_PY) -m pytest -q

test-infra:
	cd infrastructure && ../$(VENV_PY) -m pytest -q

check: test test-infra synth

synth:
	cd infrastructure && npx --yes aws-cdk@$(CDK_VERSION) synth --context environment=dev --quiet

aws-check:
	./scripts/aws_preflight.sh

aws-bootstrap:
	./scripts/aws_bootstrap.sh

aws-launch-dev:
	./scripts/aws_bootstrap.sh
	./scripts/aws_deploy.sh dev
	./scripts/aws_seed.sh dev
	./scripts/aws_outputs.sh dev

aws-deploy-dev:
	./scripts/aws_deploy.sh dev

aws-seed-dev:
	./scripts/aws_seed.sh dev

aws-url:
	./scripts/aws_outputs.sh dev
