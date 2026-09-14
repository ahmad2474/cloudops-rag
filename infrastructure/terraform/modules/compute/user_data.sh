#!/bin/bash
# Rendered by Terraform (templatefile). Installs Docker, pulls the two images from ECR,
# writes /opt/cloudops/{.env,compose.yml,Caddyfile} and starts the stack.
set -euo pipefail
exec > >(tee /var/log/cloudops-user-data.log) 2>&1

dnf install -y docker
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

install -d -m 0750 /opt/cloudops
cd /opt/cloudops

cat > compose.yml <<'YAML'
${compose}
YAML

cat > Caddyfile <<'CADDY'
${caddyfile}
CADDY

# Secrets come from SSM at boot; the rest of the app env is rendered by Terraform.
auth_secret=$(aws ssm get-parameter --region "${region}" --with-decryption \
  --name "${parameter_path}/AUTH_SECRET" --query Parameter.Value --output text)
auth_users=$(aws ssm get-parameter --region "${region}" --with-decryption \
  --name "${parameter_path}/AUTH_USERS" --query Parameter.Value --output text)

umask 077
cat > .env <<ENV
${app_env}
AUTH_SECRET=$auth_secret
AUTH_USERS=$auth_users
ENV

cat > .compose.env <<ENV
AWS_REGION=${region}
LOG_GROUP=${log_group}
API_IMAGE=${api_image}
WEB_IMAGE=${web_image}
ENV

registry=$(echo "${api_image}" | cut -d/ -f1)
aws ecr get-login-password --region "${region}" | docker login --username AWS --password-stdin "$registry"

docker compose --env-file .compose.env -f compose.yml pull
docker compose --env-file .compose.env -f compose.yml up -d
echo "cloudops demo stack started"
