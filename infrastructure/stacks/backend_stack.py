"""Scheduled acquisition Lambda and read-only HTTP API."""

from __future__ import annotations

from pathlib import Path

from aws_cdk import CfnOutput, Duration, IgnoreMode, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_scheduler as scheduler
from constructs import Construct

from stacks.config import DeploymentConfig


LOG_RETENTION = {
    1: logs.RetentionDays.ONE_DAY,
    3: logs.RetentionDays.THREE_DAYS,
    5: logs.RetentionDays.FIVE_DAYS,
    7: logs.RetentionDays.ONE_WEEK,
    14: logs.RetentionDays.TWO_WEEKS,
    30: logs.RetentionDays.ONE_MONTH,
    60: logs.RetentionDays.TWO_MONTHS,
    90: logs.RetentionDays.THREE_MONTHS,
    120: logs.RetentionDays.FOUR_MONTHS,
    150: logs.RetentionDays.FIVE_MONTHS,
    180: logs.RetentionDays.SIX_MONTHS,
    365: logs.RetentionDays.ONE_YEAR,
}


class BackendStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: DeploymentConfig,
        project_root: Path,
        raw_bucket: s3.IBucket,
        data_table: dynamodb.ITable,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        retention = LOG_RETENTION[config.log_retention_days]
        removal_policy = config.removal_policy
        lambda_code = lambda_.Code.from_asset(
            str(project_root),
            exclude=[
                "*",
                "!src/",
                "!src/**",
                "src/**/__pycache__/",
                "src/**/*.pyc",
            ],
            ignore_mode=IgnoreMode.GIT,
        )

        acquisition_logs = logs.LogGroup(
            self,
            "AcquisitionLogGroup",
            retention=retention,
            removal_policy=removal_policy,
        )
        self.acquisition_function = lambda_.Function(
            self,
            "AcquisitionFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            handler="src.aws_handlers.update_data_handler.handler",
            code=lambda_code,
            timeout=Duration.minutes(5),
            memory_size=512,
            reserved_concurrent_executions=1,
            log_group=acquisition_logs,
            environment={
                "DATA_TABLE_NAME": data_table.table_name,
                "RAW_BUCKET_NAME": raw_bucket.bucket_name,
                "WORLD_BANK_API_BASE_URL": "https://api.worldbank.org/v2",
                "WORLD_BANK_COUNTRIES": (
                    "JPN,KOR,CHN,IND,IDN,AUS,USA,CAN,MEX,BRA,GBR,FRA,DEU,ZAF,NGA"
                ),
                "DATA_START_YEAR": "2000",
                "REQUEST_TIMEOUT_SECONDS": "20",
                "REQUEST_MAX_RETRIES": "3",
                "REQUEST_BACKOFF_FACTOR": "0.8",
                "REQUEST_INTERVAL_SECONDS": "0.5",
                "USER_AGENT": "WorldDataLens/1.0 (AWS learning project)",
            },
            description="Fetch, archive and persist World Bank indicator data",
        )
        raw_bucket.grant_put(self.acquisition_function)
        data_table.grant(
            self.acquisition_function,
            "dynamodb:GetItem",
            "dynamodb:BatchGetItem",
            "dynamodb:PutItem",
            "dynamodb:BatchWriteItem",
            "dynamodb:UpdateItem",
        )

        scheduler_role = iam.Role(
            self,
            "SchedulerInvokeRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
            description="Invokes only the World Data Lens acquisition Lambda",
        )
        self.acquisition_function.grant_invoke(scheduler_role)
        self.schedule_group = scheduler.CfnScheduleGroup(
            self,
            "AcquisitionScheduleGroup",
            name=f"world-data-lens-{config.environment_name}",
        )
        self.schedule = scheduler.CfnSchedule(
            self,
            "DailyAcquisitionSchedule",
            name=f"world-data-lens-{config.environment_name}-daily",
            group_name=self.schedule_group.name,
            description="Configurable World Bank data refresh",
            schedule_expression=config.schedule_expression,
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="OFF"
            ),
            state="ENABLED",
            target=scheduler.CfnSchedule.TargetProperty(
                arn=self.acquisition_function.function_arn,
                role_arn=scheduler_role.role_arn,
                input="{}",
                retry_policy=scheduler.CfnSchedule.RetryPolicyProperty(
                    maximum_event_age_in_seconds=3600,
                    maximum_retry_attempts=2,
                ),
            ),
        )
        self.schedule.add_resource_dependency(self.schedule_group)

        api_logs = logs.LogGroup(
            self,
            "HttpApiAccessLogGroup",
            retention=retention,
            removal_policy=removal_policy,
        )
        api_lambda_logs = logs.LogGroup(
            self,
            "ApiLambdaLogGroup",
            retention=retention,
            removal_policy=removal_policy,
        )
        self.api_function = lambda_.Function(
            self,
            "ApiFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            handler="src.aws_handlers.api_handler.handler",
            code=lambda_code,
            timeout=Duration.seconds(15),
            memory_size=256,
            log_group=api_lambda_logs,
            environment={
                "DATA_TABLE_NAME": data_table.table_name,
                "DEFAULT_INDICATOR": "SP.POP.TOTL",
            },
            description="Read-only World Data Lens API",
        )
        data_table.grant_read_data(self.api_function)

        cors = None
        if config.allowed_origins:
            cors = apigwv2.CfnApi.CorsProperty(
                allow_headers=["content-type"],
                allow_methods=["GET", "OPTIONS"],
                allow_origins=list(config.allowed_origins),
                max_age=Duration.hours(1).to_seconds(),
            )
        self.http_api = apigwv2.CfnApi(
            self,
            "HttpApi",
            name=f"world-data-lens-{config.environment_name}",
            protocol_type="HTTP",
            cors_configuration=cors,
        )
        integration = apigwv2.CfnIntegration(
            self,
            "ApiLambdaIntegration",
            api_id=self.http_api.ref,
            integration_type="AWS_PROXY",
            integration_method="POST",
            integration_uri=self.api_function.function_arn,
            payload_format_version="2.0",
            timeout_in_millis=15000,
        )
        for route_id, path in (
            ("HealthRoute", "/health"),
            ("DataRoute", "/data"),
            ("CountriesRoute", "/countries"),
            ("IndicatorsRoute", "/indicators"),
            ("TimeseriesRoute", "/charts/timeseries"),
            ("RankingRoute", "/charts/ranking"),
        ):
            apigwv2.CfnRoute(
                self,
                route_id,
                api_id=self.http_api.ref,
                route_key=f"GET {path}",
                target=f"integrations/{integration.ref}",
            )

        self.api_stage = apigwv2.CfnStage(
            self,
            "DefaultApiStage",
            api_id=self.http_api.ref,
            stage_name="$default",
            auto_deploy=True,
            access_log_settings=apigwv2.CfnStage.AccessLogSettingsProperty(
                destination_arn=api_logs.log_group_arn,
                format=json_access_log_format(),
            ),
            default_route_settings=apigwv2.CfnStage.RouteSettingsProperty(
                throttling_burst_limit=100,
                throttling_rate_limit=50,
            ),
        )
        logs.CfnResourcePolicy(
            self,
            "ApiGatewayLogDeliveryPolicy",
            policy_name=f"WorldDataLens-{config.environment_name}-ApiLogs",
            policy_document=Stack.of(self).to_json_string(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "apigateway.amazonaws.com"},
                            "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                            "Resource": f"{api_logs.log_group_arn}:*",
                        }
                    ],
                }
            ),
        )
        self.api_function.add_permission(
            "AllowHttpApiInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn=Stack.of(self).format_arn(
                service="execute-api",
                resource=self.http_api.ref,
                resource_name="*/*",
            ),
        )

        self.api_url = (
            f"https://{self.http_api.ref}.execute-api.{self.region}.{self.url_suffix}"
        )
        CfnOutput(self, "HttpApiUrl", value=self.api_url)
        CfnOutput(self, "ScheduleExpression", value=config.schedule_expression)


def json_access_log_format() -> str:
    return (
        '{"requestId":"$context.requestId","routeKey":"$context.routeKey",'
        '"status":"$context.status","responseLength":"$context.responseLength",'
        '"integrationError":"$context.integrationErrorMessage"}'
    )
