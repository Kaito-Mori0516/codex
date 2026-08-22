from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template

from stacks.backend_stack import BackendStack
from stacks.config import DeploymentConfig
from stacks.data_stack import DataStack
from stacks.frontend_stack import FrontendStack
from stacks.monitoring_stack import MonitoringStack


@pytest.fixture(scope="session")
def synthesized():
    app = cdk.App(context={"environment": "dev"})
    config = DeploymentConfig.from_app(app)
    project_root = Path(__file__).resolve().parents[2]
    data = DataStack(app, "TestData", config=config)
    backend = BackendStack(
        app,
        "TestBackend",
        config=config,
        project_root=project_root,
        raw_bucket=data.raw_bucket,
        data_table=data.data_table,
    )
    frontend = FrontendStack(app, "TestFrontend", config=config)
    monitoring = MonitoringStack(
        app,
        "TestMonitoring",
        config=config,
        acquisition_function=backend.acquisition_function,
        api_function=backend.api_function,
        http_api=backend.http_api,
        schedule_group_name=backend.schedule_group.name,
    )
    return {
        "data": Template.from_stack(data),
        "backend": Template.from_stack(backend),
        "frontend": Template.from_stack(frontend),
        "monitoring": Template.from_stack(monitoring),
    }
