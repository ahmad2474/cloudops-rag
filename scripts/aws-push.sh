#!/usr/bin/env bash
# Build linux/amd64 images for the demo instance and push them to the ECR repos Terraform
# created. Prints the image tag (git short SHA) to put in environments/demo.tfvars.
set -euo pipefail
cd "$(dirname "$0")/.."

region="${AWS_REGION:-us-east-1}"
account="$(aws sts get-caller-identity --query Account --output text)"
registry="${account}.dkr.ecr.${region}.amazonaws.com"
name="${PROJECT_NAME:-cloudops-rag-demo}"
tag="$(git rev-parse --short HEAD)"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "working tree is dirty; commit first so the tag is reproducible" >&2
  exit 1
fi

aws ecr get-login-password --region "$region" | docker login --username AWS --password-stdin "$registry"

docker buildx build --platform linux/amd64 -f docker/api.Dockerfile \
  -t "${registry}/${name}/api:${tag}" --push .
docker buildx build --platform linux/amd64 -f docker/web.Dockerfile \
  --build-arg NEXT_PUBLIC_API_BASE_URL=/api \
  -t "${registry}/${name}/web:${tag}" --push .

echo
echo "image_tag = \"${tag}\""
