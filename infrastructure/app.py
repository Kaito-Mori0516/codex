#!/usr/bin/env python3
"""CDK application entry point. This file never performs a deployment by itself."""

from __future__ import annotations

import os
from pathlib import Path

import aws_cdk as cdk

from stacks.backend_stack import BackendStack
from stacks.config import DeploymentConfig
from stacks.data_stack import DataStack
from stacks.frontend_stack import FrontendStack
from stacks.monitoring_stack import MonitoringStack


app = cdk.App()
config = DeploymentConfig.from_app(app)
project_root = Path(__file__).resolve().parent.parent
aws_environment = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION"),
)
prefix = f"WorldDataLens-{config.environment_name}"

data = DataStack(
    app,
    f"{prefix}-Data",
    config=config,
    env=aws_environment,
    description="World Data Lens raw and query data stores",
)
backend = BackendStack(
    app,
    f"{prefix}-Backend",
    config=config,
    project_root=project_root,
    raw_bucket=data.raw_bucket,
    data_table=data.data_table,
    env=aws_environment,
    description="World Data Lens scheduled acquisition and read API",
)
frontend = FrontendStack(
    app,
    f"{prefix}-Frontend",
    config=config,
    env=aws_environment,
    description="World Data Lens private static frontend and CDN",
)
monitoring = MonitoringStack(
    app,
    f"{prefix}-Monitoring",
    config=config,
    acquisition_function=backend.acquisition_function,
    api_function=backend.api_function,
    http_api=backend.http_api,
    schedule_group_name=backend.schedule_group.name,
    env=aws_environment,
    description="World Data Lens alarms, dashboard and optional budget",
)

backend.add_stack_dependency(data)
monitoring.add_stack_dependency(backend)

for stack in (data, backend, frontend, monitoring):
    cdk.Tags.of(stack).add("Project", "WorldDataLens")
    cdk.Tags.of(stack).add("Environment", config.environment_name)
    cdk.Tags.of(stack).add("ManagedBy", "CDK")

app.synth()
