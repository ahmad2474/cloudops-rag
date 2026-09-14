output "api_repository_url" { value = aws_ecr_repository.this["api"].repository_url }
output "web_repository_url" { value = aws_ecr_repository.this["web"].repository_url }
output "repository_arns" { value = [for r in aws_ecr_repository.this : r.arn] }
