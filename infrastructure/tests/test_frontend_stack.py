from aws_cdk.assertions import Match


def test_frontend_bucket_is_private_and_cloudfront_uses_oac(synthesized):
    template = synthesized["frontend"]
    template.has_resource_properties(
        "AWS::S3::Bucket",
        Match.object_like(
            {
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": True,
                    "BlockPublicPolicy": True,
                    "IgnorePublicAcls": True,
                    "RestrictPublicBuckets": True,
                }
            }
        ),
    )
    template.resource_count_is("AWS::CloudFront::OriginAccessControl", 1)
    template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        Match.object_like(
            {
                "DistributionConfig": Match.object_like(
                    {
                        "DefaultRootObject": "index.html",
                        "Enabled": True,
                        "PriceClass": "PriceClass_100",
                        "DefaultCacheBehavior": Match.object_like(
                            {"ViewerProtocolPolicy": "redirect-to-https"}
                        ),
                    }
                )
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
                                        "Principal": {
                                            "Service": "cloudfront.amazonaws.com"
                                        },
                                        "Action": "s3:GetObject",
                                    }
                                )
                            ]
                        )
                    }
                )
            }
        ),
    )


def test_monitoring_covers_lambda_and_http_api(synthesized):
    template = synthesized["monitoring"]
    template.resource_count_is("AWS::CloudWatch::Alarm", 5)
    template.resource_count_is("AWS::CloudWatch::Dashboard", 1)
    template.resource_count_is("AWS::Budgets::Budget", 0)
