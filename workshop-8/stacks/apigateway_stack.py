from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_lambda as _lambda,
    Fn
)
from constructs import Construct

class ApiGatewayStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
                 name_shortcut: str, certificate_arn: str, route53_zone_id: str, route53_zone_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import lambdafunctions ARNs from LambdaStack 
        delete_lambda_arn = Fn.import_value(f"wksp-{name_shortcut}-lambda-cdk-stack-delete-function-arn")
        get_lambda_arn = Fn.import_value(f"wksp-{name_shortcut}-lambda-cdk-stack-get-function-arn")
        list_lambda_arn = Fn.import_value(f"wksp-{name_shortcut}-lambda-cdk-stack-list-function-arn")
        options_lambda_arn = Fn.import_value(f"wksp-{name_shortcut}-lambda-cdk-stack-options-function-arn")
        update_lambda_arn = Fn.import_value(f"wksp-{name_shortcut}-lambda-cdk-stack-update-function-arn")

        # Import Lambda functions by their ARN
        delete_lambda = _lambda.Function.from_function_arn(self, "Delete", delete_lambda_arn)
        get_lambda = _lambda.Function.from_function_arn(self, "Get", get_lambda_arn)
        list_lambda = _lambda.Function.from_function_arn(self, "List", list_lambda_arn)
        options_lambda = _lambda.Function.from_function_arn(self, "Options", options_lambda_arn)
        update_lambda = _lambda.Function.from_function_arn(self, "Update", update_lambda_arn)
        
        apigateway_name = f"wksp-{name_shortcut}-api-cdk"

        # define API gateway:
        api = apigateway.LambdaRestApi(
            self,
            "apigateway",
            rest_api_name = apigateway_name,
            handler=list_lambda,
            proxy=False,
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            binary_media_types=["multipart/form-data", "*/*"],
            domain_name=apigateway.DomainNameOptions(
                domain_name=f"{name_shortcut}.api.{route53_zone_name}", # i.e fika.api.workshop.virtualcomputing.cz
                certificate=acm.Certificate.from_certificate_arn(
                    self, "cert", certificate_arn
                ),
                endpoint_type=apigateway.EndpointType.REGIONAL,
            ),
            disable_execute_api_endpoint=True,
        )

        productid_resource = api.root.add_resource("{ProductID}")

        def add_method(resource, method, integration=None):
            kwargs = {"http_method": method}
            if integration is not None:
                kwargs["integration"] = integration
            resource.add_method(**kwargs)

        methods = [
            {
                "resource": productid_resource,
                "http_method": "DELETE",
                "integration": apigateway.LambdaIntegration(delete_lambda)
            },
            {
                "resource": productid_resource,
                "http_method": "GET",
                "integration": apigateway.LambdaIntegration(get_lambda),
            },
            {
                "resource": productid_resource,
                "http_method": "OPTIONS",
                "integration": apigateway.LambdaIntegration(options_lambda),
            },
            {
                "resource": productid_resource,
                "http_method": "PUT",
                "integration": apigateway.LambdaIntegration(update_lambda),
            }
        ]

        for method in methods:
            add_method(
                method["resource"], method["http_method"], method.get("integration")
            )

        # add route 53 record:
        zone = route53.HostedZone.from_hosted_zone_attributes(
            self,
            "existing-zone",
            hosted_zone_id=route53_zone_id,
            zone_name=route53_zone_name,
        )
        route53.ARecord(
            self,
            "api",
            zone=zone,
            record_name=f"{name_shortcut}.api",
            target=route53.RecordTarget.from_alias(targets.ApiGateway(api)),
        )