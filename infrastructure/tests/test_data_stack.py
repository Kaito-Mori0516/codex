import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from stacks.config import DeploymentConfig
from stacks.data_stack import DataStack


def test_raw_bucket_is_private_encrypted_and_disposable_in_dev(synthesized):
    template = synthesized["data"]
    template.has_resource_properties(
        "AWS::S3::Bucket",
        Match.object_like(
            {
                "BucketEncryption": {
                    "ServerSideEncryptionConfiguration": [
                        {
                            "ServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "AES256"
                            }
                        }
                    ]
                },
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": True,
                    "BlockPublicPolicy": True,
                    "IgnorePublicAcls": True,
                    "RestrictPublicBuckets": True,
                },
                "LifecycleConfiguration": Match.object_like(
                    {"Rules": Match.array_with([Match.object_like({"ExpirationInDays": 90})])}
                ),
            }
        ),
    )
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        Match.object_like(
            {
                "PolicyDocument": Match.object_like(
                    {
                        "Statement": Match.array_with(
                            [
                                Match.object_like(
                                    {
                                        "Effect": "Deny",
                                        "Condition": {
                                            "Bool": {"aws:SecureTransport": "false"}
                                        },
                                    }
                                )
                            ]
                        )
                    }
                )
            }
        ),
    )


def test_dynamodb_uses_on_demand_and_one_access_pattern_gsi(synthesized):
    synthesized["data"].has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "BillingMode": "PAY_PER_REQUEST",
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            "GlobalSecondaryIndexes": [
                Match.object_like(
                    {
                        "IndexName": "indicator-year-index",
                        "KeySchema": [
                            {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                            {"AttributeName": "gsi1sk", "KeyType": "RANGE"},
                        ],
                    }
                )
            ],
            "SSESpecification": {"SSEEnabled": True},
        },
    )


def test_prod_retains_and_protects_persistent_data():
    app = cdk.App(context={"environment": "prod"})
    config = DeploymentConfig.from_app(app)
    template = Template.from_stack(DataStack(app, "ProdData", config=config))
    resources = template.to_json()["Resources"]
    bucket = next(value for value in resources.values() if value["Type"] == "AWS::S3::Bucket")
    table = next(value for value in resources.values() if value["Type"] == "AWS::DynamoDB::Table")

    assert bucket["DeletionPolicy"] == "Retain"
    assert bucket["Properties"]["VersioningConfiguration"]["Status"] == "Enabled"
    assert table["DeletionPolicy"] == "Retain"
    assert table["Properties"]["DeletionProtectionEnabled"] is True
    assert table["Properties"]["PointInTimeRecoverySpecification"][
        "PointInTimeRecoveryEnabled"
    ] is True
