"""Persistent raw-data and query-data resources."""

from __future__ import annotations

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_s3 as s3
from constructs import Construct

from stacks.config import DeploymentConfig


class DataStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: DeploymentConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.raw_bucket = s3.Bucket(
            self,
            "RawDataBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=config.is_production,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireReproducibleRawData",
                    enabled=True,
                    expiration=Duration.days(365 if config.is_production else 90),
                    noncurrent_version_expiration=(
                        Duration.days(90) if config.is_production else None
                    ),
                )
            ],
            removal_policy=config.removal_policy,
            auto_delete_objects=not config.is_production,
        )

        self.data_table = dynamodb.Table(
            self,
            "IndicatorDataTable",
            partition_key=dynamodb.Attribute(
                name="pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=config.is_production
            ),
            deletion_protection=config.is_production,
            removal_policy=config.removal_policy,
        )
        self.data_table.add_global_secondary_index(
            index_name="indicator-year-index",
            partition_key=dynamodb.Attribute(
                name="gsi1pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="gsi1sk", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        CfnOutput(self, "RawBucketName", value=self.raw_bucket.bucket_name)
        CfnOutput(self, "DataTableName", value=self.data_table.table_name)
