# Managed OpenSearch, single t3.small.search node in the VPC (spec §52: $25–50 envelope; the
# hourly rate is the number to watch — see docs/aws.md). No fine-grained access control: the
# domain access policy trusts the instance role and requests are SigV4-signed
# (OPENSEARCH_AUTH=sigv4 in the API).

resource "aws_iam_service_linked_role" "es" {
  count            = var.create_service_linked_role ? 1 : 0
  aws_service_name = "opensearchservice.amazonaws.com"
}

resource "aws_opensearch_domain" "this" {
  domain_name    = var.name
  engine_version = "OpenSearch_2.19"

  cluster_config {
    instance_type          = var.instance_type
    instance_count         = 1
    zone_awareness_enabled = false
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.volume_size_gb
  }

  vpc_options {
    subnet_ids         = [var.subnet_id]
    security_group_ids = [var.security_group_id]
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
  }

  software_update_options {
    auto_software_update_enabled = false
  }

  depends_on = [aws_iam_service_linked_role.es]
}

data "aws_iam_policy_document" "access" {
  statement {
    actions   = ["es:ESHttp*"]
    resources = ["${aws_opensearch_domain.this.arn}/*"]
    principals {
      type        = "AWS"
      identifiers = [var.instance_role_arn]
    }
  }
}

resource "aws_opensearch_domain_policy" "this" {
  domain_name     = aws_opensearch_domain.this.domain_name
  access_policies = data.aws_iam_policy_document.access.json
}
