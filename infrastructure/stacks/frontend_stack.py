"""Private static-site bucket and CloudFront distribution."""

from __future__ import annotations

import json
from pathlib import Path

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3_deployment
from constructs import Construct

from stacks.config import DeploymentConfig


class FrontendStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: DeploymentConfig,
        project_root: Path,
        api_domain_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=config.is_production,
            removal_policy=config.removal_policy,
            auto_delete_objects=not config.is_production,
        )
        static_origin = origins.S3BucketOrigin.with_origin_access_control(
            self.frontend_bucket
        )
        api_origin = origins.HttpOrigin(
            api_domain_name,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
            connection_timeout=Duration.seconds(5),
            read_timeout=Duration.seconds(30),
        )
        security_headers = cloudfront.ResponseHeadersPolicy(
            self,
            "SecurityHeadersPolicy",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                content_security_policy=cloudfront.ResponseHeadersContentSecurityPolicy(
                    content_security_policy=(
                        "default-src 'self'; base-uri 'self'; object-src 'none'; "
                        "frame-ancestors 'none'; form-action 'self'; "
                        "script-src 'self' https://cdn.jsdelivr.net "
                        "https://pagead2.googlesyndication.com https://*.googlesyndication.com; "
                        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                        "font-src 'self' https://fonts.gstatic.com; "
                        "img-src 'self' data: https:; connect-src 'self' https://*.google.com "
                        "https://*.doubleclick.net; frame-src https://*.google.com "
                        "https://*.doubleclick.net https://*.googlesyndication.com; "
                        "upgrade-insecure-requests"
                    ),
                    override=True,
                ),
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(
                    override=True
                ),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY,
                    override=True,
                ),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
                    override=True,
                ),
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.days(365),
                    include_subdomains=True,
                    preload=True,
                    override=True,
                ),
                xss_protection=cloudfront.ResponseHeadersXSSProtection(
                    protection=True,
                    mode_block=True,
                    override=True,
                ),
            ),
            custom_headers_behavior=cloudfront.ResponseCustomHeadersBehavior(
                custom_headers=[
                    cloudfront.ResponseCustomHeader(
                        header="Permissions-Policy",
                        value="camera=(), microphone=(), geolocation=(), payment=()",
                        override=True,
                    )
                ]
            ),
        )
        api_cache_policy = cloudfront.CachePolicy(
            self,
            "PublicApiCachePolicy",
            min_ttl=Duration.seconds(0),
            default_ttl=Duration.minutes(5),
            max_ttl=Duration.hours(1),
            cookie_behavior=cloudfront.CacheCookieBehavior.none(),
            header_behavior=cloudfront.CacheHeaderBehavior.none(),
            query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True,
        )
        api_behavior = cloudfront.BehaviorOptions(
            origin=api_origin,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
            cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
            cache_policy=api_cache_policy,
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
            response_headers_policy=security_headers,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            compress=True,
        )
        export_behavior = cloudfront.BehaviorOptions(
            origin=api_origin,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
            cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
            response_headers_policy=security_headers,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            compress=True,
        )
        self.distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=static_origin,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                response_headers_policy=security_headers,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                compress=True,
            ),
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            http_version=cloudfront.HttpVersion.HTTP2_AND_3,
            enable_ipv6=True,
            comment=f"World Data Lens {config.environment_name} frontend",
            additional_behaviors={
                "api/export*": export_behavior,
                "api/*": api_behavior,
            },
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=404,
                    response_page_path="/404.html",
                    ttl=Duration.minutes(5),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=404,
                    response_page_path="/404.html",
                    ttl=Duration.minutes(5),
                ),
            ],
        )

        self.deployment = s3_deployment.BucketDeployment(
            self,
            "DeployFrontend",
            destination_bucket=self.frontend_bucket,
            sources=[
                s3_deployment.Source.asset(str(project_root / "frontend")),
                s3_deployment.Source.data(
                    "config.json",
                    json.dumps(config.public_site_config, ensure_ascii=False),
                ),
            ],
            distribution=self.distribution,
            distribution_paths=["/*"],
            prune=True,
            cache_control=[s3_deployment.CacheControl.from_string("public,max-age=300")],
        )

        CfnOutput(self, "FrontendBucketName", value=self.frontend_bucket.bucket_name)
        CfnOutput(
            self,
            "CloudFrontUrl",
            value=f"https://{self.distribution.distribution_domain_name}",
        )
        CfnOutput(self, "CloudFrontDistributionId", value=self.distribution.distribution_id)
