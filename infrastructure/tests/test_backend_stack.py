import json

from aws_cdk.assertions import Match


def test_two_python_312_lambdas_and_scheduler_exist(synthesized):
    template = synthesized["backend"]
    template.resource_count_is("AWS::Lambda::Function", 2)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        Match.object_like(
            {
                "Runtime": "python3.12",
                "Handler": "src.aws_handlers.update_data_handler.handler",
                "Architectures": ["arm64"],
                "Timeout": 600,
            }
        ),
    )
    template.resource_count_is("AWS::Scheduler::ScheduleGroup", 1)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        Match.object_like(
            {
                "Runtime": "python3.12",
                "Handler": "src.aws_handlers.api_handler.handler",
                "Architectures": ["arm64"],
            }
        ),
    )
    template.has_resource_properties(
        "AWS::Scheduler::Schedule",
        Match.object_like(
            {
                    "ScheduleExpression": "rate(7 days)",
                "FlexibleTimeWindow": {"Mode": "OFF"},
            }
        ),
    )


def test_http_api_has_public_read_and_export_routes(synthesized):
    template = synthesized["backend"]
    template.has_resource_properties("AWS::ApiGatewayV2::Api", {"ProtocolType": "HTTP"})
    template.resource_count_is("AWS::ApiGatewayV2::Route", 11)
    for path in (
        "/api/health",
        "/api/summary",
        "/api/catalog",
        "/api/data",
        "/api/countries",
        "/api/indicators",
        "/api/charts/timeseries",
        "/api/charts/ranking",
        "/api/charts/overview",
        "/api/export.csv",
        "/api/export.xlsx",
    ):
        template.has_resource_properties(
            "AWS::ApiGatewayV2::Route", {"RouteKey": f"GET {path}"}
        )


def test_generated_iam_contains_no_administrator_or_destructive_data_access(synthesized):
    document = json.dumps(synthesized["backend"].to_json())
    assert "AdministratorAccess" not in document
    assert '"iam:*"' not in document
    assert "dynamodb:DeleteItem" not in document
    assert "s3:DeleteObject" not in document
