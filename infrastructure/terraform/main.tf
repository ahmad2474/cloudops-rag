# Phase 10 demo environment. Rules (CLAUDE.md, spec §50–53): no NAT Gateway, no OpenSearch
# Serverless, t3.small-class only, `terraform plan` → cost estimate → approval before every
# apply, `terraform destroy` right after the demo. See docs/aws.md for the cost table.

terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Env       = var.env
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  name = "${var.project}-${var.env}"
}

module "network" {
  source       = "./modules/network"
  name         = local.name
  vpc_cidr     = var.vpc_cidr
  allowed_cidr = var.allowed_cidr
}

module "registry" {
  source = "./modules/registry"
  name   = local.name
}

module "storage" {
  source     = "./modules/storage"
  name       = local.name
  account_id = data.aws_caller_identity.current.account_id
}

module "observability" {
  source               = "./modules/observability"
  name                 = local.name
  log_retention_days   = var.log_retention_days
  alarm_email          = var.alarm_email
  daily_cost_alarm_usd = var.daily_cost_alarm_usd
}

module "iam" {
  source         = "./modules/iam"
  name           = local.name
  region         = var.aws_region
  account_id     = data.aws_caller_identity.current.account_id
  bucket_arn     = module.storage.bucket_arn
  ecr_repo_arns  = module.registry.repository_arns
  log_group_arn  = module.observability.log_group_arn
  parameter_path = "/${local.name}"
  llm_model      = var.llm_model
  rerank_model   = var.rerank_model
}

module "search" {
  source                     = "./modules/search"
  name                       = local.name
  subnet_id                  = module.network.subnet_id
  security_group_id          = module.network.search_sg_id
  instance_role_arn          = module.iam.instance_role_arn
  instance_type              = var.opensearch_instance_type
  volume_size_gb             = var.opensearch_volume_gb
  create_service_linked_role = var.create_opensearch_service_linked_role
}

module "compute" {
  source              = "./modules/compute"
  name                = local.name
  region              = var.aws_region
  subnet_id           = module.network.subnet_id
  security_group_id   = module.network.app_sg_id
  instance_profile    = module.iam.instance_profile_name
  instance_type       = var.ec2_instance_type
  api_image           = "${module.registry.api_repository_url}:${var.image_tag}"
  web_image           = "${module.registry.web_repository_url}:${var.image_tag}"
  opensearch_endpoint = module.search.endpoint
  log_group_name      = module.observability.log_group_name
  parameter_path      = "/${local.name}"
  auth_secret         = var.auth_secret
  auth_users_json     = var.auth_users_json
  cors_origins        = var.cors_origins
  llm_model           = var.llm_model
  embedding_model     = var.embedding_model
  rerank_model        = var.rerank_model
}
