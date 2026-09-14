output "console_url" {
  description = "Open this from the allowed_cidr address."
  value       = "http://${module.compute.public_ip}"
}

output "instance_id" {
  description = "Use with `aws ssm start-session --target <id>` (no SSH)."
  value       = module.compute.instance_id
}

output "opensearch_endpoint" {
  value = module.search.endpoint
}

output "ecr_api_repository" {
  value = module.registry.api_repository_url
}

output "ecr_web_repository" {
  value = module.registry.web_repository_url
}

output "corpus_bucket" {
  value = module.storage.bucket_name
}

output "log_group" {
  value = module.observability.log_group_name
}
