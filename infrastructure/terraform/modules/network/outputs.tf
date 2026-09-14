output "vpc_id" { value = aws_vpc.this.id }
output "subnet_id" { value = aws_subnet.public.id }
output "app_sg_id" { value = aws_security_group.app.id }
output "search_sg_id" { value = aws_security_group.search.id }
