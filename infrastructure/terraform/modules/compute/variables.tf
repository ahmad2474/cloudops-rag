variable "name" { type = string }
variable "region" { type = string }
variable "subnet_id" { type = string }
variable "security_group_id" { type = string }
variable "instance_profile" { type = string }
variable "instance_type" { type = string }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "opensearch_endpoint" { type = string }
variable "log_group_name" { type = string }
variable "parameter_path" { type = string }
variable "auth_secret" {
  type      = string
  sensitive = true
}
variable "auth_users_json" {
  type      = string
  sensitive = true
}
variable "cors_origins" { type = string }
variable "llm_model" { type = string }
variable "embedding_model" { type = string }
variable "rerank_model" { type = string }
