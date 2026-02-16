#!/usr/bin/env bash
# DataGod — Terraform deploy wrapper
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TF_DIR="$SCRIPT_DIR/../terraform"

# ─── Usage ─────────────────────────────────────────────────────────────
usage() {
  echo "Usage: $0 <environment> [plan|apply|destroy]"
  echo "  environment: staging | production"
  echo "  action:      plan (default) | apply | destroy"
  exit 1
}

ENV="${1:-}"
ACTION="${2:-plan}"

if [[ -z "$ENV" ]] || [[ ! "$ENV" =~ ^(staging|production)$ ]]; then
  usage
fi

if [[ ! "$ACTION" =~ ^(plan|apply|destroy)$ ]]; then
  usage
fi

# ─── Safety check for production destroy ───────────────────────────────
if [[ "$ACTION" == "destroy" && "$ENV" == "production" ]]; then
  echo "⚠️  WARNING: You are about to DESTROY production infrastructure!"
  read -p "Type 'yes-destroy-production' to confirm: " CONFIRM
  if [[ "$CONFIRM" != "yes-destroy-production" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

# ─── Variables file ────────────────────────────────────────────────────
VAR_FILE="$TF_DIR/envs/${ENV}.tfvars"
VAR_ARGS=""
if [[ -f "$VAR_FILE" ]]; then
  VAR_ARGS="-var-file=$VAR_FILE"
fi

# ─── Run Terraform ─────────────────────────────────────────────────────
echo "🚀 DataGod Deploy — Environment: $ENV, Action: $ACTION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$TF_DIR"

echo "► terraform init..."
terraform init -backend-config="key=infrastructure/${ENV}/terraform.tfstate"

case "$ACTION" in
  plan)
    echo "► terraform plan..."
    terraform plan -var="environment=$ENV" $VAR_ARGS -out="${ENV}.tfplan"
    echo ""
    echo "✅ Plan saved to ${ENV}.tfplan"
    echo "   To apply: $0 $ENV apply"
    ;;
  apply)
    if [[ -f "${ENV}.tfplan" ]]; then
      echo "► terraform apply (from saved plan)..."
      terraform apply "${ENV}.tfplan"
    else
      echo "► terraform apply..."
      terraform apply -var="environment=$ENV" $VAR_ARGS -auto-approve
    fi
    echo ""
    echo "✅ Deploy complete!"
    terraform output
    ;;
  destroy)
    echo "► terraform destroy..."
    terraform destroy -var="environment=$ENV" $VAR_ARGS -auto-approve
    echo ""
    echo "🗑️  Infrastructure destroyed."
    ;;
esac
