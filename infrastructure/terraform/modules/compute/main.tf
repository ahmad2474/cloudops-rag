# One Amazon Linux 2023 t3.small running Caddy + API + web under Docker Compose. Secrets are
# SSM SecureStrings read at boot by user_data.sh; nothing sensitive is in user-data itself.

data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_ssm_parameter" "auth_secret" {
  name  = "${var.parameter_path}/AUTH_SECRET"
  type  = "SecureString"
  value = var.auth_secret
}

resource "aws_ssm_parameter" "auth_users" {
  name  = "${var.parameter_path}/AUTH_USERS"
  type  = "SecureString"
  value = var.auth_users_json
}

locals {
  app_env = {
    APP_ENV                 = "aws"
    AWS_REGION              = var.region
    ALLOW_AWS_CALLS         = "true"
    LLM_PROVIDER            = "bedrock"
    LLM_MODEL               = var.llm_model
    EMBEDDING_PROVIDER      = "bedrock"
    EMBEDDING_MODEL         = var.embedding_model
    RERANKER_PROVIDER       = "bedrock"
    RERANKER_MODEL          = var.rerank_model
    RERANK_ENABLED          = "true"
    RETRIEVAL_STRATEGY      = "hybrid_rrf"
    SEARCH_PROVIDER         = "opensearch"
    OPENSEARCH_URL          = var.opensearch_endpoint
    OPENSEARCH_AUTH         = "sigv4"
    OPENSEARCH_INDEX_PREFIX = "cloudops"
    CORS_ORIGINS            = var.cors_origins
    AUTH_ALLOW_ROLE_HEADER  = "false"
  }
}

resource "aws_instance" "this" {
  ami                         = data.aws_ssm_parameter.al2023.value
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [var.security_group_id]
  iam_instance_profile        = var.instance_profile
  associate_public_ip_address = true
  monitoring                  = false

  metadata_options {
    http_tokens   = "required" # IMDSv2 only
    http_endpoint = "enabled"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    delete_on_termination = true
  }

  user_data = templatefile("${path.module}/user_data.sh", {
    region         = var.region
    api_image      = var.api_image
    web_image      = var.web_image
    log_group      = var.log_group_name
    parameter_path = var.parameter_path
    app_env        = join("\n", [for k, v in local.app_env : "${k}=${v}"])
    compose        = file("${path.module}/../../../../deploy/compose.demo.yml")
    caddyfile      = file("${path.module}/../../../../deploy/Caddyfile")
  })
  user_data_replace_on_change = true

  tags = { Name = var.name }

  lifecycle {
    ignore_changes = [ami]
  }
}
