"""Validated deployment context shared by all stacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

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
    data_start_year: int
    world_bank_countries: str
    operator_name: str
    contact_email: str
    business_price_label: str
    business_checkout_url: str
    enterprise_contact_url: str
    sponsor_text: str
    sponsor_url: str
    adsense_client_id: str
    adsense_slot_id: str

    @property
    def is_production(self) -> bool:
        return self.environment_name == "prod"

    @property
    def removal_policy(self) -> RemovalPolicy:
        return RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY

    @property
    def public_site_config(self) -> dict[str, str]:
        return {
            "api_base_path": "/api",
            "operator_name": self.operator_name,
            "contact_email": self.contact_email,
            "business_price_label": self.business_price_label,
            "business_checkout_url": self.business_checkout_url,
            "enterprise_contact_url": self.enterprise_contact_url,
            "sponsor_text": self.sponsor_text,
            "sponsor_url": self.sponsor_url,
            "adsense_client_id": self.adsense_client_id,
            "adsense_slot_id": self.adsense_slot_id,
        }

    @classmethod
    def from_app(cls, app: App) -> "DeploymentConfig":
        environment_name = str(app.node.try_get_context("environment") or "dev").lower()
        if environment_name not in {"dev", "prod"}:
            raise ValueError("CDK context 'environment' must be 'dev' or 'prod'")

        schedule_expression = str(
            app.node.try_get_context("schedule_expression") or "rate(7 days)"
        )
        if not schedule_expression.startswith(("rate(", "cron(", "at(")):
            raise ValueError("schedule_expression must be an EventBridge Scheduler expression")

        raw_origins: Any = app.node.try_get_context("allowed_origins")
        if raw_origins is None:
            allowed_origins = ()
        elif isinstance(raw_origins, str):
            allowed_origins = tuple(
                origin.strip() for origin in raw_origins.split(",") if origin.strip()
            )
        else:
            allowed_origins = tuple(str(origin) for origin in raw_origins)

        log_retention_days = int(app.node.try_get_context("log_retention_days") or 14)
        if log_retention_days not in {1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365}:
            raise ValueError("log_retention_days must be supported by CloudWatch Logs")

        def text_context(name: str, default: str = "") -> str:
            value = app.node.try_get_context(name)
            return str(value if value is not None else default).strip()

        def url_context(name: str) -> str:
            value = text_context(name)
            if value and urlparse(value).scheme not in {"http", "https", "mailto"}:
                raise ValueError(f"{name} must be an http(s) or mailto URL")
            return value

        data_start_year = int(app.node.try_get_context("data_start_year") or 2010)
        if not 1960 <= data_start_year <= 2100:
            raise ValueError("data_start_year must be between 1960 and 2100")

        default_countries = (
            "JPN,KOR,CHN,HKG,SGP,IND,IDN,THA,VNM,PHL,AUS,NZL,USA,CAN,MEX,"
            "BRA,ARG,CHL,GBR,FRA,DEU,ITA,ESP,NLD,CHE,SWE,NOR,POL,TUR,SAU,"
            "ARE,ISR,ZAF,NGA,EGY"
        )
        return cls(
            environment_name=environment_name,
            schedule_expression=schedule_expression,
            allowed_origins=allowed_origins,
            log_retention_days=log_retention_days,
            alarm_email=app.node.try_get_context("alarm_email"),
            budget_email=app.node.try_get_context("budget_email"),
            monthly_budget_usd=float(app.node.try_get_context("monthly_budget_usd") or 5),
            data_start_year=data_start_year,
            world_bank_countries=text_context("world_bank_countries", default_countries),
            operator_name=text_context("operator_name"),
            contact_email=text_context("contact_email"),
            business_price_label=text_context("business_price_label", "個別設定"),
            business_checkout_url=url_context("business_checkout_url"),
            enterprise_contact_url=url_context("enterprise_contact_url"),
            sponsor_text=text_context("sponsor_text"),
            sponsor_url=url_context("sponsor_url"),
            adsense_client_id=text_context("adsense_client_id"),
            adsense_slot_id=text_context("adsense_slot_id"),
        )
