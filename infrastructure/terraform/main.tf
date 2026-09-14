# Phase 10. Intentionally empty of resources until then.
# Rules: no NAT Gateway, no OpenSearch Serverless, t3.small-class instances only,
# `terraform plan` + cost estimate + approval before every apply, destroy after demo.

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
    }
  }
}
