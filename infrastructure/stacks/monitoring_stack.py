"""CloudWatch dashboard, alarms and optional budget notifications."""

from __future__ import annotations

from aws_cdk import Duration, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions
from constructs import Construct

from stacks.config import DeploymentConfig


class MonitoringStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: DeploymentConfig,
        acquisition_function: lambda_.IFunction,
        api_function: lambda_.IFunction,
        http_api: apigwv2.CfnApi,
        schedule_group_name: str,
        distribution: cloudfront.IDistribution,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        acquisition_errors = cloudwatch.Alarm(
            self,
            "AcquisitionFailureAlarm",
            metric=acquisition_function.metric_errors(
                period=Duration.minutes(5), statistic="Sum"
            ),
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Scheduled World Bank acquisition Lambda failed",
        )
        acquisition_duration = cloudwatch.Alarm(
            self,
            "AcquisitionDurationAlarm",
            metric=acquisition_function.metric_duration(
                period=Duration.minutes(5), statistic="Maximum"
            ),
            threshold=480_000,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Acquisition Lambda is close to its ten-minute timeout",
        )
        api_errors = cloudwatch.Alarm(
            self,
            "ApiLambdaErrorAlarm",
            metric=api_function.metric_errors(period=Duration.minutes(5), statistic="Sum"),
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        api_4xx = self._api_metric(http_api.ref, "4xx")
        api_5xx = self._api_metric(http_api.ref, "5xx")
        api_5xx_alarm = cloudwatch.Alarm(
            self,
            "HttpApi5xxAlarm",
            metric=api_5xx,
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        scheduler_errors = cloudwatch.Metric(
            namespace="AWS/Scheduler",
            metric_name="TargetErrorCount",
            dimensions_map={"ScheduleGroup": schedule_group_name},
            statistic="Sum",
            period=Duration.minutes(5),
        )
        scheduler_error_alarm = cloudwatch.Alarm(
            self,
            "SchedulerTargetErrorAlarm",
            metric=scheduler_errors,
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="EventBridge Scheduler could not invoke its target",
        )
        cloudfront_5xx = distribution.metric5xx_error_rate(
            period=Duration.minutes(5), statistic="Average"
        )
        cloudfront_5xx_alarm = cloudwatch.Alarm(
            self,
            "CloudFront5xxAlarm",
            metric=cloudfront_5xx,
            threshold=5,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="CloudFront 5xx error rate stayed above 5%",
        )

        if config.alarm_email:
            topic = sns.Topic(self, "AlarmTopic")
            topic.add_subscription(
                subscriptions.EmailSubscription(str(config.alarm_email))
            )
            action = cloudwatch_actions.SnsAction(topic)
            for alarm in (
                acquisition_errors,
                acquisition_duration,
                api_errors,
                api_5xx_alarm,
                scheduler_error_alarm,
                cloudfront_5xx_alarm,
            ):
                alarm.add_alarm_action(action)

        dashboard = cloudwatch.Dashboard(
            self,
            "OperationsDashboard",
            dashboard_name=f"WorldDataLens-{config.environment_name}",
        )
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Lambda errors",
                left=[
                    acquisition_function.metric_errors(),
                    api_function.metric_errors(),
                ],
            ),
            cloudwatch.GraphWidget(
                title="Lambda duration",
                left=[
                    acquisition_function.metric_duration(statistic="Maximum"),
                    api_function.metric_duration(statistic="p95"),
                ],
            ),
            cloudwatch.GraphWidget(
                title="HTTP API responses",
                left=[api_4xx, api_5xx],
            ),
            cloudwatch.GraphWidget(
                title="Scheduler target failures",
                left=[scheduler_errors],
            ),
            cloudwatch.GraphWidget(
                title="CloudFront requests and 5xx rate",
                left=[distribution.metric_requests()],
                right=[cloudfront_5xx],
            ),
        )

        if config.budget_email:
            budgets.CfnBudget(
                self,
                "LearningBudget",
                budget=budgets.CfnBudget.BudgetDataProperty(
                    budget_limit=budgets.CfnBudget.SpendProperty(
                        amount=config.monthly_budget_usd, unit="USD"
                    ),
                    budget_name=f"WorldDataLens-{config.environment_name}",
                    budget_type="COST",
                    time_unit="MONTHLY",
                ),
                notifications_with_subscribers=[
                    budgets.CfnBudget.NotificationWithSubscribersProperty(
                        notification=budgets.CfnBudget.NotificationProperty(
                            comparison_operator="GREATER_THAN",
                            notification_type="ACTUAL",
                            threshold=80,
                            threshold_type="PERCENTAGE",
                        ),
                        subscribers=[
                            budgets.CfnBudget.SubscriberProperty(
                                address=str(config.budget_email),
                                subscription_type="EMAIL",
                            )
                        ],
                    )
                ],
            )

    @staticmethod
    def _api_metric(api_id: str, metric_name: str) -> cloudwatch.Metric:
        return cloudwatch.Metric(
            namespace="AWS/ApiGateway",
            metric_name=metric_name,
            dimensions_map={"ApiId": api_id},
            statistic="Sum",
            period=Duration.minutes(5),
        )
