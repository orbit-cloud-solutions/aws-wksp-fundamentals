from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    RemovalPolicy,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class EcsAlbStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 name_shortcut: str, ecr_repository_arn: str, container_uri: str,
                 container_port: int, app_certificate_arn: str, vpc_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Fetch the existing VPC
        vpc = ec2.Vpc.from_lookup(self, "ExistingVpc", vpc_id=vpc_id)

        # Create an ECS cluster in the VPC
        cluster = ecs.Cluster(
            self,
            f"{name_shortcut}-ecs-cluster",
            vpc=vpc,
            cluster_name=f"wksp-{name_shortcut}-ecs-cluster-cdk",
        )

        # Import the ECR repository
        repository = ecr.Repository.from_repository_arn(
            self, f"{name_shortcut}-ecr-repo", ecr_repository_arn
        )

        ecs_execution_role = iam.Role(
            scope=self,
            id="CoreECSExecutionRole",
            role_name=f"wksp-{name_shortcut}-ecs-execution-role-cdk",
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    scope=self,
                    id="AmazonECSTaskExecutionRolePolicy",
                    managed_policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
                )
            ],
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ecs.amazonaws.com"),
                iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            ),
        )

        log_group = logs.LogGroup(
            self,
            "LogGroup",
            log_group_name=f"wksp-{name_shortcut}-ecs-log-group-cdk",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
        )