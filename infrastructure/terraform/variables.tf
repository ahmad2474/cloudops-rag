variable "aws_region" {
  description = "AWS region for all resources (Bedrock Nova/Titan/Cohere are in us-east-1)."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project tag applied to every resource."
  type        = string
  default     = "cloudops-rag"
}

variable "env" {
  description = "Environment suffix; the only one is the temporary demo."
  type        = string
  default     = "demo"
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/24"
}

variable "allowed_cidr" {
  description = "CIDR allowed to reach the console (your public IP, /32). Never 0.0.0.0/0."
  type        = string

  validation {
    condition     = var.allowed_cidr != "0.0.0.0/0" && can(cidrhost(var.allowed_cidr, 0))
    error_message = "allowed_cidr must be a valid CIDR and must not be 0.0.0.0/0."
  }
}

variable "ec2_instance_type" {
  type    = string
  default = "t3.small"

  validation {
    condition     = can(regex("^t3\\.(micro|small|medium)$", var.ec2_instance_type))
    error_message = "Demo compute is limited to t3.micro/small/medium."
  }
}

variable "opensearch_instance_type" {
  type    = string
  default = "t3.small.search"

  validation {
    condition     = contains(["t3.small.search", "t3.medium.search"], var.opensearch_instance_type)
    error_message = "Only t3.small.search / t3.medium.search are allowed (no serverless, no r/m classes)."
  }
}

variable "opensearch_volume_gb" {
  type    = number
  default = 10
}

variable "create_opensearch_service_linked_role" {
  description = "Set true the first time a VPC OpenSearch domain is created in the account."
  type        = bool
  default     = false
}

variable "image_tag" {
  description = "ECR image tag to run (git short SHA from `make aws-push`)."
  type        = string
}

variable "auth_secret" {
  description = "JWT signing secret for the API (>= 32 random chars). Stored in SSM SecureString."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.auth_secret) >= 32
    error_message = "auth_secret must be at least 32 characters."
  }
}

variable "auth_users_json" {
  description = "AUTH_USERS JSON (bcrypt hashes) from `make auth-demo`. Stored in SSM SecureString."
  type        = string
  sensitive   = true
}

variable "cors_origins" {
  description = "Allowed browser origins for the API; the console is same-origin behind Caddy."
  type        = string
  default     = ""
}

variable "llm_model" {
  type    = string
  default = "amazon.nova-lite-v1:0"
}

variable "embedding_model" {
  type    = string
  default = "amazon.titan-embed-text-v2:0"
}

variable "rerank_model" {
  type    = string
  default = "cohere.rerank-v3-5:0"
}

variable "log_retention_days" {
  type    = number
  default = 7
}

variable "alarm_email" {
  description = "Email for CloudWatch alarm notifications (SNS subscription must be confirmed)."
  type        = string
}

variable "daily_cost_alarm_usd" {
  description = "EstimatedCharges alarm threshold (USD, cumulative for the month)."
  type        = number
  default     = 20
}
