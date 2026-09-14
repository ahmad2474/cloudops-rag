variable "name" { type = string }
variable "subnet_id" { type = string }
variable "security_group_id" { type = string }
variable "instance_role_arn" { type = string }
variable "instance_type" { type = string }
variable "volume_size_gb" { type = number }
variable "create_service_linked_role" { type = bool }
