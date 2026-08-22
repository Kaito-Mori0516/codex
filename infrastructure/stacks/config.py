"""Validated deployment context shared by all stacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aws_cdk import App, RemovalPolicy


@dataclass(frozen=True)
class DeploymentConfig:
    environment_name: str
    schedule_expression: str
    allowed_origins: tuple[str, ...]
    log_retention_days: int
    alarm_email: str | None
    budget_email: str | None
    monthly_budget_usd: float

    @property
    def is_production(self) -> bool:
        return self.environment_name == "prod"

    @property
    def removal_policy(self) -> RemovalPolicy:
        return RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY

    @classmethod
    def from_app(cls, app: App) -> "DeploymentConfig":
        environment_name = str(app.node.try_get_context("environment") or "dev").lower()
        if environment_name not in {"dev", "prod"}:
            raise ValueError("CDK context 'environment' must be 'dev' or 'prod'")

        schedule_expression = str(
            app.node.try_get_context("schedule_expression") or "rate(1 day)"
        )
        if not schedule_expression.startswith(("rate(", "cron(", "at(")):
            raise ValueError("schedule_expression must be an EventBridge Scheduler expression")

        raw_origins: Any = app.node.try_get_context("allowed_origins")
        if raw_origins is None:
            allowed_origins = ("*",) if environment_name == "dev" else ()
        elif isinstance(raw_origins, str):
            allowed_origins = tuple(
                origin.strip() for origin in raw_origins.split(",") if origin.strip()
            )
        else:
            allowed_origins = tuple(str(origin) for origin in raw_origins)

        log_retention_days = int(app.node.try_get_context("log_retention_days") or 14)
        if log_retention_days not in {1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365}:
            raise ValueError("log_retention_days must be supported by CloudWatch Logs")

        return cls(
            environment_name=environment_name,
            schedule_expression=schedule_expression,
            allowed_origins=allowed_origins,
            log_retention_days=log_retention_days,
            alarm_email=app.node.try_get_context("alarm_email"),
            budget_email=app.node.try_get_context("budget_email"),
            monthly_budget_usd=float(app.node.try_get_context("monthly_budget_usd") or 5),
        )
